"""One-shot SRR enrichment for data/raw/metadata.csv.

Queries NCBI SRA via pysradb to expand the experiment-level metadata table
into a run-level flat table (one row per SRR), adding two columns:
- run          : SRA run accession (SRR...)
- fastq_path   : declarative FASTQ path under data/raw/ — not checked

Scheme A per docs/srr_resolution_design_v2.md (top_level §5.2 / M7.MUSTNOT.3).

Usage:
    python scripts/enrich_metadata_srr.py --dry-run
    python scripts/enrich_metadata_srr.py
"""
from __future__ import annotations

import argparse
import shutil
import time
from pathlib import Path

import pandas as pd
from pysradb.sraweb import SRAweb

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = REPO_ROOT / "data" / "raw" / "metadata.csv"
DEFAULT_BACKUP = REPO_ROOT / "data" / "raw" / "metadata.csv.preH2.bak"
DEFAULT_REPORT = REPO_ROOT / "data" / "raw" / "_srr_enrichment_report.md"
BATCH_SIZE = 50  # NCBI eutils URL length / session stability limit
MAX_RETRIES = 3
RETRY_SLEEP = 5.0


def read_metadata_preserving_tag(path: Path) -> tuple[str, pd.DataFrame]:
    """Read metadata.csv keeping row-0 'Curated Data,...' tag intact."""
    with path.open("r", encoding="utf-8") as fh:
        tag_line = fh.readline().rstrip("\n")
    df = pd.read_csv(path, header=1, dtype=str, keep_default_na=False)
    return tag_line, df


def _query_chunk_with_retry(web: SRAweb, chunk: list[str]) -> pd.DataFrame:
    """Query one chunk with retries on transient SSL/network errors."""
    last_exc: Exception | None = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            res = web.srx_to_srr(chunk)
            return res[["experiment_accession", "run_accession"]]
        except Exception as exc:  # noqa: BLE001 - NCBI can throw SSLError, HTTPError, etc.
            last_exc = exc
            print(f"[enrich]   chunk attempt {attempt}/{MAX_RETRIES} failed: {exc}")
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_SLEEP * attempt)
    assert last_exc is not None
    raise last_exc


def query_srr(srx_list: list[str]) -> pd.DataFrame:
    """Batched SRX -> SRR lookup via pysradb. Returns two-col DataFrame."""
    web = SRAweb()
    frames: list[pd.DataFrame] = []
    total = len(srx_list)
    for i in range(0, total, BATCH_SIZE):
        chunk = srx_list[i : i + BATCH_SIZE]
        print(f"[enrich]   chunk {i // BATCH_SIZE + 1} ({i}-{i + len(chunk)}/{total})")
        frames.append(_query_chunk_with_retry(web, chunk))
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(
        columns=["experiment_accession", "run_accession"]
    )


def build_fastq_path(row: pd.Series) -> str:
    """Build declarative FASTQ path matching snakescale generate_yaml.py layout."""
    if not row["run"]:
        return ""
    return f"fastq/{row['study_name']}/{row['experiment_alias']}/{row['run']}_1.fastq.gz"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    ap.add_argument("--output", type=Path, default=DEFAULT_INPUT)
    ap.add_argument("--backup-to", type=Path, default=DEFAULT_BACKUP)
    ap.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    tag_line, df = read_metadata_preserving_tag(args.input)
    srx_all = sorted(s for s in df["experiment_accession"].unique() if s)
    print(f"[enrich] input rows={len(df)} unique SRX={len(srx_all)}")

    srr_df = query_srr(srx_all)
    print(f"[enrich] pysradb returned {len(srr_df)} SRX->SRR mappings")

    merged = df.merge(srr_df, on="experiment_accession", how="left")
    merged = merged.rename(columns={"run_accession": "run"})
    merged["run"] = merged["run"].fillna("")
    merged["fastq_path"] = merged.apply(build_fastq_path, axis=1)

    unresolved = merged[merged["run"] == ""]["experiment_accession"].unique()
    fanout = (
        merged[merged["run"] != ""].groupby("experiment_accession").size().value_counts().sort_index()
    )
    report_lines = [
        "# SRR enrichment report (H2 / scheme A)",
        "",
        f"- Input rows (experiment-level): {len(df)}",
        f"- Output rows (run-level): {len(merged)}",
        f"- Unique SRX queried: {len(srx_all)}",
        f"- Unresolved SRX: {len(unresolved)}",
        "",
        "## SRX -> SRR fanout distribution",
        "",
        "| fanout | # SRX |",
        "|---|---|",
        *[f"| {k} | {v} |" for k, v in fanout.items()],
        "",
        "## Unresolved SRX (first 20)",
        "",
        *[f"- {s}" for s in list(unresolved)[:20]],
    ]
    args.report.write_text("\n".join(report_lines) + "\n", encoding="utf-8")
    print(f"[enrich] wrote report -> {args.report}")

    if args.dry_run:
        print("[enrich] --dry-run; no metadata.csv write")
        return

    shutil.copy2(args.input, args.backup_to)
    print(f"[enrich] backup -> {args.backup_to}")
    # Write: preserve original tag line + new header + run-level rows
    tag_padding = "," * (len(merged.columns) - len(tag_line.split(",")))
    with args.output.open("w", encoding="utf-8") as fh:
        fh.write(tag_line + tag_padding + "\n")
        merged.to_csv(fh, index=False)
    print(f"[enrich] wrote enriched metadata -> {args.output} ({len(merged)} rows)")


if __name__ == "__main__":
    main()
