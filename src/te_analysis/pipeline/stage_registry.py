"""Static stage registry for the local architecture skeleton.

Responsibility:
- record the intended stage order and layer split

Non-responsibility:
- no runtime dispatch
- no backend invocation
"""

from __future__ import annotations

from .models import StageDefinition, StageId, StageLayer


DEFAULT_STAGE_REGISTRY: tuple[StageDefinition, ...] = (
    StageDefinition(
        stage_id=StageId.LOCAL_STAGED_FASTQ,
        layer=StageLayer.UPSTREAM,
        method_owner="local wrapper",
        summary="Enforce the local deployment input contract for externally prepared FASTQ under the canonical staging root; this is a local wrapper stage rather than part of the original author method backend.",
        primary_inputs=("data/raw/fastq/",),
        primary_outputs=("validated local FASTQ set",),
    ),
    StageDefinition(
        stage_id=StageId.UPSTREAM_RIBO_BUILD,
        layer=StageLayer.UPSTREAM,
        method_owner="SnakeScale / RiboFlow",
        summary="Convert staged FASTQ inputs into experiment-level `.ribo` artifacts.",
        primary_inputs=("validated local FASTQ set", "upstream configs"),
        primary_outputs=("experiment-level .ribo collection", "optional all.ribo"),
        reference_backends=(
            "raw_motheds/snakescale",
            "raw_motheds/riboflow",
        ),
    ),
    StageDefinition(
        stage_id=StageId.EXPERIMENT_RIBO_HANDOFF,
        layer=StageLayer.HANDOFF,
        method_owner="local wrapper",
        summary="Normalize `.ribo` artifacts and required sidecars into an explicit handoff contract.",
        primary_inputs=("experiment-level .ribo collection", "sidecar references"),
        primary_outputs=("handoff manifest",),
    ),
    StageDefinition(
        stage_id=StageId.DOWNSTREAM_EXTRACTION,
        layer=StageLayer.DOWNSTREAM,
        method_owner="TE_model semantics",
        summary="Consume experiment-level `.ribo` artifacts and declared sidecars to form extraction-derived downstream coverage/count intermediates.",
        primary_inputs=("handoff manifest",),
        primary_outputs=("extraction-derived coverage/count intermediates",),
        reference_backends=("raw_motheds/TE_model",),
    ),
    StageDefinition(
        stage_id=StageId.DOWNSTREAM_WINSORIZATION,
        layer=StageLayer.DOWNSTREAM,
        method_owner="TE_model semantics",
        summary="Make explicit the original extraction-time winsorization semantics over extraction-derived per-gene CDS coverage/count intermediates; this is not a generic late-stage cap over already-finalized raw CSV tables.",
        primary_inputs=("extraction-derived coverage/count intermediates",),
        primary_outputs=("winsorized gene-level ribo count objects",),
        reference_backends=("raw_motheds/TE_model",),
    ),
    StageDefinition(
        stage_id=StageId.DOWNSTREAM_FILTERING,
        layer=StageLayer.DOWNSTREAM,
        method_owner="TE_model semantics",
        summary="Represent downstream filtering and dummy-gene handling explicitly.",
        primary_inputs=("winsorized gene-level ribo count objects",),
        primary_outputs=("filtered downstream count tables",),
        reference_backends=("raw_motheds/TE_model",),
    ),
    StageDefinition(
        stage_id=StageId.DOWNSTREAM_TE_COMPUTE,
        layer=StageLayer.DOWNSTREAM,
        method_owner="TE_model semantics",
        summary="Execute the preserved TE backend semantics on filtered downstream tables without changing TE numerical method definitions.",
        primary_inputs=("filtered downstream count tables",),
        primary_outputs=("raw TE backend outputs",),
        reference_backends=("raw_motheds/TE_model",),
    ),
    StageDefinition(
        stage_id=StageId.DOWNSTREAM_RESULT_PACKAGING,
        layer=StageLayer.DOWNSTREAM,
        method_owner="local wrapper",
        summary="Stabilize, manifest, and expose TE outputs for local repository use without changing TE numerical semantics.",
        primary_inputs=("raw TE backend outputs",),
        primary_outputs=("packaged results", "result manifests"),
    ),
)
