from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

from .config_builder import build_trial_config
from .contracts import (
    DEFAULT_RUNTIME_BASE,
    SPEC_VERSION,
    WRAPPER_NAME,
    HandoffManifestV1,
    MaterializationResult,
    WrapperRequest,
    load_handoff_manifest,
    load_wrapper_request,
)
from .validator import validate_request_and_manifest


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n")


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def _touch(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text("")


def _safe_symlink(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() or target.is_symlink():
        target.unlink()
    target.symlink_to(source)


def _copy_file(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)


def _write_legacy_src_init(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            (
                "import functools",
                "import sys",
                "import types",
                "from functools import lru_cache",
                "",
                "# Support legacy imports under Python runtimes that lack functools.cache.",
                "if not hasattr(functools, \"cache\"):",
                "    functools.cache = lambda user_function: lru_cache(maxsize=None)(user_function)",
                "",
                "# tqdm only provides progress reporting in Stage 0; fall back to a no-op shim when absent.",
                "try:",
                "    import tqdm as _tqdm  # noqa: F401",
                "except ImportError:",
                "    fake_tqdm = types.ModuleType(\"tqdm\")",
                "    fake_tqdm.tqdm = lambda iterable, *args, **kwargs: iterable",
                "    sys.modules[\"tqdm\"] = fake_tqdm",
                "",
            )
        )
    )


def _ensure_init(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text("")


def _materialize_legacy_source(sandbox_root: Path, source_legacy_root: Path) -> None:
    _safe_symlink(source_legacy_root / "pipeline.bash", sandbox_root / "pipeline.bash")
    src_root = sandbox_root / "src"
    src_root.mkdir(parents=True, exist_ok=True)
    _write_legacy_src_init(src_root / "__init__.py")
    for filename in ("Fasta.py", "ribo_counts_to_csv.py", "ribobase_counts_processing.py", "transpose_TE.py", "utils.py", "TE.R"):
        _safe_symlink(source_legacy_root / "src" / filename, src_root / filename)


def _materialize_experiment_ribos(sandbox_root: Path, manifest: HandoffManifestV1) -> None:
    for experiment in manifest.experiments:
        target = sandbox_root / "data" / "ribo" / experiment.study_id / "ribo" / "experiments" / f"{experiment.experiment_alias}.ribo"
        _safe_symlink(experiment.ribo_path, target)


def _materialize_sidecars(sandbox_root: Path, request: WrapperRequest) -> dict[str, str]:
    copied: dict[str, str] = {}
    nonpolya_target = sandbox_root / "data" / "nonpolyA_gene.csv"
    grouping_target = sandbox_root / "data" / "infor_filter.csv"
    _copy_file(request.sidecars.nonpolya_csv, nonpolya_target)
    _copy_file(request.sidecars.grouping_csv, grouping_target)
    copied["nonpolya_csv"] = str(nonpolya_target)
    copied["grouping_csv"] = str(grouping_target)

    if request.sidecars.sample_selection_csv is not None:
        selection_target = sandbox_root / "data" / "paxdb_filtered_sample.csv"
        _copy_file(request.sidecars.sample_selection_csv, selection_target)
        copied["sample_selection_csv"] = str(selection_target)

    return copied


def _materialize_trials_package(sandbox_root: Path, request: WrapperRequest, manifest: HandoffManifestV1) -> Path:
    trials_root = sandbox_root / "trials"
    trial_package_root = trials_root / request.run_id
    _ensure_init(trials_root / "__init__.py")
    _ensure_init(trial_package_root / "__init__.py")
    config_path = trial_package_root / "config.py"
    config_source = build_trial_config(
        run_id=request.run_id,
        execution_mode=request.execution_mode,
        experiment_aliases=[experiment.experiment_alias for experiment in manifest.experiments],
    )
    _write_text(config_path, config_source)
    return config_path


def _build_sidecars_manifest(request: WrapperRequest, copied_targets: dict[str, str]) -> dict:
    return {
        "wrapper_name": WRAPPER_NAME,
        "spec_version": SPEC_VERSION,
        "sidecars": {
            "nonpolya_csv": {
                "source": str(request.sidecars.nonpolya_csv),
                "target": copied_targets["nonpolya_csv"],
                "materialization": "copy",
            },
            "grouping_csv": {
                "source": str(request.sidecars.grouping_csv),
                "target": copied_targets["grouping_csv"],
                "materialization": "copy",
            },
            "sample_selection_csv": None
            if request.sidecars.sample_selection_csv is None
            else {
                "source": str(request.sidecars.sample_selection_csv),
                "target": copied_targets["sample_selection_csv"],
                "materialization": "copy",
            },
        },
    }


def _build_provenance_payload(
    *,
    request: WrapperRequest,
    runtime_root: Path,
    sandbox_root: Path,
    copied_targets: dict[str, str],
    config_path: Path,
    pipeline_stdout_log_path: Path,
    pipeline_stderr_log_path: Path,
) -> dict:
    timestamp = datetime.now(timezone.utc).isoformat()
    return {
        "wrapper_name": WRAPPER_NAME,
        "spec_version": SPEC_VERSION,
        "run_id": request.run_id,
        "execution_mode": request.execution_mode.value,
        "legacy_source_root": str(request.source_legacy_root),
        "sandbox_root": str(sandbox_root),
        "raw_outputs_root": str(runtime_root / "outputs" / "raw_legacy_trial_outputs"),
        "packaged_outputs_root": str(runtime_root / "outputs" / "packaged"),
        "materialization_policy": {
            "legacy_source_files": "symlink",
            "experiment_ribo_inputs": "symlink",
            "sidecars": "copy",
            "generated_files": "create_in_runtime_root",
        },
        "generated_config_path": str(config_path),
        "sidecar_targets": copied_targets,
        "log_targets": {
            "pipeline_stdout_log": str(pipeline_stdout_log_path),
            "pipeline_stderr_log": str(pipeline_stderr_log_path),
        },
        "timestamps": {
            "materialized_at": timestamp,
        },
        "status": "materialized_not_executed",
    }


def materialize_legacy_te_model_wrapper(
    request_or_path: WrapperRequest | Path | str,
    *,
    runtime_base: Path | str | None = None,
) -> MaterializationResult:
    request = request_or_path if isinstance(request_or_path, WrapperRequest) else load_wrapper_request(request_or_path)
    manifest = load_handoff_manifest(request.handoff_manifest_path)
    validate_request_and_manifest(request, manifest)

    resolved_runtime_base = DEFAULT_RUNTIME_BASE if runtime_base is None else Path(runtime_base)
    runtime_root = resolved_runtime_base / request.run_id
    handoff_root = runtime_root / "handoff"
    sandbox_root = runtime_root / "sandbox"
    outputs_root = runtime_root / "outputs"
    logs_root = runtime_root / "logs"

    (outputs_root / "raw_legacy_trial_outputs").mkdir(parents=True, exist_ok=True)
    (outputs_root / "packaged").mkdir(parents=True, exist_ok=True)
    logs_root.mkdir(parents=True, exist_ok=True)

    _materialize_legacy_source(sandbox_root, request.source_legacy_root)
    _materialize_experiment_ribos(sandbox_root, manifest)
    copied_targets = _materialize_sidecars(sandbox_root, request)
    config_path = _materialize_trials_package(sandbox_root, request, manifest)

    handoff_manifest_copy = handoff_root / "handoff_manifest.json"
    sidecars_manifest_path = handoff_root / "sidecars_manifest.json"
    wrapper_request_path = handoff_root / "wrapper_request.json"
    provenance_path = logs_root / "wrapper_provenance.json"
    materialization_log_path = logs_root / "materialization.log"
    pipeline_stdout_log_path = logs_root / "pipeline.stdout.log"
    pipeline_stderr_log_path = logs_root / "pipeline.stderr.log"

    _touch(pipeline_stdout_log_path)
    _touch(pipeline_stderr_log_path)

    _write_json(handoff_manifest_copy, manifest.as_dict())
    _write_json(sidecars_manifest_path, _build_sidecars_manifest(request, copied_targets))
    _write_json(wrapper_request_path, request.as_dict())
    _write_json(
        provenance_path,
        _build_provenance_payload(
            request=request,
            runtime_root=runtime_root,
            sandbox_root=sandbox_root,
            copied_targets=copied_targets,
            config_path=config_path,
            pipeline_stdout_log_path=pipeline_stdout_log_path,
            pipeline_stderr_log_path=pipeline_stderr_log_path,
        ),
    )
    _write_text(
        materialization_log_path,
        "materialized, not executed\n"
        f"run_id={request.run_id}\n"
        f"execution_mode={request.execution_mode.value}\n"
        f"runtime_root={runtime_root}\n",
    )

    return MaterializationResult(
        wrapper_name=WRAPPER_NAME,
        spec_version=SPEC_VERSION,
        run_id=request.run_id,
        execution_mode=request.execution_mode.value,
        runtime_root=runtime_root,
        sandbox_root=sandbox_root,
        generated_config_path=config_path,
        handoff_manifest_path=handoff_manifest_copy,
        sidecars_manifest_path=sidecars_manifest_path,
        wrapper_request_path=wrapper_request_path,
        provenance_path=provenance_path,
        materialization_log_path=materialization_log_path,
        status="materialized_not_executed",
    )
