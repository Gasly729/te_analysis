"""Prepare TE_model runtime inputs for organism-level TE aggregation.

This module only materializes inputs. It does not execute vendor/TE_model,
does not read sample-level RDA files, and does not aggregate TE values.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import py_compile
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import pandas as pd

from te_analysis.config import REPO_ROOT
from te_analysis.run_downstream import _write_trial

METADATA_DEFAULT = REPO_ROOT / "data" / "raw" / "metadata.csv"
DEFAULT_RIBO_GLOBS = (
    "output/*/ribo/experiments/*.ribo",
    "data/interim/snakescale/*/ribo/experiments/*.ribo",
    "vendor/snakescale/output/*/ribo/experiments/*.ribo",
    "vendor/snakescale/intermediates/*/ribo/experiments/*.ribo",
    "vendor/TE_model/data/ribo/*/ribo/experiments/*.ribo",
)
REQUIRED_METADATA_COLUMNS = (
    "experiment_alias",
    "study_name",
    "organism",
    "cell_line",
    "corrected_type",
    "matched_RNA-seq_experiment_alias",
    "run",
)


@dataclass(frozen=True)
class RiboRecord:
    """Resolved experiment-level ribo input."""

    study_name: str
    experiment_alias: str
    study_root: Path
    source_path: Path
    resolved_path: Path
    discovery_source: str


def _normalize_token(value: str) -> str:
    return " ".join(value.replace("_", " ").strip().lower().split())


def _slugify(value: str) -> str:
    return _normalize_token(value).replace(" ", "_")


def _is_experiment_ribo(path: Path) -> bool:
    return (
        path.suffix == ".ribo"
        and path.parent.name == "experiments"
        and path.parent.parent.name == "ribo"
    )


def _study_from_ribo_path(path: Path) -> str:
    if not _is_experiment_ribo(path):
        raise ValueError(f"not an experiment-level ribo path: {path}")
    return path.parents[2].name


def _study_root_from_ribo_path(path: Path) -> Path:
    if not _is_experiment_ribo(path):
        raise ValueError(f"not an experiment-level ribo path: {path}")
    return path.parents[2]


def _load_metadata(metadata_path: Path) -> pd.DataFrame:
    if not metadata_path.is_file():
        raise FileNotFoundError(f"metadata.csv not found: {metadata_path}")
    df = pd.read_csv(metadata_path, header=1, dtype=str, keep_default_na=False)
    missing = [col for col in REQUIRED_METADATA_COLUMNS if col not in df.columns]
    if missing:
        raise KeyError(f"metadata.csv missing required columns: {missing}")
    return df


def _collapse_metadata(df: pd.DataFrame) -> pd.DataFrame:
    filtered = df[df["corrected_type"] == "Ribo-Seq"].copy()
    rows: list[dict[str, str | int]] = []
    for experiment_alias, grp in filtered.groupby("experiment_alias", sort=True):
        row: dict[str, str | int] = {"experiment_alias": experiment_alias}
        for col in (
            "study_name",
            "organism",
            "cell_line",
            "corrected_type",
            "matched_RNA-seq_experiment_alias",
        ):
            values = sorted({v for v in grp[col] if v})
            if len(values) > 1:
                raise ValueError(
                    f"metadata conflict for {experiment_alias} column {col}: {values}"
                )
            row[col] = values[0] if values else ""
        runs = sorted({v for v in grp["run"] if v})
        row["run_count"] = len(runs)
        row["runs"] = ",".join(runs)
        rows.append(row)
    return pd.DataFrame(rows)


def _resolve_glob(pattern: str) -> str:
    target = Path(pattern)
    if target.is_absolute():
        return pattern
    return str(REPO_ROOT / pattern)


def _discover_recursive_candidates(excluded_roots: Iterable[Path]) -> list[Path]:
    excluded = [root.resolve() for root in excluded_roots if root.exists()]
    candidates: list[Path] = []
    for path in REPO_ROOT.rglob("*.ribo"):
        if not _is_experiment_ribo(path):
            continue
        resolved = path.resolve()
        if any(resolved.is_relative_to(root) for root in excluded):
            continue
        candidates.append(path)
    return sorted(candidates)


def _discover_ribo_records(
    ribo_globs: list[str] | None,
    excluded_roots: Iterable[Path],
) -> tuple[list[RiboRecord], int]:
    patterns = ribo_globs if ribo_globs else list(DEFAULT_RIBO_GLOBS)
    excluded = [root.resolve() for root in excluded_roots if root.exists()]
    discovered: dict[tuple[str, str], RiboRecord] = {}
    duplicate_count = 0

    def register(path: Path, source: str) -> None:
        nonlocal duplicate_count
        if not _is_experiment_ribo(path):
            return
        resolved = path.resolve()
        if any(resolved.is_relative_to(root) for root in excluded):
            return
        key = (_study_from_ribo_path(path), path.stem)
        record = RiboRecord(
            study_name=key[0],
            experiment_alias=key[1],
            study_root=_study_root_from_ribo_path(path),
            source_path=path,
            resolved_path=resolved,
            discovery_source=source,
        )
        if key in discovered:
            duplicate_count += 1
            return
        discovered[key] = record

    for pattern in patterns:
        for match in sorted(glob.glob(_resolve_glob(pattern))):
            register(Path(match), f"glob:{pattern}")

    for path in _discover_recursive_candidates(excluded):
        register(path, "recursive:ribo/experiments/*.ribo")

    return sorted(discovered.values(), key=lambda r: (r.study_name, r.experiment_alias)), duplicate_count


def _select_records(
    metadata_path: Path,
    organism_arg: str,
    studies: list[str],
    discovered: list[RiboRecord],
) -> tuple[pd.DataFrame, str]:
    metadata = _collapse_metadata(_load_metadata(metadata_path))
    organism_key = _normalize_token(organism_arg)
    scoped = metadata[metadata["organism"].map(_normalize_token) == organism_key].copy()
    if studies:
        scoped = scoped[scoped["study_name"].isin(studies)].copy()
    if scoped.empty:
        raise ValueError(f"no metadata rows for organism={organism_arg!r} studies={studies}")

    by_key = {
        (row["study_name"], row["experiment_alias"]): row
        for row in scoped.to_dict("records")
    }
    rows: list[dict[str, object]] = []
    for record in discovered:
        key = (record.study_name, record.experiment_alias)
        if key not in by_key:
            continue
        resolved_exists = record.resolved_path.is_file()
        if not resolved_exists:
            raise FileNotFoundError(f"ribo target missing: {record.resolved_path}")
        meta = by_key[key]
        rows.append(
            {
                "study_name": meta["study_name"],
                "experiment_alias": meta["experiment_alias"],
                "organism": meta["organism"],
                "cell_line": meta["cell_line"],
                "corrected_type": meta["corrected_type"],
                "matched_RNA-seq_experiment_alias": meta["matched_RNA-seq_experiment_alias"],
                "run_count": int(meta["run_count"]),
                "runs": meta["runs"],
                "source_study_root": str(record.study_root),
                "source_ribo_path": str(record.source_path),
                "resolved_ribo_path": str(record.resolved_path),
                "discovery_source": record.discovery_source,
            }
        )

    if not rows:
        raise ValueError(f"no experiment-level ribo files selected for organism={organism_arg!r}")

    selected = pd.DataFrame(rows).sort_values(["study_name", "experiment_alias"]).reset_index(drop=True)
    actual_organisms = sorted(set(selected["organism"]))
    if len(actual_organisms) != 1:
        raise ValueError(f"selected inputs span multiple organisms: {actual_organisms}")
    if studies:
        present = set(selected["study_name"])
        missing = [study for study in studies if study not in present]
        if missing:
            raise ValueError(f"requested study has no selected ribo experiments: {missing}")
    return selected, actual_organisms[0]


def _safe_symlink(target: Path, link_path: Path) -> None:
    link_path.parent.mkdir(parents=True, exist_ok=True)
    if link_path.exists() or link_path.is_symlink():
        if not link_path.is_symlink():
            raise FileExistsError(f"existing non-symlink blocks runtime path: {link_path}")
        current = Path(os.readlink(link_path))
        if not current.is_absolute():
            current = (link_path.parent / current).resolve()
        if current == target.resolve():
            return
        raise FileExistsError(f"existing symlink points elsewhere: {link_path} -> {current}")
    link_path.symlink_to(target)


def _source_priority(study_root: Path) -> tuple[int, str]:
    try:
        text = study_root.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        text = str(study_root)
    if text.startswith("output/"):
        return (0, text)
    if text.startswith("data/interim/snakescale/"):
        return (1, text)
    if text.startswith("vendor/snakescale/output/"):
        return (2, text)
    if text.startswith("vendor/snakescale/intermediates/"):
        return (3, text)
    if text.startswith("vendor/TE_model/data/ribo/"):
        return (4, text)
    return (99, text)


def _build_study_summary(selected: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for study_name, grp in selected.groupby("study_name", sort=True):
        candidate_roots = sorted({Path(p) for p in grp["source_study_root"]}, key=_source_priority)
        if not candidate_roots:
            raise ValueError(f"no study root discovered for study={study_name}")
        study_root = candidate_roots[0]
        missing = []
        for experiment_alias in sorted(set(grp["experiment_alias"])):
            target = study_root / "ribo" / "experiments" / f"{experiment_alias}.ribo"
            if not target.is_file():
                missing.append(experiment_alias)
        if missing:
            raise FileNotFoundError(
                f"study root {study_root} missing selected ribo experiments for {study_name}: {missing}"
            )
        rows.append(
            {
                "study_name": study_name,
                "source_study_root": str(study_root),
                "selected_experiments": int(grp["experiment_alias"].nunique()),
                "has_fastqc": (study_root / "fastqc").is_dir(),
                "has_ribo": (study_root / "ribo").is_dir(),
                "has_rnaseq": (study_root / "rnaseq").is_dir(),
                "has_stats": (study_root / "stats").is_dir(),
            }
        )
    return pd.DataFrame(rows).sort_values("study_name").reset_index(drop=True)


def _write_tables(
    selected: pd.DataFrame,
    out_dir: Path,
    organism: str,
    run_id: str,
    duplicate_discoveries: int,
    ribo_globs: list[str] | None,
    metadata_path: Path,
) -> dict[str, object]:
    manifests_dir = out_dir / "manifests"
    runtime_root = out_dir / "runtime"
    runtime_studies_dir = runtime_root / "studies"
    runtime_vendor_root = runtime_root / "vendor" / "TE_model"
    runtime_vendor_data_ribo_dir = runtime_vendor_root / "data" / "ribo"
    runtime_trials_root = runtime_vendor_root / "trials"
    logs_dir = out_dir / "logs"
    trial_dir = runtime_trials_root / run_id

    if runtime_root.exists():
        shutil.rmtree(runtime_root)

    manifests_dir.mkdir(parents=True, exist_ok=True)
    runtime_studies_dir.mkdir(parents=True, exist_ok=True)
    runtime_vendor_data_ribo_dir.mkdir(parents=True, exist_ok=True)
    runtime_trials_root.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)

    study_summary = _build_study_summary(selected)

    study_runtime_paths: dict[str, tuple[Path, Path]] = {}
    for row in study_summary.to_dict("records"):
        study_name = str(row["study_name"])
        source_study_root = Path(str(row["source_study_root"]))
        runtime_study_root = runtime_studies_dir / study_name
        runtime_vendor_ribo_root = runtime_vendor_data_ribo_dir / study_name
        _safe_symlink(source_study_root, runtime_study_root)
        _safe_symlink(runtime_study_root, runtime_vendor_ribo_root)
        study_runtime_paths[study_name] = (runtime_study_root, runtime_vendor_ribo_root)

    manifest_rows: list[dict[str, object]] = []
    for row in selected.to_dict("records"):
        runtime_study_root, runtime_vendor_ribo_root = study_runtime_paths[str(row["study_name"])]
        manifest_rows.append(
            {
                "study_name": row["study_name"],
                "experiment_alias": row["experiment_alias"],
                "organism": row["organism"],
                "cell_line": row["cell_line"],
                "corrected_type": row["corrected_type"],
                "matched_RNA-seq_experiment_alias": row["matched_RNA-seq_experiment_alias"],
                "run_count": row["run_count"],
                "source_study_root": row["source_study_root"],
                "source_ribo_path": row["source_ribo_path"],
                "resolved_ribo_path": row["resolved_ribo_path"],
                "runtime_study_root": str(runtime_study_root),
                "runtime_vendor_ribo_root": str(runtime_vendor_ribo_root),
                "runtime_vendor_ribo_path": str(
                    runtime_vendor_ribo_root / "ribo" / "experiments" / f"{row['experiment_alias']}.ribo"
                ),
                "discovery_source": row["discovery_source"],
                "has_fastqc": bool(
                    study_summary.loc[study_summary["study_name"] == row["study_name"], "has_fastqc"].iloc[0]
                ),
                "has_ribo": bool(
                    study_summary.loc[study_summary["study_name"] == row["study_name"], "has_ribo"].iloc[0]
                ),
                "has_rnaseq": bool(
                    study_summary.loc[study_summary["study_name"] == row["study_name"], "has_rnaseq"].iloc[0]
                ),
                "has_stats": bool(
                    study_summary.loc[study_summary["study_name"] == row["study_name"], "has_stats"].iloc[0]
                ),
            }
        )

    manifest = pd.DataFrame(manifest_rows).sort_values(["study_name", "experiment_alias"])
    experiments = manifest["experiment_alias"].drop_duplicates().tolist()
    if not experiments:
        raise ValueError("selected experiment count is zero after materialization")

    _write_trial(trial_dir, experiments)
    config_path = trial_dir / "config.py"
    py_compile.compile(str(config_path), doraise=True)

    selected_experiments = selected[
        [
            "study_name",
            "experiment_alias",
            "organism",
            "cell_line",
            "corrected_type",
            "matched_RNA-seq_experiment_alias",
            "run_count",
            "runs",
        ]
    ].drop_duplicates()

    selected_path = manifests_dir / "selected_experiments.tsv"
    manifest_path = manifests_dir / "selected_ribo_manifest.tsv"
    study_summary_path = manifests_dir / "study_directory_summary.tsv"
    summary_path = manifests_dir / "prepare_summary.json"

    selected_experiments.to_csv(selected_path, sep="\t", index=False)
    manifest.to_csv(manifest_path, sep="\t", index=False)
    study_summary = study_summary.assign(
        runtime_study_root=study_summary["study_name"].map(
            lambda study: str(study_runtime_paths[str(study)][0])
        ),
        runtime_vendor_ribo_root=study_summary["study_name"].map(
            lambda study: str(study_runtime_paths[str(study)][1])
        ),
    )
    study_summary.to_csv(study_summary_path, sep="\t", index=False)

    actual_study_links = list(runtime_studies_dir.glob("*"))
    actual_vendor_links = list(runtime_vendor_data_ribo_dir.glob("*"))
    if len(actual_study_links) != len(study_summary):
        raise ValueError(
            f"runtime study-root count mismatch: summary={len(study_summary)} links={len(actual_study_links)}"
        )
    if len(actual_vendor_links) != len(study_summary):
        raise ValueError(
            f"runtime vendor-ribo count mismatch: summary={len(study_summary)} links={len(actual_vendor_links)}"
        )
    visible_ribo_paths = [Path(p) for p in manifest["runtime_vendor_ribo_path"] if Path(p).is_file()]
    if len(visible_ribo_paths) != len(manifest):
        raise ValueError(
            f"runtime ribo count mismatch: manifest={len(manifest)} visible_paths={len(visible_ribo_paths)}"
        )

    summary = {
        "organism": organism,
        "organism_slug": _slugify(organism),
        "run_id": run_id,
        "prepare_only": True,
        "study_names": sorted(selected_experiments["study_name"].unique().tolist()),
        "studies_selected": int(selected_experiments["study_name"].nunique()),
        "experiments_selected": int(len(selected_experiments)),
        "ribo_files_materialized": int(len(manifest)),
        "duplicate_discoveries_dropped": int(duplicate_discoveries),
        "metadata_path": str(metadata_path),
        "selected_experiments_path": str(selected_path),
        "selected_ribo_manifest_path": str(manifest_path),
        "study_directory_summary_path": str(study_summary_path),
        "trial_config_path": str(config_path),
        "runtime_studies_root": str(runtime_studies_dir),
        "runtime_vendor_te_model_root": str(runtime_vendor_root),
        "runtime_vendor_ribo_root": str(runtime_vendor_data_ribo_dir),
        "discovery_patterns": ribo_globs if ribo_globs else list(DEFAULT_RIBO_GLOBS),
    }
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    return summary


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--organism", required=True)
    ap.add_argument("--prepare-only", action="store_true")
    ap.add_argument("--out-dir", type=Path, required=True)
    ap.add_argument("--study", dest="studies", action="append", default=[])
    ap.add_argument("--metadata", type=Path, default=METADATA_DEFAULT)
    ap.add_argument("--ribo-glob", dest="ribo_globs", action="append", default=[])
    return ap


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.prepare_only:
        raise ValueError("only --prepare-only is implemented in this round")

    metadata_path = args.metadata if args.metadata.is_absolute() else (REPO_ROOT / args.metadata)
    out_dir = args.out_dir if args.out_dir.is_absolute() else (REPO_ROOT / args.out_dir)

    excluded_roots = [
        REPO_ROOT / "tests",
        REPO_ROOT / "data" / "processed" / "te_species",
        out_dir,
    ]
    ribo_globs = args.ribo_globs or None
    discovered, duplicate_discoveries = _discover_ribo_records(ribo_globs, excluded_roots)
    if not discovered:
        raise FileNotFoundError("no experiment-level ribo files discovered")
    selected, organism = _select_records(metadata_path, args.organism, args.studies, discovered)
    run_id = f"{_slugify(organism)}_species_te_prepare"
    summary = _write_tables(
        selected=selected,
        out_dir=out_dir,
        organism=organism,
        run_id=run_id,
        duplicate_discoveries=duplicate_discoveries,
        ribo_globs=ribo_globs,
        metadata_path=metadata_path,
    )
    print(
        "[aggregate_species_te] "
        f"organism={summary['organism']} studies={summary['studies_selected']} "
        f"experiments={summary['experiments_selected']} ribo={summary['ribo_files_materialized']}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
