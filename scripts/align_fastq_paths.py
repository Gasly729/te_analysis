"""Align metadata.csv fastq_path columns to real disk layout.

Scans data/raw/ for every *.fastq.gz, builds an index keyed by SRA run
accession, then rewrites metadata.csv columns:
- fastq_path     : relative path to R1 (or the sole file for single-end
                   without _1/_2 suffix)
- fastq_path_r2  : relative path to R2 (empty for single-end)

Replaces the declarative H2 paths (which never matched disk) with the
true filesystem layout:
    {organism}/{GSE}/{experiment_alias}_{assay}_{run}_[12].fastq.gz
or (legacy, 17 files):
    {organism}/{GSE}/{experiment_alias}_{assay}_{run}.fastq.gz

Usage:
    python scripts/align_fastq_paths.py --dry-run
    python scripts/align_fastq_paths.py
"""
from __future__ import annotations

import argparse
import re
import shutil
from collections import defaultdict
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
RAW_ROOT = REPO_ROOT / "data" / "raw"
DEFAULT_INPUT = RAW_ROOT / "metadata.csv"
DEFAULT_BACKUP = RAW_ROOT / "metadata.csv.preJ1.bak"
DEFAULT_REPORT = RAW_ROOT / "_fastq_align_report.md"

# Accepts: {EXP}_{assay}_{run}_[12].fastq.gz  OR  {EXP}_{assay}_{run}.fastq.gz
FASTQ_RE = re.compile(
    r"^(?P<exp>[A-Z]+\d+)_(?P<assay>Ribo-Seq|RNA-Seq)_(?P<run>[SE]RR\d+)"
    r"(?:_(?P<read>[12]))?\.fastq\.gz$"
)


def read_metadata_preserving_tag(path: Path) -> tuple[str, pd.DataFrame]:
    """Read metadata.csv keeping row-0 'Curated Data,...' tag intact."""
    with path.open("r", encoding="utf-8") as fh:
        tag_line = fh.readline().rstrip("\n")
    df = pd.read_csv(path, header=1, dtype=str, keep_default_na=False)
    return tag_line, df


def scan_disk(raw_root: Path) -> tuple[dict[str, dict[str, str]], list[str]]:
    """Build {run: {'1': rel_path, '2': rel_path_or_none, '0': rel_path_legacy}}.

    Returns (index, skipped_filenames).
    Legacy no-read-suffix files are stored under key '0'.
    """
    index: dict[str, dict[str, str]] = defaultdict(dict)
    skipped: list[str] = []
    conflicts: list[str] = []
    for path in raw_root.rglob("*.fastq.gz"):
        m = FASTQ_RE.match(path.name)
        if not m:
            skipped.append(str(path.relative_to(raw_root)))
            continue
        run = m.group("run")
        read = m.group("read") or "0"
        rel = str(path.relative_to(raw_root))
        if read in index[run]:
            conflicts.append(f"{run} read={read}: {index[run][read]} vs {rel}")
            continue
        index[run][read] = rel
    if conflicts:
        raise RuntimeError(
            "Duplicate FASTQ candidates for same (run, read):\n  "
            + "\n  ".join(conflicts[:20])
        )
    return dict(index), skipped


def resolve_pair(run: str, run_files: dict[str, str]) -> tuple[str, str]:
    """Return (r1_path, r2_path) for a given run. r2 may be empty."""
    if not run_files:
        return "", ""
    # Prefer explicit _1 / _2; fall back to legacy unsuffixed
    r1 = run_files.get("1") or run_files.get("0") or ""
    r2 = run_files.get("2", "")
    return r1, r2


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    ap.add_argument("--output", type=Path, default=DEFAULT_INPUT)
    ap.add_argument("--backup-to", type=Path, default=DEFAULT_BACKUP)
    ap.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    ap.add_argument("--raw-root", type=Path, default=RAW_ROOT)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    print(f"[align] scanning {args.raw_root} ...")
    index, skipped = scan_disk(args.raw_root)
    print(f"[align]   indexed {len(index)} runs; skipped {len(skipped)} non-matching files")

    tag_line, df = read_metadata_preserving_tag(args.input)
    print(f"[align] metadata rows={len(df)}")

    r1_paths: list[str] = []
    r2_paths: list[str] = []
    r1_hits = r2_hits = missing_run = no_disk = 0
    unresolved_samples: list[tuple[str, str]] = []
    for _, row in df.iterrows():
        run = row.get("run", "") or ""
        if not run:
            missing_run += 1
            r1_paths.append("")
            r2_paths.append("")
            continue
        files = index.get(run)
        if not files:
            no_disk += 1
            unresolved_samples.append((row.get("experiment_alias", ""), run))
            r1_paths.append("")
            r2_paths.append("")
            continue
        r1, r2 = resolve_pair(run, files)
        if r1:
            r1_hits += 1
        if r2:
            r2_hits += 1
        r1_paths.append(r1)
        r2_paths.append(r2)

    df["fastq_path"] = r1_paths
    df["fastq_path_r2"] = r2_paths

    total = len(df)
    coverage = (r1_hits / total * 100) if total else 0.0
    report_lines = [
        "# FASTQ path alignment report (J1)",
        "",
        f"- Total metadata rows: {total}",
        f"- R1 hits (fastq_path populated): {r1_hits} ({coverage:.2f}%)",
        f"- R2 hits (fastq_path_r2 populated): {r2_hits}",
        f"- Rows with empty 'run' (H2 unresolved): {missing_run}",
        f"- Rows with 'run' set but file missing on disk: {no_disk}",
        f"- Distinct runs indexed on disk: {len(index)}",
        f"- Disk files skipped (regex non-match): {len(skipped)}",
        "",
        "## Missing-on-disk samples (first 20)",
        "",
        *[f"- experiment={e} run={r}" for e, r in unresolved_samples[:20]],
        "",
        "## Skipped disk filenames (first 20)",
        "",
        *[f"- {s}" for s in skipped[:20]],
    ]
    args.report.write_text("\n".join(report_lines) + "\n", encoding="utf-8")
    print(f"[align] wrote report -> {args.report}")
    print(f"[align] R1 coverage: {r1_hits}/{total} ({coverage:.2f}%)")

    if args.dry_run:
        print("[align] --dry-run; no metadata.csv write")
        return

    shutil.copy2(args.input, args.backup_to)
    print(f"[align] backup -> {args.backup_to}")
    tag_padding = "," * (len(df.columns) - len(tag_line.split(",")))
    with args.output.open("w", encoding="utf-8") as fh:
        fh.write(tag_line + tag_padding + "\n")
        df.to_csv(fh, index=False)
    print(f"[align] wrote -> {args.output} ({len(df)} rows, {len(df.columns)} cols)")


if __name__ == "__main__":
    main()
