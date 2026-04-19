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
import subprocess
import sys
from pathlib import Path

from te_analysis.config import REPO_ROOT

VENDOR_SNAKESCALE = REPO_ROOT / "vendor" / "snakescale"
SNAKESCALE_PROJECT_DIR = VENDOR_SNAKESCALE / "input" / "project"
DEFAULT_CORES = 4


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


def build_command(study: str, cores: int) -> list[str]:
    """Assemble the exact snakemake command per snakescale README:110."""
    return [
        "snakemake", "-p",
        "--cores", str(cores),
        "--config", f"studies=['{study}']",
    ]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--study-dir", type=Path, required=True)
    ap.add_argument("--cores", type=int, default=DEFAULT_CORES)
    args = ap.parse_args(argv)

    if not args.study_dir.is_dir():
        raise FileNotFoundError(f"--study-dir not a directory: {args.study_dir}")

    study = _study_from_dir(args.study_dir)
    link = _inject_project_yaml(args.study_dir, study)
    print(f"[run_upstream] linked {link} -> {link.resolve()}")

    cmd = build_command(study, args.cores)
    print(f"[run_upstream] {' '.join(cmd)}  (cwd={VENDOR_SNAKESCALE})")
    result = subprocess.run(cmd, cwd=VENDOR_SNAKESCALE, check=False)
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
