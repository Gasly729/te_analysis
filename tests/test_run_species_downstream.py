"""Tests for te_analysis.run_species_downstream."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from te_analysis.run_species_downstream import (
    INFOR_FILTER_NAME,
    SERIAL_PATCH_TARGET,
    STAGE1_PRODUCTS,
    STAGE2_PRODUCTS,
    STAGE3_PRODUCT,
    _build_serial_te_r,
    _discover_runtime_root,
    _extract_custom_experiment_list,
    _materialize_runtime_infor_filter,
    _validate_stage1_products,
    main,
)


def _touch(path: Path, data: bytes = b"stub") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def test_discover_runtime_root_from_species_root(tmp_path: Path) -> None:
    species_root = tmp_path / "te_species" / "Homo_sapiens"
    config = species_root / "runtime" / "vendor" / "TE_model" / "trials" / "homo_sapiens_species_te_prepare" / "config.py"
    _touch(config)
    runtime_root, trial_dir = _discover_runtime_root(species_root, None)
    assert runtime_root == config.parents[2]
    assert trial_dir == config.parent


def test_validate_stage1_products_requires_nonempty_files(tmp_path: Path) -> None:
    trial_dir = tmp_path / "trial"
    for name in STAGE1_PRODUCTS:
        _touch(trial_dir / name)
    _validate_stage1_products(trial_dir)
    (trial_dir / STAGE1_PRODUCTS[0]).write_bytes(b"")
    with pytest.raises(ValueError, match="is empty"):
        _validate_stage1_products(trial_dir)


def test_build_serial_te_r_removes_parallel_constructs() -> None:
    source_text = """library(foreach)\nlibrary(doParallel)\ncl <- makeCluster(1)\nregisterDoParallel(cl)\nout <- foreach(i = 1:3) %dopar% {\n  i\n}\nstopCluster(cl)\n"""
    patched, replacements = _build_serial_te_r(source_text)
    assert "library(doParallel)" not in patched
    assert "makeCluster(" not in patched
    assert "registerDoParallel(" not in patched
    assert "stopCluster(" not in patched
    assert "%dopar%" not in patched
    assert "%do%" in patched
    assert replacements["dopar_replaced"] == 1
    assert "library(doParallel)" in source_text


def test_extract_custom_experiment_list_from_trial_config(tmp_path: Path) -> None:
    config_path = tmp_path / "config.py"
    config_path.write_text(
        'from src.ribo_counts_to_csv import main\n'
        'main(workdir=".", sample_filter=lambda df: df, custom_experiment_list=["GSM1", "GSM2"])\n',
        encoding="utf-8",
    )
    assert _extract_custom_experiment_list(config_path) == ["GSM1", "GSM2"]


def test_materialize_runtime_infor_filter_adds_runtime_local_rows(tmp_path: Path) -> None:
    vendor_root = tmp_path / "vendor" / "TE_model"
    (vendor_root / "data").mkdir(parents=True)
    pd.DataFrame(
        [
            {"Unnamed: 0": "1", "experiment_alias": "GSM_EXISTING", "cell_line": "HeLa"},
        ]
    ).to_csv(vendor_root / "data" / INFOR_FILTER_NAME, index=False)

    metadata_path = tmp_path / "metadata.csv"
    metadata_path.write_text(
        "ignored,ignored,ignored\n"
        "experiment_alias,cell_line,study_name,corrected_type\n"
        "GSM_A1,arabidopsis_leaf,GSE50597,Ribo-Seq\n"
        "GSM_A2,,GSE109122,Ribo-Seq\n",
        encoding="utf-8",
    )

    species_root = tmp_path / "te_species" / "Arabidopsis_thaliana"
    runtime_root = species_root / "runtime" / "vendor" / "TE_model"
    trial_dir = runtime_root / "trials" / "arabidopsis_thaliana_species_te_prepare"
    _touch(
        trial_dir / "config.py",
        (
            b"from src.ribo_counts_to_csv import main\n"
            b'main(workdir=".", sample_filter=lambda df: df, custom_experiment_list=["GSM_A1", "GSM_A2"])\n'
        ),
    )

    runtime_path, patch_log = _materialize_runtime_infor_filter(
        species_root=species_root,
        runtime_root=runtime_root,
        trial_dir=trial_dir,
        vendor_root=vendor_root,
        metadata_path=metadata_path,
        stamp="20260422_000000",
        bounded_studies=["GSE50597", "GSE109122"],
    )

    assert runtime_path == runtime_root / "data" / INFOR_FILTER_NAME
    assert patch_log.is_file()
    runtime_df = pd.read_csv(runtime_path, dtype=str, keep_default_na=False)
    assert set(runtime_df["experiment_alias"]) == {"GSM_EXISTING", "GSM_A1", "GSM_A2"}
    assert runtime_df.loc[runtime_df["experiment_alias"] == "GSM_A1", "cell_line"].iloc[0] == "arabidopsis_leaf"
    assert runtime_df.loc[runtime_df["experiment_alias"] == "GSM_A2", "cell_line"].iloc[0] == ""
    shared_df = pd.read_csv(vendor_root / "data" / INFOR_FILTER_NAME, dtype=str, keep_default_na=False)
    assert list(shared_df["experiment_alias"]) == ["GSM_EXISTING"]


def test_main_runs_shared_vendor_stage2_and_stage3(tmp_path: Path) -> None:
    vendor_root = tmp_path / "vendor" / "TE_model"
    (vendor_root / "src").mkdir(parents=True)
    source_te_r = vendor_root / "src" / "TE.R"
    source_te_r.write_text(
        "library(foreach)\n"
        "library(doParallel)\n"
        "cl <- makeCluster(1)\n"
        "registerDoParallel(cl)\n"
        "out <- foreach(i = 1:3) %dopar% {\n"
        "  i\n"
        "}\n"
        "stopCluster(cl)\n",
        encoding="utf-8",
    )
    _touch(vendor_root / "src" / "transpose_TE.py")
    species_root = tmp_path / "te_species" / "Homo_sapiens"
    trial_dir = (
        species_root
        / "runtime"
        / "vendor"
        / "TE_model"
        / "trials"
        / "homo_sapiens_species_te_prepare"
    )
    _touch(trial_dir / "config.py")
    for name in STAGE1_PRODUCTS:
        _touch(trial_dir / name)

    commands: list[tuple[list[str], Path]] = []

    def fake_run(cmd, cwd, check, stdout, stderr, text):  # type: ignore[no-untyped-def]
        assert check is False
        assert stderr == -2
        assert text is True
        commands.append((cmd, cwd))
        if cmd[0] == "/path/to/Rscript" and cmd[2] == str(trial_dir.resolve()):
            for name in STAGE2_PRODUCTS:
                _touch(trial_dir / name)
        elif Path(cmd[1]).name == "transpose_TE.py":
            _touch(trial_dir / STAGE3_PRODUCT)
        return MagicMock(returncode=0)

    with patch("te_analysis.run_species_downstream.subprocess.run", side_effect=fake_run):
        rc = main(
            [
                "--species-root",
                str(species_root),
                "--vendor-root",
                str(vendor_root),
                "--rscript-bin",
                "/path/to/Rscript",
                "--python-bin",
                "/path/to/python",
                "--stage2-mode",
                "serial-fallback",
            ]
        )

    assert rc == 0
    assert commands[0][0][0] == "/path/to/Rscript"
    assert commands[0][0][2] == str(trial_dir.resolve())
    patched_te_r = Path(commands[0][0][1])
    assert patched_te_r.name.startswith(SERIAL_PATCH_TARGET)
    assert patched_te_r.is_file()
    patched_text = patched_te_r.read_text(encoding="utf-8")
    assert "%do%" in patched_text
    assert "%dopar%" not in patched_text
    assert "library(doParallel)" not in patched_text
    assert commands[0][1] == vendor_root
    assert commands[1][0] == [
        "/path/to/python",
        str((vendor_root / "src" / "transpose_TE.py").resolve()),
        "-o",
        str(trial_dir.resolve()),
    ]
    assert commands[1][1] == vendor_root
    assert "library(doParallel)" in source_te_r.read_text(encoding="utf-8")
    patch_logs = sorted((species_root / "logs").glob("TE.serial.patch.*.log"))
    assert len(patch_logs) == 1


def test_main_materializes_runtime_local_infor_filter_without_running_stage2(tmp_path: Path) -> None:
    vendor_root = tmp_path / "vendor" / "TE_model"
    (vendor_root / "src").mkdir(parents=True)
    (vendor_root / "data").mkdir(parents=True)
    _touch(vendor_root / "src" / "TE.R")
    pd.DataFrame(
        [{"Unnamed: 0": "1", "experiment_alias": "GSM_EXISTING", "cell_line": "HeLa"}]
    ).to_csv(vendor_root / "data" / INFOR_FILTER_NAME, index=False)

    metadata_path = tmp_path / "metadata.csv"
    metadata_path.write_text(
        "ignored,ignored,ignored\n"
        "experiment_alias,cell_line,study_name,corrected_type\n"
        "GSM_A1,arabidopsis_leaf,GSE50597,Ribo-Seq\n"
        "GSM_A2,,GSE109122,Ribo-Seq\n",
        encoding="utf-8",
    )

    species_root = tmp_path / "te_species" / "Arabidopsis_thaliana"
    trial_dir = (
        species_root
        / "runtime"
        / "vendor"
        / "TE_model"
        / "trials"
        / "arabidopsis_thaliana_species_te_prepare"
    )
    _touch(
        trial_dir / "config.py",
        (
            b"from src.ribo_counts_to_csv import main\n"
            b'main(workdir=".", sample_filter=lambda df: df, custom_experiment_list=["GSM_A1", "GSM_A2"])\n'
        ),
    )
    for name in STAGE1_PRODUCTS:
        _touch(trial_dir / name)

    with patch("te_analysis.run_species_downstream.subprocess.run") as mocked_run:
        rc = main(
            [
                "--species-root",
                str(species_root),
                "--vendor-root",
                str(vendor_root),
                "--metadata",
                str(metadata_path),
                "--infor-filter-mode",
                "runtime-local",
                "--bounded-study",
                "GSE50597",
                "--bounded-study",
                "GSE109122",
                "--materialize-infor-filter-only",
            ]
        )

    assert rc == 0
    mocked_run.assert_not_called()
    runtime_infor = species_root / "runtime" / "vendor" / "TE_model" / "data" / INFOR_FILTER_NAME
    assert runtime_infor.is_file()
    runtime_df = pd.read_csv(runtime_infor, dtype=str, keep_default_na=False)
    assert set(runtime_df["experiment_alias"]) == {"GSM_EXISTING", "GSM_A1", "GSM_A2"}
    bridge_logs = sorted((species_root / "logs").glob("infor_filter.bridge.*.log"))
    assert len(bridge_logs) == 1


def test_main_runtime_local_stage2_uses_runtime_cwd_and_shared_script(tmp_path: Path) -> None:
    vendor_root = tmp_path / "vendor" / "TE_model"
    (vendor_root / "src").mkdir(parents=True)
    (vendor_root / "data").mkdir(parents=True)
    source_te_r = vendor_root / "src" / "TE.R"
    source_te_r.write_text("library(foreach)\nout <- foreach(i = 1:3) %dopar% { i }\n", encoding="utf-8")
    _touch(vendor_root / "src" / "transpose_TE.py")
    pd.DataFrame(
        [{"Unnamed: 0": "1", "experiment_alias": "GSM_EXISTING", "cell_line": "HeLa"}]
    ).to_csv(vendor_root / "data" / INFOR_FILTER_NAME, index=False)

    metadata_path = tmp_path / "metadata.csv"
    metadata_path.write_text(
        "ignored,ignored,ignored\n"
        "experiment_alias,cell_line,study_name,corrected_type\n"
        "GSM_A1,arabidopsis_leaf,GSE50597,Ribo-Seq\n"
        "GSM_A2,,GSE109122,Ribo-Seq\n",
        encoding="utf-8",
    )

    species_root = tmp_path / "te_species" / "Arabidopsis_thaliana"
    runtime_root = species_root / "runtime" / "vendor" / "TE_model"
    trial_dir = runtime_root / "trials" / "arabidopsis_thaliana_species_te_prepare"
    _touch(
        trial_dir / "config.py",
        (
            b"from src.ribo_counts_to_csv import main\n"
            b'main(workdir=".", sample_filter=lambda df: df, custom_experiment_list=["GSM_A1", "GSM_A2"])\n'
        ),
    )
    for name in STAGE1_PRODUCTS:
        _touch(trial_dir / name)

    commands: list[tuple[list[str], Path]] = []

    def fake_run(cmd, cwd, check, stdout, stderr, text):  # type: ignore[no-untyped-def]
        commands.append((cmd, cwd))
        for name in STAGE2_PRODUCTS:
            _touch(trial_dir / name)
        if Path(cmd[1]).name == "transpose_TE.py":
            _touch(trial_dir / STAGE3_PRODUCT)
        return MagicMock(returncode=0)

    with patch("te_analysis.run_species_downstream.subprocess.run", side_effect=fake_run):
        rc = main(
            [
                "--species-root",
                str(species_root),
                "--vendor-root",
                str(vendor_root),
                "--metadata",
                str(metadata_path),
                "--rscript-bin",
                "/path/to/Rscript",
                "--python-bin",
                "/path/to/python",
                "--stage2-mode",
                "shared",
                "--infor-filter-mode",
                "runtime-local",
                "--bounded-study",
                "GSE50597",
                "--bounded-study",
                "GSE109122",
            ]
        )

    assert rc == 0
    assert commands[0][0] == [
        "/path/to/Rscript",
        str((vendor_root / "src" / "TE.R").resolve()),
        str(trial_dir.resolve()),
    ]
    assert commands[0][1] == runtime_root
    assert commands[1][0] == [
        "/path/to/python",
        str((vendor_root / "src" / "transpose_TE.py").resolve()),
        "-o",
        str(trial_dir.resolve()),
    ]
    assert commands[1][1] == vendor_root


def test_main_stops_when_stage2_outputs_missing(tmp_path: Path) -> None:
    vendor_root = tmp_path / "vendor" / "TE_model"
    (vendor_root / "src").mkdir(parents=True)
    _touch(vendor_root / "src" / "TE.R")
    species_root = tmp_path / "te_species" / "Homo_sapiens"
    trial_dir = (
        species_root
        / "runtime"
        / "vendor"
        / "TE_model"
        / "trials"
        / "homo_sapiens_species_te_prepare"
    )
    _touch(trial_dir / "config.py")
    for name in STAGE1_PRODUCTS:
        _touch(trial_dir / name)

    with patch(
        "te_analysis.run_species_downstream.subprocess.run",
        return_value=MagicMock(returncode=0),
    ):
        rc = main(
            [
                "--species-root",
                str(species_root),
                "--vendor-root",
                str(vendor_root),
                "--stage2-mode",
                "shared",
            ]
        )

    assert rc == 2
