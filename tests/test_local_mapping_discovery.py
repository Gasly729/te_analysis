from __future__ import annotations

from pathlib import Path

from te_analysis.raw.experiment_run_mapping import build_experiment_run_mapping_outputs
from te_analysis.raw.local_mapping_discovery import LocalMappingSourceSpec


def test_local_mapping_artifact_is_normalized_and_deduplicated(tmp_path: Path) -> None:
    source_a = tmp_path / "mapping_a.csv"
    source_b = tmp_path / "mapping_b.csv"
    source_a.write_text(
        "Run,srx\nSRR1,SRX1\nSRR1,SRX1\nSRR2,SRX1\nERS1,\n",
        encoding="utf-8",
    )
    source_b.write_text(
        "SRX,SRR\nSRX1,SRR1\nSRX3,SRR3\n",
        encoding="utf-8",
    )

    result = build_experiment_run_mapping_outputs(
        mapping_path=tmp_path / "experiment_run_mapping_local.tsv",
        report_path=tmp_path / "_experiment_run_mapping_report.md",
        source_specs=(
            LocalMappingSourceSpec(
                source_name="source.a",
                path=source_a,
                experiment_column="srx",
                run_column="Run",
                note="schema: Run/srx",
            ),
            LocalMappingSourceSpec(
                source_name="source.b",
                path=source_b,
                experiment_column="SRX",
                run_column="SRR",
                note="schema: SRX/SRR",
            ),
        ),
    )

    mapping = result.discovery.mapping_frame
    assert len(mapping) == 3
    assert mapping["run_accession"].tolist() == ["SRR1", "SRR2", "SRR3"]
    merged = mapping[mapping["run_accession"] == "SRR1"].iloc[0]
    assert merged["experiment_accession"] == "SRX1"
    assert merged["mapping_source"] == "source.a;source.b"
    assert str(source_a) in merged["mapping_source_path"]
    assert str(source_b) in merged["mapping_source_path"]


def test_mapping_report_keeps_found_and_skipped_source_provenance(tmp_path: Path) -> None:
    unsupported = tmp_path / "runtable.csv"
    supported = tmp_path / "mapping.csv"
    unsupported.write_text("Run,study_name\nSRR1,GSE1\n", encoding="utf-8")
    supported.write_text("Run,srx\nSRR1,SRX1\n", encoding="utf-8")

    result = build_experiment_run_mapping_outputs(
        mapping_path=tmp_path / "experiment_run_mapping_local.tsv",
        report_path=tmp_path / "_experiment_run_mapping_report.md",
        source_specs=(
            LocalMappingSourceSpec(
                source_name="unsupported.runtable",
                path=unsupported,
                experiment_column=None,
                run_column="Run",
                note="unsupported: no experiment accession column",
            ),
            LocalMappingSourceSpec(
                source_name="supported.mapping",
                path=supported,
                experiment_column="srx",
                run_column="Run",
                note="schema: Run/srx",
            ),
        ),
    )

    report = result.report_path.read_text(encoding="utf-8")
    assert "supported.mapping" in report
    assert "unsupported.runtable" in report
    assert "unsupported: no experiment accession column" in report
