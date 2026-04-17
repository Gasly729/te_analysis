"""Local-first run accession resolution using metadata and manifest inventory."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
import re

import pandas as pd
from pandas.errors import ParserError


READ_MODES = (
    {"header": 1, "skiprows": [0]},
    {"header": 0, "skiprows": [0]},
    {"header": 1},
)
CORE_METADATA_COLUMNS = (
    "experiment_alias",
    "study_name",
    "organism",
    "library_strategy",
    "library_layout",
)
RUN_ACCESSION_PATTERN = re.compile(r"(SRR\d+|ERR\d+|DRR\d+)")
EXPERIMENT_ACCESSION_PATTERN = re.compile(r"(GSM\d+|SRX\d+|ERX\d+|DRX\d+)")
RESOLVED_COLUMNS = (
    "run_accession",
    "run_accession_prefix",
    "experiment_accession",
    "experiment_alias",
    "study_name",
    "organism",
    "corrected_type",
    "library_strategy",
    "library_layout",
    "resolution_status",
    "resolution_source",
    "manifest_match_status",
    "fastq_presence_status",
    "source_batches",
    "manifest_row_count",
    "manifest_source_paths",
    "manifest_linked_paths",
    "manifest_statuses",
)
UNRESOLVED_COLUMNS = (
    "run_accession",
    "run_accession_prefix",
    "experiment_accession",
    "experiment_alias",
    "study_name",
    "organism",
    "corrected_type",
    "library_strategy",
    "library_layout",
    "resolution_status",
    "resolution_source",
    "manifest_match_status",
    "fastq_presence_status",
    "unresolved_reason",
)


class MetadataRunsError(RuntimeError):
    """Raised when local metadata-to-run expansion cannot proceed safely."""


@dataclass(frozen=True)
class MetadataReadResult:
    """Experiment-level metadata plus the read mode that matched the real file."""

    frame: pd.DataFrame
    read_mode_label: str


@dataclass(frozen=True)
class ResolutionResult:
    """Resolved and unresolved run-level tables plus summary counters."""

    metadata_rows_in: int
    resolved: pd.DataFrame
    unresolved: pd.DataFrame
    manifest_inventory: pd.DataFrame
    metadata_read_mode_label: str
    unresolved_reason_counts: Counter[str]
    manifest_backmatched_runs: int
    manifest_unmatched_runs: int


def _read_csv_with_supported_modes(path: Path) -> MetadataReadResult:
    last_columns: list[str] | None = None
    for read_mode in READ_MODES:
        try:
            frame = pd.read_csv(
                path,
                dtype=str,
                keep_default_na=False,
                **read_mode,
            )
        except ParserError:
            continue
        frame.columns = [str(column).strip() for column in frame.columns]
        last_columns = list(frame.columns)
        if all(column in frame.columns for column in CORE_METADATA_COLUMNS):
            label = ", ".join(f"{key}={value}" for key, value in read_mode.items())
            return MetadataReadResult(frame=frame, read_mode_label=label)
    raise MetadataRunsError(
        "metadata file is missing required columns after trying supported read modes: "
        + ", ".join(CORE_METADATA_COLUMNS)
        + f" ({path}, last_columns={last_columns})"
    )


def _normalize_text_frame(frame: pd.DataFrame) -> pd.DataFrame:
    normalized = frame.copy()
    for column in normalized.columns:
        normalized[column] = normalized[column].map(lambda value: str(value).strip())
        normalized[column] = normalized[column].replace({"nan": "", "None": ""})
    return normalized


def _split_semicolon_values(value: str) -> tuple[str, ...]:
    if not value:
        return ()
    tokens = [token.strip() for token in value.split(";")]
    return tuple(token for token in tokens if token)


def read_experiment_metadata(metadata_path: Path) -> MetadataReadResult:
    """Load experiment-level metadata using the project's proven schema handling."""

    return _read_csv_with_supported_modes(metadata_path)


def read_manifest_frame(manifest_path: Path) -> pd.DataFrame:
    """Load the physical FASTQ manifest as a string-only table."""

    frame = pd.read_csv(
        manifest_path,
        sep="\t",
        dtype=str,
        keep_default_na=False,
    )
    return _normalize_text_frame(frame)


def _collapse_unique(values: pd.Series) -> str:
    unique_values = sorted({value for value in values if value})
    return ";".join(unique_values)


def _classify_fastq_presence(layout: str, mates_value: str) -> str:
    mates = {mate for mate in mates_value.split(";") if mate}
    if layout == "PAIRED":
        if mates == {"1", "2"}:
            return "paired_complete"
        return "paired_incomplete"
    if layout == "SINGLE":
        return "single_present"
    return "layout_unknown"


def build_manifest_run_inventory(manifest_frame: pd.DataFrame) -> pd.DataFrame:
    """Collapse file-level manifest rows into run-level local inventory rows."""

    inventory_source = manifest_frame[
        (manifest_frame["srr"] != "") & (manifest_frame["source_path"] != "")
    ].copy()
    inventory_source["parsed_source_alias"] = inventory_source["source_path"].str.extract(
        EXPERIMENT_ACCESSION_PATTERN,
        expand=False,
    ).fillna("")
    grouped_rows: list[dict[str, str]] = []
    for run_accession, group in inventory_source.groupby("srr", sort=True):
        grouped_rows.append(
            {
                "run_accession": run_accession,
                "run_accession_prefix": run_accession[:3],
                "experiment_aliases": _collapse_unique(group["gsm"]),
                "parsed_source_aliases": _collapse_unique(group["parsed_source_alias"]),
                "source_batches": _collapse_unique(group["source_batch"]),
                "manifest_row_count": str(len(group)),
                "manifest_source_paths": _collapse_unique(group["source_path"]),
                "manifest_linked_paths": _collapse_unique(group["linked_path"]),
                "manifest_statuses": _collapse_unique(group["status"]),
                "inventory_mates": _collapse_unique(group["mate"]),
            }
        )
    inventory = pd.DataFrame(grouped_rows, dtype=str)
    if inventory.empty:
        return pd.DataFrame(
            columns=(
                "run_accession",
                "run_accession_prefix",
                "experiment_aliases",
                "parsed_source_aliases",
                "source_batches",
                "manifest_row_count",
                "manifest_source_paths",
                "manifest_linked_paths",
                "manifest_statuses",
                "inventory_mates",
            )
        )
    return _normalize_text_frame(inventory)


def _append_resolved_row(
    rows: list[dict[str, str]],
    metadata_row: pd.Series,
    *,
    run_accession: str,
    resolution_source: str,
    inventory_row: pd.Series | None,
) -> None:
    manifest_match_status = "manifest_present" if inventory_row is not None else "manifest_absent"
    fastq_presence_status = (
        _classify_fastq_presence(metadata_row["library_layout"], inventory_row["inventory_mates"])
        if inventory_row is not None
        else "manifest_absent"
    )
    rows.append(
        {
            "run_accession": run_accession,
            "run_accession_prefix": run_accession[:3],
            "experiment_accession": metadata_row.get("experiment_accession", ""),
            "experiment_alias": metadata_row["experiment_alias"],
            "study_name": metadata_row["study_name"],
            "organism": metadata_row["organism"],
            "corrected_type": metadata_row.get("corrected_type", ""),
            "library_strategy": metadata_row["library_strategy"],
            "library_layout": metadata_row["library_layout"],
            "resolution_status": "resolved",
            "resolution_source": resolution_source,
            "manifest_match_status": manifest_match_status,
            "fastq_presence_status": fastq_presence_status,
            "source_batches": inventory_row["source_batches"] if inventory_row is not None else "",
            "manifest_row_count": inventory_row["manifest_row_count"] if inventory_row is not None else "0",
            "manifest_source_paths": inventory_row["manifest_source_paths"] if inventory_row is not None else "",
            "manifest_linked_paths": inventory_row["manifest_linked_paths"] if inventory_row is not None else "",
            "manifest_statuses": inventory_row["manifest_statuses"] if inventory_row is not None else "",
        }
    )


def _append_unresolved_row(
    rows: list[dict[str, str]],
    metadata_row: pd.Series,
    *,
    unresolved_reason: str,
) -> None:
    rows.append(
        {
            "run_accession": "",
            "run_accession_prefix": "",
            "experiment_accession": metadata_row.get("experiment_accession", ""),
            "experiment_alias": metadata_row["experiment_alias"],
            "study_name": metadata_row["study_name"],
            "organism": metadata_row["organism"],
            "corrected_type": metadata_row.get("corrected_type", ""),
            "library_strategy": metadata_row["library_strategy"],
            "library_layout": metadata_row["library_layout"],
            "resolution_status": "unresolved",
            "resolution_source": "",
            "manifest_match_status": "manifest_absent",
            "fastq_presence_status": "manifest_absent",
            "unresolved_reason": unresolved_reason,
        }
    )


def resolve_metadata_runs(metadata_result: MetadataReadResult, manifest_frame: pd.DataFrame) -> ResolutionResult:
    """Expand experiment-level metadata rows into run-level resolved and unresolved tables."""

    metadata = _normalize_text_frame(metadata_result.frame)
    inventory = build_manifest_run_inventory(manifest_frame)

    inventory_by_run = {row["run_accession"]: row for _, row in inventory.iterrows()}
    inventory_by_alias: dict[str, list[pd.Series]] = defaultdict(list)
    inventory_by_parsed_alias: dict[str, list[pd.Series]] = defaultdict(list)
    for _, row in inventory.iterrows():
        for alias in _split_semicolon_values(row["experiment_aliases"]):
            inventory_by_alias[alias].append(row)
        for alias in _split_semicolon_values(row["parsed_source_aliases"]):
            inventory_by_parsed_alias[alias].append(row)

    resolved_rows: list[dict[str, str]] = []
    unresolved_rows: list[dict[str, str]] = []

    for _, metadata_row in metadata.iterrows():
        explicit_run_ids = _split_semicolon_values(metadata_row.get("run_alias", ""))
        if explicit_run_ids:
            for run_accession in explicit_run_ids:
                _append_resolved_row(
                    resolved_rows,
                    metadata_row,
                    run_accession=run_accession,
                    resolution_source="metadata.run_alias",
                    inventory_row=inventory_by_run.get(run_accession),
                )
            continue

        candidate_inventory: dict[str, dict[str, object]] = {}
        for inventory_row in inventory_by_alias.get(metadata_row["experiment_alias"], []):
            candidate_inventory.setdefault(
                inventory_row["run_accession"],
                {"row": inventory_row, "sources": set()},
            )["sources"].add("manifest.experiment_alias")

        experiment_accession = metadata_row.get("experiment_accession", "")
        if experiment_accession:
            for inventory_row in inventory_by_parsed_alias.get(experiment_accession, []):
                candidate_inventory.setdefault(
                    inventory_row["run_accession"],
                    {"row": inventory_row, "sources": set()},
                )["sources"].add("manifest.experiment_accession")

        if not candidate_inventory:
            _append_unresolved_row(
                unresolved_rows,
                metadata_row,
                unresolved_reason="no_local_run_match",
            )
            continue

        for run_accession in sorted(candidate_inventory):
            candidate = candidate_inventory[run_accession]
            resolution_source = ";".join(sorted(candidate["sources"]))
            _append_resolved_row(
                resolved_rows,
                metadata_row,
                run_accession=run_accession,
                resolution_source=resolution_source,
                inventory_row=candidate["row"],
            )

    resolved = pd.DataFrame(resolved_rows, columns=RESOLVED_COLUMNS, dtype=str)
    unresolved = pd.DataFrame(unresolved_rows, columns=UNRESOLVED_COLUMNS, dtype=str)
    unresolved_reason_counts = Counter(unresolved["unresolved_reason"]) if not unresolved.empty else Counter()

    resolved_run_set = set(resolved["run_accession"]) if not resolved.empty else set()
    manifest_run_set = set(inventory["run_accession"]) if not inventory.empty else set()
    manifest_backmatched_runs = len(
        {
            run_accession
            for run_accession, status in zip(
                resolved["run_accession"],
                resolved["manifest_match_status"],
            )
            if status == "manifest_present"
        }
    ) if not resolved.empty else 0
    manifest_unmatched_runs = len(manifest_run_set - resolved_run_set)

    return ResolutionResult(
        metadata_rows_in=len(metadata),
        resolved=resolved,
        unresolved=unresolved,
        manifest_inventory=inventory,
        metadata_read_mode_label=metadata_result.read_mode_label,
        unresolved_reason_counts=unresolved_reason_counts,
        manifest_backmatched_runs=manifest_backmatched_runs,
        manifest_unmatched_runs=manifest_unmatched_runs,
    )
