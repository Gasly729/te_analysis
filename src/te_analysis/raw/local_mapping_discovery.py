"""Discover local offline experiment-to-run mapping evidence."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Iterable, Sequence

import pandas as pd


RUN_ACCESSION_PATTERN = re.compile(r"^(SRR\d+|ERR\d+|DRR\d+)$")
EXPERIMENT_ACCESSION_PATTERN = re.compile(r"^(SRX\d+|ERX\d+|DRX\d+)$")
MAPPING_COLUMNS = (
    "experiment_accession",
    "run_accession",
    "run_accession_prefix",
    "mapping_source",
    "mapping_source_path",
    "mapping_confidence",
    "notes",
)


@dataclass(frozen=True)
class LocalMappingSourceSpec:
    """One candidate local file that may contain experiment/run pairs."""

    source_name: str
    path: Path
    experiment_column: str | None
    run_column: str | None
    note: str


@dataclass(frozen=True)
class LocalMappingDiscoveryResult:
    """Normalized local experiment/run mappings plus source accounting."""

    mapping_frame: pd.DataFrame
    sources_found: tuple[str, ...]
    sources_used: tuple[str, ...]
    skipped_sources: tuple[str, ...]


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def default_local_mapping_source_specs() -> tuple[LocalMappingSourceSpec, ...]:
    """Return the server-local candidate sources audited for PR -1c phase 2."""

    project_root = _repo_root().parent / "project"
    return (
        LocalMappingSourceSpec(
            source_name="external.srx_to_srr_mapping_csv",
            path=project_root / "data/external/srx_to_srr_mapping.csv",
            experiment_column="srx",
            run_column="Run",
            note="schema: Run/srx",
        ),
        LocalMappingSourceSpec(
            source_name="external.sradownloader_input",
            path=project_root / "data/external/sradownloader_input.txt",
            experiment_column="srx",
            run_column="Run",
            note="schema: Run/srx",
        ),
        LocalMappingSourceSpec(
            source_name="processed.srx_to_srr_mapping_missing",
            path=project_root / "data/processed/srx_to_srr_mapping_missing.csv",
            experiment_column="SRX",
            run_column="SRR",
            note="schema: SRX/SRR",
        ),
        LocalMappingSourceSpec(
            source_name="processed.sradownloader_input_runtable",
            path=project_root / "data/processed/sradownloader_input_runtable.csv",
            experiment_column=None,
            run_column="Run",
            note="unsupported: no experiment accession column",
        ),
    )


def _normalize_accession(value: str) -> str:
    return str(value).strip().upper()


def _read_candidate_frame(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path, dtype=str, keep_default_na=False)
    for column in frame.columns:
        frame[column] = frame[column].map(lambda value: str(value).strip())
    return frame


def _normalize_source_rows(spec: LocalMappingSourceSpec, frame: pd.DataFrame) -> list[dict[str, str]]:
    if spec.experiment_column is None or spec.run_column is None:
        return []
    if spec.experiment_column not in frame.columns or spec.run_column not in frame.columns:
        return []

    normalized_rows: list[dict[str, str]] = []
    for _, row in frame.iterrows():
        experiment_accession = _normalize_accession(row.get(spec.experiment_column, ""))
        run_accession = _normalize_accession(row.get(spec.run_column, ""))
        if not EXPERIMENT_ACCESSION_PATTERN.match(experiment_accession):
            continue
        if not RUN_ACCESSION_PATTERN.match(run_accession):
            continue
        normalized_rows.append(
            {
                "experiment_accession": experiment_accession,
                "run_accession": run_accession,
                "run_accession_prefix": run_accession[:3],
                "mapping_source": spec.source_name,
                "mapping_source_path": str(spec.path),
                "mapping_confidence": "high",
                "notes": spec.note,
            }
        )
    return normalized_rows


def _collapse_unique(values: Iterable[str]) -> str:
    unique_values = sorted({value for value in values if value})
    return ";".join(unique_values)


def _deduplicate_pairs(rows: Sequence[dict[str, str]]) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame(columns=MAPPING_COLUMNS)
    frame = pd.DataFrame(rows, dtype=str)
    grouped_rows: list[dict[str, str]] = []
    for (experiment_accession, run_accession), group in frame.groupby(
        ["experiment_accession", "run_accession"],
        sort=True,
    ):
        grouped_rows.append(
            {
                "experiment_accession": experiment_accession,
                "run_accession": run_accession,
                "run_accession_prefix": run_accession[:3],
                "mapping_source": _collapse_unique(group["mapping_source"]),
                "mapping_source_path": _collapse_unique(group["mapping_source_path"]),
                "mapping_confidence": _collapse_unique(group["mapping_confidence"]),
                "notes": _collapse_unique(group["notes"]),
            }
        )
    return pd.DataFrame(grouped_rows, columns=MAPPING_COLUMNS, dtype=str)


def discover_local_experiment_run_mappings(
    source_specs: Sequence[LocalMappingSourceSpec] | None = None,
) -> LocalMappingDiscoveryResult:
    """Harvest local-only experiment/run mappings from audited server-local artifacts."""

    specs = tuple(source_specs or default_local_mapping_source_specs())
    discovered_rows: list[dict[str, str]] = []
    sources_found: list[str] = []
    sources_used: list[str] = []
    skipped_sources: list[str] = []

    for spec in specs:
        if not spec.path.exists():
            continue
        sources_found.append(f"{spec.source_name}: {spec.path}")
        frame = _read_candidate_frame(spec.path)
        normalized_rows = _normalize_source_rows(spec, frame)
        if normalized_rows:
            discovered_rows.extend(normalized_rows)
            sources_used.append(f"{spec.source_name}: {spec.path}")
        else:
            skipped_sources.append(f"{spec.source_name}: {spec.path} ({spec.note})")

    return LocalMappingDiscoveryResult(
        mapping_frame=_deduplicate_pairs(discovered_rows),
        sources_found=tuple(sources_found),
        sources_used=tuple(sources_used),
        skipped_sources=tuple(skipped_sources),
    )
