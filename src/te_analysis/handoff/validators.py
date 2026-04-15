"""Structured validators for the local handoff contract.

Responsibility:
- enforce conservative handoff validity rules

Non-responsibility:
- no filesystem mutation
- no backend invocation
- no biological logic
"""

from __future__ import annotations

from pathlib import Path

from .ribo_manifest import (
    HandoffManifest,
    SidecarScope,
    ValidationIssue,
    ValidationState,
    ValidationSummary,
)


def validate_handoff_manifest(manifest: HandoffManifest) -> ValidationSummary:
    """Validate a handoff manifest against the current contract.

    Validation is intentionally strict:
    - at least one experiment-level `.ribo` must exist
    - `all.ribo` alone is never sufficient
    - required sidecars must be declared and resolvable
    - experiment identifiers and paths must remain coherent
    """

    issues: list[ValidationIssue] = []

    if not manifest.study_id.strip():
        issues.append(
            ValidationIssue(
                code="missing-study-id",
                message="study_id must be non-empty.",
            )
        )

    if len(manifest.experiment_ids) != len(manifest.experiment_ribo_paths):
        issues.append(
            ValidationIssue(
                code="experiment-cardinality-mismatch",
                message="experiment_ids and experiment_ribo_paths must have the same cardinality.",
            )
        )

    if len(manifest.experiment_ribo_files) != len(manifest.experiment_ids):
        issues.append(
            ValidationIssue(
                code="artifact-cardinality-mismatch",
                message="experiment_ribo_files must stay aligned with experiment_ids.",
            )
        )

    if not manifest.experiment_ribo_files:
        issues.append(
            ValidationIssue(
                code="missing-experiment-ribo",
                message="At least one experiment-level `.ribo` artifact is required for a valid handoff.",
            )
        )

    if manifest.aggregate_ribo_path is not None and not manifest.experiment_ribo_files:
        issues.append(
            ValidationIssue(
                code="all-ribo-alone-insufficient",
                message="`all.ribo` alone is not sufficient to declare a valid downstream handoff.",
            )
        )

    seen_experiment_ids: set[str] = set()
    for artifact in manifest.experiment_ribo_files:
        if artifact.experiment_id in seen_experiment_ids:
            issues.append(
                ValidationIssue(
                    code="duplicate-experiment-id",
                    message=f"Duplicate experiment_id detected: {artifact.experiment_id}.",
                )
            )
        seen_experiment_ids.add(artifact.experiment_id)

        if artifact.ribo_path.suffix != ".ribo":
            issues.append(
                ValidationIssue(
                    code="invalid-ribo-suffix",
                    message=f"Experiment artifact must end with .ribo: {artifact.ribo_path}.",
                )
            )

        if not artifact.ribo_path.exists():
            issues.append(
                ValidationIssue(
                    code="missing-ribo-artifact",
                    message=f"Declared experiment-level `.ribo` artifact does not exist: {artifact.ribo_path}.",
                )
            )

    for expected_id, expected_path, artifact in zip(
        manifest.experiment_ids,
        manifest.experiment_ribo_paths,
        manifest.experiment_ribo_files,
    ):
        if expected_id != artifact.experiment_id:
            issues.append(
                ValidationIssue(
                    code="experiment-id-coherence-failure",
                    message="experiment_ids must remain coherent with experiment_ribo_files ordering.",
                )
            )
        if expected_path != artifact.ribo_path:
            issues.append(
                ValidationIssue(
                    code="experiment-path-coherence-failure",
                    message="experiment_ribo_paths must remain coherent with experiment_ribo_files ordering.",
                )
            )

    for sidecar in manifest.study_sidecars:
        if sidecar.scope is not SidecarScope.STUDY:
            issues.append(
                ValidationIssue(
                    code="study-sidecar-scope-mismatch",
                    message=f"Study sidecar has invalid scope: {sidecar.scope.value}.",
                )
            )

    for sidecar in manifest.shared_sidecars:
        if sidecar.scope is not SidecarScope.SHARED:
            issues.append(
                ValidationIssue(
                    code="shared-sidecar-scope-mismatch",
                    message=f"Shared sidecar has invalid scope: {sidecar.scope.value}.",
                )
            )

    for sidecar in manifest.declared_sidecars:
        if sidecar.required and not sidecar.resolved:
            issues.append(
                ValidationIssue(
                    code="missing-required-sidecar",
                    message=f"Required sidecar is not resolvable: {sidecar.role.value} -> {sidecar.path}.",
                )
            )
        if sidecar.resolved and not Path(sidecar.path).exists():
            issues.append(
                ValidationIssue(
                    code="stale-sidecar-resolution",
                    message=f"Sidecar marked resolved but file does not exist: {sidecar.path}.",
                )
            )

    state = ValidationState.INVALID if issues else ValidationState.VALID
    return ValidationSummary(state=state, issues=tuple(issues))
