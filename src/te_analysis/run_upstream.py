"""Thin wrapper over vendor/snakescale (module_contracts §M2).

Command:
    snakemake -p --cores N --config studies="['<study>']"
    cwd = vendor/snakescale/

Pre-step: symlink <study-dir>/project.yaml ->
    vendor/snakescale/input/project/{GSE}/{study}.yaml
(Snakefile:36 skips generate_yaml() if the file exists; input/ is in
snakescale's own runtime area, not a tracked vendor file.)

CLI:
    python -m te_analysis.run_upstream --study-dir PATH [--cores N]
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

from te_analysis.config import REPO_ROOT
from te_analysis.stage_snakescale_injection import (
    inject_staged_fastq,
    prepare_download_bypass,
)

VENDOR_SNAKESCALE = REPO_ROOT / "vendor" / "snakescale"
SNAKESCALE_PROJECT_DIR = VENDOR_SNAKESCALE / "input" / "project"
DEFAULT_CORES = 4
STUDY_SNAKEMAKE_CONFIG_OVERRIDES = {
    # GSE132441 has fixed-length no-adapter reads; the adapter pre-check must
    # not invalidate it once stage_inputs truncates reads to RiboFlow length.
    "GSE132441": ("adapter_threshold=0",),
}


def _study_from_dir(study_dir: Path) -> str:
    """Study name = last path component (e.g. 'GSE132441' or 'GSE132441_dedup')."""
    return study_dir.name


def _inject_project_yaml(study_dir: Path, study: str) -> Path:
    """Symlink <study-dir>/project.yaml into snakescale's input/project/ area."""
    src = (study_dir / "project.yaml").resolve()
    if not src.is_file():
        raise FileNotFoundError(f"project.yaml missing under {study_dir}")
    gse_only = study.split("_", 1)[0]
    dst = SNAKESCALE_PROJECT_DIR / gse_only / f"{study}.yaml"
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.is_symlink() or dst.exists():
        dst.unlink()
    dst.symlink_to(src)
    return dst


def _default_config_overrides(study: str) -> list[str]:
    """Return study-specific Snakemake config overrides."""
    gse_only = study.split("_", 1)[0]
    return list(STUDY_SNAKEMAKE_CONFIG_OVERRIDES.get(gse_only, ()))


def build_command(
    study: str,
    cores: int,
    extra_config: list[str] | None = None,
    extra_args: list[str] | None = None,
    nolock: bool = False,
) -> list[str]:
    """Assemble the exact snakemake command per snakescale README:110."""
    config_items = [
        f"studies=['{study}']",
        *_default_config_overrides(study),
        *(extra_config or []),
    ]
    cmd = [
        "snakemake", "-p",
        "--cores", str(cores),
        "--config", *config_items,
    ]
    if nolock:
        cmd.append("--nolock")
    cmd.extend(extra_args or [])
    return cmd


def _snakemake_env() -> dict[str, str]:
    """Provide writable defaults for Snakemake caches in sandboxed runs."""
    env = os.environ.copy()
    env.setdefault("XDG_CACHE_HOME", "/tmp/snakemake-cache")
    env.setdefault("TMPDIR", "/tmp")
    return env


def _validate_config_items(items: list[str]) -> None:
    """Require Snakemake config overrides to use KEY=VALUE syntax."""
    invalid = [item for item in items if "=" not in item]
    if invalid:
        raise ValueError(f"--snakemake-config values must be KEY=VALUE: {invalid}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--study-dir", type=Path, required=True)
    ap.add_argument("--cores", type=int, default=DEFAULT_CORES)
    ap.add_argument(
        "--snakemake-config",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="extra Snakemake --config item; may be repeated",
    )
    ap.add_argument(
        "--snakemake-arg",
        action="append",
        default=[],
        help="extra raw Snakemake argument; use --snakemake-arg=--flag for flags",
    )
    ap.add_argument("--nolock", action="store_true")
    args = ap.parse_args(argv)

    if not args.study_dir.is_dir():
        raise FileNotFoundError(f"--study-dir not a directory: {args.study_dir}")
    _validate_config_items(args.snakemake_config)

    study = _study_from_dir(args.study_dir)
    link = _inject_project_yaml(args.study_dir, study)
    print(f"[run_upstream] linked {link} -> {link.resolve()}")
    staged_root = args.study_dir / "staged_fastq" / study.split("_", 1)[0]
    staged_link = inject_staged_fastq(args.study_dir, VENDOR_SNAKESCALE, study)
    placeholder_count = prepare_download_bypass(staged_root)
    print(f"[run_upstream] linked {staged_link} -> {staged_link.resolve()}")
    print(f"[run_upstream] prepared {placeholder_count} FASTQ placeholders")

    cmd = build_command(
        study,
        args.cores,
        extra_config=args.snakemake_config,
        extra_args=args.snakemake_arg,
        nolock=args.nolock,
    )
    print(f"[run_upstream] {' '.join(cmd)}  (cwd={VENDOR_SNAKESCALE})")
    result = subprocess.run(
        cmd, cwd=VENDOR_SNAKESCALE, check=False, env=_snakemake_env()
    )
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
