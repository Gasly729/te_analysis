"""Write run-level metadata expansion outputs and summary reports."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import os
from pathlib import Path
from typing import Iterable

import pandas as pd

from .experiment_run_mapping import (
    ExperimentRunMappingResult,
    build_experiment_run_mapping_outputs,
)
from .local_mapping_discovery import LocalMappingSourceSpec
from .run_accession_resolution import (
    ResolutionResult,
    read_experiment_metadata,
    read_manifest_frame,
    resolve_metadata_runs,
)


@dataclass(frozen=True)
class MetadataRunsResult:
    """Generated run-level metadata tables, mapping artifacts, and report outputs."""

    metadata_path: Path
    manifest_path: Path
    mapping_path: Path
    mapping_report_path: Path
    runs_path: Path
    unresolved_path: Path
    report_path: Path
    mapping: ExperimentRunMappingResult
    resolution: ResolutionResult


def _atomic_write_text(path: Path, content: str) -> None:
    tmp_path = path.with_name(path.name + ".tmp")
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        tmp_path.write_text(content, encoding="utf-8")
        os.replace(tmp_path, path)
    finally:
        if tmp_path.exists():
            tmp_path.unlink()


def _compute_md5(path: Path) -> str:
    digest = hashlib.md5()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_baseline_summary(
    *,
    manifest_path: Path,
    runs_path: Path,
    unresolved_path: Path,
) -> dict[str, int] | None:
    if not runs_path.exists() or not unresolved_path.exists():
        return None
    runs = pd.read_csv(runs_path, sep="\t", dtype=str, keep_default_na=False)
    unresolved = pd.read_csv(unresolved_path, sep="\t", dtype=str, keep_default_na=False)
    manifest = pd.read_csv(manifest_path, sep="\t", dtype=str, keep_default_na=False)
    manifest_run_set = set(manifest.loc[manifest["srr"] != "", "srr"])
    resolved_run_set = set(runs["run_accession"])
    return {
        "resolved_rows": len(runs),
        "unresolved_rows": len(unresolved),
        "manifest_unmatched_runs": len(manifest_run_set - resolved_run_set),
    }


def _iter_local_mapping_sources_used(resolved: pd.DataFrame) -> Iterable[str]:
    if resolved.empty:
        return ()
    sources: list[str] = []
    for resolution_source in resolved["resolution_source"]:
        for token in str(resolution_source).split(";"):
            token = token.strip()
            if token.startswith("local_mapping:"):
                sources.append(token[len("local_mapping:") :])
    return sources


def _render_report(
    *,
    metadata_path: Path,
    manifest_path: Path,
    mapping_path: Path,
    mapping_report_path: Path,
    mapping: ExperimentRunMappingResult,
    resolution: ResolutionResult,
    baseline_summary: dict[str, int] | None,
) -> str:
    resolved = resolution.resolved
    unresolved = resolution.unresolved
    inventory = resolution.manifest_inventory
    baseline = baseline_summary or {
        "resolved_rows": 0,
        "unresolved_rows": 0,
        "manifest_unmatched_runs": 0,
    }
    local_mapping_sources = pd.Series(list(_iter_local_mapping_sources_used(resolved)), dtype=str)
    lines = [
        "# Metadata Runs Expansion Report",
        "",
        f"- generated_at: {datetime.now(timezone.utc).isoformat()}",
        f"- metadata_path: {metadata_path}",
        f"- metadata_md5: {_compute_md5(metadata_path)}",
        f"- manifest_path: {manifest_path}",
        f"- manifest_md5: {_compute_md5(manifest_path)}",
        f"- mapping_path: {mapping_path}",
        f"- mapping_md5: {_compute_md5(mapping_path)}",
        f"- mapping_report_path: {mapping_report_path}",
        f"- metadata_read_mode: {resolution.metadata_read_mode_label}",
        "",
        "## Summary",
        "",
        f"- input_metadata_rows: {resolution.metadata_rows_in}",
        f"- baseline_resolved_rows: {baseline['resolved_rows']}",
        f"- phase2_resolved_rows: {len(resolved)}",
        f"- delta_resolved_rows: {len(resolved) - baseline['resolved_rows']}",
        f"- baseline_unresolved_rows: {baseline['unresolved_rows']}",
        f"- phase2_unresolved_rows: {len(unresolved)}",
        f"- delta_unresolved_rows: {len(unresolved) - baseline['unresolved_rows']}",
        f"- manifest_backmatched_runs: {resolution.manifest_backmatched_runs}",
        f"- baseline_manifest_unmatched_runs: {baseline['manifest_unmatched_runs']}",
        f"- phase2_manifest_unmatched_runs: {resolution.manifest_unmatched_runs}",
        f"- delta_manifest_unmatched_runs: {resolution.manifest_unmatched_runs - baseline['manifest_unmatched_runs']}",
        "",
        "## Local Sources Used",
        "",
        f"- {metadata_path}",
        f"- {manifest_path}",
        f"- {mapping_path}",
        "",
        "## Mapping Sources Found",
        "",
    ]
    if mapping.discovery.sources_found:
        lines.extend(f"- {entry}" for entry in mapping.discovery.sources_found)
    else:
        lines.append("- none")

    lines.extend(["", "## Mapping Sources Used", ""])
    if mapping.discovery.sources_used:
        lines.extend(f"- {entry}" for entry in mapping.discovery.sources_used)
    else:
        lines.append("- none")

    lines.extend(["", "## Top Mapping Sources Used", ""])
    if not local_mapping_sources.empty:
        for source, count in local_mapping_sources.value_counts().items():
            lines.append(f"- {source}: {count}")
    else:
        lines.append("- none")

    lines.extend(["", "## Top Remaining Unresolved Reasons", ""])
    if resolution.unresolved_reason_counts:
        for reason, count in resolution.unresolved_reason_counts.most_common():
            lines.append(f"- {reason}: {count}")
    else:
        lines.append("- none")

    lines.extend(["", "## Unresolved Reasons", ""])
    if resolution.unresolved_reason_counts:
        for reason, count in resolution.unresolved_reason_counts.most_common():
            lines.append(f"- {reason}: {count}")
    else:
        lines.append("- none")

    lines.extend(["", "## Resolution Sources", ""])
    if not resolved.empty:
        for source, count in resolved["resolution_source"].value_counts().items():
            lines.append(f"- {source}: {count}")
    else:
        lines.append("- none")

    lines.extend(["", "## Sample Unresolved Rows", ""])
    if not unresolved.empty:
        sample = unresolved.head(10)
        for _, row in sample.iterrows():
            lines.append(
                "- experiment_alias={alias} experiment_accession={accession} reason={reason}".format(
                    alias=row["experiment_alias"] or "-",
                    accession=row["experiment_accession"] or "-",
                    reason=row["unresolved_reason"],
                )
            )
    else:
        lines.append("- none")

    lines.extend(["", "## Inventory Snapshot", ""])
    lines.append(f"- manifest_inventory_rows: {len(inventory)}")
    return "\n".join(lines) + "\n"


def build_metadata_runs_outputs(
    *,
    metadata_path: Path,
    manifest_path: Path,
    mapping_path: Path,
    mapping_report_path: Path,
    runs_path: Path,
    unresolved_path: Path,
    report_path: Path,
    mapping_source_specs: tuple[LocalMappingSourceSpec, ...] | None = None,
) -> MetadataRunsResult:
    """Resolve experiment metadata to runs and write stable local output artifacts."""

    baseline_summary = _load_baseline_summary(
        manifest_path=manifest_path,
        runs_path=runs_path,
        unresolved_path=unresolved_path,
    )
    metadata_result = read_experiment_metadata(metadata_path)
    manifest_frame = read_manifest_frame(manifest_path)
    mapping = build_experiment_run_mapping_outputs(
        mapping_path=mapping_path,
        report_path=mapping_report_path,
        source_specs=mapping_source_specs,
    )
    resolution = resolve_metadata_runs(
        metadata_result,
        manifest_frame,
        local_mapping_frame=mapping.discovery.mapping_frame,
    )

    _atomic_write_text(runs_path, resolution.resolved.to_csv(sep="\t", index=False))
    _atomic_write_text(unresolved_path, resolution.unresolved.to_csv(sep="\t", index=False))
    _atomic_write_text(
        report_path,
        _render_report(
            metadata_path=metadata_path,
            manifest_path=manifest_path,
            mapping_path=mapping_path,
            mapping_report_path=mapping_report_path,
            mapping=mapping,
            resolution=resolution,
            baseline_summary=baseline_summary,
        ),
    )

    return MetadataRunsResult(
        metadata_path=metadata_path,
        manifest_path=manifest_path,
        mapping_path=mapping_path,
        mapping_report_path=mapping_report_path,
        runs_path=runs_path,
        unresolved_path=unresolved_path,
        report_path=report_path,
        mapping=mapping,
        resolution=resolution,
    )
