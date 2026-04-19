"""T4 DoD §6 (downscoped) — project.yaml schema-level validation.

DoD §6 original text: "GSE132441 project.yaml snakescale dry-run-recognized".
Downscope rationale (plan §0): snakemake dry-run needs db.sqlite3 + reference/ +
nextflow env, which are T8 scope. Here we validate structure only, against
the field table in docs/snakescale_contract.md §1.2.
"""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from te_analysis.config import REPO_ROOT
from te_analysis.stage_inputs import main as stage_inputs_main

METADATA = REPO_ROOT / "data" / "raw" / "metadata.csv"


@pytest.fixture(scope="module")
def project_yaml(tmp_path_factory: pytest.TempPathFactory) -> dict:
    out = tmp_path_factory.mktemp("gse132441")
    stage_inputs_main([
        "--metadata", str(METADATA), "--study", "GSE132441", "--out", str(out),
    ])
    return yaml.safe_load((out / "project.yaml").read_text())


def test_required_top_level_keys(project_yaml: dict) -> None:
    """All top-level keys from snakescale_contract §1.2 must exist."""
    required = {
        "do_fastqc", "do_check_file_existence", "deduplicate", "do_rnaseq",
        "do_metadata", "clip_arguments", "mapping_quality_cutoff",
        "alignment_arguments", "ribo", "output", "input", "rnaseq",
    }
    assert required.issubset(project_yaml.keys()), (
        f"missing: {sorted(required - project_yaml.keys())}"
    )


def test_input_reference_paths_populated(project_yaml: dict) -> None:
    """input.reference.{filter,transcriptome,regions,transcript_lengths} all set."""
    ref = project_yaml["input"]["reference"]
    for key in ("filter", "transcriptome", "regions", "transcript_lengths"):
        assert isinstance(ref[key], str) and ref[key].startswith("reference/"), (
            f"reference.{key}={ref[key]!r} invalid"
        )


def test_input_fastq_nonempty_lists(project_yaml: dict) -> None:
    fastq = project_yaml["input"]["fastq"]
    assert fastq, "input.fastq is empty"
    for gsm, paths in fastq.items():
        assert isinstance(paths, list) and len(paths) >= 1, f"{gsm}: {paths}"
        for p in paths:
            assert p.endswith("_1.fastq.gz"), p
            assert "staged_fastq/GSE132441/" in p, p


def test_rnaseq_fastq_matches_ribo_keys(project_yaml: dict) -> None:
    """rnaseq.fastq keys must be Ribo GSM (not RNA GSM) per generate_yaml.py:300."""
    assert set(project_yaml["rnaseq"]["fastq"].keys()) == set(
        project_yaml["input"]["fastq"].keys()
    )


def test_clip_arguments_format(project_yaml: dict) -> None:
    """Must contain '-u N' and '--quality-cutoff' at minimum."""
    clip = project_yaml["clip_arguments"]
    assert "-u " in clip
    assert "--quality-cutoff" in clip
    rna_clip = project_yaml["rnaseq"]["clip_arguments"]
    assert "-u " in rna_clip
    assert "--quality-cutoff" in rna_clip


def test_output_bases_include_study(project_yaml: dict) -> None:
    assert project_yaml["output"]["output"]["base"] == "output/GSE132441"
    assert project_yaml["output"]["intermediates"]["base"] == "intermediates/GSE132441"


def test_ribo_block_unchanged_from_template(project_yaml: dict) -> None:
    """Default RiboPy parameters must survive template override (M1.MUSTNOT.6)."""
    ribo = project_yaml["ribo"]
    assert ribo["ref_name"] == "appris-v1"
    assert ribo["metagene_radius"] == 50
    assert ribo["read_length"] == {"min": 15, "max": 40}
