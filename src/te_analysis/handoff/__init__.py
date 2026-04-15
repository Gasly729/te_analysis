"""Local handoff-layer boundaries.

This package will own explicit `.ribo` handoff validation and manifest handling.
"""

from .handoff_builder import build_handoff_manifest, serialize_handoff_manifest
from .ribo_manifest import (
    ExperimentRiboArtifact,
    HandoffManifest,
    SidecarReference,
    SidecarRole,
    SidecarScope,
    StudyHandoffArtifacts,
    ValidationIssue,
    ValidationState,
    ValidationSummary,
    load_handoff_manifest,
)
from .validators import validate_handoff_manifest

__all__ = [
    "ExperimentRiboArtifact",
    "HandoffManifest",
    "SidecarReference",
    "SidecarRole",
    "SidecarScope",
    "StudyHandoffArtifacts",
    "ValidationIssue",
    "ValidationState",
    "ValidationSummary",
    "build_handoff_manifest",
    "load_handoff_manifest",
    "serialize_handoff_manifest",
    "validate_handoff_manifest",
]
