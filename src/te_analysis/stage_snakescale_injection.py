"""Expose staged FASTQ files to snakescale's runtime cwd."""
from __future__ import annotations

import os
from pathlib import Path

PLACEHOLDER_AGE_SECONDS = 3600


def inject_staged_fastq(study_dir: Path, vendor_root: Path, study: str) -> Path:
    """Symlink <study-dir>/staged_fastq/<GSE> into vendor/snakescale/staged_fastq."""
    gse_only = study.split("_", 1)[0]
    src = (study_dir / "staged_fastq" / gse_only).resolve()
    if not src.is_dir():
        raise FileNotFoundError(f"staged FASTQ directory missing: {src}")

    dst = vendor_root / "staged_fastq" / gse_only
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.is_symlink():
        dst.unlink()
    elif dst.exists():
        raise FileExistsError(f"vendor staged FASTQ path is not a symlink: {dst}")
    dst.symlink_to(src)
    return dst


def prepare_download_bypass(staged_root: Path) -> int:
    """Create older .fastq placeholders beside staged .fastq.gz links.

    Snakescale can produce .fastq.gz via its download+gzip rules. The empty
    placeholders make the existing .fastq.gz files look newer, so Snakemake
    treats them as already available local inputs.
    """
    if not staged_root.is_dir():
        raise FileNotFoundError(f"staged FASTQ directory missing: {staged_root}")

    count = 0
    for gz_path in sorted(staged_root.rglob("*.fastq.gz")):
        plain_path = gz_path.with_suffix("")
        plain_path.touch(exist_ok=True)
        gz_mtime = gz_path.stat().st_mtime
        placeholder_mtime = max(0, gz_mtime - PLACEHOLDER_AGE_SECONDS)
        os.utime(plain_path, (placeholder_mtime, placeholder_mtime))
        count += 1
    return count
