"""Unit tests for te_analysis.run_downstream (module_contracts §M3).

DoD §4.4 numerical alignment is downscoped (T9 + T14 scope); this file
validates command structure + config.py generation + product rename.
All subprocess.run calls are mocked; no real TE.R / pipeline.bash execution.
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from te_analysis.config import REPO_ROOT
from te_analysis.run_downstream import (
    PRODUCTS,
    TE_MODEL_TRIALS,
    VENDOR_TE_MODEL,
    _copy_products,
    _load,
    _write_trial,
    main,
)

METADATA = REPO_ROOT / "data" / "raw" / "metadata.csv"


def test_load_returns_experiments_and_organism(tmp_path: Path) -> None:
    experiments, organism = _load(METADATA, "GSE132441")
    assert len(experiments) == 6  # 3 Ribo + 3 RNA
    assert all(e.startswith("GSM") for e in experiments)
    assert organism == "Arabidopsis thaliana"


def test_load_unknown_study_raises(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="not in metadata.csv"):
        _load(METADATA, "GSENONE")


def test_load_missing_metadata_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="metadata.csv not found"):
        _load(tmp_path / "ghost.csv", "GSE132441")


def test_write_trial_creates_module_files(tmp_path: Path) -> None:
    trial_dir = tmp_path / "trials" / "GSE132441"
    _write_trial(trial_dir, ["GSM1", "GSM2"])
    assert (trial_dir / "__init__.py").is_file()
    config_text = (trial_dir / "config.py").read_text()
    assert "from src.ribo_counts_to_csv import main" in config_text
    assert "custom_experiment_list=['GSM1', 'GSM2']" in config_text
    assert "ribo_dedup=False" in config_text
    assert "rna_seq_dedup=False" in config_text


def test_copy_products_renames_human_prefix(tmp_path: Path) -> None:
    trial_dir = tmp_path / "trial"
    trial_dir.mkdir()
    for name in PRODUCTS:
        (trial_dir / name).write_bytes(b"stub")
    out_dir = tmp_path / "out"
    n = _copy_products(trial_dir, out_dir, "Arabidopsis thaliana")
    assert n == 3
    assert (out_dir / "arabidopsis_thaliana_TE_cellline_all.csv").is_file()
    assert (out_dir / "arabidopsis_thaliana_TE_cellline_all_T.csv").is_file()
    assert (out_dir / "arabidopsis_thaliana_TE_sample_level.rda").is_file()


def test_copy_products_skips_missing(tmp_path: Path) -> None:
    trial_dir = tmp_path / "trial"
    trial_dir.mkdir()
    (trial_dir / PRODUCTS[0]).write_bytes(b"stub")
    n = _copy_products(trial_dir, tmp_path / "out", "Homo sapiens")
    assert n == 1


def test_missing_study_dir_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="--study-dir not a directory"):
        main(["--study-dir", str(tmp_path / "ghost"),
              "--out-dir", str(tmp_path / "out")])


def test_main_end_to_end_mocked(tmp_path: Path) -> None:
    study_dir = tmp_path / "GSE132441"
    study_dir.mkdir()
    (study_dir / "project.yaml").write_text("do_fastqc: true\n")
    out_dir = tmp_path / "out"
    trial_dir = TE_MODEL_TRIALS / "GSE132441"

    def fake_run(cmd, cwd, check, **_):
        assert cmd == ["bash", "pipeline.bash", "-t", "GSE132441"]
        assert cwd == VENDOR_TE_MODEL
        assert check is False
        # Simulate TE.R products produced under trials/<study>/
        for name in PRODUCTS:
            (trial_dir / name).write_bytes(b"stub")
        return MagicMock(returncode=0)

    try:
        with patch("te_analysis.run_downstream.subprocess.run", side_effect=fake_run):
            rc = main(["--study-dir", str(study_dir), "--out-dir", str(out_dir)])
        assert rc == 0
        assert (out_dir / "arabidopsis_thaliana_TE_cellline_all_T.csv").is_file()
        assert (trial_dir / "config.py").is_file()
    finally:
        # Clean up vendor trials artifact so vendor stays pristine between runs
        if trial_dir.exists():
            for name in ("__init__.py", "config.py", *PRODUCTS):
                f = trial_dir / name
                if f.is_file():
                    f.unlink()
            try:
                trial_dir.rmdir()
            except OSError:
                pass


def test_nonzero_subprocess_propagates(tmp_path: Path) -> None:
    study_dir = tmp_path / "GSE132441"
    study_dir.mkdir()
    trial_dir = TE_MODEL_TRIALS / "GSE132441"
    try:
        with patch("te_analysis.run_downstream.subprocess.run",
                   return_value=MagicMock(returncode=3)):
            assert main(["--study-dir", str(study_dir),
                         "--out-dir", str(tmp_path / "out")]) == 3
    finally:
        if trial_dir.exists():
            for name in ("__init__.py", "config.py"):
                f = trial_dir / name
                if f.is_file():
                    f.unlink()
            try:
                trial_dir.rmdir()
            except OSError:
                pass
