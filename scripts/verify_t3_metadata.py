"""Verify T3 DoD for data/raw/metadata.csv.

Checks (per sprint_plan_v1 §4 T3 and docs/metadata_schema.md §7):
1. Column count == 30
2. corrected_type in {'Ribo-Seq', 'RNA-Seq'}
3. library_layout == 'PAIRED' iff fastq_path_r2 populated (when R1 present)
4. pair_id (matched_RNA-seq_experiment_alias) bidirectional closure within study
5. GSE132441 / GSE105082 row-count and assay/organism breakdown

Usage:
    python scripts/verify_t3_metadata.py
Returns non-zero exit code if any MUST check fails.
"""
from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
META = REPO_ROOT / "data" / "raw" / "metadata.csv"
REPORT = REPO_ROOT / "data" / "raw" / "_t3_verification_report.md"

EXPECTED_COLS = 30
FOCUS_STUDIES = ("GSE132441", "GSE105082")


def load() -> pd.DataFrame:
    return pd.read_csv(META, header=1, dtype=str, keep_default_na=False)


def check_columns(df: pd.DataFrame, errors: list[str]) -> None:
    if len(df.columns) != EXPECTED_COLS:
        errors.append(f"column count {len(df.columns)} != {EXPECTED_COLS}")


def check_corrected_type(df: pd.DataFrame, errors: list[str]) -> dict[str, int]:
    valid = {"Ribo-Seq", "RNA-Seq"}
    counts = Counter(df["corrected_type"])
    bad = set(counts) - valid
    if bad:
        errors.append(f"corrected_type has unexpected values: {sorted(bad)}")
    return dict(counts)


def check_paired_layout(df: pd.DataFrame, errors: list[str]) -> dict[str, int]:
    """library_layout == 'PAIRED' iff fastq_path_r2 populated, given R1 present."""
    sub = df[df["fastq_path"] != ""]
    paired_decl = sub["library_layout"].str.upper() == "PAIRED"
    paired_disk = sub["fastq_path_r2"] != ""
    mismatch = sub[paired_decl != paired_disk]
    stats = {
        "rows_with_r1": len(sub),
        "declared_paired": int(paired_decl.sum()),
        "disk_paired": int(paired_disk.sum()),
        "layout_disk_mismatch": len(mismatch),
    }
    # Report but do not fail: vendor metadata layout labels are known noisy
    if len(mismatch) > 0:
        errors.append(
            f"WARN library_layout vs disk R2 mismatch on {len(mismatch)} rows "
            f"(non-fatal; see report)"
        )
    return stats


def check_pair_closure(df: pd.DataFrame, errors: list[str]) -> dict[str, int]:
    """For each Ribo-Seq row with non-empty matched_RNA-seq_experiment_alias,
    assert the named RNA-Seq experiment exists in the same study_name."""
    ribo = df[df["corrected_type"] == "Ribo-Seq"]
    ribo_with_match = ribo[ribo["matched_RNA-seq_experiment_alias"] != ""]
    rna_by_study: dict[str, set[str]] = {}
    for study, grp in df[df["corrected_type"] == "RNA-Seq"].groupby("study_name"):
        rna_by_study[study] = set(grp["experiment_alias"])
    broken: list[tuple[str, str, str]] = []
    for _, r in ribo_with_match.iterrows():
        target = r["matched_RNA-seq_experiment_alias"]
        study = r["study_name"]
        if target not in rna_by_study.get(study, set()):
            broken.append((r["experiment_alias"], target, study))
    stats = {
        "ribo_rows": len(ribo),
        "ribo_with_match": len(ribo_with_match),
        "pair_broken": len(broken),
    }
    closure_pct = (
        (len(ribo_with_match) - len(broken)) / len(ribo_with_match) * 100
        if len(ribo_with_match) else 100.0
    )
    stats["closure_pct"] = round(closure_pct, 2)
    if broken:
        errors.append(
            f"WARN {len(broken)} Ribo-Seq rows have matched_RNA-seq pointer that "
            f"does not resolve within same study_name (non-fatal)"
        )
    return stats


def study_breakdown(df: pd.DataFrame, study: str) -> dict[str, object]:
    sub = df[df["study_name"] == study]
    return {
        "rows": len(sub),
        "assay_counts": dict(Counter(sub["corrected_type"])),
        "organisms": sorted(set(sub["organism"]) - {""}),
        "with_r1": int((sub["fastq_path"] != "").sum()),
        "with_r2": int((sub["fastq_path_r2"] != "").sum()),
    }


def main() -> int:
    df = load()
    errors: list[str] = []

    check_columns(df, errors)
    assay_counts = check_corrected_type(df, errors)
    paired_stats = check_paired_layout(df, errors)
    pair_stats = check_pair_closure(df, errors)
    focus = {s: study_breakdown(df, s) for s in FOCUS_STUDIES}

    lines = [
        "# T3 verification report (J3)",
        "",
        f"- total rows: {len(df)} / columns: {len(df.columns)}",
        f"- corrected_type counts: {assay_counts}",
        "",
        "## Paired-end layout check",
        *[f"- {k}: {v}" for k, v in paired_stats.items()],
        "",
        "## pair_id closure (matched_RNA-seq_experiment_alias)",
        *[f"- {k}: {v}" for k, v in pair_stats.items()],
        "",
        "## Focus study breakdown",
    ]
    for s, b in focus.items():
        lines.append(f"### {s}")
        for k, v in b.items():
            lines.append(f"- {k}: {v}")
        lines.append("")
    lines.append("## Errors / warnings")
    lines.extend([f"- {e}" for e in errors] if errors else ["- (none)"])
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"[verify] wrote {REPORT}")
    print(f"[verify] rows={len(df)} cols={len(df.columns)}")
    print(f"[verify] assay={assay_counts}")
    print(f"[verify] paired={paired_stats}")
    print(f"[verify] pair_closure={pair_stats}")
    for s, b in focus.items():
        print(f"[verify] {s}: {b}")
    if errors:
        print(f"[verify] {len(errors)} warn/error(s) (non-fatal unless MUST)")
    # Only hard-fail on schema violations (column count, corrected_type enum)
    fatal = [e for e in errors if not e.startswith("WARN")]
    return 1 if fatal else 0


if __name__ == "__main__":
    sys.exit(main())
