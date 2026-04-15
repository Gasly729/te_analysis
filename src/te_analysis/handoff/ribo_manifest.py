"""Typed manifest models for the local handoff layer.

Responsibility:
- define the machine-readable handoff schema between upstream and downstream

Non-responsibility:
- no filesystem scanning
- no backend execution
- no `.ribo` parsing
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Union

try:
    from enum import StrEnum
except ImportError:  # pragma: no cover - Python < 3.11 compatibility
    from enum import Enum

    class StrEnum(str, Enum):
        """Compatibility shim for Python environments without `enum.StrEnum`."""


class SidecarScope(StrEnum):
    """Supported ownership scopes for declared sidecars."""

    STUDY = "study"
    SHARED = "shared"


class SidecarRole(StrEnum):
    """Supported sidecar categories for the handoff contract."""

    STUDY_MANIFEST = "study_manifest"
    PAIRING_REFERENCE = "pairing_reference"
    SAMPLE_SELECTION = "sample_selection"
    NONPOLYA_REFERENCE = "nonpolyA_reference"
    INFO_FILTER_SUPPORT = "info_filter_support"
    DOWNSTREAM_RUN_CONFIG = "downstream_run_config"


class ValidationState(StrEnum):
    """High-level manifest validation states."""

    UNVALIDATED = "unvalidated"
    VALID = "valid"
    INVALID = "invalid"


@dataclass(frozen=True)
class ValidationIssue:
    """A single machine-readable validation issue."""

    code: str
    message: str

    def as_dict(self) -> dict[str, str]:
        """Return a stable dictionary representation."""

        return {"code": self.code, "message": self.message}

    @classmethod
    def from_dict(cls, data: dict[str, str]) -> "ValidationIssue":
        """Hydrate a validation issue from serialized data."""

        return cls(code=data["code"], message=data["message"])


@dataclass(frozen=True)
class ValidationSummary:
    """Structured validation result for a handoff manifest."""

    state: ValidationState
    issues: tuple[ValidationIssue, ...] = field(default_factory=tuple)

    @classmethod
    def unvalidated(cls) -> "ValidationSummary":
        """Return the default validation state before checks run."""

        return cls(state=ValidationState.UNVALIDATED)

    @property
    def is_valid(self) -> bool:
        """Return `True` when the manifest has passed validation."""

        return self.state is ValidationState.VALID

    def as_dict(self) -> dict[str, object]:
        """Return a stable dictionary representation."""

        return {
            "state": self.state.value,
            "issues": [issue.as_dict() for issue in self.issues],
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "ValidationSummary":
        """Hydrate a validation summary from serialized data."""

        issues = tuple(
            ValidationIssue.from_dict(issue)
            for issue in data.get("issues", [])
        )
        return cls(
            state=ValidationState(data["state"]),
            issues=issues,
        )


@dataclass(frozen=True)
class ExperimentRiboArtifact:
    """A single study-scoped experiment-level `.ribo` artifact.

    This is the primary downstream handoff object.
    """

    study_id: str
    experiment_id: str
    ribo_path: Path
    rnaseq_injected: Optional[bool] = None

    def as_dict(self) -> dict[str, object]:
        """Return a stable dictionary representation."""

        return {
            "study_id": self.study_id,
            "experiment_id": self.experiment_id,
            "ribo_path": str(self.ribo_path),
            "rnaseq_injected": self.rnaseq_injected,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "ExperimentRiboArtifact":
        """Hydrate an experiment-level `.ribo` artifact from serialized data."""

        return cls(
            study_id=str(data["study_id"]),
            experiment_id=str(data["experiment_id"]),
            ribo_path=Path(str(data["ribo_path"])),
            rnaseq_injected=data.get("rnaseq_injected"),
        )


@dataclass(frozen=True)
class SidecarReference:
    """A declared non-`.ribo` dependency required by downstream wrappers.

    Sidecars may be study-scoped or shared across studies, but they must always
    be declared explicitly in the local handoff contract.
    """

    role: SidecarRole
    scope: SidecarScope
    path: Path
    required: bool = True
    resolved: bool = False
    description: str = ""

    def as_dict(self) -> dict[str, object]:
        """Return a stable dictionary representation."""

        return {
            "role": self.role.value,
            "scope": self.scope.value,
            "path": str(self.path),
            "required": self.required,
            "resolved": self.resolved,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "SidecarReference":
        """Hydrate a sidecar reference from serialized data."""

        return cls(
            role=SidecarRole(str(data["role"])),
            scope=SidecarScope(str(data["scope"])),
            path=Path(str(data["path"])),
            required=bool(data.get("required", True)),
            resolved=bool(data.get("resolved", False)),
            description=str(data.get("description", "")),
        )


@dataclass(frozen=True)
class StudyHandoffArtifacts:
    """Study-scoped artifact bundle for a single handoff manifest.

    The bundle distinguishes the primary experiment-level `.ribo` collection from
    the optional aggregate `all.ribo` artifact.
    """

    study_id: str
    experiment_ids: tuple[str, ...]
    experiment_ribo_paths: tuple[Path, ...]
    aggregate_ribo_path: Optional[Path] = None

    def as_dict(self) -> dict[str, object]:
        """Return a stable dictionary representation."""

        return {
            "study_id": self.study_id,
            "experiment_ids": list(self.experiment_ids),
            "experiment_ribo_paths": [str(path) for path in self.experiment_ribo_paths],
            "all_ribo_path": None if self.aggregate_ribo_path is None else str(self.aggregate_ribo_path),
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "StudyHandoffArtifacts":
        """Hydrate study-scoped handoff artifacts from serialized data."""

        aggregate_ribo_path = data.get("all_ribo_path")
        return cls(
            study_id=str(data["study_id"]),
            experiment_ids=tuple(str(experiment_id) for experiment_id in data.get("experiment_ids", [])),
            experiment_ribo_paths=tuple(
                Path(str(path)) for path in data.get("experiment_ribo_paths", [])
            ),
            aggregate_ribo_path=None if aggregate_ribo_path is None else Path(str(aggregate_ribo_path)),
        )


@dataclass(frozen=True)
class HandoffManifest:
    """Formal handoff manifest for downstream consumption.

    The manifest distinguishes:
    - study-scoped artifact truth
    - study-scoped sidecars
    - pipeline-global/shared sidecars
    - structured validation status
    """

    study: StudyHandoffArtifacts
    experiment_ribo_files: tuple[ExperimentRiboArtifact, ...]
    study_sidecars: tuple[SidecarReference, ...] = field(default_factory=tuple)
    shared_sidecars: tuple[SidecarReference, ...] = field(default_factory=tuple)
    validation: ValidationSummary = field(default_factory=ValidationSummary.unvalidated)

    @property
    def study_id(self) -> str:
        """Expose the study identifier as a convenience property."""

        return self.study.study_id

    @property
    def experiment_ids(self) -> tuple[str, ...]:
        """Expose study-scoped experiment identifiers."""

        return self.study.experiment_ids

    @property
    def experiment_ribo_paths(self) -> tuple[Path, ...]:
        """Expose study-scoped experiment-level `.ribo` paths."""

        return self.study.experiment_ribo_paths

    @property
    def aggregate_ribo_path(self) -> Optional[Path]:
        """Expose the optional aggregate `all.ribo` path."""

        return self.study.aggregate_ribo_path

    @property
    def declared_sidecars(self) -> tuple[SidecarReference, ...]:
        """Return all declared sidecars in stable scope order."""

        return self.study_sidecars + self.shared_sidecars

    def as_dict(self) -> dict[str, object]:
        """Return a stable dictionary representation.

        JSON serialization is used by default because it is available from the
        Python standard library and requires no extra dependencies.
        """

        return {
            "study": self.study.as_dict(),
            "experiment_ribo_files": [artifact.as_dict() for artifact in self.experiment_ribo_files],
            "study_sidecars": [sidecar.as_dict() for sidecar in self.study_sidecars],
            "shared_sidecars": [sidecar.as_dict() for sidecar in self.shared_sidecars],
            "validation": self.validation.as_dict(),
        }

    def to_json(self) -> str:
        """Serialize the manifest to stable JSON."""

        return json.dumps(self.as_dict(), indent=2, sort_keys=False)

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "HandoffManifest":
        """Hydrate a handoff manifest from serialized data."""

        return cls(
            study=StudyHandoffArtifacts.from_dict(data["study"]),
            experiment_ribo_files=tuple(
                ExperimentRiboArtifact.from_dict(artifact)
                for artifact in data.get("experiment_ribo_files", [])
            ),
            study_sidecars=tuple(
                SidecarReference.from_dict(sidecar)
                for sidecar in data.get("study_sidecars", [])
            ),
            shared_sidecars=tuple(
                SidecarReference.from_dict(sidecar)
                for sidecar in data.get("shared_sidecars", [])
            ),
            validation=ValidationSummary.from_dict(
                data.get("validation", ValidationSummary.unvalidated().as_dict())
            ),
        )

    @classmethod
    def from_json(cls, raw_json: str) -> "HandoffManifest":
        """Hydrate a handoff manifest from a JSON string."""

        return cls.from_dict(json.loads(raw_json))


def load_handoff_manifest(path: Union[Path, str]) -> HandoffManifest:
    """Load a serialized handoff manifest from disk."""

    manifest_path = Path(path)
    return HandoffManifest.from_json(manifest_path.read_text())
