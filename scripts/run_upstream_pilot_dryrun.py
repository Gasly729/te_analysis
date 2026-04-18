#!/usr/bin/env python
from __future__ import annotations

import argparse
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from te_analysis.upstream.dryrun import run_snakemake_dryrun


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run a pilot-scoped SnakeScale dry-run with repo-local cache/tmp bootstrap."
    )
    parser.add_argument("--snakefile", type=Path, required=True)
    parser.add_argument("--runtime-dir", type=Path, required=True)
    parser.add_argument("--cores", type=int, default=1)
    return parser


def main() -> int:
    parser = build_argument_parser()
    args = parser.parse_args()
    completed = run_snakemake_dryrun(
        snakefile=args.snakefile.expanduser().resolve(),
        runtime_dir=args.runtime_dir.expanduser().resolve(),
        cores=args.cores,
    )
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())

