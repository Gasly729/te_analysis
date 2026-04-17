from __future__ import annotations

import csv
import importlib.util
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "ingest_raw_symlinks.py"
ALIAS_PATH = ROOT / "scripts" / "organism_alias_min.yaml"
SPEC = importlib.util.spec_from_file_location("ingest_raw_symlinks", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


@pytest.fixture(autouse=True)
def _reset_force_prefer_state() -> None:
    MODULE.configure_force_prefer_batch2_runs("")
    MODULE.FORCED_SIZE_MISMATCH_KEYS = set()


def _write_fastq(path: Path, content: str = "fastq") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return path


def _metadata_path(tmp_path: Path) -> Path:
    return tmp_path / "data" / "raw" / "metadata.csv"


def _target_root(tmp_path: Path) -> Path:
    return tmp_path / "data" / "raw"


def _source_roots(tmp_path: Path) -> dict[str, Path]:
    roots = {
        "batch1": tmp_path / "batch1",
        "batch2": tmp_path / "batch2",
    }
    for root in roots.values():
        root.mkdir(parents=True, exist_ok=True)
    return roots


def _write_metadata(
    path: Path,
    rows: list[dict[str, str]],
    *,
    include_run_alias: bool = True,
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    headers = [
        "experiment_alias",
        "study_name",
        "organism",
        "library_strategy",
        "library_layout",
        "corrected_type",
        "experiment_accession",
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


def _load_manifest_rows(target_root: Path) -> list[dict[str, str]]:
    with (target_root / "_manifest.tsv").open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        return list(reader)


def test_batch1_only_matched(tmp_path: Path) -> None:
    sources = _source_roots(tmp_path)
    _write_fastq(sources["batch1"] / "a" / "SRR100_GSM100_Homo_sapiens_RNA-Seq.fastq.gz")
    _write_metadata(
        _metadata_path(tmp_path),
        [
            {
                "experiment_alias": "GSM100",
                "study_name": "GSE100",
                "organism": "Human",
                "library_strategy": "RNA-Seq",
                "library_layout": "SINGLE",
                "corrected_type": "RNA-Seq",
                "experiment_accession": "SRX100",
                "run_alias": "SRR100",
            }
        ],
    )

    plan = MODULE.run_ingest(
        source_roots=sources,
        target_root=_target_root(tmp_path),
        metadata_path=_metadata_path(tmp_path),
        alias_table_path=ALIAS_PATH,
        conflict_policy="prefer-batch2",
        apply=True,
    )

    assert len(plan.matched_rows) == 1
    row = plan.matched_rows[0]
    destination = Path(row.linked_path)
    assert destination.is_symlink()
    assert destination.name == "GSM100_RNA-Seq_SRR100.fastq.gz"
    assert destination.resolve() == (sources["batch1"] / "a" / "SRR100_GSM100_Homo_sapiens_RNA-Seq.fastq.gz").resolve()


def test_batch2_only_matched(tmp_path: Path) -> None:
    sources = _source_roots(tmp_path)
    _write_fastq(sources["batch2"] / "SRR200_GSM200_Homo_sapiens_OTHER.fastq.gz")
    _write_metadata(
        _metadata_path(tmp_path),
        [
            {
                "experiment_alias": "GSM200",
                "study_name": "GSE200",
                "organism": "Hela",
                "library_strategy": "OTHER",
                "library_layout": "SINGLE",
                "corrected_type": "Ribo-Seq",
                "experiment_accession": "SRX200",
                "run_alias": "SRR200",
            }
        ],
    )

    plan = MODULE.run_ingest(
        source_roots=sources,
        target_root=_target_root(tmp_path),
        metadata_path=_metadata_path(tmp_path),
        alias_table_path=ALIAS_PATH,
        conflict_policy="prefer-batch2",
        apply=True,
    )

    assert len(plan.matched_rows) == 1
    assert plan.matched_rows[0].seq_type == "Ribo-Seq"
    assert Path(plan.matched_rows[0].linked_path).name == "GSM200_Ribo-Seq_SRR200.fastq.gz"


def test_conflict_prefer_batch2(tmp_path: Path) -> None:
    sources = _source_roots(tmp_path)
    _write_fastq(sources["batch1"] / "SRR300_GSM300_Homo_sapiens_RNA-Seq.fastq.gz", content="same")
    preferred = _write_fastq(sources["batch2"] / "SRR300_GSM300_Homo_sapiens_RNA-Seq.fastq.gz", content="same")
    _write_metadata(
        _metadata_path(tmp_path),
        [
            {
                "experiment_alias": "GSM300",
                "study_name": "GSE300",
                "organism": "Homo sapiens",
                "library_strategy": "RNA-Seq",
                "library_layout": "SINGLE",
                "corrected_type": "RNA-Seq",
                "experiment_accession": "SRX300",
                "run_alias": "SRR300",
            }
        ],
    )

    plan = MODULE.run_ingest(
        source_roots=sources,
        target_root=_target_root(tmp_path),
        metadata_path=_metadata_path(tmp_path),
        alias_table_path=ALIAS_PATH,
        conflict_policy="prefer-batch2",
        apply=True,
    )

    assert len(plan.conflict_rows) == 1
    assert plan.conflict_rows[0].chosen_batch == "batch2"
    assert Path(plan.matched_rows[0].linked_path).resolve() == preferred.resolve()


def test_conflict_size_mismatch_skipped(tmp_path: Path) -> None:
    sources = _source_roots(tmp_path)
    _write_fastq(sources["batch1"] / "SRR400_GSM400_Homo_sapiens_RNA-Seq.fastq.gz", content="a")
    _write_fastq(sources["batch2"] / "SRR400_GSM400_Homo_sapiens_RNA-Seq.fastq.gz", content="bb")
    _write_metadata(
        _metadata_path(tmp_path),
        [
            {
                "experiment_alias": "GSM400",
                "study_name": "GSE400",
                "organism": "Human",
                "library_strategy": "RNA-Seq",
                "library_layout": "SINGLE",
                "corrected_type": "RNA-Seq",
                "experiment_accession": "SRX400",
                "run_alias": "SRR400",
            }
        ],
    )

    plan = MODULE.run_ingest(
        source_roots=sources,
        target_root=_target_root(tmp_path),
        metadata_path=_metadata_path(tmp_path),
        alias_table_path=ALIAS_PATH,
        conflict_policy="prefer-batch2",
        apply=False,
    )

    skipped = [row for row in plan.rows if row.skip_reason == "size_mismatch_between_batches"]
    assert len(skipped) == 2
    assert len(plan.matched_rows) == 0


def test_paired_end_both_mates_linked(tmp_path: Path) -> None:
    sources = _source_roots(tmp_path)
    _write_fastq(sources["batch1"] / "deep" / "SRR500_GSM500_Mouse_RNA-Seq_1.fastq.gz")
    _write_fastq(sources["batch1"] / "deep" / "SRR500_GSM500_Mouse_RNA-Seq_2.fastq.gz")
    _write_metadata(
        _metadata_path(tmp_path),
        [
            {
                "experiment_alias": "GSM500",
                "study_name": "GSE500",
                "organism": "Mouse",
                "library_strategy": "RNA-Seq",
                "library_layout": "PAIRED",
                "corrected_type": "RNA-Seq",
                "experiment_accession": "SRX500",
                "run_alias": "SRR500",
            }
        ],
    )

    plan = MODULE.run_ingest(
        source_roots=sources,
        target_root=_target_root(tmp_path),
        metadata_path=_metadata_path(tmp_path),
        alias_table_path=ALIAS_PATH,
        conflict_policy="prefer-batch2",
        apply=True,
    )

    assert len(plan.matched_rows) == 2
    names = sorted(Path(row.linked_path).name for row in plan.matched_rows)
    assert names == [
        "GSM500_RNA-Seq_SRR500_1.fastq.gz",
        "GSM500_RNA-Seq_SRR500_2.fastq.gz",
    ]


def test_paired_missing_mate_skipped(tmp_path: Path) -> None:
    sources = _source_roots(tmp_path)
    _write_fastq(sources["batch1"] / "SRR600_GSM600_Mouse_RNA-Seq_1.fastq.gz")
    _write_metadata(
        _metadata_path(tmp_path),
        [
            {
                "experiment_alias": "GSM600",
                "study_name": "GSE600",
                "organism": "Mouse",
                "library_strategy": "RNA-Seq",
                "library_layout": "PAIRED",
                "corrected_type": "RNA-Seq",
                "experiment_accession": "SRX600",
                "run_alias": "SRR600",
            }
        ],
    )

    plan = MODULE.run_ingest(
        source_roots=sources,
        target_root=_target_root(tmp_path),
        metadata_path=_metadata_path(tmp_path),
        alias_table_path=ALIAS_PATH,
        conflict_policy="prefer-batch2",
        apply=False,
    )

    skipped = [row for row in plan.rows if row.skip_reason == "paired_missing_mate"]
    assert len(skipped) == 1


def test_srr_not_in_metadata(tmp_path: Path) -> None:
    sources = _source_roots(tmp_path)
    _write_fastq(sources["batch1"] / "SRR700_GSM700_Mouse_RNA-Seq.fastq.gz")
    _write_metadata(_metadata_path(tmp_path), [])

    plan = MODULE.run_ingest(
        source_roots=sources,
        target_root=_target_root(tmp_path),
        metadata_path=_metadata_path(tmp_path),
        alias_table_path=ALIAS_PATH,
        conflict_policy="prefer-batch2",
        apply=False,
    )

    skipped = [row for row in plan.rows if row.skip_reason == "srr_not_in_metadata"]
    assert len(skipped) >= 1


def test_organism_unmapped_reported(tmp_path: Path) -> None:
    sources = _source_roots(tmp_path)
    _write_fastq(sources["batch1"] / "SRR800_GSM800_Customus_RNA-Seq.fastq.gz")
    _write_metadata(
        _metadata_path(tmp_path),
        [
            {
                "experiment_alias": "GSM800",
                "study_name": "GSE800",
                "organism": "Custom organism",
                "library_strategy": "RNA-Seq",
                "library_layout": "SINGLE",
                "corrected_type": "RNA-Seq",
                "experiment_accession": "SRX800",
                "run_alias": "SRR800",
            }
        ],
    )

    plan = MODULE.run_ingest(
        source_roots=sources,
        target_root=_target_root(tmp_path),
        metadata_path=_metadata_path(tmp_path),
        alias_table_path=ALIAS_PATH,
        conflict_policy="prefer-batch2",
        apply=True,
    )

    assert "Custom organism" in plan.metadata_bundle.unmapped_organisms
    report_text = (_target_root(tmp_path) / "_ingest_report.md").read_text(encoding="utf-8")
    assert "Custom organism" in report_text


def test_hybrid_species_skipped(tmp_path: Path) -> None:
    sources = _source_roots(tmp_path)
    _write_fastq(sources["batch1"] / "SRR900_GSM900_yeast_RNA-Seq.fastq.gz")
    _write_metadata(
        _metadata_path(tmp_path),
        [
            {
                "experiment_alias": "GSM900",
                "study_name": "GSE900",
                "organism": "Saccharomyces cerevisiae* Saccharomyces paradoxus",
                "library_strategy": "RNA-Seq",
                "library_layout": "SINGLE",
                "corrected_type": "RNA-Seq",
                "experiment_accession": "SRX900",
                "run_alias": "SRR900",
            }
        ],
    )

    plan = MODULE.run_ingest(
        source_roots=sources,
        target_root=_target_root(tmp_path),
        metadata_path=_metadata_path(tmp_path),
        alias_table_path=ALIAS_PATH,
        conflict_policy="prefer-batch2",
        apply=False,
    )

    skipped = [row for row in plan.rows if row.skip_reason == "hybrid_species_phase2"]
    assert len(skipped) == 1


def test_orphan_metadata_has_distinct_skip_reason(tmp_path: Path) -> None:
    sources = _source_roots(tmp_path)
    _write_metadata(
        _metadata_path(tmp_path),
        [
            {
                "experiment_alias": "GSM905",
                "study_name": "GSE905",
                "organism": "Mouse",
                "library_strategy": "RNA-Seq",
                "library_layout": "SINGLE",
                "corrected_type": "RNA-Seq",
                "experiment_accession": "SRX905",
                "run_alias": "SRR905",
            }
        ],
    )

    plan = MODULE.run_ingest(
        source_roots=sources,
        target_root=_target_root(tmp_path),
        metadata_path=_metadata_path(tmp_path),
        alias_table_path=ALIAS_PATH,
        conflict_policy="prefer-batch2",
        apply=False,
    )

    orphan_rows = [row for row in plan.rows if row.skip_reason == "orphan_metadata"]
    srr_missing_rows = [row for row in plan.rows if row.skip_reason == "srr_not_in_metadata"]
    assert len(orphan_rows) == 1
    assert orphan_rows[0].gsm == "GSM905"
    assert len(srr_missing_rows) == 0


def test_hybrid_detected_by_star_separator(tmp_path: Path) -> None:
    sources = _source_roots(tmp_path)
    _write_fastq(sources["batch1"] / "SRR906_GSM906_yeast_RNA-Seq.fastq.gz")
    _write_metadata(
        _metadata_path(tmp_path),
        [
            {
                "experiment_alias": "GSM906",
                "study_name": "GSE906",
                "organism": "Saccharomyces cerevisiae * Saccharomyces paradoxus",
                "library_strategy": "RNA-Seq",
                "library_layout": "SINGLE",
                "corrected_type": "RNA-Seq",
                "experiment_accession": "SRX906",
                "run_alias": "SRR906",
            }
        ],
    )

    plan = MODULE.run_ingest(
        source_roots=sources,
        target_root=_target_root(tmp_path),
        metadata_path=_metadata_path(tmp_path),
        alias_table_path=ALIAS_PATH,
        conflict_policy="prefer-batch2",
        apply=False,
    )

    skipped = [row for row in plan.rows if row.skip_reason == "hybrid_species_phase2"]
    assert len(skipped) == 1
    assert skipped[0].gsm == "GSM906"


def test_gse_missing_goes_to_ungrouped(tmp_path: Path) -> None:
    sources = _source_roots(tmp_path)
    _write_fastq(sources["batch1"] / "SRR1000_GSM1000_Mouse_RNA-Seq.fastq.gz")
    _write_metadata(
        _metadata_path(tmp_path),
        [
            {
                "experiment_alias": "GSM1000",
                "study_name": "",
                "organism": "Mouse",
                "library_strategy": "RNA-Seq",
                "library_layout": "SINGLE",
                "corrected_type": "RNA-Seq",
                "experiment_accession": "SRX1000",
                "run_alias": "SRR1000",
            }
        ],
    )

    plan = MODULE.run_ingest(
        source_roots=sources,
        target_root=_target_root(tmp_path),
        metadata_path=_metadata_path(tmp_path),
        alias_table_path=ALIAS_PATH,
        conflict_policy="prefer-batch2",
        apply=True,
    )

    row = plan.matched_rows[0]
    assert "/_ungrouped/" in row.linked_path
    assert row.warning == "no_gse_assignment"


def test_idempotent_rerun(tmp_path: Path) -> None:
    sources = _source_roots(tmp_path)
    source_path = _write_fastq(sources["batch1"] / "SRR1100_GSM1100_Mouse_RNA-Seq.fastq.gz")
    _write_metadata(
        _metadata_path(tmp_path),
        [
            {
                "experiment_alias": "GSM1100",
                "study_name": "GSE1100",
                "organism": "Mouse",
                "library_strategy": "RNA-Seq",
                "library_layout": "SINGLE",
                "corrected_type": "RNA-Seq",
                "experiment_accession": "SRX1100",
                "run_alias": "SRR1100",
            }
        ],
    )

    first = MODULE.run_ingest(
        source_roots=sources,
        target_root=_target_root(tmp_path),
        metadata_path=_metadata_path(tmp_path),
        alias_table_path=ALIAS_PATH,
        conflict_policy="prefer-batch2",
        apply=True,
    )
    second = MODULE.run_ingest(
        source_roots=sources,
        target_root=_target_root(tmp_path),
        metadata_path=_metadata_path(tmp_path),
        alias_table_path=ALIAS_PATH,
        conflict_policy="prefer-batch2",
        apply=True,
    )

    assert Path(first.matched_rows[0].linked_path).resolve() == source_path.resolve()
    assert Path(second.matched_rows[0].linked_path).resolve() == source_path.resolve()


def test_conflicting_symlink_errors(tmp_path: Path) -> None:
    sources = _source_roots(tmp_path)
    expected = _write_fastq(sources["batch1"] / "SRR1200_GSM1200_Mouse_RNA-Seq.fastq.gz")
    conflicting = _write_fastq(tmp_path / "other" / "SRR1200.fastq.gz")
    _write_metadata(
        _metadata_path(tmp_path),
        [
            {
                "experiment_alias": "GSM1200",
                "study_name": "GSE1200",
                "organism": "Mouse",
                "library_strategy": "RNA-Seq",
                "library_layout": "SINGLE",
                "corrected_type": "RNA-Seq",
                "experiment_accession": "SRX1200",
                "run_alias": "SRR1200",
            }
        ],
    )

    destination = _target_root(tmp_path) / "Mus_musculus" / "GSE1200" / "GSM1200_RNA-Seq_SRR1200.fastq.gz"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.symlink_to(conflicting.resolve())

    with pytest.raises(MODULE.IngestError, match="Conflicting symlink target"):
        MODULE.run_ingest(
            source_roots=sources,
            target_root=_target_root(tmp_path),
            metadata_path=_metadata_path(tmp_path),
            alias_table_path=ALIAS_PATH,
            conflict_policy="prefer-batch2",
            apply=True,
        )

    assert expected.exists()


def test_dry_run_no_filesystem_changes(tmp_path: Path) -> None:
    sources = _source_roots(tmp_path)
    _write_fastq(sources["batch1"] / "SRR1300_GSM1300_Mouse_RNA-Seq.fastq.gz")
    _write_metadata(
        _metadata_path(tmp_path),
        [
            {
                "experiment_alias": "GSM1300",
                "study_name": "GSE1300",
                "organism": "Mouse",
                "library_strategy": "RNA-Seq",
                "library_layout": "SINGLE",
                "corrected_type": "RNA-Seq",
                "experiment_accession": "SRX1300",
                "run_alias": "SRR1300",
            }
        ],
    )

    plan = MODULE.run_ingest(
        source_roots=sources,
        target_root=_target_root(tmp_path),
        metadata_path=_metadata_path(tmp_path),
        alias_table_path=ALIAS_PATH,
        conflict_policy="prefer-batch2",
        apply=False,
    )

    assert len(plan.matched_rows) == 1
    assert not (_target_root(tmp_path) / "_manifest.tsv").exists()
    assert not (_target_root(tmp_path) / "Mus_musculus" / "GSE1300").exists()


def test_old_manifest_backed_up_with_timestamp(tmp_path: Path) -> None:
    sources = _source_roots(tmp_path)
    _write_fastq(sources["batch1"] / "SRR1400_GSM1400_Mouse_RNA-Seq.fastq.gz")
    _write_metadata(
        _metadata_path(tmp_path),
        [
            {
                "experiment_alias": "GSM1400",
                "study_name": "GSE1400",
                "organism": "Mouse",
                "library_strategy": "RNA-Seq",
                "library_layout": "SINGLE",
                "corrected_type": "RNA-Seq",
                "experiment_accession": "SRX1400",
                "run_alias": "SRR1400",
            }
        ],
    )
    target_root = _target_root(tmp_path)
    target_root.mkdir(parents=True, exist_ok=True)
    old_manifest = target_root / "_manifest.tsv"
    old_manifest.write_text("old-manifest\n", encoding="utf-8")

    MODULE.run_ingest(
        source_roots=sources,
        target_root=target_root,
        metadata_path=_metadata_path(tmp_path),
        alias_table_path=ALIAS_PATH,
        conflict_policy="prefer-batch2",
        apply=True,
    )

    backups = list(target_root.glob("_manifest.tsv.bak.*"))
    assert len(backups) == 1
    assert backups[0].read_text(encoding="utf-8") == "old-manifest\n"
    assert "GSM1400" in old_manifest.read_text(encoding="utf-8")


def test_alias_fallback_without_run_alias_column(tmp_path: Path) -> None:
    sources = _source_roots(tmp_path)
    _write_fastq(sources["batch1"] / "SRR1500_GSM1500_Mouse_RNA-Seq.fastq.gz")
    _write_metadata(
        _metadata_path(tmp_path),
        [
            {
                "experiment_alias": "GSM1500",
                "study_name": "GSE1500",
                "organism": "Mouse",
                "library_strategy": "RNA-Seq",
                "library_layout": "SINGLE",
                "corrected_type": "RNA-Seq",
                "experiment_accession": "SRX1500",
            }
        ],
        include_run_alias=False,
    )

    plan = MODULE.run_ingest(
        source_roots=sources,
        target_root=_target_root(tmp_path),
        metadata_path=_metadata_path(tmp_path),
        alias_table_path=ALIAS_PATH,
        conflict_policy="prefer-batch2",
        apply=True,
    )

    assert len(plan.matched_rows) == 1
    assert plan.metadata_bundle.has_run_alias_column is False
    rows = _load_manifest_rows(_target_root(tmp_path))
    assert rows[0]["gsm"] == "GSM1500"


def test_force_prefer_batch2_promotes_size_mismatch_to_matched(tmp_path: Path) -> None:
    sources = _source_roots(tmp_path)
    _write_fastq(sources["batch1"] / "SRR1600_GSM1600_Mouse_RNA-Seq.fastq.gz", content="short")
    preferred = _write_fastq(sources["batch2"] / "SRR1600_GSM1600_Mouse_RNA-Seq.fastq.gz", content="longer")
    _write_metadata(
        _metadata_path(tmp_path),
        [
            {
                "experiment_alias": "GSM1600",
                "study_name": "GSE1600",
                "organism": "Mouse",
                "library_strategy": "RNA-Seq",
                "library_layout": "SINGLE",
                "corrected_type": "RNA-Seq",
                "experiment_accession": "SRX1600",
                "run_alias": "SRR1600",
            }
        ],
    )
    MODULE.configure_force_prefer_batch2_runs("SRR1600")

    plan = MODULE.run_ingest(
        source_roots=sources,
        target_root=_target_root(tmp_path),
        metadata_path=_metadata_path(tmp_path),
        alias_table_path=ALIAS_PATH,
        conflict_policy="prefer-batch2",
        apply=True,
    )

    assert len(plan.matched_rows) == 1
    assert Path(plan.matched_rows[0].linked_path).resolve() == preferred.resolve()
    assert "forced_prefer_batch2_size_mismatch" in plan.matched_rows[0].warning
    assert len([row for row in plan.rows if row.skip_reason == "size_mismatch_between_batches"]) == 0
