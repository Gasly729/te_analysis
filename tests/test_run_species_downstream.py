"""Tests for te_analysis.run_species_downstream."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from te_analysis.run_species_downstream import (
    SERIAL_PATCH_TARGET,
    STAGE1_PRODUCTS,
    STAGE2_PRODUCTS,
    STAGE3_PRODUCT,
    _build_serial_te_r,
    _discover_runtime_root,
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
        elif cmd[1] == "src/transpose_TE.py":
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
    assert commands[1][0] == ["/path/to/python", "src/transpose_TE.py", "-o", str(trial_dir.resolve())]
    assert commands[1][1] == vendor_root
    assert "library(doParallel)" in source_te_r.read_text(encoding="utf-8")
    patch_logs = sorted((species_root / "logs").glob("TE.serial.patch.*.log"))
    assert len(patch_logs) == 1


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
