"""Unit tests for te_analysis.run_upstream (module_contracts §M2).

Does not invoke real snakemake (E2E is T8). Mocks subprocess.run.
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from te_analysis.run_upstream import (
    SNAKESCALE_PROJECT_DIR,
    VENDOR_SNAKESCALE,
    build_command,
    main,
)


def _make_study_dir(tmp_path: Path, study: str = "GSE132441") -> Path:
    """Create <tmp>/{study}/project.yaml and return the dir."""
    d = tmp_path / study
    d.mkdir()
    (d / "project.yaml").write_text("do_fastqc: true\n")
    gse_only = study.split("_", 1)[0]
    staged = d / "staged_fastq" / gse_only / "GSM1"
    staged.mkdir(parents=True)
    (staged / "SRR1_1.fastq.gz").write_text("gz\n")
    return d


def test_missing_study_dir_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="--study-dir not a directory"):
        main(["--study-dir", str(tmp_path / "ghost")])


def test_missing_project_yaml_raises(tmp_path: Path) -> None:
    d = tmp_path / "GSE132441"
    d.mkdir()
    with pytest.raises(FileNotFoundError, match="project.yaml missing"):
        main(["--study-dir", str(d)])


def test_build_command_structure() -> None:
    cmd = build_command("GSE132441", 8)
    assert cmd == ["snakemake", "-p", "--cores", "8",
                   "--config", "studies=['GSE132441']",
                   "adapter_threshold=0"]


def test_build_command_extra_config_and_nolock() -> None:
    cmd = build_command(
        "GSE999999",
        2,
        extra_config=["rerun_incomplete=True"],
        extra_args=["--rerun-triggers", "mtime"],
        nolock=True,
    )
    assert cmd == ["snakemake", "-p", "--cores", "2",
                   "--config", "studies=['GSE999999']",
                   "rerun_incomplete=True", "--nolock",
                   "--rerun-triggers", "mtime"]


def test_symlink_and_subprocess_call(tmp_path: Path) -> None:
    d = _make_study_dir(tmp_path, "GSE132441")
    expected_link = SNAKESCALE_PROJECT_DIR / "GSE132441" / "GSE132441.yaml"
    expected_staged_link = VENDOR_SNAKESCALE / "staged_fastq" / "GSE132441"
    try:
        with patch("te_analysis.run_upstream.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            rc = main(["--study-dir", str(d), "--cores", "2"])
        assert rc == 0
        assert expected_link.is_symlink()
        assert expected_link.resolve() == (d / "project.yaml").resolve()
        assert expected_staged_link.is_symlink()
        assert (d / "staged_fastq" / "GSE132441" / "GSM1" / "SRR1_1.fastq").is_file()
        mock_run.assert_called_once()
        args, kwargs = mock_run.call_args
        assert args[0] == ["snakemake", "-p", "--cores", "2",
                           "--config", "studies=['GSE132441']",
                           "adapter_threshold=0"]
        assert kwargs["cwd"] == VENDOR_SNAKESCALE
        assert kwargs["check"] is False
        assert kwargs["env"]["XDG_CACHE_HOME"] == "/tmp/snakemake-cache"
    finally:
        if expected_link.exists() or expected_link.is_symlink():
            expected_link.unlink()
        if expected_staged_link.exists() or expected_staged_link.is_symlink():
            expected_staged_link.unlink()


def test_dedup_suffix_supported(tmp_path: Path) -> None:
    d = _make_study_dir(tmp_path, "GSE132441_dedup")
    expected_link = SNAKESCALE_PROJECT_DIR / "GSE132441" / "GSE132441_dedup.yaml"
    expected_staged_link = VENDOR_SNAKESCALE / "staged_fastq" / "GSE132441"
    try:
        with patch("te_analysis.run_upstream.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            main(["--study-dir", str(d)])
        assert expected_link.is_symlink()
        # Command carries the full suffixed study name
        assert "studies=['GSE132441_dedup']" in mock_run.call_args.args[0]
        assert "adapter_threshold=0" in mock_run.call_args.args[0]
    finally:
        if expected_link.exists() or expected_link.is_symlink():
            expected_link.unlink()
        if expected_staged_link.exists() or expected_staged_link.is_symlink():
            expected_staged_link.unlink()


def test_nonzero_exit_propagates(tmp_path: Path) -> None:
    d = _make_study_dir(tmp_path, "GSE132441")
    expected_link = SNAKESCALE_PROJECT_DIR / "GSE132441" / "GSE132441.yaml"
    expected_staged_link = VENDOR_SNAKESCALE / "staged_fastq" / "GSE132441"
    try:
        with patch("te_analysis.run_upstream.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=2)
            assert main(["--study-dir", str(d)]) == 2
    finally:
        if expected_link.exists() or expected_link.is_symlink():
            expected_link.unlink()
        if expected_staged_link.exists() or expected_staged_link.is_symlink():
            expected_staged_link.unlink()


def test_invalid_snakemake_config_raises(tmp_path: Path) -> None:
    d = _make_study_dir(tmp_path, "GSE999999")
    with pytest.raises(ValueError, match="KEY=VALUE"):
        main(["--study-dir", str(d), "--snakemake-config", "broken"])
