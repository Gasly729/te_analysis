from __future__ import annotations

import importlib
import json
import os
import subprocess
import sys
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from .contracts import (
    SPEC_VERSION,
    WRAPPER_NAME,
    ExecutionMode,
    ExecutionReadinessResult,
    HandoffManifestV1,
    MaterializationResult,
    WrapperRequest,
    load_handoff_manifest,
    load_wrapper_request,
)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n")


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def _touch(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text("")


def _resolve_runtime_root(runtime_root_or_result: MaterializationResult | Path | str) -> Path:
    if isinstance(runtime_root_or_result, MaterializationResult):
        return runtime_root_or_result.runtime_root
    return Path(runtime_root_or_result)


@contextmanager
def _sandbox_import_context(sandbox_root: Path) -> Iterator[None]:
    previous_cwd = Path.cwd()
    sys.path.insert(0, str(sandbox_root))
    try:
        os.chdir(sandbox_root)
        yield
    finally:
        os.chdir(previous_cwd)
        sys.path.pop(0)


def _restore_modules(original_modules: dict[str, Any | None]) -> None:
    for name, module in reversed(tuple(original_modules.items())):
        if module is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = module


def _check_exists(label: str, path: Path, issues: list[str]) -> dict[str, Any]:
    exists = path.exists()
    if not exists:
        issues.append(f"Missing required runtime path for {label}: {path}")
    return {
        "label": label,
        "path": str(path),
        "exists": exists,
    }


def _iter_legacy_study_layouts(study_id: str) -> tuple[str, str]:
    return (study_id, f"{study_id}_dedup")


def _collect_required_paths(
    *,
    runtime_root: Path,
    sandbox_root: Path,
    run_id: str,
    request: WrapperRequest | None,
    manifest: HandoffManifestV1 | None,
    pipeline_stdout_log_path: Path,
    pipeline_stderr_log_path: Path,
) -> tuple[list[dict[str, Any]], list[str]]:
    issues: list[str] = []
    checks: list[dict[str, Any]] = []

    required_paths = (
        ("runtime_root", runtime_root),
        ("sandbox_root", sandbox_root),
        ("pipeline_bash", sandbox_root / "pipeline.bash"),
        ("src_package", sandbox_root / "src" / "__init__.py"),
        ("stage0_entrypoint", sandbox_root / "src" / "ribo_counts_to_csv.py"),
        ("stage1_entrypoint", sandbox_root / "src" / "ribobase_counts_processing.py"),
        ("stage2_entrypoint", sandbox_root / "src" / "TE.R"),
        ("stage3_entrypoint", sandbox_root / "src" / "transpose_TE.py"),
        ("trials_package", sandbox_root / "trials" / "__init__.py"),
        ("generated_trial_package", sandbox_root / "trials" / run_id / "__init__.py"),
        ("generated_config", sandbox_root / "trials" / run_id / "config.py"),
        ("sandbox_nonpolyA_sidecar", sandbox_root / "data" / "nonpolyA_gene.csv"),
        ("sandbox_grouping_sidecar", sandbox_root / "data" / "infor_filter.csv"),
        ("pipeline_stdout_log", pipeline_stdout_log_path),
        ("pipeline_stderr_log", pipeline_stderr_log_path),
    )
    for label, path in required_paths:
        checks.append(_check_exists(label, path, issues))

    if request is not None and request.sidecars.sample_selection_csv is not None:
        checks.append(
            _check_exists(
                "sandbox_sample_selection_sidecar",
                sandbox_root / "data" / "paxdb_filtered_sample.csv",
                issues,
            )
        )

    if manifest is not None:
        for experiment in manifest.experiments:
            for legacy_study_id in _iter_legacy_study_layouts(experiment.study_id):
                sandbox_path = (
                    sandbox_root
                    / "data"
                    / "ribo"
                    / legacy_study_id
                    / "ribo"
                    / "experiments"
                    / f"{experiment.experiment_alias}.ribo"
                )
                check = _check_exists(
                    f"experiment_ribo::{legacy_study_id}::{experiment.experiment_alias}",
                    sandbox_path,
                    issues,
                )
                if check["exists"]:
                    resolved_source = str(sandbox_path.resolve())
                    expected_source = str(experiment.ribo_path.resolve())
                    check["resolved_source"] = resolved_source
                    check["expected_source"] = expected_source
                    if resolved_source != expected_source:
                        issues.append(
                            "Sandbox ribo staging points at an unexpected source for "
                            f"{legacy_study_id}/{experiment.experiment_alias}: "
                            f"{resolved_source} != {expected_source}"
                        )
                checks.append(check)

    return checks, issues


def _probe_pipeline_bash_syntax(sandbox_root: Path) -> tuple[dict[str, Any], list[str]]:
    pipeline_path = sandbox_root / "pipeline.bash"
    if not pipeline_path.exists():
        return (
            {
                "checked": False,
                "pipeline_path": str(pipeline_path),
                "bash_syntax_ok": False,
                "stdout": "",
                "stderr": "pipeline.bash is missing",
            },
            [f"Missing pipeline.bash for shell syntax validation: {pipeline_path}"],
        )

    completed = subprocess.run(
        ["bash", "-n", "pipeline.bash"],
        cwd=sandbox_root,
        capture_output=True,
        text=True,
        check=False,
    )
    issues: list[str] = []
    if completed.returncode != 0:
        issues.append(
            "pipeline.bash failed non-executing shell syntax validation: "
            f"exit={completed.returncode}"
        )
    return (
        {
            "checked": True,
            "pipeline_path": str(pipeline_path),
            "bash_syntax_ok": completed.returncode == 0,
            "returncode": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
        },
        issues,
    )


def _probe_trial_config_import(
    *,
    sandbox_root: Path,
    run_id: str,
    execution_mode: ExecutionMode | None,
    manifest: HandoffManifestV1 | None,
) -> tuple[dict[str, Any], list[str]]:
    module_name = f"trials.{run_id}.config"
    config_path = sandbox_root / "trials" / run_id / "config.py"
    expected_aliases = [] if manifest is None else [experiment.experiment_alias for experiment in manifest.experiments]
    details: dict[str, Any] = {
        "checked": False,
        "config_path": str(config_path),
        "module_name": module_name,
        "launch_cwd": str(sandbox_root),
        "expected_workdir": str((sandbox_root / "trials" / run_id).resolve()),
        "expected_experiment_aliases": expected_aliases,
        "module_import_ok": False,
        "main_callable": False,
        "sample_filter_callable": False,
        "backend_module": None,
        "observed_workdir": None,
        "observed_custom_experiment_list": None,
        "process_coverage_fn_present": False,
    }
    issues: list[str] = []
    if not config_path.exists():
        issues.append(f"Generated config is missing for import probe: {config_path}")
        return details, issues

    try:
        compile(config_path.read_text(), str(config_path), "exec")
    except SyntaxError as exc:
        issues.append(f"Generated config failed syntax compilation before import probe: {exc}")
        details["syntax_error"] = repr(exc)
        return details, issues

    module_names = (
        "src",
        "src.Fasta",
        "src.utils",
        "src.ribo_counts_to_csv",
        "trials",
        f"trials.{run_id}",
        module_name,
    )
    original_modules = {name: sys.modules.get(name) for name in module_names}

    with _sandbox_import_context(sandbox_root):
        try:
            importlib.invalidate_caches()
            module = importlib.import_module(module_name)
        except Exception as exc:
            issues.append(f"Failed to import generated config from sandbox root: {exc}")
            details["import_error"] = repr(exc)
            _restore_modules(original_modules)
            return details, issues
        finally:
            if module_name not in sys.modules:
                _restore_modules(original_modules)

    try:
        observed_workdir = getattr(module, "workdir", None)
        observed_aliases = getattr(module, "custom_experiment_list", None)
        details.update(
            {
                "checked": True,
                "module_import_ok": True,
                "main_callable": callable(getattr(module, "main", None)),
                "sample_filter_callable": callable(getattr(module, "sample_filter", None)),
                "backend_module": getattr(getattr(module, "main", None), "__module__", None),
                "observed_workdir": observed_workdir,
                "observed_custom_experiment_list": observed_aliases,
                "process_coverage_fn_present": callable(getattr(module, "process_coverage_fn", None)),
            }
        )

        if not details["main_callable"]:
            issues.append(f"Generated config does not expose callable main(): {config_path}")
        if not details["sample_filter_callable"]:
            issues.append(f"Generated config does not expose callable sample_filter: {config_path}")
        if details["backend_module"] != "src.ribo_counts_to_csv":
            issues.append(
                "Generated config does not resolve legacy Stage 0 backend from sandbox src/: "
                f"{details['backend_module']}"
            )
        if observed_workdir is None or Path(str(observed_workdir)).resolve() != (sandbox_root / "trials" / run_id).resolve():
            issues.append(
                "Generated config workdir does not resolve to the sandbox trial directory: "
                f"{observed_workdir}"
            )
        if expected_aliases and list(observed_aliases or []) != expected_aliases:
            issues.append(
                "Generated config custom_experiment_list does not match handoff manifest: "
                f"{observed_aliases}"
            )
        if execution_mode is ExecutionMode.LEGACY_WINSORIZED_COUNTS and not details["process_coverage_fn_present"]:
            issues.append("Winsorized execution mode is missing process_coverage_fn in generated config.")
        if execution_mode is ExecutionMode.LEGACY_DEFAULT_COUNTS and details["process_coverage_fn_present"]:
            issues.append("Default execution mode unexpectedly defines process_coverage_fn in generated config.")
    finally:
        _restore_modules(original_modules)

    return details, issues


def _update_provenance(
    *,
    provenance_path: Path,
    runtime_root: Path,
    sandbox_root: Path,
    run_id: str,
    generated_config_path: Path,
    pipeline_stdout_log_path: Path,
    pipeline_stderr_log_path: Path,
    readiness_report_path: Path,
    readiness_log_path: Path,
    checked_at: str,
    status: str,
    next_stage0_command: str,
    ready_for_stage0_isolated_smoke: bool,
) -> None:
    payload = _read_json(provenance_path) if provenance_path.exists() else {}
    payload.setdefault("wrapper_name", WRAPPER_NAME)
    payload.setdefault("spec_version", SPEC_VERSION)
    payload.setdefault("run_id", run_id)
    payload.setdefault("sandbox_root", str(sandbox_root))
    payload.setdefault("raw_outputs_root", str(runtime_root / "outputs" / "raw_legacy_trial_outputs"))
    payload.setdefault("packaged_outputs_root", str(runtime_root / "outputs" / "packaged"))
    payload["generated_config_path"] = str(generated_config_path)

    log_targets = payload.get("log_targets")
    if not isinstance(log_targets, dict):
        log_targets = {}
    log_targets["pipeline_stdout_log"] = str(pipeline_stdout_log_path)
    log_targets["pipeline_stderr_log"] = str(pipeline_stderr_log_path)
    log_targets["isolated_smoke_readiness_report"] = str(readiness_report_path)
    log_targets["isolated_smoke_readiness_log"] = str(readiness_log_path)
    payload["log_targets"] = log_targets

    timestamps = payload.get("timestamps")
    if not isinstance(timestamps, dict):
        timestamps = {}
    timestamps["readiness_checked_at"] = checked_at
    payload["timestamps"] = timestamps

    payload["readiness_probe"] = {
        "checked_at": checked_at,
        "status": status,
        "ready_for_stage0_isolated_smoke": ready_for_stage0_isolated_smoke,
        "launch_cwd": str(sandbox_root),
        "next_stage0_command": next_stage0_command,
        "details_path": str(readiness_report_path),
        "log_path": str(readiness_log_path),
    }
    _write_json(provenance_path, payload)


def prepare_legacy_te_model_isolated_smoke(
    runtime_root_or_result: MaterializationResult | Path | str,
) -> ExecutionReadinessResult:
    runtime_root = _resolve_runtime_root(runtime_root_or_result).resolve()
    if not runtime_root.exists():
        raise FileNotFoundError(f"Runtime root does not exist: {runtime_root}")

    handoff_root = runtime_root / "handoff"
    logs_root = runtime_root / "logs"
    sandbox_root = runtime_root / "sandbox"
    request_path = handoff_root / "wrapper_request.json"
    manifest_path = handoff_root / "handoff_manifest.json"
    provenance_path = logs_root / "wrapper_provenance.json"
    pipeline_stdout_log_path = logs_root / "pipeline.stdout.log"
    pipeline_stderr_log_path = logs_root / "pipeline.stderr.log"
    readiness_report_path = logs_root / "isolated_smoke_readiness.json"
    readiness_log_path = logs_root / "isolated_smoke_readiness.log"

    _touch(pipeline_stdout_log_path)
    _touch(pipeline_stderr_log_path)

    request = load_wrapper_request(request_path) if request_path.exists() else None
    manifest = load_handoff_manifest(manifest_path) if manifest_path.exists() else None
    run_id = (
        request.run_id
        if request is not None
        else manifest.run_id
        if manifest is not None
        else runtime_root.name
    )
    generated_config_path = sandbox_root / "trials" / run_id / "config.py"

    checked_at = datetime.now(timezone.utc).isoformat()
    next_stage0_command = f"python -m trials.{run_id}.config"
    issues: list[str] = []

    if not request_path.exists():
        issues.append(f"Missing wrapper request snapshot under runtime root: {request_path}")
    if not manifest_path.exists():
        issues.append(f"Missing handoff manifest snapshot under runtime root: {manifest_path}")
    if request is not None and request.run_id != runtime_root.name:
        issues.append(
            f"Runtime root name does not match wrapper request run_id: {runtime_root.name} != {request.run_id}"
        )
    if manifest is not None and manifest.run_id != run_id:
        issues.append(f"Handoff manifest run_id does not match runtime run_id: {manifest.run_id} != {run_id}")

    path_checks, path_issues = _collect_required_paths(
        runtime_root=runtime_root,
        sandbox_root=sandbox_root,
        run_id=run_id,
        request=request,
        manifest=manifest,
        pipeline_stdout_log_path=pipeline_stdout_log_path,
        pipeline_stderr_log_path=pipeline_stderr_log_path,
    )
    issues.extend(path_issues)

    pipeline_syntax_details, pipeline_syntax_issues = _probe_pipeline_bash_syntax(sandbox_root)
    issues.extend(pipeline_syntax_issues)

    config_import_details, config_import_issues = _probe_trial_config_import(
        sandbox_root=sandbox_root,
        run_id=run_id,
        execution_mode=None if request is None else request.execution_mode,
        manifest=manifest,
    )
    issues.extend(config_import_issues)

    ready_for_stage0_isolated_smoke = not issues
    status = (
        "ready_for_stage0_isolated_smoke"
        if ready_for_stage0_isolated_smoke
        else "not_ready_for_stage0_isolated_smoke"
    )
    report_payload = {
        "wrapper_name": WRAPPER_NAME,
        "spec_version": SPEC_VERSION,
        "run_id": run_id,
        "runtime_root": str(runtime_root),
        "sandbox_root": str(sandbox_root),
        "generated_config_path": str(generated_config_path),
        "checked_at": checked_at,
        "status": status,
        "ready_for_stage0_isolated_smoke": ready_for_stage0_isolated_smoke,
        "next_minimal_validation_action": {
            "launch_cwd": str(sandbox_root),
            "command": next_stage0_command,
            "description": "Run legacy Stage 0 only from the sandbox root.",
        },
        "checks": {
            "required_paths": path_checks,
            "pipeline_shell_syntax": pipeline_syntax_details,
            "trial_config_import": config_import_details,
        },
        "blocking_issues": issues,
    }
    _write_json(readiness_report_path, report_payload)

    log_lines = [
        f"status={status}",
        f"checked_at={checked_at}",
        f"runtime_root={runtime_root}",
        f"sandbox_root={sandbox_root}",
        f"launch_cwd={sandbox_root}",
        f"next_stage0_command={next_stage0_command}",
    ]
    if issues:
        log_lines.append("blocking_issues=")
        log_lines.extend(issues)
    else:
        log_lines.append("blocking_issues=none")
    _write_text(readiness_log_path, "\n".join(log_lines) + "\n")

    _update_provenance(
        provenance_path=provenance_path,
        runtime_root=runtime_root,
        sandbox_root=sandbox_root,
        run_id=run_id,
        generated_config_path=generated_config_path,
        pipeline_stdout_log_path=pipeline_stdout_log_path,
        pipeline_stderr_log_path=pipeline_stderr_log_path,
        readiness_report_path=readiness_report_path,
        readiness_log_path=readiness_log_path,
        checked_at=checked_at,
        status=status,
        next_stage0_command=next_stage0_command,
        ready_for_stage0_isolated_smoke=ready_for_stage0_isolated_smoke,
    )

    return ExecutionReadinessResult(
        wrapper_name=WRAPPER_NAME,
        spec_version=SPEC_VERSION,
        run_id=run_id,
        runtime_root=runtime_root,
        sandbox_root=sandbox_root,
        generated_config_path=generated_config_path,
        readiness_report_path=readiness_report_path,
        readiness_log_path=readiness_log_path,
        pipeline_stdout_log_path=pipeline_stdout_log_path,
        pipeline_stderr_log_path=pipeline_stderr_log_path,
        checked_at=checked_at,
        next_stage0_command=next_stage0_command,
        ready_for_stage0_isolated_smoke=ready_for_stage0_isolated_smoke,
        blocking_issues=tuple(issues),
        status=status,
    )
