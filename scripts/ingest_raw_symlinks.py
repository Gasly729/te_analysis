#!/usr/bin/env python
from __future__ import annotations

import argparse
import csv
import hashlib
import os
import re
import subprocess
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import pandas as pd
from pandas.errors import ParserError


DEFAULT_SOURCES = (
    ("batch1", Path("/home/xrx/raw_data/TE_ribo-seq/sradownloader_output")),
    ("batch2", Path("/home/xrx/raw_data/output2")),
)
DEFAULT_TARGET_ROOT = Path("/home/xrx/my_project/te_analysis/data/raw")
DEFAULT_METADATA_PATH = DEFAULT_TARGET_ROOT / "metadata.csv"
ALIAS_FILE = Path(__file__).with_name("organism_alias_min.yaml")
FASTQ_SUFFIXES = (".fastq.gz", ".fastq")
VALID_SEQ_TYPES = {"Ribo-Seq", "RNA-Seq"}
VALID_LAYOUTS = {"SINGLE", "PAIRED"}
MANIFEST_COLUMNS = (
    "gsm",
    "gse",
    "srr",
    "mate",
    "organism_canonical",
    "organism_raw",
    "seq_type",
    "layout",
    "source_batch",
    "source_path",
    "real_target",
    "linked_path",
    "size_bytes",
    "mtime_iso",
    "status",
    "skip_reason",
    "warning",
)
CONFLICT_COLUMNS = (
    "srr",
    "mate",
    "batch1_path",
    "batch2_path",
    "batch1_size",
    "batch2_size",
    "batch1_mtime",
    "batch2_mtime",
    "chosen_batch",
)
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
RUN_ID_PATTERN = re.compile(r"(SRR\d+|ERR\d+|DRR\d+)")
ALIAS_PATTERN = re.compile(r"(GSM\d+|SRX\d+|ERX\d+|DRX\d+)")
MATE_PATTERN = re.compile(r"_([12])\.fastq(?:\.gz)?$")
STRICT_HYBRID_PATTERN = re.compile(r"^Saccharomyces_[A-Za-z]+_x_[A-Za-z_]+$")
RAW_HYBRID_PATTERNS = (
    re.compile(r"_x_", re.IGNORECASE),
    re.compile(r"\s+x\s", re.IGNORECASE),
    re.compile(r"\s*\*\s*"),
)
FORCE_PREFER_BATCH2_RUNS: set[str] = set()
FORCED_SIZE_MISMATCH_KEYS: set[tuple[str, str]] = set()


class IngestError(RuntimeError):
    """Raised when the ingest contract is violated."""


@dataclass(frozen=True)
class SourceFile:
    source_batch: str
    source_root: Path
    source_path: Path
    real_target: Path
    basename: str
    run_id: str
    mate: str
    parsed_alias: str
    size_bytes: int
    mtime_iso: str


@dataclass(frozen=True)
class MetadataEntry:
    experiment_alias: str
    gse: str
    organism_raw: str
    seq_type_raw: str
    layout: str
    run_ids: tuple[str, ...]
    experiment_accession: str


@dataclass(frozen=True)
class ManifestRow:
    gsm: str
    gse: str
    srr: str
    mate: str
    organism_canonical: str
    organism_raw: str
    seq_type: str
    layout: str
    source_batch: str
    source_path: str
    real_target: str
    linked_path: str
    size_bytes: str
    mtime_iso: str
    status: str
    skip_reason: str
    warning: str

    def as_dict(self) -> dict[str, str]:
        return {
            "gsm": self.gsm,
            "gse": self.gse,
            "srr": self.srr,
            "mate": self.mate,
            "organism_canonical": self.organism_canonical,
            "organism_raw": self.organism_raw,
            "seq_type": self.seq_type,
            "layout": self.layout,
            "source_batch": self.source_batch,
            "source_path": self.source_path,
            "real_target": self.real_target,
            "linked_path": self.linked_path,
            "size_bytes": self.size_bytes,
            "mtime_iso": self.mtime_iso,
            "status": self.status,
            "skip_reason": self.skip_reason,
            "warning": self.warning,
        }


@dataclass(frozen=True)
class ConflictRow:
    srr: str
    mate: str
    batch1_path: str
    batch2_path: str
    batch1_size: str
    batch2_size: str
    batch1_mtime: str
    batch2_mtime: str
    chosen_batch: str

    def as_dict(self) -> dict[str, str]:
        return {
            "srr": self.srr,
            "mate": self.mate,
            "batch1_path": self.batch1_path,
            "batch2_path": self.batch2_path,
            "batch1_size": self.batch1_size,
            "batch2_size": self.batch2_size,
            "batch1_mtime": self.batch1_mtime,
            "batch2_mtime": self.batch2_mtime,
            "chosen_batch": self.chosen_batch,
        }


@dataclass(frozen=True)
class SourceProbeSummary:
    source_batch: str
    source_root: Path
    total_files: int
    total_size_bytes: int
    depth_counts: dict[int, int]
    run_id_hit_count: int
    unmatched_examples: tuple[str, ...]


@dataclass(frozen=True)
class MetadataBundle:
    entries: tuple[MetadataEntry, ...]
    by_run_id: dict[str, MetadataEntry]
    by_alias: dict[str, MetadataEntry]
    by_accession: dict[str, MetadataEntry]
    organism_alias_map: dict[str, str]
    unmapped_organisms: tuple[str, ...]
    read_mode_label: str
    has_run_alias_column: bool


@dataclass(frozen=True)
class IngestPlan:
    rows: tuple[ManifestRow, ...]
    conflict_rows: tuple[ConflictRow, ...]
    probe_summaries: tuple[SourceProbeSummary, ...]
    target_root: Path
    metadata_path: Path
    source_roots: dict[str, Path]
    metadata_bundle: MetadataBundle
    selected_source_files: tuple[SourceFile, ...]

    @property
    def matched_rows(self) -> tuple[ManifestRow, ...]:
        return tuple(row for row in self.rows if row.status == "matched")


def _format_iso8601(timestamp: float) -> str:
    return datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat()


def _matches_fastq_suffix(path: Path) -> bool:
    return any(path.name.endswith(suffix) for suffix in FASTQ_SUFFIXES)


def _parse_run_id(filename: str) -> str:
    match = RUN_ID_PATTERN.search(filename)
    if match is None:
        raise IngestError(f"Could not parse run id from FASTQ name: {filename}")
    return match.group(1)


def _parse_mate(filename: str) -> str:
    match = MATE_PATTERN.search(filename)
    if match is None:
        return ""
    return match.group(1)


def _parse_alias(filename: str) -> str:
    match = ALIAS_PATTERN.search(filename)
    if match is None:
        return ""
    return match.group(1)


def _is_binomial_name(value: str) -> bool:
    parts = value.split("_")
    if len(parts) != 2:
        return False
    genus, species = parts
    return genus[:1].isupper() and genus[1:].islower() and species.islower()


def is_hybrid_species(organism_canonical: str) -> bool:
    if STRICT_HYBRID_PATTERN.match(organism_canonical):
        return True
    if "_x_" not in organism_canonical:
        return False
    left, right = organism_canonical.split("_x_", 1)
    return _is_binomial_name(left) and _is_binomial_name(right)


def is_hybrid_organism_raw(organism_raw: str) -> bool:
    normalized = organism_raw.strip()
    if not normalized:
        return False
    return any(pattern.search(normalized) for pattern in RAW_HYBRID_PATTERNS)


def configure_force_prefer_batch2_runs(raw_value: str) -> None:
    global FORCE_PREFER_BATCH2_RUNS
    tokens = [token.strip() for token in raw_value.split(",")]
    FORCE_PREFER_BATCH2_RUNS = {token for token in tokens if token}


def _load_alias_table(path: Path) -> dict[str, str]:
    if not path.exists():
        raise IngestError(f"organism alias file does not exist: {path}")
    alias_map: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if ":" not in stripped:
            raise IngestError(f"Invalid organism alias mapping line: {line!r}")
        raw_key, raw_value = stripped.split(":", 1)
        key = raw_key.strip().strip("'\"")
        value = raw_value.strip().strip("'\"")
        if not key or not value:
            raise IngestError(f"Invalid organism alias mapping line: {line!r}")
        alias_map[key.casefold()] = value
    return alias_map


def scan_source_root(source_batch: str, source_root: Path) -> tuple[tuple[SourceFile, ...], SourceProbeSummary]:
    if not source_root.exists():
        raise IngestError(f"source root does not exist: {source_root}")

    files: list[SourceFile] = []
    total_fastq_files = 0
    total_size_bytes = 0
    depth_counts: Counter[int] = Counter()
    run_id_hit_count = 0
    unmatched_examples: list[str] = []

    for path in sorted(source_root.rglob("*")):
        if not path.is_file() or not _matches_fastq_suffix(path):
            continue
        total_fastq_files += 1
        relative = path.relative_to(source_root)
        depth_counts[len(relative.parts)] += 1
        total_size_bytes += path.stat().st_size
        run_match = RUN_ID_PATTERN.search(path.name)
        if run_match is None:
            if len(unmatched_examples) < 20:
                unmatched_examples.append(path.name)
            continue
        run_id_hit_count += 1
        real_target = Path(os.path.realpath(path))
        files.append(
            SourceFile(
                source_batch=source_batch,
                source_root=source_root,
                source_path=path,
                real_target=real_target,
                basename=path.name,
                run_id=run_match.group(1),
                mate=_parse_mate(path.name),
                parsed_alias=_parse_alias(path.name),
                size_bytes=real_target.stat().st_size,
                mtime_iso=_format_iso8601(real_target.stat().st_mtime),
            )
        )

    summary = SourceProbeSummary(
        source_batch=source_batch,
        source_root=source_root,
        total_files=total_fastq_files,
        total_size_bytes=total_size_bytes,
        depth_counts=dict(sorted(depth_counts.items())),
        run_id_hit_count=run_id_hit_count,
        unmatched_examples=tuple(unmatched_examples),
    )
    return tuple(files), summary


def _load_metadata_frame(metadata_path: Path) -> tuple[pd.DataFrame, str]:
    last_columns: list[str] | None = None
    for read_mode in READ_MODES:
        try:
            frame = pd.read_csv(metadata_path, **read_mode)
        except ParserError:
            continue
        frame.columns = [str(column).strip() for column in frame.columns]
        last_columns = list(frame.columns)
        if all(column in frame.columns for column in CORE_METADATA_COLUMNS):
            label = ", ".join(f"{key}={value}" for key, value in read_mode.items())
            return frame, label
    raise IngestError(
        "metadata file is missing required columns after trying supported read modes: "
        + ", ".join(CORE_METADATA_COLUMNS)
        + f" ({metadata_path}, last_columns={last_columns})"
    )


def _split_run_aliases(value: object) -> tuple[str, ...]:
    if value is None:
        return ()
    text = str(value).strip()
    if not text or text.lower() == "nan":
        return ()
    tokens = [token.strip() for token in text.split(";")]
    return tuple(token for token in tokens if token)


def _normalize_layout(raw_value: object) -> str:
    text = str(raw_value or "").strip().upper()
    if text in VALID_LAYOUTS:
        return text
    raise IngestError(f"Unsupported library_layout value: {raw_value!r}")


def _normalize_seq_type(raw_value: str) -> str:
    normalized = raw_value.casefold()
    if "ribo" in normalized:
        return "Ribo-Seq"
    if "rna" in normalized:
        return "RNA-Seq"
    return ""


def _clean_metadata_value(value: object) -> str:
    if pd.isna(value):
        return ""
    text = str(value).strip()
    if text.lower() == "nan":
        return ""
    return text


def load_metadata_bundle(metadata_path: Path, alias_table_path: Path) -> MetadataBundle:
    frame, read_mode_label = _load_metadata_frame(metadata_path)
    has_run_alias_column = "run_alias" in frame.columns
    alias_map = _load_alias_table(alias_table_path)
    entries: list[MetadataEntry] = []
    by_run_id: dict[str, MetadataEntry] = {}
    by_alias: dict[str, MetadataEntry] = {}
    by_accession: dict[str, MetadataEntry] = {}
    unmapped_organisms = {
        organism
        for organism in sorted(frame["organism"].fillna("").astype(str).unique())
        if organism.strip() and organism.strip().casefold() not in alias_map
    }

    for _, row in frame.iterrows():
        experiment_alias = _clean_metadata_value(row["experiment_alias"])
        if not experiment_alias:
            continue
        organism_raw = _clean_metadata_value(row["organism"])
        corrected_type = _clean_metadata_value(row.get("corrected_type", ""))
        library_strategy = _clean_metadata_value(row["library_strategy"])
        seq_type_raw = corrected_type or library_strategy
        entry = MetadataEntry(
            experiment_alias=experiment_alias,
            gse=_clean_metadata_value(row["study_name"]),
            organism_raw=organism_raw,
            seq_type_raw=seq_type_raw,
            layout=_normalize_layout(row["library_layout"]),
            run_ids=_split_run_aliases(row.get("run_alias")) if has_run_alias_column else (),
            experiment_accession=_clean_metadata_value(row.get("experiment_accession", "")),
        )
        entries.append(entry)

        if experiment_alias in by_alias and by_alias[experiment_alias] != entry:
            raise IngestError(f"Duplicate experiment_alias with conflicting metadata: {experiment_alias}")
        by_alias[experiment_alias] = entry

        if entry.experiment_accession:
            if entry.experiment_accession in by_accession and by_accession[entry.experiment_accession] != entry:
                raise IngestError(
                    f"Duplicate experiment_accession with conflicting metadata: {entry.experiment_accession}"
                )
            by_accession[entry.experiment_accession] = entry

        for run_id in entry.run_ids:
            existing = by_run_id.get(run_id)
            if existing is not None and existing != entry:
                raise IngestError(f"run_alias maps to multiple metadata rows: {run_id}")
            by_run_id[run_id] = entry

    return MetadataBundle(
        entries=tuple(entries),
        by_run_id=by_run_id,
        by_alias=by_alias,
        by_accession=by_accession,
        organism_alias_map=alias_map,
        unmapped_organisms=tuple(sorted(unmapped_organisms)),
        read_mode_label=read_mode_label,
        has_run_alias_column=has_run_alias_column,
    )


def _conflict_row_from_pair(key: tuple[str, str], files: list[SourceFile], chosen_batch: str) -> ConflictRow:
    by_batch = {source_file.source_batch: source_file for source_file in files}
    batch1 = by_batch.get("batch1")
    batch2 = by_batch.get("batch2")
    return ConflictRow(
        srr=key[0],
        mate=key[1],
        batch1_path=str(batch1.source_path) if batch1 else "",
        batch2_path=str(batch2.source_path) if batch2 else "",
        batch1_size=str(batch1.size_bytes) if batch1 else "",
        batch2_size=str(batch2.size_bytes) if batch2 else "",
        batch1_mtime=batch1.mtime_iso if batch1 else "",
        batch2_mtime=batch2.mtime_iso if batch2 else "",
        chosen_batch=chosen_batch,
    )


def resolve_source_conflicts(
    source_files: Iterable[SourceFile],
    *,
    conflict_policy: str,
) -> tuple[tuple[SourceFile, ...], tuple[ConflictRow, ...], dict[tuple[str, str], str]]:
    global FORCED_SIZE_MISMATCH_KEYS
    FORCED_SIZE_MISMATCH_KEYS = set()
    grouped: dict[tuple[str, str], list[SourceFile]] = defaultdict(list)
    for source_file in source_files:
        grouped[(source_file.run_id, source_file.mate)].append(source_file)

    selected: list[SourceFile] = []
    conflict_rows: list[ConflictRow] = []
    size_mismatch_keys: dict[tuple[str, str], str] = {}

    for key in sorted(grouped):
        files = sorted(grouped[key], key=lambda item: (item.source_batch, item.source_path))
        by_batch: dict[str, list[SourceFile]] = defaultdict(list)
        for source_file in files:
            by_batch[source_file.source_batch].append(source_file)
        for batch_name, batch_files in by_batch.items():
            if len(batch_files) > 1:
                raise IngestError(f"Multiple FASTQ files share the same run/mate within {batch_name}: {key}")

        if len(files) == 1:
            selected.append(files[0])
            continue

        size_values = {source_file.size_bytes for source_file in files}
        if len(size_values) != 1:
            if key[0] in FORCE_PREFER_BATCH2_RUNS and "batch2" in by_batch:
                selected.append(by_batch["batch2"][0])
                conflict_rows.append(_conflict_row_from_pair(key, files, chosen_batch="batch2"))
                FORCED_SIZE_MISMATCH_KEYS.add(key)
                continue
            conflict_rows.append(_conflict_row_from_pair(key, files, chosen_batch=""))
            size_mismatch_keys[key] = "size_mismatch_between_batches"
            continue

        if conflict_policy == "fail":
            raise IngestError(f"Conflict detected for run/mate {key} and conflict_policy=fail")

        chosen_batch = "batch2" if conflict_policy == "prefer-batch2" else "batch1"
        selected.append(by_batch[chosen_batch][0])
        conflict_rows.append(_conflict_row_from_pair(key, files, chosen_batch=chosen_batch))

    return tuple(selected), tuple(conflict_rows), size_mismatch_keys


def _canonicalize_organism(organism_raw: str, alias_map: dict[str, str]) -> str:
    return alias_map.get(organism_raw.strip().casefold(), "")


def _warning_for_gse(gse: str) -> tuple[str, str]:
    if gse:
        return gse, ""
    return "_ungrouped", "no_gse_assignment"


def _manifest_row_for_source_file(
    source_file: SourceFile,
    *,
    metadata: MetadataEntry | None,
    organism_canonical: str,
    seq_type: str,
    gse: str,
    linked_path: str,
    status: str,
    skip_reason: str,
    warning: str,
) -> ManifestRow:
    return ManifestRow(
        gsm=metadata.experiment_alias if metadata else source_file.parsed_alias,
        gse=metadata.gse if metadata else "",
        srr=source_file.run_id,
        mate=source_file.mate,
        organism_canonical=organism_canonical,
        organism_raw=metadata.organism_raw if metadata else "",
        seq_type=seq_type,
        layout=metadata.layout if metadata else "",
        source_batch=source_file.source_batch,
        source_path=str(source_file.source_path),
        real_target=str(source_file.real_target),
        linked_path=linked_path,
        size_bytes=str(source_file.size_bytes),
        mtime_iso=source_file.mtime_iso,
        status=status,
        skip_reason=skip_reason,
        warning=warning,
    )


def _orphan_metadata_rows(
    bundle: MetadataBundle,
    matched_aliases: set[str],
) -> tuple[ManifestRow, ...]:
    rows: list[ManifestRow] = []
    for metadata in bundle.entries:
        if metadata.experiment_alias in matched_aliases:
            continue
        organism_canonical = _canonicalize_organism(metadata.organism_raw, bundle.organism_alias_map)
        seq_type = _normalize_seq_type(metadata.seq_type_raw)
        run_ids = metadata.run_ids or ("",)
        for run_id in run_ids:
            rows.append(
                ManifestRow(
                    gsm=metadata.experiment_alias,
                    gse=metadata.gse,
                    srr=run_id,
                    mate="",
                    organism_canonical=organism_canonical,
                    organism_raw=metadata.organism_raw,
                    seq_type=seq_type,
                    layout=metadata.layout,
                    source_batch="",
                    source_path="",
                    real_target="",
                    linked_path="",
                    size_bytes="",
                    mtime_iso="",
                    status="skipped",
                    skip_reason="orphan_metadata",
                    warning="",
                )
            )
    return tuple(rows)


def _resolve_metadata_for_file(source_file: SourceFile, bundle: MetadataBundle) -> MetadataEntry | None:
    by_run_id = bundle.by_run_id.get(source_file.run_id)
    if by_run_id is not None:
        return by_run_id
    if source_file.parsed_alias:
        by_alias = bundle.by_alias.get(source_file.parsed_alias)
        if by_alias is not None:
            return by_alias
        by_accession = bundle.by_accession.get(source_file.parsed_alias)
        if by_accession is not None:
            return by_accession
    return None


def build_ingest_plan(
    *,
    source_roots: dict[str, Path],
    target_root: Path,
    metadata_path: Path,
    alias_table_path: Path,
    conflict_policy: str,
) -> IngestPlan:
    all_source_files: list[SourceFile] = []
    probe_summaries: list[SourceProbeSummary] = []
    for source_batch, source_root in source_roots.items():
        scanned_files, summary = scan_source_root(source_batch, source_root)
        all_source_files.extend(scanned_files)
        probe_summaries.append(summary)

    metadata_bundle = load_metadata_bundle(metadata_path, alias_table_path)
    selected_files, conflict_rows, size_mismatch_keys = resolve_source_conflicts(
        all_source_files,
        conflict_policy=conflict_policy,
    )

    selected_by_key = {(source_file.run_id, source_file.mate): source_file for source_file in selected_files}
    rows: list[ManifestRow] = []
    matched_aliases: set[str] = set()
    grouped_by_run: dict[str, list[tuple[SourceFile, MetadataEntry]]] = defaultdict(list)

    for source_file in selected_files:
        metadata = _resolve_metadata_for_file(source_file, metadata_bundle)
        if metadata is None:
            rows.append(
                _manifest_row_for_source_file(
                    source_file,
                    metadata=None,
                    organism_canonical="",
                    seq_type="",
                    gse="",
                    linked_path="",
                    status="skipped",
                    skip_reason="srr_not_in_metadata",
                    warning="",
                )
            )
            continue

        if is_hybrid_organism_raw(metadata.organism_raw):
            rows.append(
                _manifest_row_for_source_file(
                    source_file,
                    metadata=metadata,
                    organism_canonical="",
                    seq_type="",
                    gse="",
                    linked_path="",
                    status="skipped",
                    skip_reason="hybrid_species_phase2",
                    warning="",
                )
            )
            continue

        organism_canonical = _canonicalize_organism(metadata.organism_raw, metadata_bundle.organism_alias_map)
        if not organism_canonical:
            rows.append(
                _manifest_row_for_source_file(
                    source_file,
                    metadata=metadata,
                    organism_canonical="",
                    seq_type="",
                    gse="",
                    linked_path="",
                    status="skipped",
                    skip_reason="organism_unmapped",
                    warning="",
                )
            )
            continue

        if is_hybrid_species(organism_canonical):
            rows.append(
                _manifest_row_for_source_file(
                    source_file,
                    metadata=metadata,
                    organism_canonical=organism_canonical,
                    seq_type="",
                    gse="",
                    linked_path="",
                    status="skipped",
                    skip_reason="hybrid_species_phase2",
                    warning="",
                )
            )
            continue

        seq_type = _normalize_seq_type(metadata.seq_type_raw)
        if not seq_type:
            rows.append(
                _manifest_row_for_source_file(
                    source_file,
                    metadata=metadata,
                    organism_canonical=organism_canonical,
                    seq_type="",
                    gse="",
                    linked_path="",
                    status="skipped",
                    skip_reason="unknown_seq_type",
                    warning="",
                )
            )
            continue

        grouped_by_run[source_file.run_id].append((source_file, metadata))

    for key, reason in size_mismatch_keys.items():
        run_id, mate = key
        for source_file in sorted(
            [item for item in all_source_files if item.run_id == run_id and item.mate == mate],
            key=lambda item: (item.source_batch, item.source_path),
        ):
            rows.append(
                _manifest_row_for_source_file(
                    source_file,
                    metadata=_resolve_metadata_for_file(source_file, metadata_bundle),
                    organism_canonical="",
                    seq_type="",
                    gse="",
                    linked_path="",
                    status="skipped",
                    skip_reason=reason,
                    warning="",
                )
            )

    for run_id in sorted(grouped_by_run):
        items = grouped_by_run[run_id]
        metadata = items[0][1]
        organism_canonical = _canonicalize_organism(metadata.organism_raw, metadata_bundle.organism_alias_map)
        seq_type = _normalize_seq_type(metadata.seq_type_raw)
        gse_dir, gse_warning = _warning_for_gse(metadata.gse)
        by_mate = {source_file.mate: source_file for source_file, _ in items}

        if metadata.layout == "PAIRED":
            if "1" not in by_mate or "2" not in by_mate:
                for source_file, _ in items:
                    rows.append(
                        _manifest_row_for_source_file(
                            source_file,
                            metadata=metadata,
                            organism_canonical=organism_canonical,
                            seq_type=seq_type,
                            gse=gse_dir,
                            linked_path="",
                            status="skipped",
                            skip_reason="paired_missing_mate",
                            warning="",
                        )
                    )
                continue
            candidate_files = [by_mate["1"], by_mate["2"]]
            warning = gse_warning
        else:
            if "" in by_mate:
                candidate_files = [by_mate[""]]
                warning = gse_warning
            elif "1" in by_mate:
                candidate_files = [by_mate["1"]]
                warning = ";".join(filter(None, (gse_warning, "single_but_mate_1_only")))
            else:
                first_file = sorted(items, key=lambda item: (item[0].mate, item[0].source_path))[0][0]
                candidate_files = [first_file]
                warning = ";".join(filter(None, (gse_warning, "single_but_mate_1_only")))

        for source_file in candidate_files:
            suffix = f"_{source_file.mate}" if source_file.mate else ""
            normalized_name = f"{metadata.experiment_alias}_{seq_type}_{source_file.run_id}{suffix}.fastq.gz"
            linked_path = str(target_root / organism_canonical / gse_dir / normalized_name)
            forced_warning = ""
            if (source_file.run_id, source_file.mate) in FORCED_SIZE_MISMATCH_KEYS:
                forced_warning = "forced_prefer_batch2_size_mismatch"
            rows.append(
                _manifest_row_for_source_file(
                    source_file,
                    metadata=metadata,
                    organism_canonical=organism_canonical,
                    seq_type=seq_type,
                    gse=gse_dir,
                    linked_path=linked_path,
                    status="matched",
                    skip_reason="",
                    warning=";".join(filter(None, (warning, forced_warning))),
                )
            )
            matched_aliases.add(metadata.experiment_alias)

    rows.extend(_orphan_metadata_rows(metadata_bundle, matched_aliases))

    sorted_rows = tuple(
        sorted(
            rows,
            key=lambda row: (
                row.status,
                row.skip_reason,
                row.organism_canonical,
                row.gsm,
                row.srr,
                row.mate,
                row.source_batch,
            ),
        )
    )
    return IngestPlan(
        rows=sorted_rows,
        conflict_rows=tuple(sorted(conflict_rows, key=lambda row: (row.srr, row.mate))),
        probe_summaries=tuple(probe_summaries),
        target_root=target_root,
        metadata_path=metadata_path,
        source_roots=source_roots,
        metadata_bundle=metadata_bundle,
        selected_source_files=tuple(sorted(selected_files, key=lambda item: (item.run_id, item.mate, item.source_batch))),
    )


def validate_existing_links(plan: IngestPlan) -> None:
    for row in plan.matched_rows:
        destination = Path(row.linked_path)
        expected_target = Path(row.real_target)
        if not destination.exists() and not destination.is_symlink():
            continue
        if destination.is_symlink():
            existing_target = Path(os.path.realpath(destination))
            if existing_target != expected_target:
                raise IngestError(
                    f"Conflicting symlink target for {destination}: {existing_target} != {expected_target}"
                )
            continue
        raise IngestError(f"Destination exists as a regular file and will not be overwritten: {destination}")


def apply_symlink_plan(plan: IngestPlan) -> None:
    validate_existing_links(plan)
    for row in plan.matched_rows:
        destination = Path(row.linked_path)
        if destination.is_symlink():
            continue
        destination.parent.mkdir(parents=True, exist_ok=True)
        os.symlink(Path(row.real_target), destination)


def _render_tsv(columns: tuple[str, ...], rows: Iterable[dict[str, str]]) -> str:
    lines = ["\t".join(columns)]
    for row in rows:
        lines.append("\t".join(row[column] for column in columns))
    return "\n".join(lines) + "\n"


def render_manifest_tsv(rows: Iterable[ManifestRow]) -> str:
    return _render_tsv(MANIFEST_COLUMNS, (row.as_dict() for row in rows))


def render_conflict_tsv(rows: Iterable[ConflictRow]) -> str:
    return _render_tsv(CONFLICT_COLUMNS, (row.as_dict() for row in rows))


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


def _get_git_commit() -> str:
    completed = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        return "unknown"
    return completed.stdout.strip() or "unknown"


def _human_size(size_bytes: int) -> str:
    units = ("B", "KB", "MB", "GB", "TB")
    value = float(size_bytes)
    for unit in units:
        if value < 1024 or unit == units[-1]:
            return f"{value:.1f}{unit}"
        value /= 1024
    return f"{size_bytes}B"


def render_ingest_report(plan: IngestPlan) -> str:
    matched_rows = [row for row in plan.rows if row.status == "matched"]
    skipped_rows = [row for row in plan.rows if row.status == "skipped"]
    skip_counts = Counter(row.skip_reason for row in skipped_rows)
    seq_type_counts = Counter(row.seq_type for row in matched_rows if row.seq_type)
    by_species_files = Counter(row.organism_canonical for row in matched_rows)
    by_species_gsms: dict[str, set[str]] = defaultdict(set)
    by_species_gses: dict[str, set[str]] = defaultdict(set)
    for row in matched_rows:
        by_species_gsms[row.organism_canonical].add(row.gsm)
        by_species_gses[row.organism_canonical].add(row.gse)

    lines = [
        "# Raw Symlink Ingest Report",
        "",
        f"- generated_at: {datetime.now(timezone.utc).isoformat()}",
        f"- git_commit: {_get_git_commit()}",
        f"- metadata_path: {plan.metadata_path}",
        f"- metadata_md5: {_compute_md5(plan.metadata_path)}",
        f"- metadata_read_mode: {plan.metadata_bundle.read_mode_label}",
        f"- metadata_has_run_alias_column: {plan.metadata_bundle.has_run_alias_column}",
        "",
        "## Source Probe Summary",
        "",
    ]
    for summary in plan.probe_summaries:
        lines.extend(
            [
                f"### {summary.source_batch}",
                "",
                f"- source_root: {summary.source_root}",
                f"- total_fastq_files: {summary.total_files}",
                f"- total_size_bytes: {summary.total_size_bytes}",
                f"- total_size_human: {_human_size(summary.total_size_bytes)}",
                f"- depth_distribution: {summary.depth_counts}",
                f"- run_id_hit_count: {summary.run_id_hit_count}",
                f"- run_id_hit_rate: {summary.run_id_hit_count}/{summary.total_files}",
                "- unmatched_filename_examples:",
            ]
        )
        if summary.unmatched_examples:
            lines.extend(f"  - {example}" for example in summary.unmatched_examples)
        else:
            lines.append("  - none")
        lines.append("")

    lines.extend(
        [
            "## Summary",
            "",
            f"- scanned_fastq_files: {sum(summary.total_files for summary in plan.probe_summaries)}",
            f"- matched_rows: {len(matched_rows)}",
            f"- skipped_rows: {len(skipped_rows)}",
            f"- conflicts_reported: {len(plan.conflict_rows)}",
        ]
    )
    for reason in (
        "orphan_metadata",
        "srr_not_in_metadata",
        "organism_unmapped",
        "hybrid_species_phase2",
        "paired_missing_mate",
        "unknown_seq_type",
        "size_mismatch_between_batches",
    ):
        lines.append(f"- {reason}: {skip_counts.get(reason, 0)}")

    lines.extend(["", "## UNMAPPED_ORGANISMS", ""])
    if plan.metadata_bundle.unmapped_organisms:
        lines.extend(f"- {organism}" for organism in plan.metadata_bundle.unmapped_organisms)
    else:
        lines.append("- none")

    lines.extend(
        [
            "",
            "## Source Conflicts",
            "",
            f"- conflict_manifest: {plan.target_root / '_source_conflict.tsv'}",
            f"- conflict_rows: {len(plan.conflict_rows)}",
        ]
    )

    lines.extend(["", "## By Species", "", "| organism | matched_fastq | matched_gsm | matched_gse |", "| --- | ---: | ---: | ---: |"])
    for organism in sorted(by_species_files):
        lines.append(
            "| {organism} | {fastq} | {gsm} | {gse} |".format(
                organism=organism,
                fastq=by_species_files[organism],
                gsm=len(by_species_gsms[organism]),
                gse=len(by_species_gses[organism]),
            )
        )

    lines.extend(["", "## By Seq Type", ""])
    for seq_type in sorted(seq_type_counts):
        lines.append(f"- {seq_type}: {seq_type_counts[seq_type]}")

    lines.extend(["", "## Top Skip Examples", ""])
    for reason in (
        "orphan_metadata",
        "srr_not_in_metadata",
        "organism_unmapped",
        "hybrid_species_phase2",
        "paired_missing_mate",
        "unknown_seq_type",
        "size_mismatch_between_batches",
    ):
        lines.append(f"### {reason}")
        examples = [row for row in skipped_rows if row.skip_reason == reason][:5]
        if examples:
            for example in examples:
                lines.append(
                    "- srr={srr} mate={mate} gsm={gsm} batch={batch} source={source}".format(
                        srr=example.srr or "-",
                        mate=example.mate or "-",
                        gsm=example.gsm or "-",
                        batch=example.source_batch or "-",
                        source=example.source_path or "-",
                    )
                )
        else:
            lines.append("- none")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def _backup_existing_manifest(manifest_path: Path) -> Path | None:
    if not manifest_path.exists():
        return None
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = manifest_path.with_name(f"{manifest_path.name}.bak.{timestamp}")
    os.replace(manifest_path, backup_path)
    return backup_path


def ensure_gitignore_rule(project_root: Path) -> None:
    gitignore_path = project_root / ".gitignore"
    required_rules = ("/data/raw/", "/data/scratch/", "/data/ribo/", "/data/qc/")
    if not gitignore_path.exists():
        gitignore_path.write_text("\n".join(required_rules) + "\n", encoding="utf-8")
        return
    content = gitignore_path.read_text(encoding="utf-8")
    missing = [rule for rule in required_rules if rule not in content.splitlines()]
    if not missing:
        return
    new_content = content.rstrip() + "\n"
    for rule in missing:
        new_content += f"{rule}\n"
    gitignore_path.write_text(new_content, encoding="utf-8")


def print_plan(plan: IngestPlan) -> None:
    matched_rows = [row for row in plan.rows if row.status == "matched"]
    skipped_rows = [row for row in plan.rows if row.status == "skipped"]
    skip_counts = Counter(row.skip_reason for row in skipped_rows)
    print("ingest_raw_symlinks: planned")
    print(f"metadata: {plan.metadata_path}")
    for summary in plan.probe_summaries:
        print(
            "source={batch} files={files} size={size} depth={depth} run_id_hits={hits}/{files}".format(
                batch=summary.source_batch,
                files=summary.total_files,
                size=summary.total_size_bytes,
                depth=summary.depth_counts,
                hits=summary.run_id_hit_count,
            )
        )
    print(f"matched_rows: {len(matched_rows)}")
    print(f"conflict_rows: {len(plan.conflict_rows)}")
    for reason in sorted(skip_counts):
        print(f"skip_{reason}: {skip_counts[reason]}")
    if plan.metadata_bundle.unmapped_organisms:
        print("unmapped_organisms:")
        for organism in plan.metadata_bundle.unmapped_organisms:
            print(f"  - {organism}")


def run_ingest(
    *,
    source_roots: dict[str, Path],
    target_root: Path,
    metadata_path: Path,
    alias_table_path: Path,
    conflict_policy: str,
    apply: bool,
) -> IngestPlan:
    plan = build_ingest_plan(
        source_roots=source_roots,
        target_root=target_root,
        metadata_path=metadata_path,
        alias_table_path=alias_table_path,
        conflict_policy=conflict_policy,
    )
    validate_existing_links(plan)
    print_plan(plan)
    if not apply:
        return plan

    ensure_gitignore_rule(Path(__file__).resolve().parents[1])
    apply_symlink_plan(plan)
    manifest_path = target_root / "_manifest.tsv"
    _backup_existing_manifest(manifest_path)
    _atomic_write_text(manifest_path, render_manifest_tsv(plan.rows))
    _atomic_write_text(target_root / "_source_conflict.tsv", render_conflict_tsv(plan.conflict_rows))
    _atomic_write_text(target_root / "_ingest_report.md", render_ingest_report(plan))
    return plan


def _parse_source_argument(value: str) -> tuple[str, Path]:
    if "=" not in value:
        raise argparse.ArgumentTypeError(f"Invalid source specification: {value!r}")
    batch_name, raw_path = value.split("=", 1)
    batch_name = batch_name.strip()
    if not batch_name:
        raise argparse.ArgumentTypeError(f"Invalid source specification: {value!r}")
    return batch_name, Path(raw_path).expanduser().resolve()


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Rebuild raw FASTQ symlinks from multiple sradownloader sources.")
    parser.add_argument(
        "--sources",
        nargs="+",
        default=[f"{name}={path}" for name, path in DEFAULT_SOURCES],
        help="Source roots in the form batch=path.",
    )
    parser.add_argument("--target-root", type=Path, default=DEFAULT_TARGET_ROOT)
    parser.add_argument("--metadata", type=Path, default=DEFAULT_METADATA_PATH)
    parser.add_argument("--conflict-policy", choices=("prefer-batch2", "prefer-batch1", "fail"), default="prefer-batch2")
    parser.add_argument("--alias-table", type=Path, default=ALIAS_FILE)
    parser.add_argument("--force-prefer-batch2", default="")
    parser.add_argument("--dry-run", action="store_true", default=True)
    parser.add_argument("--apply", action="store_true")
    return parser


def main() -> int:
    parser = build_argument_parser()
    args = parser.parse_args()
    configure_force_prefer_batch2_runs(args.force_prefer_batch2)
    source_roots = dict(_parse_source_argument(item) for item in args.sources)
    run_ingest(
        source_roots=source_roots,
        target_root=args.target_root.expanduser().resolve(),
        metadata_path=args.metadata.expanduser().resolve(),
        alias_table_path=args.alias_table.expanduser().resolve(),
        conflict_policy=args.conflict_policy,
        apply=args.apply,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
