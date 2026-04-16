from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterable

from .contracts import (
    LEGACY_SOURCE_ROOT,
    RUN_ID_PATTERN,
    ExecutionMode,
    HandoffExperiment,
    HandoffManifestV1,
    LegacyTeModelContractError,
    RnaSeqFailureCategory,
    RnaSeqValidationError,
    WrapperRequest,
)


def _require_absolute_path(path: Path, *, code: str, label: str) -> None:
    if not path.is_absolute():
        raise LegacyTeModelContractError(code, f"{label} must be an absolute path: {path}")


def _require_existing_file(path: Path, *, code: str, label: str) -> None:
    if not path.exists() or not path.is_file():
        raise LegacyTeModelContractError(code, f"{label} must exist as a file: {path}")


def _read_csv_header(path: Path) -> tuple[str, ...]:
    with path.open(newline="") as handle:
        reader = csv.reader(handle)
        try:
            header = next(reader)
        except StopIteration as exc:
            raise LegacyTeModelContractError("empty-sidecar", f"CSV file is empty: {path}") from exc
    return tuple(header)


def _read_csv_dict_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise LegacyTeModelContractError("empty-sidecar", f"CSV file is empty: {path}")
        return [dict(row) for row in reader]


def validate_wrapper_request(request: WrapperRequest) -> None:
    if not RUN_ID_PATTERN.match(request.run_id):
        raise LegacyTeModelContractError(
            "invalid-run-id",
            f"run_id does not match the frozen regex: {request.run_id}",
        )

    if request.execution_mode not in (
        ExecutionMode.LEGACY_DEFAULT_COUNTS,
        ExecutionMode.LEGACY_WINSORIZED_COUNTS,
    ):
        raise LegacyTeModelContractError(
            "invalid-execution-mode",
            f"Unsupported execution_mode: {request.execution_mode}",
        )

    if request.target_stage not in (0, 1, 2, 3):
        raise LegacyTeModelContractError(
            "invalid-target-stage",
            f"target_stage must be one of 0, 1, 2, or 3: {request.target_stage}",
        )

    _require_absolute_path(
        request.handoff_manifest_path,
        code="handoff-manifest-not-absolute",
        label="handoff_manifest_path",
    )
    _require_existing_file(
        request.handoff_manifest_path,
        code="missing-handoff-manifest",
        label="handoff_manifest_path",
    )

    _require_absolute_path(
        request.sidecars.nonpolya_csv,
        code="nonpolya-not-absolute",
        label="sidecars.nonpolya_csv",
    )
    _require_existing_file(
        request.sidecars.nonpolya_csv,
        code="missing-nonpolya-csv",
        label="sidecars.nonpolya_csv",
    )

    _require_absolute_path(
        request.sidecars.grouping_csv,
        code="grouping-not-absolute",
        label="sidecars.grouping_csv",
    )
    _require_existing_file(
        request.sidecars.grouping_csv,
        code="missing-grouping-csv",
        label="sidecars.grouping_csv",
    )

    if request.sidecars.sample_selection_csv is not None:
        _require_absolute_path(
            request.sidecars.sample_selection_csv,
            code="sample-selection-not-absolute",
            label="sidecars.sample_selection_csv",
        )
        _require_existing_file(
            request.sidecars.sample_selection_csv,
            code="missing-sample-selection-csv",
            label="sidecars.sample_selection_csv",
        )

    if request.source_legacy_root != LEGACY_SOURCE_ROOT:
        raise LegacyTeModelContractError(
            "legacy-root-mismatch",
            f"source_legacy_root must equal frozen legacy source root: {LEGACY_SOURCE_ROOT}",
        )
    if not request.source_legacy_root.exists():
        raise LegacyTeModelContractError(
            "missing-legacy-root",
            f"Frozen legacy source root does not exist: {request.source_legacy_root}",
        )


def validate_handoff_manifest(manifest: HandoffManifestV1, *, request: WrapperRequest) -> None:
    if manifest.manifest_version != "1.0":
        raise LegacyTeModelContractError(
            "invalid-manifest-version",
            f"manifest_version must be 1.0, got: {manifest.manifest_version}",
        )
    if manifest.run_id != request.run_id:
        raise LegacyTeModelContractError(
            "run-id-mismatch",
            f"Manifest run_id does not match request run_id: {manifest.run_id} != {request.run_id}",
        )
    if manifest.input_mode != "experiment_level_ribo":
        raise LegacyTeModelContractError(
            "invalid-input-mode",
            f"input_mode must be experiment_level_ribo, got: {manifest.input_mode}",
        )
    if not manifest.experiments:
        if manifest.all_ribo_path is not None:
            raise LegacyTeModelContractError(
                "all-ribo-alone-insufficient",
                "all.ribo alone is not a valid wrapper handoff without experiment-level records.",
            )
        raise LegacyTeModelContractError(
            "missing-experiments",
            "experiments must be a non-empty array.",
        )

    seen_aliases: set[str] = set()
    materialized_paths: set[Path] = set()
    organism_values: set[str] = set()
    path_to_study: dict[Path, str] = {}
    for experiment in manifest.experiments:
        _validate_handoff_experiment(experiment)
        if experiment.experiment_alias in seen_aliases:
            raise LegacyTeModelContractError(
                "duplicate-experiment-alias",
                f"Duplicate experiment_alias detected: {experiment.experiment_alias}",
            )
        seen_aliases.add(experiment.experiment_alias)
        materialized_path = Path(
            "data",
            "ribo",
            experiment.study_id,
            "ribo",
            "experiments",
            f"{experiment.experiment_alias}.ribo",
        )
        if materialized_path in materialized_paths:
            raise LegacyTeModelContractError(
                "materialization-path-collision",
                f"Two experiment records would materialize to the same sandbox path: {materialized_path}",
            )
        materialized_paths.add(materialized_path)
        previous_study = path_to_study.get(experiment.ribo_path)
        if previous_study is not None and previous_study != experiment.study_id:
            raise LegacyTeModelContractError(
                "conflicting-study-id",
                f"Same ribo_path mapped to conflicting study_id values: {experiment.ribo_path}",
            )
        path_to_study[experiment.ribo_path] = experiment.study_id
        organism_values.add(experiment.organism)

    if len(organism_values) != 1:
        raise LegacyTeModelContractError(
            "mixed-organism-input",
            "Mixed-organism input is not allowed in v1.",
        )
    only_organism = next(iter(organism_values))
    if only_organism.lower() != "human":
        raise LegacyTeModelContractError(
            "unsupported-organism",
            f"Only human input is allowed in v1, got: {only_organism}",
        )


def _validate_handoff_experiment(experiment: HandoffExperiment) -> None:
    if not experiment.experiment_alias.strip():
        raise LegacyTeModelContractError("missing-experiment-alias", "experiment_alias must be non-empty.")
    if not experiment.study_id.strip():
        raise LegacyTeModelContractError("missing-study-id", "study_id must be non-empty.")
    _require_absolute_path(experiment.ribo_path, code="ribo-path-not-absolute", label="experiment.ribo_path")
    _require_existing_file(experiment.ribo_path, code="missing-ribo-file", label="experiment.ribo_path")
    if experiment.ribo_path.suffix != ".ribo":
        raise LegacyTeModelContractError(
            "invalid-ribo-suffix",
            f"experiment.ribo_path must end with .ribo: {experiment.ribo_path}",
        )
    if experiment.has_rnaseq is not True:
        raise RnaSeqValidationError(
            RnaSeqFailureCategory.MANIFEST_DECLARATION_FAILURE,
            f"Manifest declares has_rnaseq != true for experiment {experiment.experiment_alias}",
        )


def validate_sidecars(manifest: HandoffManifestV1, *, request: WrapperRequest) -> None:
    nonpolya_rows = _read_csv_dict_rows(request.sidecars.nonpolya_csv)
    nonpolya_header = tuple(nonpolya_rows[0].keys()) if nonpolya_rows else _read_csv_header(request.sidecars.nonpolya_csv)
    if "Gene" not in nonpolya_header:
        raise LegacyTeModelContractError(
            "missing-gene-column",
            f"nonpolya_csv must contain a Gene column: {request.sidecars.nonpolya_csv}",
        )
    if not any((row.get("Gene") or "").strip() for row in nonpolya_rows):
        raise LegacyTeModelContractError(
            "empty-gene-column",
            f"nonpolya_csv must contain at least one non-empty Gene value: {request.sidecars.nonpolya_csv}",
        )

    grouping_rows = _read_csv_dict_rows(request.sidecars.grouping_csv)
    grouping_header = tuple(grouping_rows[0].keys()) if grouping_rows else _read_csv_header(request.sidecars.grouping_csv)
    for required_column in ("experiment_alias", "cell_line"):
        if required_column not in grouping_header:
            raise LegacyTeModelContractError(
                f"missing-{required_column}-column",
                f"grouping_csv must contain {required_column}: {request.sidecars.grouping_csv}",
            )
    alias_to_cell_line: dict[str, str] = {}
    for row in grouping_rows:
        alias = (row.get("experiment_alias") or "").strip()
        cell_line = (row.get("cell_line") or "").strip()
        if not alias:
            raise LegacyTeModelContractError(
                "empty-grouping-experiment-alias",
                "grouping_csv contains an empty experiment_alias.",
            )
        if alias in alias_to_cell_line:
            raise LegacyTeModelContractError(
                "duplicate-grouping-alias",
                f"grouping_csv contains duplicate experiment_alias: {alias}",
            )
        if not cell_line:
            raise LegacyTeModelContractError(
                "empty-cell-line",
                f"grouping_csv contains an empty cell_line for experiment_alias: {alias}",
            )
        alias_to_cell_line[alias] = cell_line

    missing_aliases = sorted(
        experiment.experiment_alias
        for experiment in manifest.experiments
        if experiment.experiment_alias not in alias_to_cell_line
    )
    if missing_aliases:
        raise LegacyTeModelContractError(
            "grouping-coverage-missing",
            "grouping_csv does not cover all experiment aliases: " + ", ".join(missing_aliases),
        )

    if request.sidecars.sample_selection_csv is not None:
        selection_header = _read_csv_header(request.sidecars.sample_selection_csv)
        if "experiment_alias" not in selection_header:
            raise LegacyTeModelContractError(
                "missing-sample-selection-experiment-alias",
                f"sample_selection_csv must contain experiment_alias: {request.sidecars.sample_selection_csv}",
            )


def validate_target_stage_eligibility(manifest: HandoffManifestV1, *, request: WrapperRequest) -> None:
    if request.target_stage < 2:
        return

    matched_sample_count = len(manifest.experiments)
    if matched_sample_count < 2:
        raise LegacyTeModelContractError(
            "stage2-methodological-boundary",
            "target_stage >= 2 requires at least 2 matched samples covered by grouping_csv. "
            "Single-sample runtimes remain valid for Stage 0/1 smoke but are not Stage-2-eligible.",
        )


def inspect_ribo_for_rnaseq_presence(experiment: HandoffExperiment) -> bool:
    try:
        from ribopy import Ribo
        import ribopy
    except ImportError as exc:
        raise RnaSeqValidationError(
            RnaSeqFailureCategory.RIBO_INSPECTION_FAILURE,
            "ribopy is required for read-only .ribo inspection but is not available.",
        ) from exc

    alias_fn = getattr(ribopy.api.alias, "apris_human_alias", None)
    try:
        ribo = Ribo(str(experiment.ribo_path), alias=alias_fn)
    except Exception as exc:
        if alias_fn is not None:
            try:
                ribo = Ribo(str(experiment.ribo_path), alias=None)
            except Exception as fallback_exc:
                raise RnaSeqValidationError(
                    RnaSeqFailureCategory.RIBO_INSPECTION_FAILURE,
                    f"Failed to open .ribo for read-only inspection: {experiment.ribo_path}",
                ) from fallback_exc
        else:
            raise RnaSeqValidationError(
                RnaSeqFailureCategory.RIBO_INSPECTION_FAILURE,
                f"Failed to open .ribo for read-only inspection: {experiment.ribo_path}",
            ) from exc

    has_rnaseq = getattr(ribo, "has_rnaseq", None)
    if callable(has_rnaseq):
        try:
            return bool(has_rnaseq(experiment.experiment_alias))
        except Exception as exc:
            raise RnaSeqValidationError(
                RnaSeqFailureCategory.RIBO_INSPECTION_FAILURE,
                f"Failed to inspect RNA-seq presence via has_rnaseq for {experiment.experiment_alias}",
            ) from exc

    get_rnaseq = getattr(ribo, "get_rnaseq", None)
    if not callable(get_rnaseq):
        raise RnaSeqValidationError(
            RnaSeqFailureCategory.RIBO_INSPECTION_FAILURE,
            f"Cannot inspect RNA-seq presence for {experiment.experiment_alias}: backend exposes no has_rnaseq or get_rnaseq method.",
        )
    try:
        rnaseq_table = get_rnaseq(experiment.experiment_alias)
    except Exception as exc:
        raise RnaSeqValidationError(
            RnaSeqFailureCategory.RIBO_INSPECTION_FAILURE,
            f"Failed to inspect RNA-seq table for {experiment.experiment_alias}",
        ) from exc
    if rnaseq_table is None:
        return False
    index = getattr(rnaseq_table, "index", None)
    if index is not None and getattr(index, "nlevels", 1) >= 2:
        try:
            return experiment.experiment_alias in index.get_level_values(0)
        except Exception as exc:
            raise RnaSeqValidationError(
                RnaSeqFailureCategory.RIBO_INSPECTION_FAILURE,
                f"Failed to inspect RNA-seq MultiIndex for {experiment.experiment_alias}",
            ) from exc
    columns = getattr(rnaseq_table, "columns", None)
    if columns is not None:
        return "CDS" in columns or experiment.experiment_alias in columns
    return True


def validate_dual_rnaseq(manifest: HandoffManifestV1) -> None:
    for experiment in manifest.experiments:
        if experiment.has_rnaseq is not True:
            raise RnaSeqValidationError(
                RnaSeqFailureCategory.MANIFEST_DECLARATION_FAILURE,
                f"Manifest declares has_rnaseq != true for experiment {experiment.experiment_alias}",
            )
        observed_has_rnaseq = inspect_ribo_for_rnaseq_presence(experiment)
        if not observed_has_rnaseq:
            raise RnaSeqValidationError(
                RnaSeqFailureCategory.MANIFEST_INSPECTION_CONTRADICTION,
                f"Manifest declares RNA-seq present but read-only .ribo inspection could not verify it for experiment {experiment.experiment_alias}",
            )


def validate_request_and_manifest(request: WrapperRequest, manifest: HandoffManifestV1) -> None:
    validate_wrapper_request(request)
    validate_handoff_manifest(manifest, request=request)
    validate_sidecars(manifest, request=request)
    validate_target_stage_eligibility(manifest, request=request)
    validate_dual_rnaseq(manifest)
