from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    from enum import StrEnum
except ImportError:
    from enum import Enum

    class StrEnum(str, Enum):
        pass


WRAPPER_NAME = "legacy_te_model_wrapper"
SPEC_VERSION = "1.0"
RUN_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{2,127}$")
_REPO_ROOT = Path(__file__).resolve().parents[4]
LEGACY_SOURCE_ROOT = _REPO_ROOT / "raw_motheds" / "TE_model"
DEFAULT_RUNTIME_BASE = _REPO_ROOT / "data" / "downstream_runs"


class ExecutionMode(StrEnum):
    LEGACY_DEFAULT_COUNTS = "legacy_default_counts"
    LEGACY_WINSORIZED_COUNTS = "legacy_winsorized_counts"


class RnaSeqFailureCategory(StrEnum):
    MANIFEST_DECLARATION_FAILURE = "manifest_declaration_failure"
    RIBO_INSPECTION_FAILURE = "ribo_inspection_failure"
    MANIFEST_INSPECTION_CONTRADICTION = "manifest_inspection_contradiction"


class LegacyTeModelContractError(RuntimeError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


class RnaSeqValidationError(LegacyTeModelContractError):
    def __init__(self, category: RnaSeqFailureCategory, message: str):
        super().__init__(str(category.value), message)
        self.category = category


@dataclass(frozen=True)
class WrapperSidecars:
    nonpolya_csv: Path
    grouping_csv: Path
    sample_selection_csv: Path | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "nonpolya_csv": str(self.nonpolya_csv),
            "grouping_csv": str(self.grouping_csv),
            "sample_selection_csv": None if self.sample_selection_csv is None else str(self.sample_selection_csv),
        }


@dataclass(frozen=True)
class HandoffExperiment:
    experiment_alias: str
    study_id: str
    ribo_path: Path
    organism: str
    has_rnaseq: bool

    def as_dict(self) -> dict[str, Any]:
        return {
            "experiment_alias": self.experiment_alias,
            "study_id": self.study_id,
            "ribo_path": str(self.ribo_path),
            "organism": self.organism,
            "has_rnaseq": self.has_rnaseq,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "HandoffExperiment":
        return cls(
            experiment_alias=str(data["experiment_alias"]),
            study_id=str(data["study_id"]),
            ribo_path=Path(str(data["ribo_path"])),
            organism=str(data["organism"]),
            has_rnaseq=bool(data["has_rnaseq"]),
        )


@dataclass(frozen=True)
class HandoffManifestV1:
    manifest_version: str
    run_id: str
    input_mode: str
    experiments: tuple[HandoffExperiment, ...]
    all_ribo_path: Path | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "manifest_version": self.manifest_version,
            "run_id": self.run_id,
            "input_mode": self.input_mode,
            "experiments": [experiment.as_dict() for experiment in self.experiments],
            "all_ribo_path": None if self.all_ribo_path is None else str(self.all_ribo_path),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "HandoffManifestV1":
        all_ribo_path = data.get("all_ribo_path")
        return cls(
            manifest_version=str(data.get("manifest_version", "")),
            run_id=str(data.get("run_id", "")),
            input_mode=str(data.get("input_mode", "")),
            experiments=tuple(
                HandoffExperiment.from_dict(item)
                for item in data.get("experiments", [])
            ),
            all_ribo_path=None if all_ribo_path is None else Path(str(all_ribo_path)),
        )

    def to_json(self) -> str:
        return json.dumps(self.as_dict(), indent=2, sort_keys=False)


@dataclass(frozen=True)
class WrapperRequest:
    run_id: str
    execution_mode: ExecutionMode
    handoff_manifest_path: Path
    sidecars: WrapperSidecars
    source_legacy_root: Path = LEGACY_SOURCE_ROOT

    def as_dict(self) -> dict[str, Any]:
        return {
            "wrapper_name": WRAPPER_NAME,
            "run_id": self.run_id,
            "execution_mode": self.execution_mode.value,
            "handoff_manifest_path": str(self.handoff_manifest_path),
            "sidecars": self.sidecars.as_dict(),
            "source_legacy_root": str(self.source_legacy_root),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "WrapperRequest":
        sidecars = data.get("sidecars", {})
        return cls(
            run_id=str(data["run_id"]),
            execution_mode=ExecutionMode(str(data["execution_mode"])),
            handoff_manifest_path=Path(str(data["handoff_manifest_path"])),
            sidecars=WrapperSidecars(
                nonpolya_csv=Path(str(sidecars["nonpolya_csv"])),
                grouping_csv=Path(str(sidecars["grouping_csv"])),
                sample_selection_csv=None
                if sidecars.get("sample_selection_csv") is None
                else Path(str(sidecars["sample_selection_csv"])),
            ),
            source_legacy_root=Path(str(data.get("source_legacy_root", LEGACY_SOURCE_ROOT))),
        )


@dataclass(frozen=True)
class MaterializationResult:
    wrapper_name: str
    spec_version: str
    run_id: str
    execution_mode: str
    runtime_root: Path
    sandbox_root: Path
    generated_config_path: Path
    handoff_manifest_path: Path
    sidecars_manifest_path: Path
    wrapper_request_path: Path
    provenance_path: Path
    materialization_log_path: Path
    status: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "wrapper_name": self.wrapper_name,
            "spec_version": self.spec_version,
            "run_id": self.run_id,
            "execution_mode": self.execution_mode,
            "runtime_root": str(self.runtime_root),
            "sandbox_root": str(self.sandbox_root),
            "generated_config_path": str(self.generated_config_path),
            "handoff_manifest_path": str(self.handoff_manifest_path),
            "sidecars_manifest_path": str(self.sidecars_manifest_path),
            "wrapper_request_path": str(self.wrapper_request_path),
            "provenance_path": str(self.provenance_path),
            "materialization_log_path": str(self.materialization_log_path),
            "status": self.status,
        }


def load_wrapper_request(path: Path | str) -> WrapperRequest:
    request_path = Path(path)
    return WrapperRequest.from_dict(json.loads(request_path.read_text()))


def load_handoff_manifest(path: Path | str) -> HandoffManifestV1:
    manifest_path = Path(path)
    return HandoffManifestV1.from_dict(json.loads(manifest_path.read_text()))
