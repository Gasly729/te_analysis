"""test_config — smoke tests for te_analysis.config.load_paths."""
from __future__ import annotations

from pathlib import Path

import pytest

from te_analysis.config import REPO_ROOT, load_paths


def test_repo_root_is_repo_marker() -> None:
    """REPO_ROOT should contain pyproject.toml (project marker)."""
    assert (REPO_ROOT / "pyproject.toml").is_file()


def test_load_paths_returns_absolute_paths() -> None:
    paths = load_paths()
    assert set(paths.keys()) >= {"data", "vendor", "references"}
    for section, body in paths.items():
        for key, value in body.items():
            assert value.is_absolute(), f"{section}.{key} = {value} (not absolute)"


def test_load_paths_anchors_at_repo_root() -> None:
    paths = load_paths()
    assert paths["data"]["raw_fastq"] == REPO_ROOT / "data" / "raw" / "fastq"
    assert paths["vendor"]["snakescale"] == REPO_ROOT / "vendor" / "snakescale"


def test_load_paths_raises_on_missing_section(tmp_path: Path) -> None:
    bad = tmp_path / "bad.toml"
    bad.write_text('[data]\nraw = "data/raw"\n')  # missing vendor / references
    with pytest.raises(KeyError, match="vendor|references"):
        load_paths(bad)


def test_load_paths_raises_on_missing_file(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_paths(tmp_path / "does_not_exist.toml")
