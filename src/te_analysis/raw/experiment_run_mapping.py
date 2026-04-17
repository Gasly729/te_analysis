"""Write reusable local experiment-to-run mapping artifacts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import os
from pathlib import Path

from .local_mapping_discovery import (
    LocalMappingDiscoveryResult,
    LocalMappingSourceSpec,
    discover_local_experiment_run_mappings,
)


@dataclass(frozen=True)
class ExperimentRunMappingResult:
    """Persisted local experiment/run mapping table plus source summary."""

    mapping_path: Path
    report_path: Path
    discovery: LocalMappingDiscoveryResult


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


def _render_mapping_report(
    *,
    mapping_path: Path,
    discovery: LocalMappingDiscoveryResult,
) -> str:
    lines = [
        "# Local Experiment-to-Run Mapping Report",
        "",
        f"- generated_at: {datetime.now(timezone.utc).isoformat()}",
        f"- mapping_path: {mapping_path}",
        f"- mapping_rows: {len(discovery.mapping_frame)}",
    ]
    if mapping_path.exists():
        lines.append(f"- mapping_md5: {_compute_md5(mapping_path)}")
    lines.extend(["", "## Sources Found", ""])
    if discovery.sources_found:
        lines.extend(f"- {entry}" for entry in discovery.sources_found)
    else:
        lines.append("- none")
    lines.extend(["", "## Sources Used", ""])
    if discovery.sources_used:
        lines.extend(f"- {entry}" for entry in discovery.sources_used)
    else:
        lines.append("- none")
    lines.extend(["", "## Sources Skipped", ""])
    if discovery.skipped_sources:
        lines.extend(f"- {entry}" for entry in discovery.skipped_sources)
    else:
        lines.append("- none")
    lines.extend(["", "## Top Mapping Sources", ""])
    if not discovery.mapping_frame.empty:
        for source, count in discovery.mapping_frame["mapping_source"].value_counts().items():
            lines.append(f"- {source}: {count}")
    else:
        lines.append("- none")
    return "\n".join(lines) + "\n"


def build_experiment_run_mapping_outputs(
    *,
    mapping_path: Path,
    report_path: Path,
    source_specs: tuple[LocalMappingSourceSpec, ...] | None = None,
) -> ExperimentRunMappingResult:
    """Discover, normalize, and persist local experiment/run mappings."""

    discovery = discover_local_experiment_run_mappings(source_specs=source_specs)
    _atomic_write_text(mapping_path, discovery.mapping_frame.to_csv(sep="\t", index=False))
    _atomic_write_text(
        report_path,
        _render_mapping_report(
            mapping_path=mapping_path,
            discovery=discovery,
        ),
    )
    return ExperimentRunMappingResult(
        mapping_path=mapping_path,
        report_path=report_path,
        discovery=discovery,
    )
