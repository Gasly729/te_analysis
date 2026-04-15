"""Minimal downstream extraction wrapper for experiment-level `.ribo` handoff.

Responsibility:
- consume a validated handoff manifest
- extract per-experiment raw ribo and RNA-seq counts
- write deterministic extraction outputs owned by the downstream layer

Non-responsibility:
- no winsorization
- no filtering or dummy-gene handling
- no TE computation
- no backend orchestration
"""

from __future__ import annotations

import csv
import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Mapping, Optional, Union, cast

from te_analysis.handoff import HandoffManifest, ValidationState, load_handoff_manifest
from te_analysis.handoff.ribo_manifest import ExperimentRiboArtifact

try:
    from enum import StrEnum
except ImportError:  # pragma: no cover - Python < 3.11 compatibility
    from enum import Enum

    class StrEnum(str, Enum):
        """Compatibility shim for Python environments without `enum.StrEnum`."""


_REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_EXTRACTION_OUTPUT_ROOT = _REPO_ROOT / "data" / "derived" / "downstream" / "extraction"
_EXTRACTION_SCHEMA_VERSION = "1"
_EXTRACTION_STAGE_NAME = "downstream_extraction"

CountValue = Union[int, float]
CountsMapping = Mapping[str, CountValue]


class ExtractionContractError(RuntimeError):
    """Raised when extraction input contracts are violated."""


class MissingRiboArtifactError(FileNotFoundError, ExtractionContractError):
    """Raised when a declared experiment-level `.ribo` artifact is missing."""


class RnaSeqStatus(StrEnum):
    """Structured RNA-seq extraction states for each experiment."""

    PRESENT = "present"
    ABSENT = "absent"


@dataclass(frozen=True)
class ExperimentCounts:
    """Raw per-experiment counts extracted from a single `.ribo` artifact."""

    ribo_counts: CountsMapping
    rnaseq_counts: Optional[CountsMapping] = None


class ExperimentRiboReader:
    """Minimal protocol for extracting counts from one experiment-level `.ribo`."""

    def extract_counts(self, experiment_id: str) -> ExperimentCounts:
        """Return raw ribo counts and optional RNA-seq counts."""

        raise NotImplementedError


ReaderFactory = Callable[[Path], ExperimentRiboReader]


@dataclass(frozen=True)
class ExperimentExtractionRecord:
    """Materialized downstream extraction outputs for one experiment."""

    study_id: str
    experiment_id: str
    source_ribo_path: Path
    ribo_counts_path: Path
    rnaseq_counts_path: Optional[Path]
    rnaseq_status: RnaSeqStatus
    ribo_gene_count: int
    rnaseq_gene_count: Optional[int]

    def as_dict(self) -> dict[str, object]:
        """Return a stable dictionary representation."""

        return {
            "study_id": self.study_id,
            "experiment_id": self.experiment_id,
            "source_ribo_path": str(self.source_ribo_path),
            "ribo_counts_path": str(self.ribo_counts_path),
            "rnaseq_counts_path": None if self.rnaseq_counts_path is None else str(self.rnaseq_counts_path),
            "rnaseq_status": self.rnaseq_status.value,
            "ribo_gene_count": self.ribo_gene_count,
            "rnaseq_gene_count": self.rnaseq_gene_count,
        }


@dataclass(frozen=True)
class ExtractionRunResult:
    """Structured result for one downstream extraction run."""

    stage_name: str
    study_id: str
    schema_version: str
    output_dir: Path
    extraction_manifest_path: Path
    run_summary_path: Path
    manifest_source: str
    source_handoff_manifest_sha256: str
    records: tuple[ExperimentExtractionRecord, ...] = field(default_factory=tuple)

    def as_dict(self) -> dict[str, object]:
        """Return a stable dictionary representation."""

        return {
            "stage_name": self.stage_name,
            "schema_version": self.schema_version,
            "study_id": self.study_id,
            "output_dir": str(self.output_dir),
            "manifest_source": self.manifest_source,
            "source_handoff_manifest_sha256": self.source_handoff_manifest_sha256,
            "extraction_manifest_path": str(self.extraction_manifest_path),
            "run_summary_path": str(self.run_summary_path),
            "records": [record.as_dict() for record in self.records],
        }

    def to_json(self) -> str:
        """Serialize the run result to stable JSON."""

        return json.dumps(self.as_dict(), indent=2, sort_keys=False)


class RibopyExperimentReader:
    """Default `ribopy`-based reader for experiment-level `.ribo` files."""

    def __init__(self, ribo_path: Path):
        self._ribo_path = ribo_path

    def extract_counts(self, experiment_id: str) -> ExperimentCounts:
        """Read raw ribo and optional RNA-seq counts from one `.ribo` file."""

        from ribopy import Ribo
        import ribopy

        alias_fn = getattr(ribopy.api.alias, "apris_human_alias", None)
        ribo = Ribo(str(self._ribo_path), alias=alias_fn)
        ribo_counts_table = ribo.get_region_counts(
            "CDS",
            sum_lengths=True,
            sum_references=False,
            alias=True,
            experiments=experiment_id,
        )
        ribo_counts = _coerce_counts_mapping(
            _select_experiment_view(
                ribo_counts_table,
                experiment_id=experiment_id,
                context="ribo CDS counts",
                allow_missing=False,
            ),
            context="ribo CDS counts",
        )
        rnaseq_counts = _extract_rnaseq_counts(
            ribo=ribo,
            experiment_id=experiment_id,
            alias_fn=alias_fn,
        )
        return ExperimentCounts(
            ribo_counts=ribo_counts,
            rnaseq_counts=rnaseq_counts,
        )


def _load_manifest_source(handoff: Union[HandoffManifest, Path, str]) -> tuple[HandoffManifest, str]:
    """Load a handoff manifest from an in-memory object or JSON path."""

    if isinstance(handoff, HandoffManifest):
        return handoff, "<in-memory-handoff-manifest>"

    manifest_path = Path(handoff)
    return load_handoff_manifest(manifest_path), str(manifest_path)


def _compute_handoff_manifest_sha256(
    handoff: Union[HandoffManifest, Path, str],
    manifest: HandoffManifest,
) -> str:
    """Return a stable SHA-256 provenance digest for the source handoff manifest."""

    if isinstance(handoff, HandoffManifest):
        payload = manifest.to_json().encode("utf-8")
    else:
        payload = Path(handoff).read_bytes()
    return hashlib.sha256(payload).hexdigest()


def _resolve_output_root(output_root: Union[Path, str, None]) -> Path:
    """Resolve the downstream-owned extraction output root."""

    if output_root is None:
        return DEFAULT_EXTRACTION_OUTPUT_ROOT
    return Path(output_root)


def _ensure_extractable_manifest(manifest: HandoffManifest) -> None:
    """Enforce the minimal extraction preconditions on the handoff object."""

    if manifest.validation.state is not ValidationState.VALID:
        raise ExtractionContractError(
            "Extraction requires a validated handoff manifest with state=valid."
        )

    if not manifest.experiment_ribo_files:
        raise ExtractionContractError(
            "Extraction requires at least one experiment-level `.ribo` artifact."
        )

    if len(manifest.experiment_ribo_files) != len(manifest.experiment_ids):
        raise ExtractionContractError(
            "experiment_ribo_files must remain aligned with study-scoped experiment_ids."
        )

    if len(manifest.experiment_ribo_files) != len(manifest.experiment_ribo_paths):
        raise ExtractionContractError(
            "experiment_ribo_files must remain aligned with study-scoped experiment_ribo_paths."
        )

    for expected_id, expected_path, artifact in zip(
        manifest.experiment_ids,
        manifest.experiment_ribo_paths,
        manifest.experiment_ribo_files,
    ):
        if artifact.study_id != manifest.study_id:
            raise ExtractionContractError(
                "Experiment artifacts must remain scoped to the enclosing study_id."
            )
        if artifact.experiment_id != expected_id:
            raise ExtractionContractError(
                "Experiment artifact ordering must remain coherent with experiment_ids."
            )
        if artifact.ribo_path != expected_path:
            raise ExtractionContractError(
                "Experiment artifact ordering must remain coherent with experiment_ribo_paths."
            )


def _iter_experiment_artifacts(manifest: HandoffManifest) -> tuple[ExperimentRiboArtifact, ...]:
    """Return experiment artifacts in stable deterministic order."""

    return tuple(
        sorted(
            manifest.experiment_ribo_files,
            key=lambda artifact: artifact.experiment_id,
        )
    )


def _write_counts_csv(path: Path, counts: CountsMapping) -> None:
    """Write one per-experiment counts table in stable key order."""

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(("gene_id", "count"))
        for gene_id, count in sorted(counts.items(), key=lambda item: item[0]):
            writer.writerow((gene_id, count))


def _write_run_summary(path: Path, records: tuple[ExperimentExtractionRecord, ...]) -> None:
    """Write a compact tabular summary for downstream extraction outputs."""

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            (
                "study_id",
                "experiment_id",
                "source_ribo_path",
                "ribo_counts_path",
                "rnaseq_counts_path",
                "rnaseq_status",
                "ribo_gene_count",
                "rnaseq_gene_count",
            )
        )
        for record in records:
            writer.writerow(
                (
                    record.study_id,
                    record.experiment_id,
                    str(record.source_ribo_path),
                    str(record.ribo_counts_path),
                    "" if record.rnaseq_counts_path is None else str(record.rnaseq_counts_path),
                    record.rnaseq_status.value,
                    record.ribo_gene_count,
                    "" if record.rnaseq_gene_count is None else record.rnaseq_gene_count,
                )
            )


def _coerce_counts_mapping(raw_counts: object, *, context: str) -> dict[str, CountValue]:
    """Normalize a series-like or mapping-like object into a plain dictionary."""

    if isinstance(raw_counts, Mapping):
        items = raw_counts.items()
    elif hasattr(raw_counts, "items"):
        items = cast(object, raw_counts).items()
    else:
        raise ExtractionContractError(
            f"Could not normalize {context} into a mapping-like object."
        )

    normalized: dict[str, CountValue] = {}
    for key, value in items:
        normalized[str(key)] = cast(CountValue, value)
    return normalized


def _select_experiment_view(
    table: object,
    *,
    experiment_id: str,
    context: str,
    allow_missing: bool,
) -> Optional[object]:
    """Select one experiment slice from a series-like or table-like object."""

    if table is None:
        return None if allow_missing else _raise_missing_experiment_view(context, experiment_id)

    ndim = getattr(table, "ndim", None)
    if ndim == 1:
        return table

    columns = getattr(table, "columns", ())
    if experiment_id in columns:
        return table[experiment_id]

    index = getattr(table, "index", ())
    if experiment_id in index:
        return table.loc[experiment_id]

    if allow_missing:
        return None

    return _raise_missing_experiment_view(context, experiment_id)


def _raise_missing_experiment_view(context: str, experiment_id: str) -> None:
    """Raise a coherent extraction contract error for missing experiment views."""

    raise ExtractionContractError(
        f"Could not resolve experiment `{experiment_id}` from {context}."
    )


def _looks_like_missing_rnaseq(exc: Exception) -> bool:
    """Detect likely absence of RNA-seq data without masking unrelated failures."""

    if isinstance(exc, (KeyError, IndexError)):
        return True

    message = str(exc).lower()
    return "rnaseq" in message and (
        "missing" in message
        or "not found" in message
        or "empty" in message
        or "absent" in message
    )


def _has_explicit_rnaseq_presence(ribo: object, experiment_id: str) -> Optional[bool]:
    """Return explicit RNA-seq presence when the backend exposes that contract."""

    has_rnaseq = getattr(ribo, "has_rnaseq", None)
    if not callable(has_rnaseq):
        return None

    try:
        return bool(has_rnaseq(experiment_id))
    except Exception as exc:  # pragma: no cover - depends on ribopy runtime behavior
        raise ExtractionContractError(
            f"Failed to determine RNA-seq presence for experiment `{experiment_id}`."
        ) from exc


def _normalize_rnaseq_experiment_frame(
    rnaseq_table: object,
    *,
    experiment_id: str,
) -> object:
    """Normalize a `ribopy.get_rnaseq()` table to one experiment-scoped frame."""

    if rnaseq_table is None:
        return None

    index = getattr(rnaseq_table, "index", None)
    if index is None:
        raise ExtractionContractError(
            "RNA-seq extraction returned an object without an index."
        )

    nlevels = getattr(index, "nlevels", 1)
    if nlevels >= 2:
        if experiment_id not in index.get_level_values(0):
            raise ExtractionContractError(
                f"RNA-seq table does not contain experiment `{experiment_id}` in its first index level."
            )
        try:
            return rnaseq_table.xs(experiment_id, level=0)
        except Exception as exc:
            raise ExtractionContractError(
                f"Failed to select experiment `{experiment_id}` from RNA-seq MultiIndex table."
            ) from exc

    experiment_view = _select_experiment_view(
        rnaseq_table,
        experiment_id=experiment_id,
        context="RNA-seq table",
        allow_missing=False,
    )
    return experiment_view


def _extract_rnaseq_counts(
    *,
    ribo: object,
    experiment_id: str,
    alias_fn: object,
) -> Optional[dict[str, CountValue]]:
    """Extract optional RNA-seq CDS counts from a `.ribo` backend handle."""

    explicit_presence = _has_explicit_rnaseq_presence(ribo, experiment_id)
    if explicit_presence is False:
        return None

    try:
        rnaseq_table = ribo.get_rnaseq(experiment_id)
    except Exception as exc:  # pragma: no cover - exercised through injected readers in tests
        if explicit_presence is None and _looks_like_missing_rnaseq(exc):
            return None
        raise ExtractionContractError(
            f"Failed to resolve RNA-seq counts for experiment `{experiment_id}`."
        ) from exc

    if rnaseq_table is None:
        if explicit_presence is None:
            return None
        raise ExtractionContractError(
            f"RNA-seq was declared present for experiment `{experiment_id}` but `get_rnaseq()` returned None."
        )

    experiment_view = _normalize_rnaseq_experiment_frame(
        rnaseq_table,
        experiment_id=experiment_id,
    )
    if experiment_view is None:
        raise ExtractionContractError(
            f"RNA-seq table resolved to an empty experiment view for `{experiment_id}`."
        )

    if hasattr(experiment_view, "columns") and "CDS" in experiment_view.columns:
        cds_counts = experiment_view["CDS"]
    elif isinstance(experiment_view, Mapping) and "CDS" in experiment_view:
        cds_counts = experiment_view["CDS"]
    else:  # pragma: no cover - depends on ribopy runtime object layout
        raise ExtractionContractError(
            f"RNA-seq counts for experiment `{experiment_id}` do not expose a CDS view."
        )

    normalized_counts = _coerce_counts_mapping(cds_counts, context="RNA-seq CDS counts")
    if callable(alias_fn):
        return {
            str(alias_fn(gene_id)): count
            for gene_id, count in normalized_counts.items()
        }
    return normalized_counts


def extract_from_handoff(
    handoff: Union[HandoffManifest, Path, str],
    *,
    output_root: Union[Path, str, None] = None,
    reader_factory: Optional[ReaderFactory] = None,
) -> ExtractionRunResult:
    """Run the minimal downstream extraction stage from a validated handoff."""

    manifest, manifest_source = _load_manifest_source(handoff)
    _ensure_extractable_manifest(manifest)

    resolved_output_root = _resolve_output_root(output_root)
    study_output_dir = resolved_output_root / manifest.study_id
    experiments_output_dir = study_output_dir / "experiments"
    extraction_manifest_path = study_output_dir / "extraction_manifest.json"
    run_summary_path = study_output_dir / "run_summary.csv"

    if reader_factory is None:
        reader_factory = RibopyExperimentReader

    records: list[ExperimentExtractionRecord] = []
    source_handoff_manifest_sha256 = _compute_handoff_manifest_sha256(handoff, manifest)
    for artifact in _iter_experiment_artifacts(manifest):
        if not artifact.ribo_path.exists():
            raise MissingRiboArtifactError(
                f"Declared experiment-level `.ribo` artifact does not exist: {artifact.ribo_path}"
            )

        experiment_output_dir = experiments_output_dir / artifact.experiment_id
        ribo_counts_path = experiment_output_dir / "ribo_raw_counts.csv"
        rnaseq_counts_path = experiment_output_dir / "rnaseq_raw_counts.csv"

        reader = reader_factory(artifact.ribo_path)
        extracted_counts = reader.extract_counts(artifact.experiment_id)

        _write_counts_csv(ribo_counts_path, extracted_counts.ribo_counts)

        if extracted_counts.rnaseq_counts is None:
            resolved_rnaseq_counts_path = None
            rnaseq_status = RnaSeqStatus.ABSENT
            rnaseq_gene_count = None
        else:
            _write_counts_csv(rnaseq_counts_path, extracted_counts.rnaseq_counts)
            resolved_rnaseq_counts_path = rnaseq_counts_path
            rnaseq_status = RnaSeqStatus.PRESENT
            rnaseq_gene_count = len(extracted_counts.rnaseq_counts)

        records.append(
            ExperimentExtractionRecord(
                study_id=manifest.study_id,
                experiment_id=artifact.experiment_id,
                source_ribo_path=artifact.ribo_path,
                ribo_counts_path=ribo_counts_path,
                rnaseq_counts_path=resolved_rnaseq_counts_path,
                rnaseq_status=rnaseq_status,
                ribo_gene_count=len(extracted_counts.ribo_counts),
                rnaseq_gene_count=rnaseq_gene_count,
            )
        )

    result = ExtractionRunResult(
        stage_name=_EXTRACTION_STAGE_NAME,
        study_id=manifest.study_id,
        schema_version=_EXTRACTION_SCHEMA_VERSION,
        output_dir=study_output_dir,
        extraction_manifest_path=extraction_manifest_path,
        run_summary_path=run_summary_path,
        manifest_source=manifest_source,
        source_handoff_manifest_sha256=source_handoff_manifest_sha256,
        records=tuple(records),
    )

    study_output_dir.mkdir(parents=True, exist_ok=True)
    _write_run_summary(run_summary_path, result.records)
    extraction_manifest_path.write_text(result.to_json())
    return result


def run_extraction(
    handoff: Union[HandoffManifest, Path, str],
    *,
    output_root: Union[Path, str, None] = None,
    reader_factory: Optional[ReaderFactory] = None,
) -> ExtractionRunResult:
    """Compatibility alias for the minimal extraction entrypoint."""

    return extract_from_handoff(
        handoff,
        output_root=output_root,
        reader_factory=reader_factory,
    )
