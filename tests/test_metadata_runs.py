from __future__ import annotations

import csv
from pathlib import Path

import pandas as pd

from te_analysis.raw import build_metadata_runs_outputs
from te_analysis.raw.local_mapping_discovery import LocalMappingSourceSpec
from te_analysis.raw.run_accession_resolution import RESOLVED_COLUMNS, UNRESOLVED_COLUMNS


def _write_metadata(path: Path, rows: list[dict[str, str]], *, include_run_alias: bool = True) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    headers = [
        "experiment_alias",
        "organism",
        "corrected_type",
        "experiment_accession",
        "study_name",
        "library_strategy",
        "library_layout",
    ]
    if include_run_alias:
        headers.append("run_alias")
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["Curated Data"] + [""] * (len(headers) - 1))
        writer.writerow(headers)
        for row in rows:
            writer.writerow([row.get(header, "") for header in headers])
    return path


def _write_manifest(path: Path, rows: list[dict[str, str]]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    columns = [
        "gsm",
        "gse",
        "srr",
        "mate",
        "organism_canonical",
        "organism_raw",
        "seq_type",
        "layout",
        "source_batch",
        "source_path",
        "real_target",
        "linked_path",
        "size_bytes",
        "mtime_iso",
        "status",
        "skip_reason",
        "warning",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, delimiter="\t")
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in columns})
    return path


def _build_outputs(
    tmp_path: Path,
    metadata_rows: list[dict[str, str]],
    manifest_rows: list[dict[str, str]],
    *,
    include_run_alias: bool = True,
    mapping_source_specs: tuple[LocalMappingSourceSpec, ...] | None = (),
):
    metadata_path = _write_metadata(tmp_path / "raw" / "metadata.csv", metadata_rows, include_run_alias=include_run_alias)
    manifest_path = _write_manifest(tmp_path / "raw" / "_manifest.tsv", manifest_rows)
    mapping_path = tmp_path / "raw" / "experiment_run_mapping_local.tsv"
    mapping_report_path = tmp_path / "raw" / "_experiment_run_mapping_report.md"
    runs_path = tmp_path / "raw" / "metadata_runs.tsv"
    unresolved_path = tmp_path / "raw" / "metadata_runs_unresolved.tsv"
    report_path = tmp_path / "raw" / "_metadata_runs_report.md"
    return build_metadata_runs_outputs(
        metadata_path=metadata_path,
        manifest_path=manifest_path,
        mapping_path=mapping_path,
        mapping_report_path=mapping_report_path,
        runs_path=runs_path,
        unresolved_path=unresolved_path,
        report_path=report_path,
        mapping_source_specs=mapping_source_specs,
    )


def test_experiment_row_expands_to_multiple_runs(tmp_path: Path) -> None:
    result = _build_outputs(
        tmp_path,
        metadata_rows=[
            {
                "experiment_alias": "GSM1",
                "organism": "Human",
                "corrected_type": "RNA-Seq",
                "experiment_accession": "SRX1",
                "study_name": "GSE1",
                "library_strategy": "RNA-Seq",
                "library_layout": "SINGLE",
            }
        ],
        manifest_rows=[
            {
                "gsm": "GSM1",
                "gse": "GSE1",
                "srr": "SRR1",
                "mate": "",
                "source_batch": "batch1",
                "source_path": "/tmp/SRR1_GSM1.fastq.gz",
                "status": "matched",
            },
            {
                "gsm": "GSM1",
                "gse": "GSE1",
                "srr": "SRR2",
                "mate": "",
                "source_batch": "batch1",
                "source_path": "/tmp/SRR2_GSM1.fastq.gz",
                "status": "matched",
            },
        ],
        include_run_alias=False,
    )

    assert len(result.resolution.resolved) == 2
    assert sorted(result.resolution.resolved["run_accession"].tolist()) == ["SRR1", "SRR2"]
    assert set(result.resolution.resolved["resolution_source"]) == {
        "manifest.experiment_accession;manifest.experiment_alias"
    }


def test_unresolved_rows_are_preserved_with_reason(tmp_path: Path) -> None:
    result = _build_outputs(
        tmp_path,
        metadata_rows=[
            {
                "experiment_alias": "GSM2",
                "organism": "Human",
                "corrected_type": "Ribo-Seq",
                "experiment_accession": "SRX2",
                "study_name": "GSE2",
                "library_strategy": "OTHER",
                "library_layout": "SINGLE",
            }
        ],
        manifest_rows=[],
        include_run_alias=False,
    )

    assert len(result.resolution.resolved) == 0
    assert len(result.resolution.unresolved) == 1
    unresolved = result.resolution.unresolved.iloc[0]
    assert unresolved["unresolved_reason"] == "no_local_run_match"


def test_run_alias_absence_does_not_break_resolution(tmp_path: Path) -> None:
    result = _build_outputs(
        tmp_path,
        metadata_rows=[
            {
                "experiment_alias": "GSM3",
                "organism": "Mouse",
                "corrected_type": "RNA-Seq",
                "experiment_accession": "SRX3",
                "study_name": "GSE3",
                "library_strategy": "RNA-Seq",
                "library_layout": "SINGLE",
            }
        ],
        manifest_rows=[
            {
                "gsm": "GSM3",
                "gse": "GSE3",
                "srr": "SRR3",
                "mate": "",
                "source_batch": "batch1",
                "source_path": "/tmp/SRR3_GSM3.fastq.gz",
                "status": "matched",
            }
        ],
        include_run_alias=False,
    )

    assert len(result.resolution.resolved) == 1
    assert result.resolution.resolved.iloc[0]["run_accession"] == "SRR3"


def test_manifest_backed_experiment_accession_matching_works(tmp_path: Path) -> None:
    result = _build_outputs(
        tmp_path,
        metadata_rows=[
            {
                "experiment_alias": "GSM4",
                "organism": "Human",
                "corrected_type": "RNA-Seq",
                "experiment_accession": "SRX4",
                "study_name": "GSE4",
                "library_strategy": "RNA-Seq",
                "library_layout": "SINGLE",
            }
        ],
        manifest_rows=[
            {
                "gsm": "",
                "gse": "GSE4",
                "srr": "SRR4",
                "mate": "",
                "source_batch": "batch1",
                "source_path": "/tmp/SRR4_SRX4.fastq.gz",
                "status": "skipped",
            }
        ],
        include_run_alias=False,
    )

    assert len(result.resolution.resolved) == 1
    row = result.resolution.resolved.iloc[0]
    assert row["run_accession"] == "SRR4"
    assert row["resolution_source"] == "manifest.experiment_accession"


def test_output_schema_is_stable(tmp_path: Path) -> None:
    result = _build_outputs(
        tmp_path,
        metadata_rows=[
            {
                "experiment_alias": "GSM5",
                "organism": "Mouse",
                "corrected_type": "RNA-Seq",
                "experiment_accession": "SRX5",
                "study_name": "GSE5",
                "library_strategy": "RNA-Seq",
                "library_layout": "SINGLE",
                "run_alias": "SRR5",
            }
        ],
        manifest_rows=[],
        include_run_alias=True,
    )

    assert tuple(result.resolution.resolved.columns) == RESOLVED_COLUMNS
    assert tuple(result.resolution.unresolved.columns) == UNRESOLVED_COLUMNS
    written_resolved = pd.read_csv(result.runs_path, sep="\t", dtype=str)
    written_unresolved = pd.read_csv(result.unresolved_path, sep="\t", dtype=str)
    assert tuple(written_resolved.columns) == RESOLVED_COLUMNS
    assert tuple(written_unresolved.columns) == UNRESOLVED_COLUMNS


def test_local_mapping_resolves_without_manifest_direct_evidence(tmp_path: Path) -> None:
    mapping_csv = tmp_path / "offline_mapping.csv"
    mapping_csv.write_text(
        "Run,srx\nSRR6,SRX6\nSRR7,SRX6\n",
        encoding="utf-8",
    )
    result = _build_outputs(
        tmp_path,
        metadata_rows=[
            {
                "experiment_alias": "GSM6",
                "organism": "Human",
                "corrected_type": "RNA-Seq",
                "experiment_accession": "SRX6",
                "study_name": "GSE6",
                "library_strategy": "RNA-Seq",
                "library_layout": "SINGLE",
            }
        ],
        manifest_rows=[],
        include_run_alias=False,
        mapping_source_specs=(
            LocalMappingSourceSpec(
                source_name="test.mapping",
                path=mapping_csv,
                experiment_column="srx",
                run_column="Run",
                note="schema: Run/srx",
            ),
        ),
    )

    assert sorted(result.resolution.resolved["run_accession"].tolist()) == ["SRR6", "SRR7"]
    assert set(result.resolution.resolved["resolution_source"]) == {"local_mapping:test.mapping"}


def test_direct_manifest_evidence_beats_weaker_local_mapping(tmp_path: Path) -> None:
    mapping_csv = tmp_path / "offline_mapping.csv"
    mapping_csv.write_text(
        "Run,srx\nSRR999,SRX7\n",
        encoding="utf-8",
    )
    result = _build_outputs(
        tmp_path,
        metadata_rows=[
            {
                "experiment_alias": "GSM7",
                "organism": "Human",
                "corrected_type": "RNA-Seq",
                "experiment_accession": "SRX7",
                "study_name": "GSE7",
                "library_strategy": "RNA-Seq",
                "library_layout": "SINGLE",
            }
        ],
        manifest_rows=[
            {
                "gsm": "GSM7",
                "gse": "GSE7",
                "srr": "SRR7",
                "mate": "",
                "source_batch": "batch1",
                "source_path": "/tmp/SRR7_GSM7.fastq.gz",
                "status": "matched",
            }
        ],
        include_run_alias=False,
        mapping_source_specs=(
            LocalMappingSourceSpec(
                source_name="test.mapping",
                path=mapping_csv,
                experiment_column="srx",
                run_column="Run",
                note="schema: Run/srx",
            ),
        ),
    )

    assert result.resolution.resolved["run_accession"].tolist() == ["SRR7"]
    assert (
        result.resolution.resolved.iloc[0]["resolution_source"]
        == "manifest.experiment_accession;manifest.experiment_alias"
    )
