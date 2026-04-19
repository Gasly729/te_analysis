"""metadata.csv -> snakescale-native project.yaml + staged FASTQ symlinks.

Implements te_analysis_module_contracts_v1.md §M1. Sole writer of:
- <out>/project.yaml
- <out>/staged_fastq/{GSE}/{GSM}/{SRR}_[12].fastq.gz (symlinks)

CLI:
    python -m te_analysis.stage_inputs \
        --metadata data/raw/metadata.csv \
        --study    GSE132441 \
        --out      data/interim/snakescale/GSE132441
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

import pandas as pd
import yaml

from te_analysis.config import REPO_ROOT

# Immutable vendor references (GC-3 single source of truth)
VENDOR_TEMPLATE = REPO_ROOT / "vendor" / "snakescale" / "project.yaml"
VENDOR_REFERENCES = REPO_ROOT / "vendor" / "snakescale" / "scripts" / "references.yaml"
REFERENCE_FOLDER = "reference"  # prefix used inside snakescale runtime

# Clip-argument base strings, vendored from generate_yaml.py:159,161
RIBO_CLIP_BASE = "-u 1 --maximum-length=40 --minimum-length=15 --quality-cutoff=28"
RNA_CLIP_BASE = "-u 5 -l 40 --quality-cutoff=28"

STAGED_DIR = "staged_fastq"
DATA_RAW = REPO_ROOT / "data" / "raw"


def _read_metadata(path: Path) -> pd.DataFrame:
    """Read run-level metadata.csv (tag row 0, header row 1)."""
    if not path.is_file():
        raise FileNotFoundError(f"metadata.csv not found: {path}")
    return pd.read_csv(path, header=1, dtype=str, keep_default_na=False)


def _filter_study(df: pd.DataFrame, study: str) -> pd.DataFrame:
    """Filter rows by study_name; raise with suggestions if unknown."""
    gse_only = study.split("_", 1)[0]
    sub = df[df["study_name"] == gse_only].copy()
    if sub.empty:
        available = sorted(df["study_name"].unique())[:20]
        raise ValueError(
            f"study_name={gse_only!r} not in metadata.csv. First 20 available: {available}"
        )
    # Drop rows missing the fields we need downstream
    sub = sub[(sub["run"] != "") & (sub["fastq_path"] != "")]
    if sub.empty:
        raise ValueError(f"study {gse_only!r} has no rows with populated run/fastq_path")
    return sub


def _partition(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Split filtered rows into Ribo-Seq and RNA-Seq."""
    ribo = df[df["corrected_type"] == "Ribo-Seq"]
    rna = df[df["corrected_type"] == "RNA-Seq"]
    if ribo.empty:
        raise ValueError("no Ribo-Seq rows in study (snakescale requires at least one)")
    return ribo, rna


def _resolve_references(organism: str, refs_yaml: dict) -> dict[str, str]:
    """Look up the reference file paths for `organism` (case-insensitive)."""
    key = organism.strip().lower()
    if key not in refs_yaml:
        available = sorted(refs_yaml.keys())
        raise KeyError(
            f"organism {organism!r} not in references.yaml. Supported: {available}"
        )
    entry = refs_yaml[key]
    out = {}
    for ref_key in ("filter", "transcriptome", "regions", "transcript_lengths"):
        if ref_key not in entry:
            raise KeyError(f"references.yaml[{key}] missing required key {ref_key!r}")
        out[ref_key] = f"{REFERENCE_FOLDER}/{entry[ref_key]}"
    return out


def _build_clip_arguments(base: str, adapters: set[str], is_ribo: bool) -> str:
    """Port of generate_yaml.py:32-67 generate_clip_sequence.

    Uses the first (sorted) non-empty adapter to keep output deterministic.
    """
    non_empty = sorted(a for a in adapters if a)
    if not non_empty:
        return base
    if len({a for a in non_empty}) > 1:
        raise ValueError(
            f"multiple distinct adapters within study: {non_empty}; "
            "snakescale does not support this"
        )
    adapter = non_empty[0]
    overlap = 4
    for ch in adapter:
        if ch == "N":
            overlap += 1
        else:
            break
    parts = [base, f"-a {adapter}", f"--overlap={overlap}"]
    if is_ribo:
        parts.append("--trimmed-only")
    return " ".join(parts)


def _fastq_relpath(gse: str, gsm: str, run: str, read: str = "1") -> str:
    """Path under <out>/staged_fastq/, relative to <out>/project.yaml."""
    return f"{STAGED_DIR}/{gse}/{gsm}/{run}_{read}.fastq.gz"


def _build_fastq_maps(
    ribo: pd.DataFrame, rna: pd.DataFrame, gse: str
) -> tuple[dict[str, list[str]], dict[str, list[str]]]:
    """Return (input.fastq dict, rnaseq.fastq dict). Both keyed by Ribo GSM.

    Matches vendor generate_yaml.py:262-300 semantics exactly.
    """
    input_fastq: dict[str, list[str]] = {}
    rnaseq_fastq: dict[str, list[str]] = {}
    rna_by_alias = {row["experiment_alias"]: row for _, row in rna.iterrows()}

    for ribo_gsm, grp in ribo.groupby("experiment_alias", sort=True):
        ribo_paths = [
            _fastq_relpath(gse, ribo_gsm, r["run"])
            for _, r in grp.sort_values("run").iterrows()
        ]
        if not ribo_paths:
            raise ValueError(f"Ribo GSM {ribo_gsm} has zero FASTQ files")
        input_fastq[str(ribo_gsm)] = ribo_paths

        matched_name = grp.iloc[0]["matched_RNA-seq_experiment_alias"]
        if matched_name and matched_name in rna_by_alias:
            rna_rows = rna[rna["experiment_alias"] == matched_name].sort_values("run")
            rnaseq_fastq[str(ribo_gsm)] = [
                _fastq_relpath(gse, matched_name, r["run"]) for _, r in rna_rows.iterrows()
            ]
    return input_fastq, rnaseq_fastq


def _create_symlinks(
    ribo: pd.DataFrame, rna: pd.DataFrame, gse: str, out: Path
) -> None:
    """Materialize <out>/staged_fastq/{GSE}/{GSM}/{run}_[12].fastq.gz symlinks."""
    staged_root = out / STAGED_DIR
    if staged_root.exists():
        shutil.rmtree(staged_root)
    rows_in_study = pd.concat([ribo, rna], ignore_index=True)
    for _, row in rows_in_study.iterrows():
        gsm = row["experiment_alias"]
        run = row["run"]
        for read, col in (("1", "fastq_path"), ("2", "fastq_path_r2")):
            rel = row.get(col, "") or ""
            if not rel:
                continue
            src = (DATA_RAW / rel).resolve()
            if not src.is_file():
                raise FileNotFoundError(
                    f"fastq_path missing on disk for run={run}: {src}"
                )
            dst = staged_root / gse / gsm / f"{run}_{read}.fastq.gz"
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.symlink_to(src)


def _build_project_yaml(
    template: dict,
    ribo: pd.DataFrame,
    rna: pd.DataFrame,
    gse: str,
    study_suffix: str,
    refs_yaml: dict,
) -> dict:
    """Override dynamic fields on the vendor template dict."""
    doc = dict(template)  # shallow copy; leaves keyed as existing
    organisms = {o for o in ribo["organism"] if o}
    if len(organisms) != 1:
        raise ValueError(f"expected exactly one organism in Ribo-Seq rows, got {organisms}")
    organism = organisms.pop()
    ref_paths = _resolve_references(organism, refs_yaml)

    # Ribo clip
    ribo_adapters = set(ribo["threep_adapter"])
    doc["clip_arguments"] = _build_clip_arguments(RIBO_CLIP_BASE, ribo_adapters, is_ribo=True)
    # RNA clip (use only matched-to-Ribo RNA rows' adapters; empty adapter is fine)
    matched_rna_names = {
        a for a in ribo["matched_RNA-seq_experiment_alias"] if a
    }
    matched_rna_rows = rna[rna["experiment_alias"].isin(matched_rna_names)]
    rna_adapters = set(matched_rna_rows["threep_adapter"])
    doc.setdefault("rnaseq", {})
    doc["rnaseq"]["clip_arguments"] = _build_clip_arguments(
        RNA_CLIP_BASE, rna_adapters, is_ribo=False
    )

    # deduplicate (from study_name suffix)
    dedup = study_suffix == "dedup"
    doc["deduplicate"] = dedup
    doc["rnaseq"]["deduplicate"] = dedup

    # references
    doc.setdefault("input", {}).setdefault("reference", {})
    for key, val in ref_paths.items():
        doc["input"]["reference"][key] = val

    # fastq maps
    input_fastq, rnaseq_fastq = _build_fastq_maps(ribo, rna, gse)
    doc["input"]["fastq_base"] = ""
    doc["input"]["fastq"] = input_fastq
    doc["rnaseq"]["fastq_base"] = ""
    doc["rnaseq"]["fastq"] = rnaseq_fastq
    doc["do_rnaseq"] = bool(rnaseq_fastq)

    # output bases per generate_yaml.py:315-316
    doc.setdefault("output", {}).setdefault("output", {})["base"] = f"output/{gse}{('_' + study_suffix) if study_suffix else ''}"
    doc["output"].setdefault("intermediates", {})["base"] = f"intermediates/{gse}{('_' + study_suffix) if study_suffix else ''}"
    return doc


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--metadata", type=Path, required=True)
    ap.add_argument("--study", type=str, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args(argv)

    for required_path in (VENDOR_TEMPLATE, VENDOR_REFERENCES):
        if not required_path.is_file():
            raise FileNotFoundError(f"vendor asset missing: {required_path}")

    with VENDOR_TEMPLATE.open("r", encoding="utf-8") as fh:
        template = yaml.safe_load(fh)
    with VENDOR_REFERENCES.open("r", encoding="utf-8") as fh:
        refs_yaml = yaml.safe_load(fh)

    study_parts = args.study.split("_", 1)
    gse_only = study_parts[0]
    suffix = study_parts[1] if len(study_parts) > 1 else ""
    if suffix and suffix not in ("dedup", "test"):
        raise ValueError(f"invalid study suffix {suffix!r}; allowed: dedup, test")

    df = _read_metadata(args.metadata)
    study_df = _filter_study(df, args.study)
    ribo, rna = _partition(study_df)

    args.out.mkdir(parents=True, exist_ok=True)
    _create_symlinks(ribo, rna, gse_only, args.out)
    doc = _build_project_yaml(template, ribo, rna, gse_only, suffix, refs_yaml)

    yaml_path = args.out / "project.yaml"
    with yaml_path.open("w", encoding="utf-8") as fh:
        yaml.safe_dump(doc, fh, sort_keys=False, default_flow_style=False)
    print(f"[stage_inputs] wrote {yaml_path}")
    print(f"[stage_inputs] staged {len(ribo)} Ribo + {len(rna)} RNA rows under {args.out / STAGED_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
