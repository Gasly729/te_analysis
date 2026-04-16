from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASELINE_PATH = ROOT / "configs" / "downstream" / "legacy_te_stage2_positive_baseline.json"


def _load_baseline() -> dict[str, object]:
    return json.loads(BASELINE_PATH.read_text())


def test_stage2_positive_baseline_descriptor_is_locked() -> None:
    baseline = _load_baseline()

    assert baseline["baseline_name"] == "legacy_te_stage2_positive_smoke"
    assert baseline["run_id"] == "verify_gse105082_hela_triplet_stage2"
    assert baseline["target_stage"] == 2
    assert baseline["study_id"] == "GSE105082"
    assert baseline["grouping"] == "HeLa"
    assert baseline["cohort"] == ["GSM2817679", "GSM2817680", "GSM2817681"]
    assert baseline["minimum_stage2_samples"] == 2
    assert baseline["single_sample_stage2_expected_failure"] is True
    assert baseline["stage3_in_scope"] is False
    assert baseline["expected_stage2_outputs"] == [
        "human_TE_sample_level.rda",
        "human_TE_cellline_all.csv",
    ]


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


def test_stage2_positive_baseline_doc_mentions_boundary_and_outputs() -> None:
    doc_path = ROOT / "docs" / "architecture" / "legacy_te_stage2_positive_baseline.md"
    text = doc_path.read_text()

    assert "verify_gse105082_hela_triplet_stage2" in text
    assert "single-sample Stage 2 failure is an expected methodological boundary" in text
    assert "human_TE_sample_level.rda" in text
    assert "human_TE_cellline_all.csv" in text
    assert "Stage 3 is not part of this baseline" in text
