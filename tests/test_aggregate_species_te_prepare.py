"""Tests for organism-level TE_model input materialization."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from te_analysis.aggregate_species_te import main


def _write_metadata(path: Path, rows: list[dict[str, str]]) -> None:
    header = ",".join(rows[0].keys())
    body = "\n".join(",".join(row[col] for col in rows[0].keys()) for row in rows)
    path.write_text(f"# metadata fixture\n{header}\n{body}\n")


def _touch_ribo(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"stub-ribo")


def _touch_study_root(path: Path, experiment_alias: str, *, with_fastqc: bool = True) -> Path:
    if with_fastqc:
        (path / "fastqc").mkdir(parents=True, exist_ok=True)
    (path / "rnaseq").mkdir(parents=True, exist_ok=True)
    (path / "stats").mkdir(parents=True, exist_ok=True)
    ribo_path = path / "ribo" / "experiments" / f"{experiment_alias}.ribo"
    _touch_ribo(ribo_path)
    return ribo_path


def test_prepare_only_materializes_runtime_inputs(tmp_path: Path) -> None:
    metadata_path = tmp_path / "metadata.csv"
    rows = [
        {
            "experiment_alias": "GSM_A1",
            "cell_line": "HeLa",
            "study_id_index": "1",
            "organism": "Homo sapiens",
            "matched_RNA-seq_experiment_alias": "GSM_R1",
            "corrected_type": "Ribo-Seq",
            "_empty_col": "",
            "source_name_GEO": "",
            "cell_info_GEO": "",
            "experiment_accession": "",
            "study_name": "GSE125086",
            "title": "",
            "sample_accession": "",
            "library_strategy": "",
            "library_layout": "",
            "library_construction_protocol": "",
            "platform": "",
            "platform_parameters": "",
            "xref_link": "",
            "experiment_attribute": "",
            "submission_accession": "",
            "sradb_updated": "",
            "group": "",
            "threep_adapter": "",
            "fivep_adapter": "",
            "threep_umi_length": "",
            "fivep_umi_length": "",
            "run": "SRR0001",
            "fastq_path": "",
            "fastq_path_r2": "",
        },
        {
            "experiment_alias": "GSM_B1",
            "cell_line": "HEK293T",
            "study_id_index": "2",
            "organism": "Homo sapiens",
            "matched_RNA-seq_experiment_alias": "GSM_R2",
            "corrected_type": "Ribo-Seq",
            "_empty_col": "",
            "source_name_GEO": "",
            "cell_info_GEO": "",
            "experiment_accession": "",
            "study_name": "GSE65885",
            "title": "",
            "sample_accession": "",
            "library_strategy": "",
            "library_layout": "",
            "library_construction_protocol": "",
            "platform": "",
            "platform_parameters": "",
            "xref_link": "",
            "experiment_attribute": "",
            "submission_accession": "",
            "sradb_updated": "",
            "group": "",
            "threep_adapter": "",
            "fivep_adapter": "",
            "threep_umi_length": "",
            "fivep_umi_length": "",
            "run": "SRR0002",
            "fastq_path": "",
            "fastq_path_r2": "",
        },
        {
            "experiment_alias": "GSM_X1",
            "cell_line": "leaf",
            "study_id_index": "3",
            "organism": "Arabidopsis thaliana",
            "matched_RNA-seq_experiment_alias": "GSM_RX",
            "corrected_type": "Ribo-Seq",
            "_empty_col": "",
            "source_name_GEO": "",
            "cell_info_GEO": "",
            "experiment_accession": "",
            "study_name": "GSE50597",
            "title": "",
            "sample_accession": "",
            "library_strategy": "",
            "library_layout": "",
            "library_construction_protocol": "",
            "platform": "",
            "platform_parameters": "",
            "xref_link": "",
            "experiment_attribute": "",
            "submission_accession": "",
            "sradb_updated": "",
            "group": "",
            "threep_adapter": "",
            "fivep_adapter": "",
            "threep_umi_length": "",
            "fivep_umi_length": "",
            "run": "SRR0003",
            "fastq_path": "",
            "fastq_path_r2": "",
        },
    ]
    _write_metadata(metadata_path, rows)

    source_root = tmp_path / "sources"
    ribo_a = _touch_study_root(source_root / "GSE125086", "GSM_A1")
    ribo_b = _touch_study_root(source_root / "GSE65885", "GSM_B1", with_fastqc=False)
    ribo_x = _touch_study_root(source_root / "GSE50597", "GSM_X1")

    out_dir = tmp_path / "te_species" / "Homo_sapiens"
    rc = main(
        [
            "--organism",
            "Homo_sapiens",
            "--prepare-only",
            "--out-dir",
            str(out_dir),
            "--metadata",
            str(metadata_path),
            "--ribo-glob",
            str(source_root / "*" / "ribo" / "experiments" / "*.ribo"),
        ]
    )
    assert rc == 0

    selected = pd.read_csv(out_dir / "manifests" / "selected_experiments.tsv", sep="\t")
    manifest = pd.read_csv(out_dir / "manifests" / "selected_ribo_manifest.tsv", sep="\t")
    study_summary = pd.read_csv(out_dir / "manifests" / "study_directory_summary.tsv", sep="\t")
    summary = json.loads((out_dir / "manifests" / "prepare_summary.json").read_text())
    config_text = (
        out_dir
        / "runtime"
        / "vendor"
        / "TE_model"
        / "trials"
        / "homo_sapiens_species_te_prepare"
        / "config.py"
    ).read_text()

    assert len(selected) == 2
    assert sorted(selected["experiment_alias"].tolist()) == ["GSM_A1", "GSM_B1"]
    assert len(manifest) == 2
    assert len(study_summary) == 2
    assert summary["studies_selected"] == 2
    assert summary["experiments_selected"] == 2
    assert summary["ribo_files_materialized"] == 2
    assert "custom_experiment_list=['GSM_A1', 'GSM_B1']" in config_text

    study_link_a = out_dir / "runtime" / "studies" / "GSE125086"
    study_link_b = out_dir / "runtime" / "studies" / "GSE65885"
    vendor_link_a = out_dir / "runtime" / "vendor" / "TE_model" / "data" / "ribo" / "GSE125086"
    vendor_link_b = out_dir / "runtime" / "vendor" / "TE_model" / "data" / "ribo" / "GSE65885"
    assert study_link_a.is_symlink()
    assert study_link_b.is_symlink()
    assert vendor_link_a.is_symlink()
    assert vendor_link_b.is_symlink()
    assert study_link_a.resolve() == (source_root / "GSE125086").resolve()
    assert study_link_b.resolve() == (source_root / "GSE65885").resolve()
    assert vendor_link_a.resolve() == (source_root / "GSE125086").resolve()
    assert vendor_link_b.resolve() == (source_root / "GSE65885").resolve()
    assert (vendor_link_a / "ribo" / "experiments" / "GSM_A1.ribo").resolve() == ribo_a.resolve()
    assert (vendor_link_b / "ribo" / "experiments" / "GSM_B1.ribo").resolve() == ribo_b.resolve()

    summary_by_study = {row["study_name"]: row for row in study_summary.to_dict("records")}
    assert bool(summary_by_study["GSE125086"]["has_fastqc"]) is True
    assert bool(summary_by_study["GSE65885"]["has_fastqc"]) is False
    assert bool(summary_by_study["GSE125086"]["has_ribo"]) is True
    assert bool(summary_by_study["GSE125086"]["has_rnaseq"]) is True
    assert bool(summary_by_study["GSE125086"]["has_stats"]) is True


def test_prepare_only_requested_study_without_ribo_raises(tmp_path: Path) -> None:
    metadata_path = tmp_path / "metadata.csv"
    _write_metadata(
        metadata_path,
        [
            {
                "experiment_alias": "GSM_A1",
                "cell_line": "HeLa",
                "study_id_index": "1",
                "organism": "Homo sapiens",
                "matched_RNA-seq_experiment_alias": "GSM_R1",
                "corrected_type": "Ribo-Seq",
                "_empty_col": "",
                "source_name_GEO": "",
                "cell_info_GEO": "",
                "experiment_accession": "",
                "study_name": "GSE125086",
                "title": "",
                "sample_accession": "",
                "library_strategy": "",
                "library_layout": "",
                "library_construction_protocol": "",
                "platform": "",
                "platform_parameters": "",
                "xref_link": "",
                "experiment_attribute": "",
                "submission_accession": "",
                "sradb_updated": "",
                "group": "",
                "threep_adapter": "",
                "fivep_adapter": "",
                "threep_umi_length": "",
                "fivep_umi_length": "",
                "run": "SRR0001",
                "fastq_path": "",
                "fastq_path_r2": "",
            }
        ],
    )
    source_root = tmp_path / "sources"
    _touch_study_root(source_root / "GSE125086", "GSM_A1")

    with pytest.raises(ValueError, match="requested study has no selected ribo experiments"):
        main(
            [
                "--organism",
                "Homo_sapiens",
                "--prepare-only",
                "--out-dir",
                str(tmp_path / "out"),
                "--metadata",
                str(metadata_path),
                "--study",
                "GSE999999",
                "--ribo-glob",
                str(source_root / "*" / "ribo" / "experiments" / "*.ribo"),
            ]
        )
