#!/usr/bin/env python
from __future__ import annotations

import argparse
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from te_analysis.raw import build_metadata_runs_outputs


DEFAULT_RAW_ROOT = Path("/home/xrx/my_project/te_analysis/data/raw")


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Expand experiment-level metadata into run-level metadata.")
    parser.add_argument("--metadata", type=Path, default=DEFAULT_RAW_ROOT / "metadata.csv")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_RAW_ROOT / "_manifest.tsv")
    parser.add_argument("--runs-output", type=Path, default=DEFAULT_RAW_ROOT / "metadata_runs.tsv")
    parser.add_argument(
        "--unresolved-output",
        type=Path,
        default=DEFAULT_RAW_ROOT / "metadata_runs_unresolved.tsv",
    )
    parser.add_argument("--report-output", type=Path, default=DEFAULT_RAW_ROOT / "_metadata_runs_report.md")
    return parser


def main() -> int:
    parser = build_argument_parser()
    args = parser.parse_args()
    result = build_metadata_runs_outputs(
        metadata_path=args.metadata.expanduser().resolve(),
        manifest_path=args.manifest.expanduser().resolve(),
        runs_path=args.runs_output.expanduser().resolve(),
        unresolved_path=args.unresolved_output.expanduser().resolve(),
        report_path=args.report_output.expanduser().resolve(),
    )
    print("metadata_runs: generated")
    print(f"metadata_path: {result.metadata_path}")
    print(f"manifest_path: {result.manifest_path}")
    print(f"runs_path: {result.runs_path}")
    print(f"unresolved_path: {result.unresolved_path}")
    print(f"report_path: {result.report_path}")
    print(f"resolved_run_rows: {len(result.resolution.resolved)}")
    print(f"unresolved_rows: {len(result.resolution.unresolved)}")
    print(f"manifest_backmatched_runs: {result.resolution.manifest_backmatched_runs}")
    print(f"manifest_unmatched_runs: {result.resolution.manifest_unmatched_runs}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
