"""Read-only builders for local handoff manifests.

Responsibility:
- resolve study-scoped `.ribo` handoff artifacts from explicit local paths
- collect declared sidecar references
- build a machine-readable manifest

Non-responsibility:
- no `.ribo` parsing
- no backend execution
- no filesystem mutation
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Iterable, Optional, Union

from .ribo_manifest import (
    ExperimentRiboArtifact,
    HandoffManifest,
    SidecarReference,
    SidecarScope,
    StudyHandoffArtifacts,
)
from .validators import validate_handoff_manifest


_EXPERIMENT_RIBO_SUBPATHS: tuple[Path, ...] = (
    Path("ribo/experiments"),
    Path("output/ribo/experiments"),
)
_AGGREGATE_RIBO_SUBPATHS: tuple[Path, ...] = (
    Path("ribo/all.ribo"),
    Path("output/ribo/all.ribo"),
)


def _coerce_path(value: Union[Path, str, None]) -> Optional[Path]:
    """Normalize optional path-like inputs."""

    if value is None:
        return None
    return Path(value)


def _resolve_study_root(
    *,
    study_id: Optional[str],
    study_root: Union[Path, str, None],
    search_roots: Iterable[Union[Path, str]],
) -> Path:
    """Resolve the study root from explicit input or configured search roots."""

    explicit_root = _coerce_path(study_root)
    if explicit_root is not None:
        return explicit_root

    if not study_id:
        raise ValueError("study_id or study_root must be provided.")

    candidate_roots = [Path(root) / study_id for root in search_roots]
    for candidate in candidate_roots:
        if candidate.exists():
            return candidate

    if candidate_roots:
        return candidate_roots[0]

    raise ValueError("study_id was provided without a resolvable study_root or search_roots.")


def _candidate_experiment_ribo_roots(study_root: Path) -> tuple[Path, ...]:
    """Return explicit candidate locations for experiment-level `.ribo` artifacts."""

    candidates: list[Path] = []

    if study_root.name == "experiments":
        candidates.append(study_root)

    for subpath in _EXPERIMENT_RIBO_SUBPATHS:
        candidates.append(study_root / subpath)

    return tuple(candidates)


def _resolve_experiment_ribo_root(
    *,
    study_root: Path,
    experiment_ribo_root: Union[Path, str, None],
) -> Path:
    """Resolve the experiment-level `.ribo` directory."""

    explicit_root = _coerce_path(experiment_ribo_root)
    if explicit_root is not None:
        return explicit_root

    for candidate in _candidate_experiment_ribo_roots(study_root):
        if candidate.exists():
            return candidate

    return study_root / _EXPERIMENT_RIBO_SUBPATHS[0]


def _resolve_aggregate_ribo_path(
    *,
    study_root: Path,
    experiment_ribo_root: Path,
    aggregate_ribo_path: Union[Path, str, None],
) -> Optional[Path]:
    """Resolve the optional aggregate `all.ribo` artifact path."""

    explicit_path = _coerce_path(aggregate_ribo_path)
    if explicit_path is not None:
        return explicit_path if explicit_path.exists() else None

    candidates: list[Path] = []
    if experiment_ribo_root.parent.name == "ribo":
        candidates.append(experiment_ribo_root.parent / "all.ribo")
    for subpath in _AGGREGATE_RIBO_SUBPATHS:
        candidates.append(study_root / subpath)

    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def _discover_experiment_ribo_artifacts(study_id: str, experiment_ribo_root: Path) -> tuple[ExperimentRiboArtifact, ...]:
    """Discover study-scoped experiment-level `.ribo` files."""

    if not experiment_ribo_root.exists():
        return ()

    artifacts: list[ExperimentRiboArtifact] = []
    for ribo_path in sorted(experiment_ribo_root.glob("*.ribo")):
        if ribo_path.name == "all.ribo":
            continue
        artifacts.append(
            ExperimentRiboArtifact(
                study_id=study_id,
                experiment_id=ribo_path.stem,
                ribo_path=ribo_path,
                rnaseq_injected=None,
            )
        )
    return tuple(artifacts)


def _normalize_sidecars(
    sidecars: Iterable[SidecarReference],
    *,
    expected_scope: SidecarScope,
    base_root: Optional[Path],
) -> tuple[SidecarReference, ...]:
    """Resolve sidecar paths conservatively and preserve declared scope."""

    normalized: list[SidecarReference] = []
    for sidecar in sidecars:
        path = sidecar.path
        if not path.is_absolute() and base_root is not None:
            path = base_root / path
        normalized.append(
            replace(
                sidecar,
                scope=expected_scope,
                path=path,
                resolved=path.exists(),
            )
        )
    return tuple(normalized)


def build_handoff_manifest(
    *,
    study_id: Optional[str] = None,
    study_root: Union[Path, str, None] = None,
    search_roots: Iterable[Union[Path, str]] = (),
    experiment_ribo_root: Union[Path, str, None] = None,
    aggregate_ribo_path: Union[Path, str, None] = None,
    study_sidecars: Iterable[SidecarReference] = (),
    shared_sidecars: Iterable[SidecarReference] = (),
    shared_sidecar_root: Union[Path, str, None] = None,
    validate: bool = True,
) -> HandoffManifest:
    """Build a read-only handoff manifest from local repository state."""

    resolved_study_root = _resolve_study_root(
        study_id=study_id,
        study_root=study_root,
        search_roots=search_roots,
    )
    resolved_study_id = study_id or resolved_study_root.name
    resolved_experiment_root = _resolve_experiment_ribo_root(
        study_root=resolved_study_root,
        experiment_ribo_root=experiment_ribo_root,
    )
    resolved_aggregate_ribo = _resolve_aggregate_ribo_path(
        study_root=resolved_study_root,
        experiment_ribo_root=resolved_experiment_root,
        aggregate_ribo_path=aggregate_ribo_path,
    )

    artifacts = _discover_experiment_ribo_artifacts(
        study_id=resolved_study_id,
        experiment_ribo_root=resolved_experiment_root,
    )
    experiment_ids = tuple(artifact.experiment_id for artifact in artifacts)
    experiment_paths = tuple(artifact.ribo_path for artifact in artifacts)

    manifest = HandoffManifest(
        study=StudyHandoffArtifacts(
            study_id=resolved_study_id,
            experiment_ids=experiment_ids,
            experiment_ribo_paths=experiment_paths,
            aggregate_ribo_path=resolved_aggregate_ribo,
        ),
        experiment_ribo_files=artifacts,
        study_sidecars=_normalize_sidecars(
            study_sidecars,
            expected_scope=SidecarScope.STUDY,
            base_root=resolved_study_root,
        ),
        shared_sidecars=_normalize_sidecars(
            shared_sidecars,
            expected_scope=SidecarScope.SHARED,
            base_root=_coerce_path(shared_sidecar_root),
        ),
    )

    if not validate:
        return manifest

    return replace(manifest, validation=validate_handoff_manifest(manifest))


def serialize_handoff_manifest(manifest: HandoffManifest) -> str:
    """Serialize a manifest to stable JSON.

    JSON is used because it is available in the standard library and keeps the
    handoff layer dependency-light.
    """

    return manifest.to_json()
