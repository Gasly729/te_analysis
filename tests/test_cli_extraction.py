from __future__ import annotations

from pathlib import Path
import sys
from typing import Optional

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from te_analysis import cli
from te_analysis.downstream import (
    ExtractionRunResult,
    ExperimentExtractionRecord,
    MissingRiboArtifactError,
    RnaSeqStatus,
)


def _build_result(tmp_path: Path) -> ExtractionRunResult:
    output_dir = tmp_path / "outputs" / "GSE_CLI"
    return ExtractionRunResult(
        stage_name="downstream_extraction",
        study_id="GSE_CLI",
        schema_version="1",
        output_dir=output_dir,
        extraction_manifest_path=output_dir / "extraction_manifest.json",
        run_summary_path=output_dir / "run_summary.csv",
        manifest_source=str(tmp_path / "handoff_manifest.json"),
        source_handoff_manifest_sha256="a" * 64,
        records=(
            ExperimentExtractionRecord(
                study_id="GSE_CLI",
                experiment_id="EXP_A",
                source_ribo_path=tmp_path / "EXP_A.ribo",
                ribo_counts_path=output_dir / "experiments" / "EXP_A" / "ribo_raw_counts.csv",
                rnaseq_counts_path=output_dir / "experiments" / "EXP_A" / "rnaseq_raw_counts.csv",
                rnaseq_status=RnaSeqStatus.PRESENT,
                ribo_gene_count=2,
                rnaseq_gene_count=2,
            ),
            ExperimentExtractionRecord(
                study_id="GSE_CLI",
                experiment_id="EXP_B",
                source_ribo_path=tmp_path / "EXP_B.ribo",
                ribo_counts_path=output_dir / "experiments" / "EXP_B" / "ribo_raw_counts.csv",
                rnaseq_counts_path=None,
                rnaseq_status=RnaSeqStatus.ABSENT,
                ribo_gene_count=3,
                rnaseq_gene_count=None,
            ),
        ),
    )


def test_extract_cli_success_path_delegates_to_extraction_wrapper(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    expected_result = _build_result(tmp_path)
    calls: list[tuple[str, Path]] = []

    def _fake_run_extraction(handoff: str, *, output_root: Optional[Path] = None) -> ExtractionRunResult:
        calls.append((handoff, output_root))
        return expected_result

    monkeypatch.setattr(cli, "run_extraction", _fake_run_extraction)

    exit_code = cli.main(
        [
            "extract",
            "--handoff",
            str(tmp_path / "handoff_manifest.json"),
            "--output-root",
            str(tmp_path / "outputs"),
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert calls == [(str(tmp_path / "handoff_manifest.json"), tmp_path / "outputs")]
    assert "downstream_extraction: success" in captured.out
    assert "study_id: GSE_CLI" in captured.out
    assert "manifest_source: {path}".format(path=expected_result.manifest_source) in captured.out
    assert "output_dir: {path}".format(path=expected_result.output_dir) in captured.out
    assert "experiments_processed: 2" in captured.out
    assert "rnaseq_present: 1" in captured.out
    assert "rnaseq_absent: 1" in captured.out
    assert captured.err == ""


def test_extract_cli_requires_handoff_argument(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc_info:
        cli.main(["extract"])

    captured = capsys.readouterr()
    assert exc_info.value.code == 2
    assert "--handoff" in captured.err


def test_extract_cli_missing_ribo_artifact_returns_nonzero(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def _fake_run_extraction(handoff: str, *, output_root: Optional[Path] = None) -> ExtractionRunResult:
        raise MissingRiboArtifactError("Declared experiment-level `.ribo` artifact does not exist.")

    monkeypatch.setattr(cli, "run_extraction", _fake_run_extraction)

    exit_code = cli.main(
        [
            "extract",
            "--handoff",
            str(tmp_path / "handoff_manifest.json"),
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "downstream_extraction: error" in captured.err
    assert "Declared experiment-level `.ribo` artifact does not exist." in captured.err


def test_extract_cli_summary_reports_rnaseq_present_and_absent_counts(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        cli,
        "run_extraction",
        lambda handoff, output_root=None: _build_result(tmp_path),
    )

    exit_code = cli.main(
        [
            "extract",
            "--handoff",
            str(tmp_path / "handoff_manifest.json"),
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "rnaseq_present: 1" in captured.out
    assert "rnaseq_absent: 1" in captured.out
