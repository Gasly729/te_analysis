from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_pipeline_default_config_locks_local_staged_fastq_mode() -> None:
    text = (ROOT / "configs/pipeline/default.yaml").read_text()

    assert "input_mode: local_staged_fastq" in text
    assert "download_enabled: false" in text
    assert "/home/xrx/my_project/te_analysis/data/raw/fastq" in text


def test_te_only_config_makes_winsorization_an_explicit_downstream_stage() -> None:
    text = (ROOT / "configs/pipeline/te_only.yaml").read_text()

    assert "downstream.winsorization" in text
    assert "all_ribo_role: optional_aggregate_only" in text


def test_downstream_configs_model_te_model_and_winsorization_as_explicit_wrappers() -> None:
    te_model_text = (ROOT / "configs/downstream/te_model.yaml").read_text()
    winsor_text = (ROOT / "configs/downstream/winsorization.yaml").read_text()

    assert "reference_backend_root: /home/xrx/my_project/te_analysis/raw_motheds/TE_model" in te_model_text
    assert "main_handoff_object: experiment_ribo_collection" in te_model_text
    assert "status: explicit_stage_documented_not_migrated" in winsor_text
    assert "source_of_truth: experiment_level_ribo_collection" in winsor_text
    assert "artifact: winsorized_gene_level_ribo_counts" in winsor_text
