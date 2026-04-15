"""Typed stage models for the local architecture skeleton.

Responsibility:
- encode stage identity, layer ownership, and contract metadata

Non-responsibility:
- no execution logic
- no biological computation
"""

from __future__ import annotations

from dataclasses import dataclass, field

try:
    from enum import StrEnum
except ImportError:  # pragma: no cover - Python < 3.11 compatibility
    from enum import Enum

    class StrEnum(str, Enum):
        """Compatibility shim for Python environments without `enum.StrEnum`."""


class StageLayer(StrEnum):
    """Engineering-layer identifiers for the new local architecture."""

    UPSTREAM = "upstream"
    HANDOFF = "handoff"
    DOWNSTREAM = "downstream"


class StageId(StrEnum):
    """Ordered stage identifiers for the wrapper registry."""

    LOCAL_STAGED_FASTQ = "local_staged_fastq"
    UPSTREAM_RIBO_BUILD = "upstream_ribo_build"
    EXPERIMENT_RIBO_HANDOFF = "experiment_ribo_handoff"
    DOWNSTREAM_EXTRACTION = "downstream_extraction"
    DOWNSTREAM_WINSORIZATION = "downstream_winsorization"
    DOWNSTREAM_FILTERING = "downstream_filtering"
    DOWNSTREAM_TE_COMPUTE = "downstream_te_compute"
    DOWNSTREAM_RESULT_PACKAGING = "downstream_result_packaging"


@dataclass(frozen=True)
class StageDefinition:
    """Static metadata describing a stage boundary."""

    stage_id: StageId
    layer: StageLayer
    method_owner: str
    summary: str
    primary_inputs: tuple[str, ...] = field(default_factory=tuple)
    primary_outputs: tuple[str, ...] = field(default_factory=tuple)
    reference_backends: tuple[str, ...] = field(default_factory=tuple)
