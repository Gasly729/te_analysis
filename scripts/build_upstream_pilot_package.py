#!/usr/bin/env python
from __future__ import annotations

import argparse
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from te_analysis.upstream.pilot_package import build_upstream_pilot_package


DEFAULT_RAW_ROOT = REPO_ROOT / "data/raw"
DEFAULT_PILOT_ROOT = REPO_ROOT / "data/upstream/pilot"


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build one local-only upstream pilot package from resolved FASTQ inputs.")
    parser.add_argument("--metadata", type=Path, default=DEFAULT_RAW_ROOT / "metadata.csv")
    parser.add_argument("--metadata-runs", type=Path, default=DEFAULT_RAW_ROOT / "metadata_runs.tsv")
    parser.add_argument("--metadata-runs-unresolved", type=Path, default=DEFAULT_RAW_ROOT / "metadata_runs_unresolved.tsv")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_RAW_ROOT / "_manifest.tsv")
    parser.add_argument("--pilot-root", type=Path, default=DEFAULT_PILOT_ROOT)
    return parser


def main() -> int:
    parser = build_argument_parser()
    args = parser.parse_args()
    result = build_upstream_pilot_package(
        metadata_path=args.metadata.expanduser().resolve(),
        runs_path=args.metadata_runs.expanduser().resolve(),
        unresolved_path=args.metadata_runs_unresolved.expanduser().resolve(),
        manifest_path=args.manifest.expanduser().resolve(),
        pilot_root=args.pilot_root.expanduser().resolve(),
    )
    print("upstream_pilot: generated")
    print(f"study_name: {result.study_name}")
    print(f"organism: {result.organism}")
    print(f"candidates_path: {result.candidates_path}")
    print(f"selection_path: {result.selection_path}")
    print(f"study_manifest_path: {result.study_manifest_path}")
    print(f"fastq_manifest_path: {result.fastq_manifest_path}")
    print(f"project_yaml_path: {result.project_yaml_path}")
    print(f"report_path: {result.report_path}")
    print(f"staged_fastq_count: {result.staged_fastq_count}")
    print(f"symlinks_ok: {result.symlinks_ok}")
    print(f"manifest_consistent: {result.manifest_consistent}")
    print(f"config_generated: {result.config_generated}")
    print(f"unresolved_rows_leaked: {result.unresolved_rows_leaked}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
