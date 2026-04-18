"""Helpers for pilot-scoped SnakeScale dry-run execution."""

from __future__ import annotations

from pathlib import Path
import os
import subprocess
from typing import Mapping, Sequence


def build_snakemake_dryrun_command(*, snakefile: Path, runtime_dir: Path, cores: int = 1) -> list[str]:
    """Build the canonical SnakeScale dry-run command without altering semantics."""

    return [
        "snakemake",
        "-n",
        "-s",
        str(snakefile),
        "--directory",
        str(runtime_dir),
        "--cores",
        str(cores),
    ]


def build_snakemake_dryrun_env(*, runtime_dir: Path, base_env: Mapping[str, str] | None = None) -> dict[str, str]:
    """Redirect Snakemake cache/tmp state into a pilot-local writable runtime."""

    env = dict(base_env or os.environ)
    cache_dir = runtime_dir / ".cache"
    tmp_dir = runtime_dir / ".tmp"
    cache_dir.mkdir(parents=True, exist_ok=True)
    tmp_dir.mkdir(parents=True, exist_ok=True)
    env["XDG_CACHE_HOME"] = str(cache_dir)
    env["TMPDIR"] = str(tmp_dir)
    return env


def run_snakemake_dryrun(
    *,
    snakefile: Path,
    runtime_dir: Path,
    cores: int = 1,
    base_env: Mapping[str, str] | None = None,
) -> subprocess.CompletedProcess:
    """Run the canonical Snakemake dry-run with pilot-local writable cache/tmp."""

    command = build_snakemake_dryrun_command(
        snakefile=snakefile,
        runtime_dir=runtime_dir,
        cores=cores,
    )
    env = build_snakemake_dryrun_env(runtime_dir=runtime_dir, base_env=base_env)
    return subprocess.run(command, env=env, check=False)

