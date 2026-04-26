"""Unit tests for te_analysis.run_downstream (module_contracts §M3).

DoD §4.4 numerical alignment is downscoped (T9 + T14 scope); this file
validates command structure + config.py generation + product rename.
All subprocess.run calls are mocked; no real TE.R execution.
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from te_analysis.config import REPO_ROOT
from te_analysis.run_downstream import (
    PRODUCTS,
    TE_MODEL_RIBO_DATA,
    TE_MODEL_TRIALS,
    VENDOR_TE_MODEL,
    _copy_products,
    _inject_ribo_input,
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


def test_write_trial_patches_alias_for_nonhuman(tmp_path: Path) -> None:
    trial_dir = tmp_path / "trials" / "GSE132441"
    _write_trial(trial_dir, ["GSM1"], organism="Arabidopsis thaliana")
    config_text = (trial_dir / "config.py").read_text()
    assert "ribopy.api.alias.apris_human_alias = _identity_alias" in config_text
    compile(config_text, str(trial_dir / "config.py"), "exec")


def test_inject_ribo_input_links_study_output(tmp_path: Path) -> None:
    study_dir = tmp_path / "GSE132441"
    (study_dir / "ribo").mkdir(parents=True)
    (study_dir / "ribo" / "all.ribo").write_bytes(b"ribo")
    expected_link = TE_MODEL_RIBO_DATA / "GSE132441"
    try:
        link = _inject_ribo_input(study_dir, "GSE132441")
        assert link == expected_link
        assert link.is_symlink()
        assert link.resolve() == study_dir.resolve()
    finally:
        if expected_link.exists() or expected_link.is_symlink():
            expected_link.unlink()


def test_copy_products_renames_human_prefix(tmp_path: Path) -> None:
    trial_dir = tmp_path / "trial"
    trial_dir.mkdir()
    for name in PRODUCTS:
        if name.endswith(".csv"):
            (trial_dir / name).write_text(",GSM1\nGENE1,1\n")
        else:
            (trial_dir / name).write_bytes(b"stub")
    out_dir = tmp_path / "out"
    n = _copy_products(trial_dir, out_dir, "Arabidopsis thaliana", "GSE132441")
    assert n == 4
    assert (out_dir / "arabidopsis_thaliana_TE_cellline_all.csv").is_file()
    assert (out_dir / "arabidopsis_thaliana_TE_cellline_all_T.csv").is_file()
    assert (out_dir / "arabidopsis_thaliana_TE_sample_level.rda").is_file()
    assert (out_dir / "GSE132441_TE.csv").is_file()


def test_copy_products_skips_missing(tmp_path: Path) -> None:
    trial_dir = tmp_path / "trial"
    trial_dir.mkdir()
    (trial_dir / PRODUCTS[0]).write_text(",GSM1\nGENE1,1\n")
    n = _copy_products(trial_dir, tmp_path / "out", "Homo sapiens", "GSE132441")
    assert n == 2


def test_missing_study_dir_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="--study-dir not a directory"):
        main(["--study-dir", str(tmp_path / "ghost"),
              "--out-dir", str(tmp_path / "out")])


def test_main_end_to_end_mocked(tmp_path: Path) -> None:
    study_dir = tmp_path / "GSE132441"
    (study_dir / "ribo").mkdir(parents=True)
    (study_dir / "project.yaml").write_text("do_fastqc: true\n")
    (study_dir / "ribo" / "all.ribo").write_bytes(b"ribo")
    out_dir = tmp_path / "out"
    trial_dir = TE_MODEL_TRIALS / "GSE132441"
    ribo_link = TE_MODEL_RIBO_DATA / "GSE132441"

    def fake_run(cmd, cwd, check, **_):
        assert cwd == VENDOR_TE_MODEL
        assert check is False
        if cmd[1:3] == ["-m", "trials.GSE132441.config"]:
            (trial_dir / "ribo_raw.csv").write_text(",GSM1\nGENE1,1\n")
            (trial_dir / "rnaseq_raw.csv").write_text(",GSM1\nGENE1,1\n")
        elif cmd[1] == "src/ribobase_counts_processing.py":
            (trial_dir / "ribo_paired_count_dummy.csv").write_text(",GSM1\nGENE1,1\n")
            (trial_dir / "rna_paired_count_dummy.csv").write_text(",GSM1\nGENE1,1\n")
        elif cmd[0] == "Rscript":
            (trial_dir / "human_TE_cellline_all.csv").write_text(",GENE1\nHeLa,1\n")
            (trial_dir / "human_TE_sample_level.rda").write_bytes(b"stub")
        elif cmd[1] == "src/transpose_TE.py":
            (trial_dir / "human_TE_cellline_all_T.csv").write_text(",HeLa\nGENE1,1\n")
        else:
            raise AssertionError(cmd)
        return MagicMock(returncode=0)

    try:
        with patch("te_analysis.run_downstream.subprocess.run", side_effect=fake_run):
            rc = main(["--study-dir", str(study_dir), "--out-dir", str(out_dir)])
        assert rc == 0
        assert (out_dir / "arabidopsis_thaliana_TE_cellline_all_T.csv").is_file()
        assert (out_dir / "GSE132441_TE.csv").is_file()
        assert (trial_dir / "config.py").is_file()
        assert ribo_link.is_symlink()
    finally:
        if ribo_link.exists() or ribo_link.is_symlink():
            ribo_link.unlink()
        # Clean up vendor trials artifact so vendor stays pristine between runs
        if trial_dir.exists():
            for name in (
                "__init__.py",
                "config.py",
                "ribo_raw.csv",
                "rnaseq_raw.csv",
                "ribo_paired_count_dummy.csv",
                "rna_paired_count_dummy.csv",
                *PRODUCTS,
            ):
                f = trial_dir / name
                if f.is_file():
                    f.unlink()
            try:
                trial_dir.rmdir()
            except OSError:
                pass


def test_nonzero_subprocess_propagates(tmp_path: Path) -> None:
    study_dir = tmp_path / "GSE132441"
    (study_dir / "ribo").mkdir(parents=True)
    (study_dir / "ribo" / "all.ribo").write_bytes(b"ribo")
    trial_dir = TE_MODEL_TRIALS / "GSE132441"
    ribo_link = TE_MODEL_RIBO_DATA / "GSE132441"
    try:
        with patch("te_analysis.run_downstream.subprocess.run",
                   return_value=MagicMock(returncode=3)):
            assert main(["--study-dir", str(study_dir),
                         "--out-dir", str(tmp_path / "out")]) == 3
    finally:
        if ribo_link.exists() or ribo_link.is_symlink():
            ribo_link.unlink()
        if trial_dir.exists():
            for name in ("__init__.py", "config.py"):
                f = trial_dir / name
                if f.is_file():
                    f.unlink()
            try:
                trial_dir.rmdir()
            except OSError:
                pass
