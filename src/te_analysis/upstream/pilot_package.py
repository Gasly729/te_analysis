"""Build a local-only upstream pilot package from resolved FASTQ inputs."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os

import pandas as pd
import yaml

from te_analysis.raw.run_accession_resolution import read_experiment_metadata, read_manifest_frame


DEFAULT_REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_REFERENCE_YAML = DEFAULT_REPO_ROOT / "raw_motheds/snakescale/scripts/references.yaml"
DEFAULT_PROJECT_TEMPLATE = DEFAULT_REPO_ROOT / "raw_motheds/snakescale/project.yaml"
DEFAULT_PILOT_ROOT = DEFAULT_REPO_ROOT / "data/upstream/pilot"


@dataclass(frozen=True)
class PilotBuildResult:
    """Materialized pilot package plus validation flags."""

    candidates_path: Path
    selection_path: Path
    pilot_root: Path
    study_name: str
    organism: str
    study_manifest_path: Path
    fastq_manifest_path: Path
    staged_fastq_root: Path
    project_yaml_path: Path
    report_path: Path
    staged_fastq_count: int
    symlinks_ok: bool
    manifest_consistent: bool
    config_generated: bool
    unresolved_rows_leaked: bool


def _normalize_frame(frame: pd.DataFrame) -> pd.DataFrame:
    normalized = frame.copy()
    for column in normalized.columns:
        normalized[column] = normalized[column].map(lambda value: str(value).strip())
        normalized[column] = normalized[column].replace({"nan": "", "None": ""})
    return normalized


def _atomic_write_text(path: Path, content: str) -> None:
    tmp_path = path.with_name(path.name + ".tmp")
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        tmp_path.write_text(content, encoding="utf-8")
        os.replace(tmp_path, path)
    finally:
        if tmp_path.exists():
            tmp_path.unlink()


def _collapse_unique(values: pd.Series) -> str:
    unique_values = sorted({value for value in values if value})
    return ";".join(unique_values)


def _paired_rna_aliases(study_metadata: pd.DataFrame) -> dict[str, str]:
    aliases = set(study_metadata["experiment_alias"])
    pair_map: dict[str, str] = {}
    ribo_rows = study_metadata[study_metadata["corrected_type"] == "Ribo-Seq"]
    for _, row in ribo_rows.iterrows():
        candidate = row.get("matched_RNA-seq_experiment_alias", "")
        if candidate and candidate != "NA" and candidate in aliases:
            pair_map[row["experiment_alias"]] = candidate
    return pair_map


def _load_reference_catalog(reference_yaml_path: Path) -> dict[str, dict[str, str]]:
    with reference_yaml_path.open("r", encoding="utf-8") as handle:
        contents = yaml.safe_load(handle) or {}
    return {str(key).strip().lower(): value for key, value in contents.items()}


def build_pilot_candidates(
    *,
    metadata_frame: pd.DataFrame,
    runs_frame: pd.DataFrame,
    unresolved_frame: pd.DataFrame,
    manifest_frame: pd.DataFrame,
    reference_catalog: dict[str, dict[str, str]],
) -> pd.DataFrame:
    """Rank upstream pilot candidates using resolved local FASTQ evidence."""

    metadata = _normalize_frame(metadata_frame)
    runs = _normalize_frame(runs_frame)
    unresolved = _normalize_frame(unresolved_frame)
    manifest = _normalize_frame(manifest_frame)
    manifest_matched = manifest[manifest["status"] == "matched"].copy()
    candidate_rows: list[dict[str, object]] = []

    for study_name, study_runs in runs.groupby("study_name", sort=True):
        study_metadata = metadata[metadata["study_name"] == study_name].copy()
        study_unresolved = unresolved[unresolved["study_name"] == study_name].copy()
        run_accessions = set(study_runs["run_accession"])
        study_manifest = manifest_matched[manifest_matched["srr"].isin(run_accessions)].copy()
        organisms = sorted({value for value in study_runs["organism"] if value})
        source_batches = sorted({value for value in study_manifest["source_batch"] if value})
        corrected_types = sorted({value for value in study_runs["corrected_type"] if value})
        pair_map = _paired_rna_aliases(study_metadata)
        ribo_experiments = sorted(set(study_runs.loc[study_runs["corrected_type"] == "Ribo-Seq", "experiment_alias"]))
        rna_experiments = sorted(set(study_runs.loc[study_runs["corrected_type"] == "RNA-Seq", "experiment_alias"]))
        staged_candidates = [
            Path(path)
            for path in study_manifest["linked_path"]
            if path
        ]
        all_fastq_present = bool(staged_candidates) and all(path.exists() for path in staged_candidates)
        pairing_complete = bool(ribo_experiments) and all(exp in pair_map for exp in ribo_experiments)
        balanced_modalities = bool(ribo_experiments) and len(ribo_experiments) == len(rna_experiments)
        supported_reference = len(organisms) == 1 and organisms[0].lower() in reference_catalog

        score = 0
        if len(study_unresolved) == 0:
            score += 100
        if "Ribo-Seq" in corrected_types and "RNA-Seq" in corrected_types:
            score += 80
        if all_fastq_present:
            score += 60
        if len(organisms) == 1:
            score += 40
        if supported_reference:
            score += 30
        if len(source_batches) == 1:
            score += 20
        if pairing_complete:
            score += 20
        if balanced_modalities:
            score += 15
        if set(study_runs["library_layout"]) == {"SINGLE"}:
            score += 10
        score -= abs(study_runs["run_accession"].nunique() - 6) * 5

        candidate_rows.append(
            {
                "study_name": study_name,
                "organism": _collapse_unique(study_runs["organism"]),
                "resolved_run_rows": len(study_runs),
                "resolved_run_unique": study_runs["run_accession"].nunique(),
                "experiment_alias_unique": study_runs["experiment_alias"].nunique(),
                "has_ribo": "Ribo-Seq" in corrected_types,
                "has_rna": "RNA-Seq" in corrected_types,
                "unresolved_rows": len(study_unresolved),
                "source_batch_count": len(source_batches),
                "source_batches": ";".join(source_batches),
                "all_fastq_present": all_fastq_present,
                "single_organism": len(organisms) == 1,
                "supported_reference": supported_reference,
                "pairing_complete": pairing_complete,
                "ribo_experiment_count": len(ribo_experiments),
                "rna_experiment_count": len(rna_experiments),
                "balanced_modalities": balanced_modalities,
                "library_layouts": _collapse_unique(study_runs["library_layout"]),
                "pilot_ready": (
                    len(study_unresolved) == 0
                    and len(organisms) == 1
                    and "Ribo-Seq" in corrected_types
                    and "RNA-Seq" in corrected_types
                    and all_fastq_present
                    and supported_reference
                    and pairing_complete
                ),
                "score": score,
            }
        )

    candidates = pd.DataFrame(candidate_rows)
    if candidates.empty:
        return candidates
    return candidates.sort_values(
        [
            "pilot_ready",
            "score",
            "unresolved_rows",
            "resolved_run_unique",
            "study_name",
        ],
        ascending=[False, False, True, True, True],
    ).reset_index(drop=True)


def select_pilot_candidate(candidates: pd.DataFrame) -> pd.Series:
    """Choose the highest-ranked pilot-ready study."""

    if candidates.empty:
        raise RuntimeError("no pilot candidates were produced from metadata_runs.tsv")
    ready = candidates[candidates["pilot_ready"]]
    if ready.empty:
        raise RuntimeError("no pilot-ready study satisfied local-only upstream packaging requirements")
    return ready.iloc[0]


def _study_fastq_rows(study_name: str, runs_frame: pd.DataFrame, manifest_frame: pd.DataFrame) -> pd.DataFrame:
    run_accessions = set(runs_frame.loc[runs_frame["study_name"] == study_name, "run_accession"])
    fastq_rows = manifest_frame[(manifest_frame["srr"].isin(run_accessions)) & (manifest_frame["status"] == "matched")].copy()
    if fastq_rows.empty:
        raise RuntimeError(f"study {study_name} has no matched manifest rows for staging")
    return fastq_rows.sort_values(["gsm", "srr", "mate", "source_batch"]).reset_index(drop=True)


def _symlink_target(row: pd.Series) -> Path:
    for column in ("real_target", "linked_path", "source_path"):
        value = row.get(column, "")
        if value:
            return Path(value)
    raise RuntimeError(f"manifest row for {row.get('srr', '')} has no usable source path")


def _materialize_staged_symlink(dest: Path, target: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() or dest.is_symlink():
        if dest.is_symlink() and dest.resolve() == target.resolve():
            return
        raise RuntimeError(f"staged FASTQ path already exists with different target: {dest}")
    dest.symlink_to(target)


def _fastq_extension(path: Path) -> str:
    name = path.name
    if name.endswith(".fastq.gz"):
        return ".fastq.gz"
    if name.endswith(".fastq"):
        return ".fastq"
    raise RuntimeError(f"unsupported FASTQ suffix for staged alias planning: {path}")


def _snakefile_staged_basename(row: pd.Series) -> str:
    target = _symlink_target(row)
    run_accession = str(row["srr"]).strip()
    mate = str(row.get("mate", "")).strip()
    extension = _fastq_extension(target)
    if mate in {"1", "2"}:
        return f"{run_accession}_{mate}{extension}"
    return f"{run_accession}{extension}"


def _build_fastq_manifest(study_name: str, fastq_rows: pd.DataFrame, pilot_dir: Path) -> pd.DataFrame:
    rows: list[dict[str, str]] = []
    staged_root = pilot_dir / "staged_fastq"
    for _, row in fastq_rows.iterrows():
        staged_basename = _snakefile_staged_basename(row)
        staged_path = staged_root / staged_basename
        rows.append(
            {
                "study_name": study_name,
                "experiment_alias": row["gsm"],
                "run_accession": row["srr"],
                "mate": row["mate"],
                "source_batch": row["source_batch"],
                "source_path": row["source_path"],
                "inventory_linked_path": row["linked_path"],
                "real_target": row.get("real_target", ""),
                "staged_fastq_basename": staged_basename,
                "staged_fastq_path": str(staged_path),
                "warning": row.get("warning", ""),
            }
        )
    return pd.DataFrame(rows, dtype=str)


def _sync_staged_fastq_aliases(fastq_manifest: pd.DataFrame, fastq_rows: pd.DataFrame, pilot_dir: Path) -> None:
    staged_root = pilot_dir / "staged_fastq"
    staged_root.mkdir(parents=True, exist_ok=True)
    desired_paths = {Path(path) for path in fastq_manifest["staged_fastq_path"]}

    if len(fastq_manifest) != len(fastq_rows):
        raise RuntimeError("fastq manifest rows and source manifest rows diverged during staging")

    for existing_path in staged_root.iterdir():
        if existing_path in desired_paths:
            continue
        if existing_path.is_symlink() or existing_path.is_file():
            existing_path.unlink()
            continue
        raise RuntimeError(f"unexpected non-file entry in staged FASTQ root: {existing_path}")

    for (_, manifest_row), (_, source_row) in zip(fastq_manifest.iterrows(), fastq_rows.iterrows()):
        target = _symlink_target(source_row)
        _materialize_staged_symlink(Path(manifest_row["staged_fastq_path"]), target)


def _build_study_manifest(
    study_name: str,
    study_runs: pd.DataFrame,
    fastq_manifest: pd.DataFrame,
    study_metadata: pd.DataFrame,
) -> pd.DataFrame:
    pair_map = _paired_rna_aliases(study_metadata)
    grouped_rows: list[dict[str, str]] = []
    for _, row in study_runs.sort_values(["corrected_type", "experiment_alias", "run_accession"]).iterrows():
        run_fastqs = fastq_manifest[fastq_manifest["run_accession"] == row["run_accession"]]
        grouped_rows.append(
            {
                "study_name": study_name,
                "organism": row["organism"],
                "experiment_alias": row["experiment_alias"],
                "experiment_accession": row["experiment_accession"],
                "matched_rnaseq_experiment_alias": pair_map.get(row["experiment_alias"], ""),
                "run_accession": row["run_accession"],
                "corrected_type": row["corrected_type"],
                "library_strategy": row["library_strategy"],
                "library_layout": row["library_layout"],
                "fastq_path": _collapse_unique(run_fastqs["staged_fastq_path"]),
                "source_batch": _collapse_unique(run_fastqs["source_batch"]),
                "manifest_match_status": _collapse_unique(run_fastqs["run_accession"].map(lambda _: row["manifest_match_status"])),
                "fastq_presence_status": row["fastq_presence_status"],
            }
        )
    return pd.DataFrame(grouped_rows, dtype=str)


def _reference_paths(organism: str, reference_catalog: dict[str, dict[str, str]], repo_root: Path) -> dict[str, str]:
    key = organism.strip().lower()
    if key not in reference_catalog:
        raise RuntimeError(f"organism {organism} is not present in legacy references.yaml")
    spec = reference_catalog[key]
    reference_root = repo_root
    return {
        "filter": str(reference_root / spec["filter"]),
        "transcriptome": str(reference_root / spec["transcriptome"]),
        "regions": str(reference_root / spec["regions"]),
        "transcript_lengths": str(reference_root / spec["transcript_lengths"]),
    }


def _build_project_yaml(
    *,
    study_name: str,
    organism: str,
    study_manifest: pd.DataFrame,
    fastq_manifest: pd.DataFrame,
    template_path: Path,
    reference_catalog: dict[str, dict[str, str]],
    repo_root: Path,
    pilot_dir: Path,
) -> dict:
    with template_path.open("r", encoding="utf-8") as handle:
        project_yaml = yaml.safe_load(handle)

    project_yaml["do_rnaseq"] = True
    project_yaml["do_metadata"] = False
    project_yaml["input"]["reference"] = _reference_paths(organism, reference_catalog, repo_root)
    project_yaml["input"]["fastq_base"] = ""

    ribo_fastq: dict[str, list[str]] = {}
    rna_fastq: dict[str, list[str]] = {}
    for _, row in study_manifest.iterrows():
        experiment_alias = row["experiment_alias"]
        run_fastqs = fastq_manifest[fastq_manifest["run_accession"] == row["run_accession"]]
        staged_paths = sorted(run_fastqs["staged_fastq_path"].tolist())
        if row["corrected_type"] == "Ribo-Seq":
            ribo_fastq[experiment_alias] = staged_paths
            matched_rna_alias = row["matched_rnaseq_experiment_alias"]
            if matched_rna_alias:
                matched_rows = study_manifest[study_manifest["experiment_alias"] == matched_rna_alias]
                rna_paths = []
                for _, matched_row in matched_rows.iterrows():
                    matched_fastqs = fastq_manifest[fastq_manifest["run_accession"] == matched_row["run_accession"]]
                    rna_paths.extend(sorted(matched_fastqs["staged_fastq_path"].tolist()))
                rna_fastq[experiment_alias] = sorted(rna_paths)

    if not ribo_fastq:
        raise RuntimeError(f"study {study_name} has no ribo FASTQ entries for project.yaml")
    if any(not paths for paths in ribo_fastq.values()):
        raise RuntimeError(f"study {study_name} has empty ribo FASTQ slots in project.yaml planning")
    if any(not paths for paths in rna_fastq.values()):
        raise RuntimeError(f"study {study_name} has empty RNA FASTQ slots in project.yaml planning")

    project_yaml["input"]["fastq"] = ribo_fastq
    project_yaml["rnaseq"]["fastq"] = rna_fastq
    project_yaml["output"]["output"]["base"] = str(pilot_dir / "output" / study_name)
    project_yaml["output"]["intermediates"]["base"] = str(pilot_dir / "intermediates" / study_name)
    return project_yaml


def _validate_symlinks(fastq_manifest: pd.DataFrame) -> bool:
    for staged_path in fastq_manifest["staged_fastq_path"]:
        path = Path(staged_path)
        if not path.is_symlink():
            return False
        try:
            resolved = path.resolve(strict=True)
        except FileNotFoundError:
            return False
        if not resolved.exists():
            return False
    return True


def _validate_manifest_consistency(study_manifest: pd.DataFrame, fastq_manifest: pd.DataFrame) -> bool:
    expected_runs = set(study_manifest["run_accession"])
    fastq_runs = set(fastq_manifest["run_accession"])
    return expected_runs == fastq_runs and all(Path(path).exists() for path in fastq_manifest["inventory_linked_path"])


def _render_selection_markdown(candidates: pd.DataFrame, selected: pd.Series) -> str:
    lines = [
        "# Upstream Pilot Selection",
        "",
        "## Selected Study",
        "",
        f"- study_name: {selected['study_name']}",
        f"- organism: {selected['organism']}",
        f"- reason: all runs resolved, both Ribo/RNA present, local FASTQ complete, single organism, supported reference, deterministic top score={selected['score']}",
        "",
        "## Top 5 Candidates",
        "",
    ]
    for _, row in candidates.head(5).iterrows():
        lines.append(
            f"- {row['study_name']} | organism={row['organism']} | runs={row['resolved_run_unique']} | unresolved={row['unresolved_rows']} | score={row['score']}"
        )
    return "\n".join(lines) + "\n"


def _render_pilot_report(
    *,
    selected: pd.Series,
    study_manifest_path: Path,
    fastq_manifest_path: Path,
    project_yaml_path: Path,
    symlinks_ok: bool,
    manifest_consistent: bool,
    unresolved_rows_leaked: bool,
) -> str:
    lines = [
        "# Upstream Pilot Build Report",
        "",
        f"- study_name: {selected['study_name']}",
        f"- organism: {selected['organism']}",
        f"- score: {selected['score']}",
        f"- symlinks_ok: {str(symlinks_ok).lower()}",
        f"- manifest_consistent: {str(manifest_consistent).lower()}",
        f"- config_generated: true",
        f"- unresolved_rows_leaked: {str(unresolved_rows_leaked).lower()}",
        "",
        "## Outputs",
        "",
        f"- study_manifest: {study_manifest_path}",
        f"- fastq_manifest: {fastq_manifest_path}",
        f"- project_yaml: {project_yaml_path}",
    ]
    return "\n".join(lines) + "\n"


def build_upstream_pilot_package(
    *,
    metadata_path: Path,
    runs_path: Path,
    unresolved_path: Path,
    manifest_path: Path,
    pilot_root: Path = DEFAULT_PILOT_ROOT,
    reference_yaml_path: Path = DEFAULT_REFERENCE_YAML,
    project_template_path: Path = DEFAULT_PROJECT_TEMPLATE,
) -> PilotBuildResult:
    """Select one clean study and materialize a local-only upstream pilot package."""

    metadata = read_experiment_metadata(metadata_path).frame
    runs = pd.read_csv(runs_path, sep="\t", dtype=str, keep_default_na=False)
    unresolved = pd.read_csv(unresolved_path, sep="\t", dtype=str, keep_default_na=False)
    manifest = read_manifest_frame(manifest_path)
    reference_catalog = _load_reference_catalog(reference_yaml_path)

    candidates = build_pilot_candidates(
        metadata_frame=metadata,
        runs_frame=runs,
        unresolved_frame=unresolved,
        manifest_frame=manifest,
        reference_catalog=reference_catalog,
    )
    selected = select_pilot_candidate(candidates)
    study_name = selected["study_name"]
    organism = selected["organism"]
    pilot_dir = pilot_root / study_name
    study_runs = runs[runs["study_name"] == study_name].copy()
    study_metadata = _normalize_frame(metadata[metadata["study_name"] == study_name].copy())
    if not unresolved[unresolved["study_name"] == study_name].empty:
        raise RuntimeError(f"selected study {study_name} still contains unresolved rows")

    fastq_rows = _study_fastq_rows(study_name, study_runs, manifest)
    fastq_manifest = _build_fastq_manifest(study_name, fastq_rows, pilot_dir)
    _sync_staged_fastq_aliases(fastq_manifest, fastq_rows, pilot_dir)

    study_manifest = _build_study_manifest(study_name, study_runs, fastq_manifest, study_metadata)
    project_yaml = _build_project_yaml(
        study_name=study_name,
        organism=organism,
        study_manifest=study_manifest,
        fastq_manifest=fastq_manifest,
        template_path=project_template_path,
        reference_catalog=reference_catalog,
        repo_root=reference_yaml_path.parents[1] / "reference",
        pilot_dir=pilot_dir,
    )

    candidates_path = pilot_root / "pilot_candidates.tsv"
    selection_path = pilot_root / "pilot_selection.md"
    study_manifest_path = pilot_dir / "study_manifest.tsv"
    fastq_manifest_path = pilot_dir / "fastq_manifest.tsv"
    project_yaml_path = pilot_dir / "project.yaml"
    report_path = pilot_dir / "_pilot_build_report.md"

    _atomic_write_text(candidates_path, candidates.to_csv(sep="\t", index=False))
    _atomic_write_text(selection_path, _render_selection_markdown(candidates, selected))
    _atomic_write_text(study_manifest_path, study_manifest.to_csv(sep="\t", index=False))
    _atomic_write_text(fastq_manifest_path, fastq_manifest.to_csv(sep="\t", index=False))
    _atomic_write_text(project_yaml_path, yaml.safe_dump(project_yaml, sort_keys=False))

    symlinks_ok = _validate_symlinks(fastq_manifest)
    manifest_consistent = _validate_manifest_consistency(study_manifest, fastq_manifest)
    unresolved_rows_leaked = not unresolved[unresolved["study_name"] == study_name].empty
    _atomic_write_text(
        report_path,
        _render_pilot_report(
            selected=selected,
            study_manifest_path=study_manifest_path,
            fastq_manifest_path=fastq_manifest_path,
            project_yaml_path=project_yaml_path,
            symlinks_ok=symlinks_ok,
            manifest_consistent=manifest_consistent,
            unresolved_rows_leaked=unresolved_rows_leaked,
        ),
    )

    with project_yaml_path.open("r", encoding="utf-8") as handle:
        yaml.safe_load(handle)

    return PilotBuildResult(
        candidates_path=candidates_path,
        selection_path=selection_path,
        pilot_root=pilot_root,
        study_name=study_name,
        organism=organism,
        study_manifest_path=study_manifest_path,
        fastq_manifest_path=fastq_manifest_path,
        staged_fastq_root=pilot_dir / "staged_fastq",
        project_yaml_path=project_yaml_path,
        report_path=report_path,
        staged_fastq_count=len(fastq_manifest),
        symlinks_ok=symlinks_ok,
        manifest_consistent=manifest_consistent,
        config_generated=True,
        unresolved_rows_leaked=unresolved_rows_leaked,
    )
