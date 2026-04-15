from __future__ import annotations

import json
import sys
import tempfile
import types
from pathlib import Path
from typing import Dict, Optional

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from te_analysis.downstream.extraction_wrapper import (
    ExtractionContractError,
    ExperimentCounts,
    MissingRiboArtifactError,
    RibopyExperimentReader,
    RnaSeqStatus,
    extract_from_handoff,
)
from te_analysis.handoff.handoff_builder import build_handoff_manifest
from te_analysis.handoff.ribo_manifest import (
    ExperimentRiboArtifact,
    HandoffManifest,
    StudyHandoffArtifacts,
    ValidationState,
    ValidationSummary,
)


class _StaticReader:
    def __init__(self, *, ribo_counts: Dict[str, int], rnaseq_counts: Optional[Dict[str, int]]):
        self._ribo_counts = ribo_counts
        self._rnaseq_counts = rnaseq_counts

    def extract_counts(self, experiment_id: str) -> ExperimentCounts:
        return ExperimentCounts(
            ribo_counts=self._ribo_counts,
            rnaseq_counts=self._rnaseq_counts,
        )


def test_valid_handoff_manifest_path_extracts_counts_and_writes_outputs() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_root = Path(tmpdir)
        study_root = tmp_root / "GSE_EXTRACT"
        experiments_dir = study_root / "ribo" / "experiments"
        experiments_dir.mkdir(parents=True)
        (experiments_dir / "EXP_A.ribo").write_text("")

        manifest = build_handoff_manifest(study_root=study_root, validate=True)
        manifest_path = tmp_root / "handoff_manifest.json"
        manifest_path.write_text(manifest.to_json())

        result = extract_from_handoff(
            manifest_path,
            output_root=tmp_root / "outputs",
            reader_factory=lambda _: _StaticReader(
                ribo_counts={"GENE2": 2, "GENE1": 5},
                rnaseq_counts={"GENE1": 9},
            ),
        )

        assert result.study_id == "GSE_EXTRACT"
        assert result.output_dir == tmp_root / "outputs" / "GSE_EXTRACT"
        assert result.extraction_manifest_path.exists()
        assert result.run_summary_path.exists()
        assert len(result.records) == 1

        record = result.records[0]
        assert record.experiment_id == "EXP_A"
        assert record.rnaseq_status is RnaSeqStatus.PRESENT
        assert record.ribo_counts_path.exists()
        assert record.rnaseq_counts_path is not None
        assert record.rnaseq_counts_path.exists()

        ribo_lines = record.ribo_counts_path.read_text().splitlines()
        assert ribo_lines == [
            "gene_id,count",
            "GENE1,5",
            "GENE2,2",
        ]

        summary = json.loads(result.extraction_manifest_path.read_text())
        assert summary["stage_name"] == "downstream_extraction"
        assert summary["schema_version"] == "1"
        assert summary["study_id"] == "GSE_EXTRACT"
        assert summary["manifest_source"].endswith("handoff_manifest.json")
        assert len(summary["source_handoff_manifest_sha256"]) == 64
        assert summary["records"][0]["rnaseq_status"] == "present"


def test_missing_ribo_file_raises_missing_ribo_artifact_error() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_root = Path(tmpdir)
        study_root = tmp_root / "GSE_MISSING_RIBO"
        experiments_dir = study_root / "ribo" / "experiments"
        experiments_dir.mkdir(parents=True)
        ribo_path = experiments_dir / "EXP_A.ribo"
        ribo_path.write_text("")

        manifest = build_handoff_manifest(study_root=study_root, validate=True)
        ribo_path.unlink()

        try:
            extract_from_handoff(
                manifest,
                output_root=tmp_root / "outputs",
                reader_factory=lambda _: _StaticReader(
                    ribo_counts={"GENE1": 1},
                    rnaseq_counts={"GENE1": 1},
                ),
            )
        except MissingRiboArtifactError:
            pass
        else:
            raise AssertionError("Expected MissingRiboArtifactError for deleted `.ribo` artifact.")


def test_malformed_handoff_entry_raises_contract_error() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_root = Path(tmpdir)
        study_root = tmp_root / "GSE_BAD_HANDOFF"
        experiments_dir = study_root / "ribo" / "experiments"
        experiments_dir.mkdir(parents=True)
        ribo_path = experiments_dir / "EXP_A.ribo"
        ribo_path.write_text("")

        malformed_manifest = HandoffManifest(
            study=StudyHandoffArtifacts(
                study_id="GSE_BAD_HANDOFF",
                experiment_ids=("EXP_A", "EXP_B"),
                experiment_ribo_paths=(ribo_path,),
                aggregate_ribo_path=None,
            ),
            experiment_ribo_files=(
                ExperimentRiboArtifact(
                    study_id="GSE_BAD_HANDOFF",
                    experiment_id="EXP_A",
                    ribo_path=ribo_path,
                    rnaseq_injected=None,
                ),
            ),
            validation=ValidationSummary(state=ValidationState.VALID),
        )

        try:
            extract_from_handoff(
                malformed_manifest,
                output_root=tmp_root / "outputs",
                reader_factory=lambda _: _StaticReader(
                    ribo_counts={"GENE1": 1},
                    rnaseq_counts=None,
                ),
            )
        except ExtractionContractError:
            pass
        else:
            raise AssertionError("Expected ExtractionContractError for malformed handoff entry.")


def test_ribo_only_experiment_records_explicit_rnaseq_absence() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_root = Path(tmpdir)
        study_root = tmp_root / "GSE_RIBO_ONLY"
        experiments_dir = study_root / "ribo" / "experiments"
        experiments_dir.mkdir(parents=True)
        (experiments_dir / "EXP_A.ribo").write_text("")

        manifest = build_handoff_manifest(study_root=study_root, validate=True)
        result = extract_from_handoff(
            manifest,
            output_root=tmp_root / "outputs",
            reader_factory=lambda _: _StaticReader(
                ribo_counts={"GENE1": 7},
                rnaseq_counts=None,
            ),
        )

        record = result.records[0]
        assert record.rnaseq_status is RnaSeqStatus.ABSENT
        assert record.rnaseq_counts_path is None
        assert record.rnaseq_gene_count is None
        assert not (result.output_dir / "experiments" / "EXP_A" / "rnaseq_raw_counts.csv").exists()

        summary = json.loads(result.extraction_manifest_path.read_text())
        assert summary["records"][0]["rnaseq_status"] == "absent"
        assert summary["records"][0]["rnaseq_counts_path"] is None
        assert "absent" in result.run_summary_path.read_text()


def test_ribopy_reader_smoke_with_runtime_shaped_tables() -> None:
    fake_ribopy = types.ModuleType("ribopy")

    class _FakeRibo:
        def __init__(self, ribo_path: str, alias=None):
            self.ribo_path = ribo_path
            self.alias = alias

        def get_region_counts(
            self,
            region_name: str,
            *,
            sum_lengths: bool,
            sum_references: bool,
            alias: bool,
            experiments: str,
        ) -> pd.DataFrame:
            assert region_name == "CDS"
            assert sum_lengths is True
            assert sum_references is False
            assert alias is True
            assert experiments == "EXP_A"
            return pd.DataFrame({"EXP_A": [11, 22]}, index=["tx1", "tx2"])

        def has_rnaseq(self, experiment_id: str) -> bool:
            return experiment_id == "EXP_A"

        def get_rnaseq(self, experiments: str) -> pd.DataFrame:
            assert experiments == "EXP_A"
            index = pd.MultiIndex.from_tuples(
                [("EXP_A", "tx1"), ("EXP_A", "tx2")],
                names=["experiment", "reference"],
            )
            return pd.DataFrame(
                {
                    "UTR5": [0, 0],
                    "CDS": [101, 202],
                    "UTR3": [0, 0],
                },
                index=index,
            )

    fake_ribopy.Ribo = _FakeRibo
    fake_ribopy.api = types.SimpleNamespace(
        alias=types.SimpleNamespace(apris_human_alias=lambda gene_id: "GENE_" + gene_id.upper())
    )

    original_ribopy = sys.modules.get("ribopy")
    try:
        sys.modules["ribopy"] = fake_ribopy
        counts = RibopyExperimentReader(Path("/tmp/fake.ribo")).extract_counts("EXP_A")
    finally:
        if original_ribopy is None:
            del sys.modules["ribopy"]
        else:
            sys.modules["ribopy"] = original_ribopy

    assert dict(counts.ribo_counts) == {"tx1": 11, "tx2": 22}
    assert dict(counts.rnaseq_counts) == {"GENE_TX1": 101, "GENE_TX2": 202}


def test_ribopy_reader_rejects_malformed_rnaseq_table() -> None:
    fake_ribopy = types.ModuleType("ribopy")

    class _FakeRibo:
        def __init__(self, ribo_path: str, alias=None):
            self.ribo_path = ribo_path
            self.alias = alias

        def get_region_counts(
            self,
            region_name: str,
            *,
            sum_lengths: bool,
            sum_references: bool,
            alias: bool,
            experiments: str,
        ) -> pd.DataFrame:
            return pd.DataFrame({"EXP_A": [3]}, index=["tx1"])

        def has_rnaseq(self, experiment_id: str) -> bool:
            return True

        def get_rnaseq(self, experiments: str) -> pd.DataFrame:
            index = pd.MultiIndex.from_tuples(
                [("EXP_A", "tx1")],
                names=["experiment", "reference"],
            )
            return pd.DataFrame({"UTR5": [0], "UTR3": [0]}, index=index)

    fake_ribopy.Ribo = _FakeRibo
    fake_ribopy.api = types.SimpleNamespace(
        alias=types.SimpleNamespace(apris_human_alias=lambda gene_id: gene_id)
    )

    original_ribopy = sys.modules.get("ribopy")
    try:
        sys.modules["ribopy"] = fake_ribopy
        try:
            RibopyExperimentReader(Path("/tmp/fake.ribo")).extract_counts("EXP_A")
        except ExtractionContractError as exc:
            assert "do not expose a CDS view" in str(exc)
        else:
            raise AssertionError("Expected ExtractionContractError for malformed RNA-seq runtime shape.")
    finally:
        if original_ribopy is None:
            del sys.modules["ribopy"]
        else:
            sys.modules["ribopy"] = original_ribopy
