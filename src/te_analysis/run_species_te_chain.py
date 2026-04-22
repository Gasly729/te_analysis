"""Thin single-species chain for prepare, downstream, and canonical CSV intake."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from te_analysis.aggregate_species_te import METADATA_DEFAULT, main as aggregate_main
from te_analysis.config import REPO_ROOT
from te_analysis.run_species_downstream import _discover_runtime_root, main as downstream_main

CANONICAL_CSV_NAME = "human_TE_cellline_all.csv"


def _normalize_token(value: str) -> str:
    return " ".join(value.replace("_", " ").strip().lower().split())


def _slugify(value: str) -> str:
    return _normalize_token(value).replace(" ", "_")


def _default_trial_name(organism: str) -> str:
    return f"{_slugify(organism)}_species_te_prepare"


def _resolve_path(path: Path) -> Path:
    return path if path.is_absolute() else (REPO_ROOT / path)


def _resolve_trial_dir(species_root: Path, trial_name: str | None) -> tuple[Path, Path]:
    runtime_root, trial_dir = _discover_runtime_root(species_root, trial_name)
    return runtime_root, trial_dir


def _canonical_csv_path(species_root: Path, trial_name: str | None) -> Path:
    _, trial_dir = _resolve_trial_dir(species_root, trial_name)
    return trial_dir / CANONICAL_CSV_NAME


def _check_canonical_csv(path: Path) -> dict[str, int | list[int] | str]:
    if not path.is_file():
        raise FileNotFoundError(f"canonical CSV missing: {path}")
    if path.stat().st_size == 0:
        raise ValueError(f"canonical CSV is empty: {path}")

    df = pd.read_csv(path, index_col=0)
    if df.shape[0] == 0 or df.shape[1] == 0:
        raise ValueError(f"canonical CSV has empty shape: {path} shape={df.shape}")
    if not df.columns.is_unique:
        raise ValueError(f"canonical CSV has duplicate columns: {path}")
    if int(df.isna().all(axis=0).sum()) > 0:
        raise ValueError(f"canonical CSV has all-NA columns: {path}")
    if int(df.isna().all(axis=1).sum()) > 0:
        raise ValueError(f"canonical CSV has all-NA rows: {path}")
    if int(((df.fillna(0) == 0).all(axis=0)).sum()) > 0:
        raise ValueError(f"canonical CSV has all-zero columns: {path}")
    if int(((df.fillna(0) == 0).all(axis=1)).sum()) > 0:
        raise ValueError(f"canonical CSV has all-zero rows: {path}")

    return {
        "canonical_csv": str(path),
        "shape": [int(df.shape[0]), int(df.shape[1])],
        "all_na_rows": int(df.isna().all(axis=1).sum()),
        "all_na_columns": int(df.isna().all(axis=0).sum()),
        "all_zero_rows": int(((df.fillna(0) == 0).all(axis=1)).sum()),
        "all_zero_columns": int(((df.fillna(0) == 0).all(axis=0)).sum()),
    }


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--organism", required=True)
    ap.add_argument("--out-dir", type=Path, required=True)
    ap.add_argument("--trial", default=None)
    ap.add_argument("--metadata", type=Path, default=METADATA_DEFAULT)
    ap.add_argument("--ribo-glob", dest="ribo_globs", action="append", default=[])
    ap.add_argument("--study", dest="studies", action="append", default=[])
    ap.add_argument("--stage2-mode", choices=("shared", "serial-fallback"), default="serial-fallback")
    ap.add_argument("--vendor-root", type=Path, default=REPO_ROOT / "vendor" / "TE_model")
    ap.add_argument(
        "--rscript-bin",
        default="/home/xrx/miniconda3/envs/snakemake-ribo/bin/Rscript",
    )
    ap.add_argument(
        "--python-bin",
        default="/home/xrx/miniconda3/envs/te_analysis/bin/python",
    )
    ap.add_argument("--prepare", action="store_true")
    ap.add_argument("--run-downstream", action="store_true")
    ap.add_argument("--check-output", action="store_true")
    return ap


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not (args.prepare or args.run_downstream or args.check_output):
        raise ValueError("at least one action must be selected: --prepare / --run-downstream / --check-output")

    species_root = _resolve_path(args.out_dir)
    metadata_path = _resolve_path(args.metadata)
    vendor_root = _resolve_path(args.vendor_root)
    expected_trial = _default_trial_name(args.organism)
    trial_name = args.trial or expected_trial

    if args.prepare and args.trial and args.trial != expected_trial:
        raise ValueError(
            "prepare step does not support custom trial naming; "
            f"expected trial for organism {args.organism!r} is {expected_trial!r}"
        )

    if args.prepare:
        prepare_argv = [
            "--organism",
            args.organism,
            "--prepare-only",
            "--out-dir",
            str(species_root),
            "--metadata",
            str(metadata_path),
        ]
        for study in args.studies:
            prepare_argv.extend(["--study", study])
        for pattern in args.ribo_globs:
            prepare_argv.extend(["--ribo-glob", pattern])
        rc = aggregate_main(prepare_argv)
        if rc != 0:
            return rc

    if args.run_downstream:
        downstream_argv = [
            "--species-root",
            str(species_root),
            "--trial",
            trial_name,
            "--stage2-mode",
            args.stage2_mode,
            "--vendor-root",
            str(vendor_root),
            "--rscript-bin",
            args.rscript_bin,
            "--python-bin",
            args.python_bin,
        ]
        rc = downstream_main(downstream_argv)
        if rc != 0:
            return rc

    if args.check_output:
        summary = _check_canonical_csv(_canonical_csv_path(species_root, trial_name))
        print(f"[run_species_te_chain] canonical CSV ready: {json.dumps(summary, sort_keys=True)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
