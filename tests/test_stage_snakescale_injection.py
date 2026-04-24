"""Unit tests for snakescale runtime FASTQ injection."""
from __future__ import annotations

from pathlib import Path

import pytest

from te_analysis.stage_snakescale_injection import (
    inject_staged_fastq,
    prepare_download_bypass,
)


def _make_staged_tree(tmp_path: Path, study: str = "GSE132441") -> Path:
    """Create a minimal staged FASTQ tree."""
    staged = tmp_path / study / "staged_fastq" / study / "GSM1"
    staged.mkdir(parents=True)
    (staged / "SRR1_1.fastq.gz").write_text("gz\n")
    return tmp_path / study


def test_inject_staged_fastq_links_vendor_visible_tree(tmp_path: Path) -> None:
    study_dir = _make_staged_tree(tmp_path)
    vendor_root = tmp_path / "vendor" / "snakescale"

    link = inject_staged_fastq(study_dir, vendor_root, "GSE132441")

    assert link.is_symlink()
    assert link.resolve() == (study_dir / "staged_fastq" / "GSE132441").resolve()


def test_inject_staged_fastq_refuses_real_directory(tmp_path: Path) -> None:
    study_dir = _make_staged_tree(tmp_path)
    vendor_root = tmp_path / "vendor" / "snakescale"
    (vendor_root / "staged_fastq" / "GSE132441").mkdir(parents=True)

    with pytest.raises(FileExistsError, match="not a symlink"):
        inject_staged_fastq(study_dir, vendor_root, "GSE132441")


def test_prepare_download_bypass_creates_older_plain_fastq(tmp_path: Path) -> None:
    study_dir = _make_staged_tree(tmp_path)
    staged_root = study_dir / "staged_fastq" / "GSE132441"
    gz_path = staged_root / "GSM1" / "SRR1_1.fastq.gz"

    count = prepare_download_bypass(staged_root)

    plain_path = staged_root / "GSM1" / "SRR1_1.fastq"
    assert count == 1
    assert plain_path.is_file()
    assert plain_path.stat().st_size == 0
    assert plain_path.stat().st_mtime < gz_path.stat().st_mtime
