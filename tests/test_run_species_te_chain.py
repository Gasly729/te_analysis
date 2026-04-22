"""Tests for te_analysis.run_species_te_chain."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from te_analysis.run_species_te_chain import (
    CANONICAL_CSV_NAME,
    _check_canonical_csv,
    _default_trial_name,
    main,
)


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _touch_runtime(species_root: Path, trial_name: str) -> Path:
    trial_dir = (
        species_root
        / "runtime"
        / "vendor"
        / "TE_model"
        / "trials"
        / trial_name
    )
    _write(trial_dir / "config.py", "stub = True\n")
    return trial_dir


def test_prepare_only_dispatches_to_aggregate(tmp_path: Path) -> None:
    species_root = tmp_path / "te_species" / "Homo_sapiens"
    with patch("te_analysis.run_species_te_chain.aggregate_main", return_value=0) as aggregate_mock:
        rc = main(
            [
                "--organism",
                "Homo_sapiens",
                "--out-dir",
                str(species_root),
                "--metadata",
                str(tmp_path / "metadata.csv"),
                "--prepare",
            ]
        )

    assert rc == 0
    aggregate_argv = aggregate_mock.call_args.args[0]
    assert aggregate_argv[:4] == ["--organism", "Homo_sapiens", "--prepare-only", "--out-dir"]
    assert "--ribo-glob" not in aggregate_argv


def test_downstream_only_dispatches_to_species_runner(tmp_path: Path) -> None:
    species_root = tmp_path / "te_species" / "Homo_sapiens"
    _touch_runtime(species_root, "homo_sapiens_species_te_prepare")
    with patch("te_analysis.run_species_te_chain.downstream_main", return_value=0) as downstream_mock:
        rc = main(
            [
                "--organism",
                "Homo_sapiens",
                "--out-dir",
                str(species_root),
                "--trial",
                "homo_sapiens_species_te_prepare",
                "--run-downstream",
            ]
        )

    assert rc == 0
    downstream_argv = downstream_mock.call_args.args[0]
    assert downstream_argv[0:4] == ["--species-root", str(species_root), "--trial", "homo_sapiens_species_te_prepare"]
    assert "--stage2-mode" in downstream_argv
    assert downstream_argv[downstream_argv.index("--stage2-mode") + 1] == "serial-fallback"


def test_check_output_only_uses_canonical_csv_and_not_t_file(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    species_root = tmp_path / "te_species" / "Homo_sapiens"
    trial_name = _default_trial_name("Homo_sapiens")
    trial_dir = _touch_runtime(species_root, trial_name)
    _write(
        trial_dir / CANONICAL_CSV_NAME,
        ",feature_a,feature_b\nHeLa,1.0,2.0\nBJ,3.0,4.0\n",
    )

    rc = main(
        [
            "--organism",
            "Homo_sapiens",
            "--out-dir",
            str(species_root),
            "--check-output",
        ]
    )

    assert rc == 0
    output = capsys.readouterr().out
    assert "canonical CSV ready" in output
    assert "human_TE_cellline_all_T.csv" not in output


def test_prepare_downstream_check_chain_dispatches_in_order(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    species_root = tmp_path / "te_species" / "Homo_sapiens"
    trial_name = _default_trial_name("Homo_sapiens")
    trial_dir = _touch_runtime(species_root, trial_name)

    def fake_downstream(argv: list[str]) -> int:
        _write(
            trial_dir / CANONICAL_CSV_NAME,
            ",feature_a,feature_b\nHeLa,1.0,2.0\nBJ,3.0,4.0\n",
        )
        return 0

    with patch("te_analysis.run_species_te_chain.aggregate_main", return_value=0) as aggregate_mock, patch(
        "te_analysis.run_species_te_chain.downstream_main",
        side_effect=fake_downstream,
    ) as downstream_mock:
        rc = main(
            [
                "--organism",
                "Homo_sapiens",
                "--out-dir",
                str(species_root),
                "--prepare",
                "--run-downstream",
                "--check-output",
            ]
        )

    assert rc == 0
    assert aggregate_mock.call_count == 1
    assert downstream_mock.call_count == 1
    output = capsys.readouterr().out
    payload = json.loads(output.split("canonical CSV ready: ", 1)[1])
    assert payload["shape"] == [2, 2]


def test_check_canonical_csv_rejects_all_zero_column(tmp_path: Path) -> None:
    csv_path = tmp_path / CANONICAL_CSV_NAME
    _write(csv_path, ",feature_a,feature_b\nHeLa,1,0\nBJ,2,0\n")
    with pytest.raises(ValueError, match="all-zero columns"):
        _check_canonical_csv(csv_path)


def test_prepare_rejects_custom_trial_name(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="does not support custom trial naming"):
        main(
            [
                "--organism",
                "Homo_sapiens",
                "--out-dir",
                str(tmp_path / "te_species" / "Homo_sapiens"),
                "--trial",
                "custom_trial",
                "--prepare",
            ]
        )
