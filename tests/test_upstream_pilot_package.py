from __future__ import annotations

import csv
from pathlib import Path

import pandas as pd
import yaml

from te_analysis.raw.run_accession_resolution import RESOLVED_COLUMNS, UNRESOLVED_COLUMNS
from te_analysis.upstream.pilot_package import build_pilot_candidates, build_upstream_pilot_package


def _write_metadata_csv(path: Path, rows: list[dict[str, str]]) -> Path:
    headers = [
        "experiment_alias",
        "experiment_accession",
        "study_name",
        "organism",
        "corrected_type",
        "matched_RNA-seq_experiment_alias",
        "library_strategy",
        "library_layout",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["Curated Data"] + [""] * (len(headers) - 1))
        writer.writerow(headers)
        for row in rows:
            writer.writerow([row.get(header, "") for header in headers])
    return path


def _write_tsv(path: Path, columns: tuple[str, ...], rows: list[dict[str, str]]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(columns), delimiter="\t")
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in columns})
    return path


def _write_manifest(path: Path, rows: list[dict[str, str]]) -> Path:
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
    return _write_tsv(path, tuple(columns), rows)


def _prepare_reference_and_template(tmp_path: Path) -> tuple[Path, Path]:
    snake_root = tmp_path / "snake"
    reference_yaml = snake_root / "scripts/references.yaml"
    reference_yaml.parent.mkdir(parents=True, exist_ok=True)
    reference_yaml.write_text(
        '\n'.join(
            [
                '"homo sapiens":',
                '  filter: "filter/human/filter*"',
                '  transcriptome: "transcriptome/human/transcriptome*"',
                '  regions: "transcriptome/human/regions.bed"',
                '  transcript_lengths: "transcriptome/human/lengths.tsv"',
                "",
            ]
        ),
        encoding="utf-8",
    )
    template_path = snake_root / "project.yaml"
    template_path.write_text(
        yaml.safe_dump(
            {
                "do_rnaseq": True,
                "do_metadata": False,
                "input": {
                    "reference": {
                        "filter": "",
                        "transcriptome": "",
                        "regions": "",
                        "transcript_lengths": "",
                    },
                    "fastq_base": "",
                    "fastq": {},
                    "root_meta": "",
                    "metadata": {"base": "", "files": {}},
                },
                "rnaseq": {"fastq": {}},
                "output": {
                    "output": {"base": ""},
                    "intermediates": {"base": ""},
                },
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    return reference_yaml, template_path


def _prepare_source_fastq(tmp_path: Path, filename: str) -> tuple[Path, Path]:
    source_path = tmp_path / "source_fastq" / filename
    source_path.parent.mkdir(parents=True, exist_ok=True)
    source_path.write_text("FASTQ\n", encoding="utf-8")
    linked_path = tmp_path / "raw_links" / filename
    linked_path.parent.mkdir(parents=True, exist_ok=True)
    linked_path.symlink_to(source_path)
    return source_path, linked_path


def _resolved_row(**kwargs: str) -> dict[str, str]:
    row = {column: "" for column in RESOLVED_COLUMNS}
    row.update(kwargs)
    return row


def _unresolved_row(**kwargs: str) -> dict[str, str]:
    row = {column: "" for column in UNRESOLVED_COLUMNS}
    row.update(kwargs)
    return row


def test_pilot_candidate_ranking_prefers_clean_complete_study(tmp_path: Path) -> None:
    metadata_rows = [
        {
            "experiment_alias": "GSM_RNA_A",
            "experiment_accession": "SRX_A_RNA",
            "study_name": "GSE_A",
            "organism": "Homo sapiens",
            "corrected_type": "RNA-Seq",
            "matched_RNA-seq_experiment_alias": "NA",
            "library_strategy": "RNA-Seq",
            "library_layout": "SINGLE",
        },
        {
            "experiment_alias": "GSM_RIBO_A",
            "experiment_accession": "SRX_A_RIBO",
            "study_name": "GSE_A",
            "organism": "Homo sapiens",
            "corrected_type": "Ribo-Seq",
            "matched_RNA-seq_experiment_alias": "GSM_RNA_A",
            "library_strategy": "OTHER",
            "library_layout": "SINGLE",
        },
        {
            "experiment_alias": "GSM_BAD",
            "experiment_accession": "SRX_BAD",
            "study_name": "GSE_BAD",
            "organism": "Homo sapiens",
            "corrected_type": "Ribo-Seq",
            "matched_RNA-seq_experiment_alias": "NA",
            "library_strategy": "OTHER",
            "library_layout": "SINGLE",
        },
    ]
    metadata_path = _write_metadata_csv(tmp_path / "raw/metadata.csv", metadata_rows)
    metadata = pd.read_csv(metadata_path, dtype=str, keep_default_na=False, header=0, skiprows=[0])
    source_a, linked_a = _prepare_source_fastq(tmp_path, "GSM_RNA_A_RNA-Seq_SRR1_1.fastq.gz")
    source_b, linked_b = _prepare_source_fastq(tmp_path, "GSM_RIBO_A_Ribo-Seq_SRR2_1.fastq.gz")
    runs = pd.DataFrame(
        [
            _resolved_row(
                run_accession="SRR1",
                run_accession_prefix="SRR",
                experiment_accession="SRX_A_RNA",
                experiment_alias="GSM_RNA_A",
                study_name="GSE_A",
                organism="Homo sapiens",
                corrected_type="RNA-Seq",
                library_strategy="RNA-Seq",
                library_layout="SINGLE",
                resolution_status="resolved",
                resolution_source="manifest.experiment_alias",
                manifest_match_status="manifest_present",
                fastq_presence_status="single_present",
                source_batches="batch1",
            ),
            _resolved_row(
                run_accession="SRR2",
                run_accession_prefix="SRR",
                experiment_accession="SRX_A_RIBO",
                experiment_alias="GSM_RIBO_A",
                study_name="GSE_A",
                organism="Homo sapiens",
                corrected_type="Ribo-Seq",
                library_strategy="OTHER",
                library_layout="SINGLE",
                resolution_status="resolved",
                resolution_source="manifest.experiment_alias",
                manifest_match_status="manifest_present",
                fastq_presence_status="single_present",
                source_batches="batch1",
            ),
        ],
        dtype=str,
    )
    unresolved = pd.DataFrame(
        [
            _unresolved_row(
                experiment_accession="SRX_BAD",
                experiment_alias="GSM_BAD",
                study_name="GSE_BAD",
                organism="Homo sapiens",
                corrected_type="Ribo-Seq",
                library_strategy="OTHER",
                library_layout="SINGLE",
                resolution_status="unresolved",
                unresolved_reason="no_local_run_match",
            )
        ],
        dtype=str,
    )
    manifest = pd.DataFrame(
        [
            {
                "gsm": "GSM_RNA_A",
                "gse": "GSE_A",
                "srr": "SRR1",
                "mate": "1",
                "organism_canonical": "Homo_sapiens",
                "organism_raw": "Homo sapiens",
                "seq_type": "RNA-Seq",
                "layout": "SINGLE",
                "source_batch": "batch1",
                "source_path": str(source_a),
                "real_target": str(source_a),
                "linked_path": str(linked_a),
                "size_bytes": "5",
                "mtime_iso": "",
                "status": "matched",
                "skip_reason": "",
                "warning": "single_but_mate_1_only",
            },
            {
                "gsm": "GSM_RIBO_A",
                "gse": "GSE_A",
                "srr": "SRR2",
                "mate": "1",
                "organism_canonical": "Homo_sapiens",
                "organism_raw": "Homo sapiens",
                "seq_type": "Ribo-Seq",
                "layout": "SINGLE",
                "source_batch": "batch1",
                "source_path": str(source_b),
                "real_target": str(source_b),
                "linked_path": str(linked_b),
                "size_bytes": "5",
                "mtime_iso": "",
                "status": "matched",
                "skip_reason": "",
                "warning": "single_but_mate_1_only",
            },
        ],
        dtype=str,
    )
    candidates = build_pilot_candidates(
        metadata_frame=metadata,
        runs_frame=runs,
        unresolved_frame=unresolved,
        manifest_frame=manifest,
        reference_catalog={"homo sapiens": {"filter": "filter/human/filter*", "transcriptome": "transcriptome/human/transcriptome*", "regions": "transcriptome/human/regions.bed", "transcript_lengths": "transcriptome/human/lengths.tsv"}},
    )
    assert candidates.iloc[0]["study_name"] == "GSE_A"
    assert bool(candidates.iloc[0]["pilot_ready"])


def test_build_upstream_pilot_package_generates_manifests_symlinks_and_config(tmp_path: Path) -> None:
    metadata_rows = [
        {
            "experiment_alias": "GSM_RNA_A",
            "experiment_accession": "SRX_A_RNA",
            "study_name": "GSE_A",
            "organism": "Homo sapiens",
            "corrected_type": "RNA-Seq",
            "matched_RNA-seq_experiment_alias": "NA",
            "library_strategy": "RNA-Seq",
            "library_layout": "SINGLE",
        },
        {
            "experiment_alias": "GSM_RIBO_A",
            "experiment_accession": "SRX_A_RIBO",
            "study_name": "GSE_A",
            "organism": "Homo sapiens",
            "corrected_type": "Ribo-Seq",
            "matched_RNA-seq_experiment_alias": "GSM_RNA_A",
            "library_strategy": "OTHER",
            "library_layout": "SINGLE",
        },
    ]
    metadata_path = _write_metadata_csv(tmp_path / "raw/metadata.csv", metadata_rows)
    runs_path = _write_tsv(
        tmp_path / "raw/metadata_runs.tsv",
        RESOLVED_COLUMNS,
        [
            _resolved_row(
                run_accession="SRR1",
                run_accession_prefix="SRR",
                experiment_accession="SRX_A_RNA",
                experiment_alias="GSM_RNA_A",
                study_name="GSE_A",
                organism="Homo sapiens",
                corrected_type="RNA-Seq",
                library_strategy="RNA-Seq",
                library_layout="SINGLE",
                resolution_status="resolved",
                resolution_source="manifest.experiment_alias",
                manifest_match_status="manifest_present",
                fastq_presence_status="single_present",
                source_batches="batch1",
            ),
            _resolved_row(
                run_accession="SRR2",
                run_accession_prefix="SRR",
                experiment_accession="SRX_A_RIBO",
                experiment_alias="GSM_RIBO_A",
                study_name="GSE_A",
                organism="Homo sapiens",
                corrected_type="Ribo-Seq",
                library_strategy="OTHER",
                library_layout="SINGLE",
                resolution_status="resolved",
                resolution_source="manifest.experiment_alias",
                manifest_match_status="manifest_present",
                fastq_presence_status="single_present",
                source_batches="batch1",
            ),
        ],
    )
    unresolved_path = _write_tsv(tmp_path / "raw/metadata_runs_unresolved.tsv", UNRESOLVED_COLUMNS, [])
    source_a, linked_a = _prepare_source_fastq(tmp_path, "GSM_RNA_A_RNA-Seq_SRR1_1.fastq.gz")
    source_b, linked_b = _prepare_source_fastq(tmp_path, "GSM_RIBO_A_Ribo-Seq_SRR2_1.fastq.gz")
    manifest_path = _write_manifest(
        tmp_path / "raw/_manifest.tsv",
        [
            {
                "gsm": "GSM_RNA_A",
                "gse": "GSE_A",
                "srr": "SRR1",
                "mate": "1",
                "organism_canonical": "Homo_sapiens",
                "organism_raw": "Homo sapiens",
                "seq_type": "RNA-Seq",
                "layout": "SINGLE",
                "source_batch": "batch1",
                "source_path": str(source_a),
                "real_target": str(source_a),
                "linked_path": str(linked_a),
                "size_bytes": "5",
                "mtime_iso": "",
                "status": "matched",
                "skip_reason": "",
                "warning": "single_but_mate_1_only",
            },
            {
                "gsm": "GSM_RIBO_A",
                "gse": "GSE_A",
                "srr": "SRR2",
                "mate": "1",
                "organism_canonical": "Homo_sapiens",
                "organism_raw": "Homo sapiens",
                "seq_type": "Ribo-Seq",
                "layout": "SINGLE",
                "source_batch": "batch1",
                "source_path": str(source_b),
                "real_target": str(source_b),
                "linked_path": str(linked_b),
                "size_bytes": "5",
                "mtime_iso": "",
                "status": "matched",
                "skip_reason": "",
                "warning": "single_but_mate_1_only",
            },
        ],
    )
    reference_yaml, template_path = _prepare_reference_and_template(tmp_path)

    result = build_upstream_pilot_package(
        metadata_path=metadata_path,
        runs_path=runs_path,
        unresolved_path=unresolved_path,
        manifest_path=manifest_path,
        pilot_root=tmp_path / "pilot",
        reference_yaml_path=reference_yaml,
        project_template_path=template_path,
    )

    assert result.study_name == "GSE_A"
    assert result.symlinks_ok is True
    assert result.manifest_consistent is True
    assert result.config_generated is True
    assert result.unresolved_rows_leaked is False
    staged_links = sorted(result.staged_fastq_root.iterdir())
    assert len(staged_links) == 2
    assert all(path.is_symlink() for path in staged_links)
    project_yaml = yaml.safe_load(result.project_yaml_path.read_text(encoding="utf-8"))
    assert sorted(project_yaml["input"]["fastq"].keys()) == ["GSM_RIBO_A"]
    assert sorted(project_yaml["rnaseq"]["fastq"].keys()) == ["GSM_RIBO_A"]
    study_manifest = pd.read_csv(result.study_manifest_path, sep="\t", dtype=str)
    assert set(study_manifest["experiment_alias"]) == {"GSM_RNA_A", "GSM_RIBO_A"}


def test_unresolved_rows_are_excluded_from_selected_pilot_package(tmp_path: Path) -> None:
    metadata_rows = [
        {
            "experiment_alias": "GSM_RNA_A",
            "experiment_accession": "SRX_A_RNA",
            "study_name": "GSE_A",
            "organism": "Homo sapiens",
            "corrected_type": "RNA-Seq",
            "matched_RNA-seq_experiment_alias": "NA",
            "library_strategy": "RNA-Seq",
            "library_layout": "SINGLE",
        },
        {
            "experiment_alias": "GSM_RIBO_A",
            "experiment_accession": "SRX_A_RIBO",
            "study_name": "GSE_A",
            "organism": "Homo sapiens",
            "corrected_type": "Ribo-Seq",
            "matched_RNA-seq_experiment_alias": "GSM_RNA_A",
            "library_strategy": "OTHER",
            "library_layout": "SINGLE",
        },
        {
            "experiment_alias": "GSM_BAD",
            "experiment_accession": "SRX_BAD",
            "study_name": "GSE_BAD",
            "organism": "Homo sapiens",
            "corrected_type": "Ribo-Seq",
            "matched_RNA-seq_experiment_alias": "NA",
            "library_strategy": "OTHER",
            "library_layout": "SINGLE",
        },
    ]
    metadata_path = _write_metadata_csv(tmp_path / "raw/metadata.csv", metadata_rows)
    runs_path = _write_tsv(
        tmp_path / "raw/metadata_runs.tsv",
        RESOLVED_COLUMNS,
        [
            _resolved_row(
                run_accession="SRR1",
                run_accession_prefix="SRR",
                experiment_accession="SRX_A_RNA",
                experiment_alias="GSM_RNA_A",
                study_name="GSE_A",
                organism="Homo sapiens",
                corrected_type="RNA-Seq",
                library_strategy="RNA-Seq",
                library_layout="SINGLE",
                resolution_status="resolved",
                resolution_source="manifest.experiment_alias",
                manifest_match_status="manifest_present",
                fastq_presence_status="single_present",
                source_batches="batch1",
            ),
            _resolved_row(
                run_accession="SRR2",
                run_accession_prefix="SRR",
                experiment_accession="SRX_A_RIBO",
                experiment_alias="GSM_RIBO_A",
                study_name="GSE_A",
                organism="Homo sapiens",
                corrected_type="Ribo-Seq",
                library_strategy="OTHER",
                library_layout="SINGLE",
                resolution_status="resolved",
                resolution_source="manifest.experiment_alias",
                manifest_match_status="manifest_present",
                fastq_presence_status="single_present",
                source_batches="batch1",
            ),
        ],
    )
    unresolved_path = _write_tsv(
        tmp_path / "raw/metadata_runs_unresolved.tsv",
        UNRESOLVED_COLUMNS,
        [
            _unresolved_row(
                experiment_accession="SRX_BAD",
                experiment_alias="GSM_BAD",
                study_name="GSE_BAD",
                organism="Homo sapiens",
                corrected_type="Ribo-Seq",
                library_strategy="OTHER",
                library_layout="SINGLE",
                resolution_status="unresolved",
                unresolved_reason="no_local_run_match",
            )
        ],
    )
    source_a, linked_a = _prepare_source_fastq(tmp_path, "GSM_RNA_A_RNA-Seq_SRR1_1.fastq.gz")
    source_b, linked_b = _prepare_source_fastq(tmp_path, "GSM_RIBO_A_Ribo-Seq_SRR2_1.fastq.gz")
    manifest_path = _write_manifest(
        tmp_path / "raw/_manifest.tsv",
        [
            {
                "gsm": "GSM_RNA_A",
                "gse": "GSE_A",
                "srr": "SRR1",
                "mate": "1",
                "organism_canonical": "Homo_sapiens",
                "organism_raw": "Homo sapiens",
                "seq_type": "RNA-Seq",
                "layout": "SINGLE",
                "source_batch": "batch1",
                "source_path": str(source_a),
                "real_target": str(source_a),
                "linked_path": str(linked_a),
                "size_bytes": "5",
                "mtime_iso": "",
                "status": "matched",
                "skip_reason": "",
                "warning": "single_but_mate_1_only",
            },
            {
                "gsm": "GSM_RIBO_A",
                "gse": "GSE_A",
                "srr": "SRR2",
                "mate": "1",
                "organism_canonical": "Homo_sapiens",
                "organism_raw": "Homo sapiens",
                "seq_type": "Ribo-Seq",
                "layout": "SINGLE",
                "source_batch": "batch1",
                "source_path": str(source_b),
                "real_target": str(source_b),
                "linked_path": str(linked_b),
                "size_bytes": "5",
                "mtime_iso": "",
                "status": "matched",
                "skip_reason": "",
                "warning": "single_but_mate_1_only",
            },
        ],
    )
    reference_yaml, template_path = _prepare_reference_and_template(tmp_path)

    result = build_upstream_pilot_package(
        metadata_path=metadata_path,
        runs_path=runs_path,
        unresolved_path=unresolved_path,
        manifest_path=manifest_path,
        pilot_root=tmp_path / "pilot",
        reference_yaml_path=reference_yaml,
        project_template_path=template_path,
    )

    assert result.study_name == "GSE_A"
    assert "GSE_BAD" not in result.selection_path.read_text(encoding="utf-8").split("## Selected Study", 1)[1]
