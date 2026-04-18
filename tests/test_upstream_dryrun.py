from __future__ import annotations

from pathlib import Path

from te_analysis.upstream.dryrun import build_snakemake_dryrun_command, build_snakemake_dryrun_env


def test_build_snakemake_dryrun_env_redirects_cache_and_tmp_into_runtime(tmp_path: Path) -> None:
    runtime_dir = tmp_path / "pilot_runtime"
    env = build_snakemake_dryrun_env(runtime_dir=runtime_dir, base_env={"HOME": "/home/example"})

    assert env["HOME"] == "/home/example"
    assert env["XDG_CACHE_HOME"] == str(runtime_dir / ".cache")
    assert env["TMPDIR"] == str(runtime_dir / ".tmp")
    assert (runtime_dir / ".cache").is_dir()
    assert (runtime_dir / ".tmp").is_dir()


def test_build_snakemake_dryrun_command_preserves_existing_snakemake_arguments() -> None:
    snakefile = Path("/repo/raw_motheds/snakescale/Snakefile")
    runtime_dir = Path("/repo/data/upstream/pilot/GSE132441/snakescale_dryrun_runtime")

    command = build_snakemake_dryrun_command(
        snakefile=snakefile,
        runtime_dir=runtime_dir,
        cores=1,
    )

    assert command == [
        "snakemake",
        "-n",
        "-s",
        str(snakefile),
        "--directory",
        str(runtime_dir),
        "--cores",
        "1",
    ]

