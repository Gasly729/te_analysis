"""Compatibility exports for handoff I/O contracts.

Responsibility:
- expose the handoff-layer contract models through the older pipeline import path

Non-responsibility:
- no additional model definitions
- no handoff logic
"""

from te_analysis.handoff.ribo_manifest import (
    ExperimentRiboArtifact,
    HandoffManifest,
    SidecarReference,
    SidecarRole,
    SidecarScope,
    StudyHandoffArtifacts,
    ValidationIssue,
    ValidationSummary,
)

__all__ = [
    "ExperimentRiboArtifact",
    "HandoffManifest",
    "SidecarReference",
    "SidecarRole",
    "SidecarScope",
    "StudyHandoffArtifacts",
    "ValidationIssue",
    "ValidationSummary",
]
