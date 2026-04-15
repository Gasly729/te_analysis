"""Local downstream wrapper boundaries.

This package will wrap TE_model stages without reimplementing reference semantics.
"""

from .extraction_wrapper import (
    DEFAULT_EXTRACTION_OUTPUT_ROOT,
    ExtractionContractError,
    ExtractionRunResult,
    ExperimentExtractionRecord,
    MissingRiboArtifactError,
    RnaSeqStatus,
    extract_from_handoff,
    run_extraction,
)
from .legacy_te_model import materialize_legacy_te_model_wrapper

__all__ = [
    "DEFAULT_EXTRACTION_OUTPUT_ROOT",
    "ExtractionContractError",
    "ExtractionRunResult",
    "ExperimentExtractionRecord",
    "MissingRiboArtifactError",
    "RnaSeqStatus",
    "extract_from_handoff",
    "materialize_legacy_te_model_wrapper",
    "run_extraction",
]
