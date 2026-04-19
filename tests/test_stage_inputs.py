"""Unit tests for te_analysis.stage_inputs (module_contracts §M10 T10).

Uses real GSE132441 metadata + real on-disk FASTQ. No snakemake invocation.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from te_analysis.config import REPO_ROOT
from te_analysis.stage_inputs import main

METADATA = REPO_ROOT / "data" / "raw" / "metadata.csv"
HAPPY_STUDY = "GSE132441"


def _run(*args: str) -> int:
    return main(list(args))


def test_metadata_not_found_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="metadata.csv not found"):
        _run("--metadata", str(tmp_path / "nope.csv"),
             "--study", HAPPY_STUDY, "--out", str(tmp_path / "out"))


def test_unknown_study_raises_with_suggestions(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="not in metadata.csv"):
        _run("--metadata", str(METADATA),
             "--study", "GSENONE", "--out", str(tmp_path / "out"))


def test_invalid_suffix_raises(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="invalid study suffix"):
        _run("--metadata", str(METADATA),
             "--study", "GSE132441_bogus", "--out", str(tmp_path / "out"))


def test_happy_path_gse132441(tmp_path: Path) -> None:
    out = tmp_path / "gse132441"
    rc = _run("--metadata", str(METADATA), "--study", HAPPY_STUDY, "--out", str(out))
    assert rc == 0

    # project.yaml structural checks
    doc = yaml.safe_load((out / "project.yaml").read_text())
    assert doc["do_rnaseq"] is True
    assert doc["deduplicate"] is False
    assert set(doc["input"]["fastq"].keys()) == {
        "GSM3863556", "GSM3863558", "GSM3863561"
    }
    assert set(doc["rnaseq"]["fastq"].keys()) == set(doc["input"]["fastq"].keys()), (
        "rnaseq.fastq MUST be keyed by Ribo GSM (generate_yaml.py:300)"
    )
    for gsm, paths in doc["input"]["fastq"].items():
        assert paths, f"{gsm} has empty Ribo SRR list"
        for p in paths:
            assert p.startswith(f"staged_fastq/{HAPPY_STUDY}/"), p
    # Reference paths populated for arabidopsis
    for k in ("filter", "transcriptome", "regions", "transcript_lengths"):
        assert doc["input"]["reference"][k].startswith("reference/"), k

    # Symlinks actually point to real files
    staged = out / "staged_fastq" / HAPPY_STUDY
    assert staged.is_dir()
    links = sorted(staged.rglob("*.fastq.gz"))
    assert len(links) == 6  # 3 Ribo + 3 RNA (all single-end for this study)
    for link in links:
        assert link.is_symlink()
        assert link.resolve().is_file()


def test_idempotent(tmp_path: Path) -> None:
    out = tmp_path / "gse132441"
    _run("--metadata", str(METADATA), "--study", HAPPY_STUDY, "--out", str(out))
    snapshot = (out / "project.yaml").read_bytes()
    _run("--metadata", str(METADATA), "--study", HAPPY_STUDY, "--out", str(out))
    assert (out / "project.yaml").read_bytes() == snapshot


def test_cli_module_invocation(tmp_path: Path) -> None:
    """Smoke test `python -m te_analysis.stage_inputs` exit code path."""
    out = tmp_path / "cli"
    res = subprocess.run(
        [sys.executable, "-m", "te_analysis.stage_inputs",
         "--metadata", str(METADATA), "--study", HAPPY_STUDY, "--out", str(out)],
        cwd=REPO_ROOT, capture_output=True, text=True,
        env={"PYTHONPATH": str(REPO_ROOT / "src"), "PATH": "/usr/bin:/bin"},
    )
    assert res.returncode == 0, res.stderr
    assert (out / "project.yaml").is_file()


def test_cli_missing_arg_exits_nonzero(tmp_path: Path) -> None:
    res = subprocess.run(
        [sys.executable, "-m", "te_analysis.stage_inputs",
         "--metadata", str(METADATA), "--study", HAPPY_STUDY],  # missing --out
        cwd=REPO_ROOT, capture_output=True, text=True,
        env={"PYTHONPATH": str(REPO_ROOT / "src"), "PATH": "/usr/bin:/bin"},
    )
    assert res.returncode != 0
    assert "--out" in res.stderr


def test_missing_fastq_on_disk_raises(tmp_path: Path) -> None:
    """If fastq_path points to a non-existent file, FileNotFoundError is raised."""
    fake_meta = tmp_path / "fake_metadata.csv"
    # Row schema: copy header from real metadata + one fabricated row
    header_lines = METADATA.read_text().splitlines()[:2]
    header = header_lines[1].split(",")
    row = [""] * len(header)
    def _set(col: str, val: str) -> None:
        row[header.index(col)] = val
    _set("experiment_alias", "GSMFAKE")
    _set("organism", "Homo sapiens")
    _set("matched_RNA-seq_experiment_alias", "")
    _set("corrected_type", "Ribo-Seq")
    _set("experiment_accession", "SRXFAKE")
    _set("study_name", "GSEFAKET4")
    _set("run", "SRRFAKE")
    _set("fastq_path", "nonexistent_org/GSEFAKET4/GSMFAKE_Ribo-Seq_SRRFAKE_1.fastq.gz")
    fake_meta.write_text(
        header_lines[0] + "\n" + header_lines[1] + "\n" + ",".join(row) + "\n"
    )
    with pytest.raises(FileNotFoundError, match="fastq_path missing on disk"):
        _run("--metadata", str(fake_meta), "--study", "GSEFAKET4",
             "--out", str(tmp_path / "out"))
