"""Thin Stage 2/3 bridge from species prepare output to shared vendor/TE_model."""
from __future__ import annotations

import ast
import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

from te_analysis.config import REPO_ROOT

VENDOR_TE_MODEL = REPO_ROOT / "vendor" / "TE_model"
METADATA_DEFAULT = REPO_ROOT / "data" / "raw" / "metadata.csv"
STAGE1_PRODUCTS = ("ribo_paired_count_dummy.csv", "rna_paired_count_dummy.csv")
STAGE2_PRODUCTS = ("human_TE_sample_level.rda", "human_TE_cellline_all.csv")
STAGE3_PRODUCT = "human_TE_cellline_all_T.csv"
SERIAL_PATCH_TARGET = "TE.serial.patched"
INFOR_FILTER_NAME = "infor_filter.csv"


def _timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _discover_runtime_root(species_root: Path, trial_name: str | None) -> tuple[Path, Path]:
    patterns = (
        "runtime/vendor/TE_model/trials/*/config.py",
        "runtime/trials/*/config.py",
    )
    matches: list[Path] = []
    for pattern in patterns:
        matches.extend(species_root.glob(pattern))
    matches = sorted({path.resolve() for path in matches})
    if not matches:
        raise FileNotFoundError(f"no species runtime trial config found under {species_root}")

    if trial_name is None:
        if len(matches) != 1:
            raise ValueError(
                f"multiple species trials found under {species_root}; pass --trial-name explicitly: {matches}"
            )
        config_path = matches[0]
    else:
        target = [path for path in matches if path.parent.name == trial_name]
        if not target:
            raise FileNotFoundError(
                f"trial {trial_name!r} not found under {species_root}; available={[p.parent.name for p in matches]}"
            )
        if len(target) != 1:
            raise ValueError(f"multiple config paths found for trial {trial_name!r}: {target}")
        config_path = target[0]

    runtime_root = config_path.parents[2]
    trial_dir = config_path.parent
    return runtime_root, trial_dir


def _require_nonempty(path: Path, label: str) -> None:
    if not path.is_file():
        raise FileNotFoundError(f"{label} missing: {path}")
    if path.stat().st_size == 0:
        raise ValueError(f"{label} is empty: {path}")


def _validate_stage1_products(trial_dir: Path) -> None:
    for name in STAGE1_PRODUCTS:
        _require_nonempty(trial_dir / name, f"Stage 1 product {name}")


def _load_metadata(metadata_path: Path) -> pd.DataFrame:
    if not metadata_path.is_file():
        raise FileNotFoundError(f"metadata.csv not found: {metadata_path}")
    return pd.read_csv(metadata_path, header=1, dtype=str, keep_default_na=False)


def _load_vendor_infor_filter(vendor_root: Path) -> pd.DataFrame:
    source_path = vendor_root / "data" / INFOR_FILTER_NAME
    if not source_path.is_file():
        raise FileNotFoundError(f"shared vendor infor_filter.csv not found: {source_path}")
    df = pd.read_csv(source_path, dtype=str, keep_default_na=False)
    required = {"experiment_alias", "cell_line"}
    missing = required - set(df.columns)
    if missing:
        raise KeyError(f"shared vendor infor_filter.csv missing required columns: {sorted(missing)}")
    return df


def _extract_custom_experiment_list(config_path: Path) -> list[str]:
    if not config_path.is_file():
        raise FileNotFoundError(f"trial config not found: {config_path}")
    module = ast.parse(config_path.read_text(encoding="utf-8"), filename=str(config_path))
    for node in ast.walk(module):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if not isinstance(func, ast.Name) or func.id != "main":
            continue
        for keyword in node.keywords:
            if keyword.arg != "custom_experiment_list":
                continue
            value = ast.literal_eval(keyword.value)
            if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
                raise ValueError(f"custom_experiment_list must be a list[str] in {config_path}")
            if not value:
                raise ValueError(f"custom_experiment_list is empty in {config_path}")
            return value
    raise ValueError(f"custom_experiment_list not found in {config_path}")


def _build_runtime_infor_filter_rows(
    *,
    metadata: pd.DataFrame,
    experiments: list[str],
    study_names: list[str] | None = None,
) -> pd.DataFrame:
    required = {"experiment_alias", "cell_line"}
    missing = required - set(metadata.columns)
    if missing:
        raise KeyError(f"metadata.csv missing required columns for infor_filter bridge: {sorted(missing)}")

    scoped = metadata[metadata["experiment_alias"].isin(experiments)].copy()
    if study_names:
        if "study_name" not in scoped.columns:
            raise KeyError("metadata.csv missing study_name; cannot scope bounded smoke studies")
        scoped = scoped[scoped["study_name"].isin(study_names)].copy()

    rows: list[dict[str, str]] = []
    missing_experiments: list[str] = []
    for experiment_alias in experiments:
        grp = scoped[scoped["experiment_alias"] == experiment_alias].copy()
        if grp.empty:
            missing_experiments.append(experiment_alias)
            continue
        values = sorted({value for value in grp["cell_line"] if value})
        if len(values) > 1:
            raise ValueError(
                f"metadata conflict for experiment_alias={experiment_alias!r} cell_line={values}"
            )
        rows.append(
            {
                "experiment_alias": experiment_alias,
                "cell_line": values[0] if values else "",
            }
        )

    if missing_experiments:
        raise ValueError(
            "metadata.csv missing experiment_alias rows for runtime-local infor_filter bridge: "
            f"{missing_experiments}"
        )

    return pd.DataFrame(rows)


def _materialize_runtime_infor_filter(
    *,
    species_root: Path,
    runtime_root: Path,
    trial_dir: Path,
    vendor_root: Path,
    metadata_path: Path,
    stamp: str,
    bounded_studies: list[str] | None = None,
) -> tuple[Path, Path]:
    base = _load_vendor_infor_filter(vendor_root)
    metadata = _load_metadata(metadata_path)
    experiments = _extract_custom_experiment_list(trial_dir / "config.py")
    bridge_rows = _build_runtime_infor_filter_rows(
        metadata=metadata,
        experiments=experiments,
        study_names=bounded_studies,
    )

    runtime_data_dir = runtime_root / "data"
    runtime_data_dir.mkdir(parents=True, exist_ok=True)
    runtime_path = runtime_data_dir / INFOR_FILTER_NAME

    bridge_experiments = set(bridge_rows["experiment_alias"])
    merged = pd.concat(
        [base[~base["experiment_alias"].isin(bridge_experiments)].copy(), bridge_rows],
        ignore_index=True,
    )
    if "Unnamed: 0" in merged.columns:
        merged["Unnamed: 0"] = [str(i) for i in range(1, len(merged) + 1)]
    merged.to_csv(runtime_path, index=False)

    patch_log = species_root / "logs" / f"infor_filter.bridge.{stamp}.log"
    patch_log.parent.mkdir(parents=True, exist_ok=True)
    patch_log.write_text(
        json.dumps(
            {
                "shared_infor_filter": str(vendor_root / "data" / INFOR_FILTER_NAME),
                "runtime_infor_filter": str(runtime_path),
                "metadata_path": str(metadata_path),
                "trial_config": str(trial_dir / "config.py"),
                "bounded_studies": bounded_studies or [],
                "experiments_requested": experiments,
                "bridge_rows_added": bridge_rows.to_dict("records"),
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return runtime_path, patch_log


def _build_serial_te_r(source_text: str) -> tuple[str, dict[str, int]]:
    replacements = {
        "library_doParallel_removed": 0,
        "makeCluster_removed": 0,
        "registerDoParallel_removed": 0,
        "dopar_replaced": 0,
        "stopCluster_removed": 0,
    }
    patched_lines: list[str] = []
    for line in source_text.splitlines(keepends=True):
        stripped = line.strip()
        if stripped == "library(doParallel)":
            replacements["library_doParallel_removed"] += 1
            continue
        if "makeCluster(" in stripped:
            replacements["makeCluster_removed"] += 1
            continue
        if "registerDoParallel(" in stripped:
            replacements["registerDoParallel_removed"] += 1
            continue
        if "stopCluster(" in stripped:
            replacements["stopCluster_removed"] += 1
            continue
        if "%dopar%" in line:
            line = line.replace("%dopar%", "%do%")
            replacements["dopar_replaced"] += 1
        patched_lines.append(line)

    if replacements["dopar_replaced"] == 0:
        raise ValueError("serial TE.R patch failed: no %dopar% token found")
    return "".join(patched_lines), replacements


def _materialize_serial_te_r(*, species_root: Path, vendor_root: Path, stamp: str) -> tuple[Path, Path]:
    source_path = vendor_root / "src" / "TE.R"
    if not source_path.is_file():
        raise FileNotFoundError(f"shared vendor TE.R not found: {source_path}")

    patched_text, replacements = _build_serial_te_r(source_path.read_text(encoding="utf-8"))
    runtime_overrides = species_root / "runtime_overrides"
    runtime_overrides.mkdir(parents=True, exist_ok=True)
    patched_path = runtime_overrides / f"{SERIAL_PATCH_TARGET}.{stamp}.R"
    patched_path.write_text(patched_text, encoding="utf-8")

    patch_log = species_root / "logs" / f"TE.serial.patch.{stamp}.log"
    patch_log.parent.mkdir(parents=True, exist_ok=True)
    patch_log.write_text(
        json.dumps(
            {
                "source_te_r": str(source_path),
                "patched_te_r": str(patched_path),
                "replacements": replacements,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return patched_path, patch_log


def _run_logged(command: list[str], *, cwd: Path, log_path: Path) -> int:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("w", encoding="utf-8") as fh:
        fh.write(f"$ {' '.join(command)}\n")
        fh.write(f"cwd={cwd}\n\n")
        fh.flush()
        proc = subprocess.run(
            command,
            cwd=cwd,
            check=False,
            stdout=fh,
            stderr=subprocess.STDOUT,
            text=True,
        )
    return proc.returncode


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__)
    root_group = ap.add_mutually_exclusive_group(required=True)
    root_group.add_argument("--species-root", type=Path)
    root_group.add_argument("--runtime-root", type=Path)
    ap.add_argument("--trial", "--trial-name", dest="trial_name", default=None)
    ap.add_argument("--vendor-root", type=Path, default=VENDOR_TE_MODEL)
    ap.add_argument("--metadata", type=Path, default=METADATA_DEFAULT)
    ap.add_argument("--rscript-bin", default="Rscript")
    ap.add_argument("--python-bin", default=sys.executable)
    ap.add_argument("--stage2-mode", choices=("shared", "serial-fallback"), default="shared")
    ap.add_argument("--infor-filter-mode", choices=("shared", "runtime-local"), default="shared")
    ap.add_argument("--bounded-study", dest="bounded_studies", action="append", default=[])
    ap.add_argument("--materialize-infor-filter-only", action="store_true")
    ap.add_argument("--skip-stage3", action="store_true")
    return ap


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    vendor_root = args.vendor_root if args.vendor_root.is_absolute() else (REPO_ROOT / args.vendor_root)
    if not vendor_root.is_dir():
        raise FileNotFoundError(f"vendor root not found: {vendor_root}")
    metadata_path = args.metadata if args.metadata.is_absolute() else (REPO_ROOT / args.metadata)

    if args.runtime_root is not None:
        runtime_root = args.runtime_root if args.runtime_root.is_absolute() else (REPO_ROOT / args.runtime_root)
        if not runtime_root.is_dir():
            raise FileNotFoundError(f"runtime root not found: {runtime_root}")
        trial_name = args.trial_name
        if not trial_name:
            trial_candidates = sorted((runtime_root / "trials").glob("*/config.py"))
            if len(trial_candidates) != 1:
                raise ValueError(
                    f"multiple trials under runtime root {runtime_root}; pass --trial-name explicitly"
                )
            trial_dir = trial_candidates[0].parent
        else:
            trial_dir = runtime_root / "trials" / trial_name
        species_root = runtime_root.parents[3]
    else:
        species_root = args.species_root if args.species_root.is_absolute() else (REPO_ROOT / args.species_root)
        if not species_root.is_dir():
            raise FileNotFoundError(f"species root not found: {species_root}")
        runtime_root, trial_dir = _discover_runtime_root(species_root, args.trial_name)

    if not trial_dir.is_dir():
        raise FileNotFoundError(f"trial dir not found: {trial_dir}")

    _validate_stage1_products(trial_dir)
    run_id = trial_dir.name
    logs_dir = species_root / "logs"
    stamp = _timestamp()
    stage2_log = logs_dir / f"{run_id}.stage2.{args.stage2_mode}.{stamp}.log"
    stage3_log = logs_dir / f"{run_id}.stage3.{args.stage2_mode}.{stamp}.log"

    trial_arg = str(trial_dir.resolve())
    stage2_entry = str((vendor_root / "src" / "TE.R").resolve())
    stage2_cwd = vendor_root
    bridge_log: Path | None = None
    patch_log: Path | None = None
    if args.infor_filter_mode == "runtime-local":
        runtime_infor_filter, bridge_log = _materialize_runtime_infor_filter(
            species_root=species_root,
            runtime_root=runtime_root,
            trial_dir=trial_dir,
            vendor_root=vendor_root,
            metadata_path=metadata_path,
            stamp=stamp,
            bounded_studies=args.bounded_studies,
        )
        stage2_cwd = runtime_root
        print(f"[run_species_downstream] runtime-local infor_filter={runtime_infor_filter}")
        print(f"[run_species_downstream] infor_filter bridge log={bridge_log}")
    if args.materialize_infor_filter_only:
        if args.infor_filter_mode != "runtime-local":
            raise ValueError("--materialize-infor-filter-only requires --infor-filter-mode runtime-local")
        return 0
    if args.stage2_mode == "serial-fallback":
        patched_te_r, patch_log = _materialize_serial_te_r(
            species_root=species_root,
            vendor_root=vendor_root,
            stamp=stamp,
        )
        stage2_entry = str(patched_te_r)
        print(f"[run_species_downstream] serial patch log={patch_log}")
        print(f"[run_species_downstream] serial patched TE.R={patched_te_r}")
    stage2_cmd = [args.rscript_bin, stage2_entry, trial_arg]
    print(f"[run_species_downstream] stage2 cwd={stage2_cwd}")
    print(f"[run_species_downstream] {' '.join(stage2_cmd)}")
    stage2_rc = _run_logged(stage2_cmd, cwd=stage2_cwd, log_path=stage2_log)

    stage2_ready = True
    for name in STAGE2_PRODUCTS:
        target = trial_dir / name
        if not target.is_file() or target.stat().st_size == 0:
            stage2_ready = False
            break

    if not stage2_ready:
        print(
            f"[run_species_downstream] Stage 2 incomplete rc={stage2_rc}; "
            f"expected outputs missing under {trial_dir}"
        )
        return stage2_rc if stage2_rc != 0 else 2

    print(f"[run_species_downstream] Stage 2 outputs ready in {trial_dir}")
    if args.skip_stage3:
        return 0

    stage3_cmd = [args.python_bin, str((vendor_root / "src" / "transpose_TE.py").resolve()), "-o", trial_arg]
    print(f"[run_species_downstream] stage3 cwd={vendor_root}")
    print(f"[run_species_downstream] {' '.join(stage3_cmd)}")
    stage3_rc = _run_logged(stage3_cmd, cwd=vendor_root, log_path=stage3_log)
    stage3_target = trial_dir / STAGE3_PRODUCT
    if not stage3_target.is_file() or stage3_target.stat().st_size == 0:
        print(
            f"[run_species_downstream] Stage 3 incomplete rc={stage3_rc}; "
            f"expected output missing: {stage3_target}"
        )
        return stage3_rc if stage3_rc != 0 else 3
    print(f"[run_species_downstream] Stage 3 output ready: {stage3_target}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
