"""Thin Stage 2/3 bridge from species prepare output to shared vendor/TE_model."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from te_analysis.config import REPO_ROOT

VENDOR_TE_MODEL = REPO_ROOT / "vendor" / "TE_model"
STAGE1_PRODUCTS = ("ribo_paired_count_dummy.csv", "rna_paired_count_dummy.csv")
STAGE2_PRODUCTS = ("human_TE_sample_level.rda", "human_TE_cellline_all.csv")
STAGE3_PRODUCT = "human_TE_cellline_all_T.csv"
SERIAL_PATCH_TARGET = "TE.serial.patched"


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
    ap.add_argument("--rscript-bin", default="Rscript")
    ap.add_argument("--python-bin", default=sys.executable)
    ap.add_argument("--stage2-mode", choices=("shared", "serial-fallback"), default="shared")
    ap.add_argument("--skip-stage3", action="store_true")
    return ap


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    vendor_root = args.vendor_root if args.vendor_root.is_absolute() else (REPO_ROOT / args.vendor_root)
    if not vendor_root.is_dir():
        raise FileNotFoundError(f"vendor root not found: {vendor_root}")

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
    stage2_entry = "src/TE.R"
    patch_log: Path | None = None
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
    print(f"[run_species_downstream] stage2 cwd={vendor_root}")
    print(f"[run_species_downstream] {' '.join(stage2_cmd)}")
    stage2_rc = _run_logged(stage2_cmd, cwd=vendor_root, log_path=stage2_log)

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

    stage3_cmd = [args.python_bin, "src/transpose_TE.py", "-o", trial_arg]
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
