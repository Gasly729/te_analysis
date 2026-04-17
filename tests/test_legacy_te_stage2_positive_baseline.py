from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASELINE_PATH = ROOT / "configs" / "downstream" / "legacy_te_stage2_positive_baseline.json"


def _load_baseline() -> dict[str, object]:
    return json.loads(BASELINE_PATH.read_text())


def test_stage2_positive_baseline_descriptor_is_locked() -> None:
    baseline = _load_baseline()

    assert baseline["baseline_name"] == "legacy_te_final_positive_smoke"
    assert baseline["run_id"] == "verify_gse105082_hela_triplet_stage2"
    assert baseline["target_stage"] == 3
    assert baseline["study_id"] == "GSE105082"
    assert baseline["grouping"] == "HeLa"
    assert baseline["cohort"] == ["GSM2817679", "GSM2817680", "GSM2817681"]
    assert baseline["minimum_stage2_samples"] == 2
    assert baseline["single_sample_stage2_expected_failure"] is True
    assert baseline["stage3_in_scope"] is True
    assert baseline["expected_stage2_outputs"] == [
        "human_TE_sample_level.rda",
        "human_TE_cellline_all.csv",
    ]
    assert baseline["expected_stage3_outputs"] == ["human_TE_cellline_all_T.csv"]
    regression = baseline["baseline_specific_final_output_regression"]
    general_contract = baseline["general_stage3_output_contract"]
    assert regression["shape"] == [10862, 1]
    assert regression["column_names"] == ["HeLa"]
    assert regression["index_null_count"] == 0
    assert regression["index_unique"] is False
    assert regression["duplicate_gene_identifier_count"] == 15
    assert general_contract["output_file_name"] == "human_TE_cellline_all_T.csv"
    assert general_contract["must_live_under_runtime_root"] is True
    assert general_contract["must_be_non_empty"] is True
    assert general_contract["minimum_output_columns"] == 1
    assert general_contract["column_axis_unique"] is True
    assert general_contract["index_null_count"] == 0


def test_stage2_positive_baseline_assets_exist() -> None:
    baseline = _load_baseline()
    run_id = str(baseline["run_id"])
    runtime_root = ROOT / "data" / "downstream_runs" / run_id
    trial_root = runtime_root / "sandbox" / "trials" / run_id

    assert (runtime_root / "inputs" / "wrapper_request.json").exists()
    assert (runtime_root / "inputs" / "handoff_manifest.json").exists()
    assert (runtime_root / "inputs" / "grouping.csv").exists()
    assert (runtime_root / "compatibility_note.md").exists()
    for output_name in baseline["expected_stage2_outputs"]:
        assert (trial_root / str(output_name)).exists()
    for output_name in baseline["expected_stage3_outputs"]:
        assert (trial_root / str(output_name)).exists()


def test_stage3_final_baseline_regression_is_locked_to_human_hela_runtime() -> None:
    import pandas as pd

    baseline = _load_baseline()
    run_id = str(baseline["run_id"])
    regression = baseline["baseline_specific_final_output_regression"]
    runtime_root = ROOT / "data" / "downstream_runs" / run_id
    stage3_path = runtime_root / regression["path_relative_to_runtime"]
    stage3_df = pd.read_csv(stage3_path, index_col=0)

    assert stage3_df.shape == tuple(regression["shape"])
    assert list(stage3_df.columns) == regression["column_names"]
    assert int(stage3_df.index.isna().sum()) == regression["index_null_count"]
    assert bool(stage3_df.index.is_unique) is regression["index_unique"]
    duplicate_gene_count = int(stage3_df.index.duplicated().sum())
    assert duplicate_gene_count == regression["duplicate_gene_identifier_count"]
    duplicate_families = stage3_df.index[stage3_df.index.duplicated(keep=False)].unique().tolist()
    assert duplicate_families == regression["duplicate_gene_identifier_families"]


def test_stage2_positive_baseline_doc_mentions_boundary_and_outputs() -> None:
    doc_path = ROOT / "docs" / "architecture" / "legacy_te_stage2_positive_baseline.md"
    text = doc_path.read_text()

    assert "verify_gse105082_hela_triplet_stage2" in text
    assert "single-sample Stage 2 failure is an expected methodological boundary" in text
    assert "human_TE_sample_level.rda" in text
    assert "human_TE_cellline_all.csv" in text
    assert "human_TE_cellline_all_T.csv" in text
    assert "Baseline-specific Stage-3 regression lock" in text
    assert "General Stage-3 output contract" in text
    assert "duplicate gene identifiers remain in the final row index" in text
