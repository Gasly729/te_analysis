"""Write run-level metadata expansion outputs and summary reports."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import os
from pathlib import Path

from .run_accession_resolution import (
    ResolutionResult,
    read_experiment_metadata,
    read_manifest_frame,
    resolve_metadata_runs,
)


@dataclass(frozen=True)
class MetadataRunsResult:
    """Generated run-level metadata tables and report artifacts."""

    metadata_path: Path
    manifest_path: Path
    runs_path: Path
    unresolved_path: Path
    report_path: Path
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


def _render_report(
    *,
    metadata_path: Path,
    manifest_path: Path,
    resolution: ResolutionResult,
) -> str:
    resolved = resolution.resolved
    unresolved = resolution.unresolved
    inventory = resolution.manifest_inventory
    lines = [
        "# Metadata Runs Expansion Report",
        "",
        f"- generated_at: {datetime.now(timezone.utc).isoformat()}",
        f"- metadata_path: {metadata_path}",
        f"- metadata_md5: {_compute_md5(metadata_path)}",
        f"- manifest_path: {manifest_path}",
        f"- manifest_md5: {_compute_md5(manifest_path)}",
        f"- metadata_read_mode: {resolution.metadata_read_mode_label}",
        "",
        "## Summary",
        "",
        f"- input_metadata_rows: {resolution.metadata_rows_in}",
        f"- resolved_run_rows: {len(resolved)}",
        f"- unresolved_rows: {len(unresolved)}",
        f"- manifest_backmatched_runs: {resolution.manifest_backmatched_runs}",
        f"- manifest_unmatched_runs: {resolution.manifest_unmatched_runs}",
        "",
        "## Local Sources Used",
        "",
        f"- {metadata_path}",
        f"- {manifest_path}",
        "",
        "## Unresolved Reasons",
        "",
    ]
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
    runs_path: Path,
    unresolved_path: Path,
    report_path: Path,
) -> MetadataRunsResult:
    """Resolve experiment metadata to runs and write stable local output artifacts."""

    metadata_result = read_experiment_metadata(metadata_path)
    manifest_frame = read_manifest_frame(manifest_path)
    resolution = resolve_metadata_runs(metadata_result, manifest_frame)

    _atomic_write_text(runs_path, resolution.resolved.to_csv(sep="\t", index=False))
    _atomic_write_text(unresolved_path, resolution.unresolved.to_csv(sep="\t", index=False))
    _atomic_write_text(
        report_path,
        _render_report(
            metadata_path=metadata_path,
            manifest_path=manifest_path,
            resolution=resolution,
        ),
    )

    return MetadataRunsResult(
        metadata_path=metadata_path,
        manifest_path=manifest_path,
        runs_path=runs_path,
        unresolved_path=unresolved_path,
        report_path=report_path,
        resolution=resolution,
    )
