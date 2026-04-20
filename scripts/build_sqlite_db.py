"""
build_sqlite_db.py - Build the SnakeScale sqlite input database from metadata.csv.

Decision anchors:
  D1: matched_experiment_id / metadata_srr.experiment_id use integer foreign keys
  D2: Pre-allocate deterministic integer ids without AUTOINCREMENT
  D3: threep_adapter missing values become empty strings
  D4: Do not build unitmetadata_* tables
  D5: Keep OPTIONAL column names in DDL and leave their values NULL
  D6: Drop Ribo-Seq experiments whose matched RNA-Seq alias is missing or unresolvable
  D7: Keep unsupported-organism studies in sqlite and only flag them in the audit
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd
import yaml


DEFAULT_METADATA_CSV = Path("data/raw/metadata.csv")
DEFAULT_REFERENCES_YAML = Path("vendor/snakescale/scripts/references.yaml")
DEFAULT_OUTPUT_DB = Path("data/interim/snakescale/db.sqlite3")
DEFAULT_DROP_LOG = Path("data/interim/snakescale/etl_drop_log.csv")

REQUIRED_SOURCE_COLUMNS = [
    "run",
    "experiment_alias",
    "study_name",
    "corrected_type",
    "organism",
    "threep_adapter",
]

DDL_FULL = """
CREATE TABLE metadata_study (
    id INTEGER PRIMARY KEY,
    creation_date TEXT,
    notes TEXT,
    metadata_checked TEXT,
    modifier TEXT,
    geo_accession TEXT NOT NULL,
    study_accession TEXT,
    study_title TEXT,
    study_type TEXT,
    study_abstract TEXT,
    study_description TEXT,
    xref_link TEXT,
    submission_accession TEXT,
    sradb_updated TEXT,
    soft_deleted TEXT
);
CREATE INDEX idx_study_geo ON metadata_study(geo_accession);

CREATE TABLE metadata_experiment (
    id INTEGER PRIMARY KEY,
    creation_date TEXT,
    notes TEXT,
    metadata_checked TEXT,
    modifier TEXT,
    study_id INTEGER NOT NULL,
    matched_experiment_id INTEGER,
    experiment_alias TEXT NOT NULL,
    experiment_accession TEXT,
    type TEXT NOT NULL,
    title TEXT,
    study_name TEXT,
    design_description TEXT,
    sample_accession TEXT,
    sample_attribute TEXT,
    library_strategy TEXT,
    library_layout TEXT,
    library_construction_protocol TEXT,
    platform TEXT,
    platform_parameters TEXT,
    xref_link TEXT,
    experiment_attribute TEXT,
    submission_accession TEXT,
    sradb_updated TEXT,
    organism TEXT NOT NULL,
    cell_line TEXT,
    "group" TEXT,
    threep_adapter TEXT NOT NULL DEFAULT '',
    fivep_adapter TEXT,
    threep_umi_length INTEGER,
    fivep_umi_length INTEGER,
    read_length TEXT,
    is_paired_end TEXT,
    experiment_file TEXT
);
CREATE INDEX idx_exp_study_id ON metadata_experiment(study_id);
CREATE INDEX idx_exp_alias ON metadata_experiment(experiment_alias);
CREATE INDEX idx_exp_type ON metadata_experiment(type);
CREATE INDEX idx_exp_matched_id ON metadata_experiment(matched_experiment_id);

CREATE TABLE metadata_srr (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sra_accession TEXT NOT NULL,
    experiment_id INTEGER NOT NULL,
    creation_date TEXT
);
CREATE INDEX idx_srr_exp_id ON metadata_srr(experiment_id);
CREATE INDEX idx_srr_acc ON metadata_srr(sra_accession);
"""


@dataclass
class BuildArtifacts:
    study_df: pd.DataFrame
    experiment_internal_df: pd.DataFrame
    experiment_out_df: pd.DataFrame
    srr_df: pd.DataFrame
    drop_log_df: pd.DataFrame
    dropped_experiment_df: pd.DataFrame
    dropped_study_df: pd.DataFrame
    organism_audit_df: pd.DataFrame
    blocked_study_df: pd.DataFrame
    supported_organisms: list[str]
    skipped_run_rows: int
    smoke_candidate: dict[str, Any] | None


def load_metadata(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, skiprows=[0])
    for column in REQUIRED_SOURCE_COLUMNS:
        if column not in df.columns:
            raise AssertionError(f"missing source col: {column}")

    return df.copy()


def load_supported_organisms(path: Path) -> list[str]:
    with path.open() as handle:
        contents = yaml.safe_load(handle)

    if not isinstance(contents, dict):
        raise ValueError("references.yaml must contain a top-level mapping")

    return sorted(str(key).lower().strip() for key in contents.keys())


def normalize_organism(raw_value: Any) -> tuple[str, bool, str]:
    original = "" if pd.isna(raw_value) else str(raw_value).strip()
    normalized = original.lower().strip()
    is_hybrid = "_x_" in normalized or "*" in normalized

    if normalized == "rat":
        normalized = "rattus norvegicus"

    note = ""
    if is_hybrid:
        note = "hybrid/multi-species"

    return normalized, is_hybrid, note


def build_organism_audit(
    metadata_df: pd.DataFrame, supported_organisms: list[str]
) -> tuple[pd.DataFrame, pd.DataFrame]:
    supported_set = set(supported_organisms)
    audit_df = metadata_df.copy()
    normalized_info = audit_df["organism"].apply(normalize_organism)
    audit_df["normalized"] = normalized_info.map(lambda item: item[0])
    audit_df["is_hybrid"] = normalized_info.map(lambda item: item[1])
    audit_df["coverage_note"] = normalized_info.map(lambda item: item[2])
    audit_df["supported"] = audit_df["normalized"].isin(supported_set) & ~audit_df["is_hybrid"]

    organism_summary = (
        audit_df.groupby(["organism", "normalized", "supported"], dropna=False)
        .agg(
            sample_count=("run", "size"),
            experiment_count=("experiment_alias", "nunique"),
            study_count=("study_name", "nunique"),
        )
        .reset_index()
        .sort_values(
            ["sample_count", "experiment_count", "study_count", "organism"],
            ascending=[False, False, False, True],
        )
        .reset_index(drop=True)
    )

    blocked_df = audit_df[~audit_df["supported"]].copy()
    blocked_summary = (
        blocked_df.groupby(
            ["study_name", "organism", "normalized", "coverage_note"], dropna=False
        )
        .agg(
            ribo_seq_sample_count=(
                "corrected_type",
                lambda values: int((values == "Ribo-Seq").sum()),
            ),
            rnaseq_sample_count=(
                "corrected_type",
                lambda values: int((values == "RNA-Seq").sum()),
            ),
        )
        .reset_index()
        .sort_values(
            ["study_name", "ribo_seq_sample_count", "rnaseq_sample_count", "organism"],
            ascending=[True, False, False, True],
        )
        .reset_index(drop=True)
    )
    blocked_summary["coverage_note"] = blocked_summary["coverage_note"].replace("", "not in references.yaml")

    return organism_summary, blocked_summary


def _resolve_preliminary_drop_reason(
    row: pd.Series, alias_to_pre_id: dict[str, int], alias_to_type: dict[str, str]
) -> str | None:
    if row["corrected_type"] != "Ribo-Seq":
        return None

    matched_alias = row.get("matched_RNA-seq_experiment_alias")
    if pd.isna(matched_alias) or str(matched_alias).strip() in {"", "NA"}:
        return "matched_RNA-Seq missing"

    matched_alias = str(matched_alias).strip()
    if matched_alias not in alias_to_pre_id:
        return "matched_RNA-Seq unresolvable"

    if alias_to_type.get(matched_alias) != "RNA-Seq":
        return "matched target is not RNA-Seq"

    return None


def build_sqlite_inputs(metadata_df: pd.DataFrame, supported_organisms: list[str]) -> BuildArtifacts:
    organism_audit_df, blocked_study_df = build_organism_audit(metadata_df, supported_organisms)

    experiment_seed_df = (
        metadata_df.sort_values(["study_name", "experiment_alias", "run"], na_position="last")
        .drop_duplicates(subset=["experiment_alias"], keep="first")
        .copy()
    )
    experiment_seed_df["study_name"] = experiment_seed_df["study_name"].astype(str).str.strip()
    experiment_seed_df = experiment_seed_df.sort_values(["study_name", "experiment_alias"]).reset_index(drop=True)
    experiment_seed_df["pre_id"] = experiment_seed_df.index + 1

    alias_to_pre_id = dict(zip(experiment_seed_df["experiment_alias"], experiment_seed_df["pre_id"]))
    alias_to_type = dict(zip(experiment_seed_df["experiment_alias"], experiment_seed_df["corrected_type"]))

    experiment_seed_df["drop_reason"] = experiment_seed_df.apply(
        _resolve_preliminary_drop_reason,
        axis=1,
        alias_to_pre_id=alias_to_pre_id,
        alias_to_type=alias_to_type,
    )

    dropped_experiment_df = experiment_seed_df.loc[
        experiment_seed_df["drop_reason"].notna(),
        ["experiment_alias", "study_name", "corrected_type", "drop_reason"],
    ].copy()
    dropped_experiment_df.insert(0, "level", "experiment")

    experiment_kept_df = experiment_seed_df[experiment_seed_df["drop_reason"].isna()].copy()
    experiment_kept_df = experiment_kept_df.sort_values(["study_name", "experiment_alias"]).reset_index(drop=True)

    study_df = (
        experiment_kept_df[["study_name"]]
        .drop_duplicates()
        .rename(columns={"study_name": "geo_accession"})
        .sort_values("geo_accession")
        .reset_index(drop=True)
    )
    study_df["id"] = study_df.index + 1

    study_name_to_id = dict(zip(study_df["geo_accession"], study_df["id"]))
    experiment_kept_df["study_id"] = experiment_kept_df["study_name"].map(study_name_to_id).astype(int)
    experiment_kept_df = experiment_kept_df.sort_values(["study_id", "experiment_alias"]).reset_index(drop=True)
    experiment_kept_df["id"] = experiment_kept_df.index + 1

    alias_to_final_id = dict(zip(experiment_kept_df["experiment_alias"], experiment_kept_df["id"]))

    def translate_matched(row: pd.Series) -> int | None:
        if row["corrected_type"] != "Ribo-Seq":
            return None
        matched_alias = str(row["matched_RNA-seq_experiment_alias"]).strip()
        matched_id = alias_to_final_id.get(matched_alias)
        if matched_id is None:
            raise KeyError(f"matched RNA-Seq alias missing after filtering: {matched_alias}")
        return int(matched_id)

    experiment_kept_df["matched_experiment_id"] = experiment_kept_df.apply(translate_matched, axis=1)
    experiment_kept_df["matched_experiment_id"] = experiment_kept_df["matched_experiment_id"].astype("Int64")

    study_all_df = (
        metadata_df[["study_name"]]
        .drop_duplicates()
        .rename(columns={"study_name": "geo_accession"})
        .sort_values("geo_accession")
        .reset_index(drop=True)
    )
    dropped_study_df = study_all_df.loc[
        ~study_all_df["geo_accession"].isin(study_df["geo_accession"]),
        ["geo_accession"],
    ].copy()
    dropped_study_df.insert(0, "level", "study")
    dropped_study_df["experiment_alias"] = None
    dropped_study_df["study_name"] = dropped_study_df["geo_accession"]
    dropped_study_df["corrected_type"] = None
    dropped_study_df["drop_reason"] = "all experiments dropped"
    dropped_study_df = dropped_study_df[
        ["level", "experiment_alias", "study_name", "corrected_type", "drop_reason"]
    ]

    kept_aliases = set(experiment_kept_df["experiment_alias"])
    srr_source_df = metadata_df[metadata_df["experiment_alias"].isin(kept_aliases)].copy()
    valid_run_mask = srr_source_df["run"].fillna("").astype(str).str.strip().ne("")
    skipped_run_rows = int((~valid_run_mask).sum())
    srr_source_df = srr_source_df[valid_run_mask].copy()
    srr_source_df["experiment_id"] = srr_source_df["experiment_alias"].map(alias_to_final_id).astype("Int64")
    srr_source_df = srr_source_df.rename(columns={"run": "sra_accession"})
    srr_df = (
        srr_source_df[["sra_accession", "experiment_id"]]
        .dropna(subset=["sra_accession", "experiment_id"])
        .drop_duplicates(subset=["sra_accession", "experiment_id"])
        .sort_values(["experiment_id", "sra_accession"])
        .reset_index(drop=True)
    )

    experiment_out_df = pd.DataFrame(
        {
            "id": experiment_kept_df["id"].astype(int),
            "study_id": experiment_kept_df["study_id"].astype(int),
            "matched_experiment_id": experiment_kept_df["matched_experiment_id"].astype("Int64"),
            "experiment_alias": experiment_kept_df["experiment_alias"].astype(str),
            "type": experiment_kept_df["corrected_type"].astype(str),
            "organism": experiment_kept_df["organism"].astype(str),
            "threep_adapter": experiment_kept_df["threep_adapter"].where(
                experiment_kept_df["threep_adapter"].notna(), ""
            ),
        }
    )

    drop_log_df = pd.concat(
        [
            dropped_experiment_df[
                ["level", "experiment_alias", "study_name", "corrected_type", "drop_reason"]
            ],
            dropped_study_df,
        ],
        ignore_index=True,
    )

    smoke_candidate = select_smoke_candidate(experiment_kept_df, srr_df, supported_organisms)

    return BuildArtifacts(
        study_df=study_df[["id", "geo_accession"]].copy(),
        experiment_internal_df=experiment_kept_df.copy(),
        experiment_out_df=experiment_out_df,
        srr_df=srr_df,
        drop_log_df=drop_log_df,
        dropped_experiment_df=dropped_experiment_df.copy(),
        dropped_study_df=dropped_study_df.copy(),
        organism_audit_df=organism_audit_df,
        blocked_study_df=blocked_study_df,
        supported_organisms=supported_organisms,
        skipped_run_rows=skipped_run_rows,
        smoke_candidate=smoke_candidate,
    )


def select_smoke_candidate(
    experiment_df: pd.DataFrame, srr_df: pd.DataFrame, supported_organisms: list[str]
) -> dict[str, Any] | None:
    supported_set = set(supported_organisms)
    srr_counts = srr_df.groupby("experiment_id").size().to_dict()
    candidates: list[dict[str, Any]] = []

    for study_id, study_group in experiment_df.groupby("study_id"):
        ribo_group = study_group[study_group["corrected_type"] == "Ribo-Seq"].copy()
        if ribo_group.empty:
            continue

        ribo_group["normalized_organism"] = ribo_group["organism"].apply(lambda value: normalize_organism(value)[0])
        ribo_group["is_hybrid"] = ribo_group["organism"].apply(lambda value: normalize_organism(value)[1])
        normalized_organisms = sorted(set(ribo_group["normalized_organism"]))

        if len(normalized_organisms) != 1:
            continue

        normalized_organism = normalized_organisms[0]
        if normalized_organism not in supported_set:
            continue

        if bool(ribo_group["is_hybrid"].any()):
            continue

        if ribo_group["matched_experiment_id"].isna().any():
            continue

        ribo_srr_counts = ribo_group["id"].map(lambda exp_id: int(srr_counts.get(exp_id, 0)))
        if (ribo_srr_counts < 1).any():
            continue

        matched_rna_ids = sorted(set(int(value) for value in ribo_group["matched_experiment_id"].dropna()))
        if not matched_rna_ids:
            continue

        matched_rna_srr_counts = [int(srr_counts.get(exp_id, 0)) for exp_id in matched_rna_ids]
        if any(count < 1 for count in matched_rna_srr_counts):
            continue

        candidates.append(
            {
                "study": str(ribo_group["study_name"].iloc[0]),
                "study_id": int(study_id),
                "organism": str(ribo_group["organism"].iloc[0]),
                "normalized_organism": normalized_organism,
                "ribo_experiment_count": int(len(ribo_group)),
                "matched_rnaseq_experiment_count": int(len(matched_rna_ids)),
                "study_srr_count": int(
                    srr_df[srr_df["experiment_id"].isin(study_group["id"])].shape[0]
                ),
            }
        )

    if not candidates:
        return None

    return sorted(candidates, key=lambda item: (item["normalized_organism"], item["study_id"]))[0]


def write_sqlite(output_db: Path, study_df: pd.DataFrame, experiment_df: pd.DataFrame, srr_df: pd.DataFrame) -> None:
    output_db.parent.mkdir(parents=True, exist_ok=True)
    if output_db.exists():
        output_db.unlink()

    connection = sqlite3.connect(output_db)
    try:
        connection.executescript(DDL_FULL)
        study_df.to_sql("metadata_study", connection, if_exists="append", index=False)
        experiment_df.to_sql("metadata_experiment", connection, if_exists="append", index=False)
        srr_df.to_sql("metadata_srr", connection, if_exists="append", index=False)
        connection.commit()
    finally:
        connection.close()


def build_summary(artifacts: BuildArtifacts) -> dict[str, Any]:
    summary = {
        "supported_organisms": artifacts.supported_organisms,
        "organism_audit": artifacts.organism_audit_df.to_dict(orient="records"),
        "blocked_studies": artifacts.blocked_study_df.to_dict(orient="records"),
        "counts": {
            "study": int(len(artifacts.study_df)),
            "experiment": int(len(artifacts.experiment_out_df)),
            "srr": int(len(artifacts.srr_df)),
            "dropped_experiment": int(len(artifacts.dropped_experiment_df)),
            "dropped_study": int(len(artifacts.dropped_study_df)),
            "skipped_run_rows": int(artifacts.skipped_run_rows),
            "blocked_study_rows": int(len(artifacts.blocked_study_df)),
            "blocked_study_count": int(artifacts.blocked_study_df["study_name"].nunique()),
        },
        "smoke_candidate": artifacts.smoke_candidate,
    }
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build SnakeScale sqlite input database.")
    parser.add_argument("--metadata-csv", type=Path, default=DEFAULT_METADATA_CSV)
    parser.add_argument("--references-yaml", type=Path, default=DEFAULT_REFERENCES_YAML)
    parser.add_argument("--output-db", type=Path, default=DEFAULT_OUTPUT_DB)
    parser.add_argument("--drop-log", type=Path, default=DEFAULT_DROP_LOG)
    parser.add_argument("--summary-json", type=Path, default=None)
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    metadata_df = load_metadata(args.metadata_csv)
    supported_organisms = load_supported_organisms(args.references_yaml)
    artifacts = build_sqlite_inputs(metadata_df, supported_organisms)

    write_sqlite(args.output_db, artifacts.study_df, artifacts.experiment_out_df, artifacts.srr_df)
    args.drop_log.parent.mkdir(parents=True, exist_ok=True)
    artifacts.drop_log_df.to_csv(args.drop_log, index=False)

    summary = build_summary(artifacts)
    if args.summary_json is not None:
        args.summary_json.parent.mkdir(parents=True, exist_ok=True)
        args.summary_json.write_text(json.dumps(summary, indent=2, ensure_ascii=False))

    print(f"[OK] wrote {args.output_db}")
    print(
        "     study={study}, experiment={experiment}, srr={srr}".format(
            **summary["counts"]
        )
    )
    print(
        "     dropped: experiment={dropped_experiment}, study={dropped_study}, skipped_run_rows={skipped_run_rows}".format(
            **summary["counts"]
        )
    )
    if summary["smoke_candidate"] is None:
        print("     smoke_candidate=None")
    else:
        candidate = summary["smoke_candidate"]
        print(
            "     smoke_candidate={study} ({normalized_organism})".format(
                **candidate
            )
        )


if __name__ == "__main__":
    main()
