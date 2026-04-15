from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from te_analysis.pipeline.models import StageId, StageLayer
from te_analysis.pipeline.stage_registry import DEFAULT_STAGE_REGISTRY


def test_stage_registry_encodes_two_stage_method_and_three_layer_engineering_split() -> None:
    stage_ids = [stage.stage_id for stage in DEFAULT_STAGE_REGISTRY]
    assert stage_ids == [
        StageId.LOCAL_STAGED_FASTQ,
        StageId.UPSTREAM_RIBO_BUILD,
        StageId.EXPERIMENT_RIBO_HANDOFF,
        StageId.DOWNSTREAM_EXTRACTION,
        StageId.DOWNSTREAM_WINSORIZATION,
        StageId.DOWNSTREAM_FILTERING,
        StageId.DOWNSTREAM_TE_COMPUTE,
        StageId.DOWNSTREAM_RESULT_PACKAGING,
    ]

    layers = [stage.layer for stage in DEFAULT_STAGE_REGISTRY]
    assert layers.count(StageLayer.UPSTREAM) == 2
    assert layers.count(StageLayer.HANDOFF) == 1
    assert layers.count(StageLayer.DOWNSTREAM) == 5


def test_stage_registry_keeps_reference_backends_outside_the_active_package_surface() -> None:
    upstream_backend_stage = DEFAULT_STAGE_REGISTRY[1]
    downstream_backend_stage = DEFAULT_STAGE_REGISTRY[3]

    assert "raw_motheds/snakescale" in upstream_backend_stage.reference_backends
    assert "raw_motheds/riboflow" in upstream_backend_stage.reference_backends
    assert downstream_backend_stage.reference_backends == ("raw_motheds/TE_model",)


def test_stage_registry_remains_compatible_with_the_explicit_handoff_contract() -> None:
    extraction_stage = DEFAULT_STAGE_REGISTRY[3]
    handoff_stage = DEFAULT_STAGE_REGISTRY[2]
    winsorization_stage = DEFAULT_STAGE_REGISTRY[4]

    assert handoff_stage.stage_id is StageId.EXPERIMENT_RIBO_HANDOFF
    assert "handoff manifest" in handoff_stage.primary_outputs
    assert "experiment-level .ribo collection" in handoff_stage.primary_inputs

    assert extraction_stage.stage_id is StageId.DOWNSTREAM_EXTRACTION
    assert extraction_stage.layer is StageLayer.DOWNSTREAM
    assert "handoff manifest" in extraction_stage.primary_inputs
    assert "coverage/count intermediates" in extraction_stage.primary_outputs[0]

    assert winsorization_stage.stage_id is StageId.DOWNSTREAM_WINSORIZATION
    assert "extraction-time winsorization semantics" in winsorization_stage.summary
    assert "finalized raw CSV tables" in winsorization_stage.summary
