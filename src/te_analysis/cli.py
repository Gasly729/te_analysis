"""CLI boundary for the new local wrapper package.

Responsibility:
- expose thin user-facing command boundaries for approved wrapper stages

Non-responsibility:
- no business-logic duplication
- no downloader behavior
- no biological logic
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Sequence

from te_analysis.downstream import (
    ExtractionContractError,
    ExtractionRunResult,
    MissingRiboArtifactError,
    RnaSeqStatus,
    materialize_legacy_te_model_wrapper,
    prepare_legacy_te_model_isolated_smoke,
    run_extraction,
)


@dataclass(frozen=True)
class CliCommandSpec:
    """Static description of an eventual CLI command boundary."""

    name: str
    summary: str


KNOWN_COMMANDS: tuple[CliCommandSpec, ...] = (
    CliCommandSpec(name="upstream", summary="Future upstream wrapper entrypoint."),
    CliCommandSpec(name="handoff", summary="Future handoff validation entrypoint."),
    CliCommandSpec(name="extract", summary="Run the minimal downstream extraction wrapper."),
    CliCommandSpec(name="legacy-materialize", summary="Validate and materialize the non-executing legacy TE_model wrapper runtime."),
    CliCommandSpec(name="legacy-readiness", summary="Probe a materialized legacy TE_model runtime for isolated Stage 0 smoke readiness."),
)


def _build_parser() -> argparse.ArgumentParser:
    """Create the thin CLI parser for the current wrapper surface."""

    parser = argparse.ArgumentParser(
        prog="python -m te_analysis.cli",
        description="Thin CLI for the te_analysis local wrapper architecture.",
    )
    subparsers = parser.add_subparsers(dest="command")

    extract_parser = subparsers.add_parser(
        "extract",
        help="Run the minimal read-only downstream extraction wrapper.",
        description="Consume a validated handoff manifest and write extraction-owned outputs.",
    )
    extract_parser.add_argument(
        "--handoff",
        required=True,
        help="Path to a validated handoff manifest JSON file.",
    )
    extract_parser.add_argument(
        "--output-root",
        help="Optional downstream-owned output root for extraction outputs.",
    )
    extract_parser.set_defaults(handler=_run_extract_command)

    legacy_parser = subparsers.add_parser(
        "legacy-materialize",
        help="Validate and materialize the legacy TE_model wrapper runtime without executing legacy pipeline.",
        description="Consume a wrapper request JSON, validate contracts, materialize sandbox runtime, and stop before legacy execution.",
    )
    legacy_parser.add_argument(
        "--request",
        required=True,
        help="Absolute path to a wrapper request JSON file.",
    )
    legacy_parser.add_argument(
        "--runtime-base",
        help="Optional absolute runtime base override.",
    )
    legacy_parser.set_defaults(handler=_run_legacy_materialize_command)

    readiness_parser = subparsers.add_parser(
        "legacy-readiness",
        help="Probe a materialized legacy TE_model runtime for isolated Stage 0 smoke readiness.",
        description="Use a non-executing readiness probe to verify sandbox structure, config import, and cwd-relative assumptions before running legacy Stage 0.",
    )
    readiness_parser.add_argument(
        "--runtime-root",
        required=True,
        help="Absolute path to an already materialized runtime root.",
    )
    readiness_parser.set_defaults(handler=_run_legacy_readiness_command)
    return parser


def _count_rnaseq_states(result: ExtractionRunResult) -> tuple[int, int]:
    """Count experiments with RNA-seq present and absent."""

    rnaseq_present = 0
    rnaseq_absent = 0
    for record in result.records:
        if record.rnaseq_status is RnaSeqStatus.PRESENT:
            rnaseq_present += 1
        elif record.rnaseq_status is RnaSeqStatus.ABSENT:
            rnaseq_absent += 1
    return rnaseq_present, rnaseq_absent


def _format_extraction_summary(result: ExtractionRunResult) -> str:
    """Return a compact terminal summary for a successful extraction run."""

    rnaseq_present, rnaseq_absent = _count_rnaseq_states(result)
    summary_lines = (
        "downstream_extraction: success",
        "study_id: {study_id}".format(study_id=result.study_id),
        "manifest_source: {manifest_source}".format(manifest_source=result.manifest_source),
        "output_dir: {output_dir}".format(output_dir=result.output_dir),
        "experiments_processed: {count}".format(count=len(result.records)),
        "rnaseq_present: {count}".format(count=rnaseq_present),
        "rnaseq_absent: {count}".format(count=rnaseq_absent),
    )
    return "\n".join(summary_lines)


def _run_extract_command(args: argparse.Namespace) -> int:
    """Execute the minimal downstream extraction wrapper from CLI arguments."""

    output_root = None if args.output_root is None else Path(args.output_root)
    result = run_extraction(
        args.handoff,
        output_root=output_root,
    )
    print(_format_extraction_summary(result))
    return 0


def _run_legacy_materialize_command(args: argparse.Namespace) -> int:
    """Validate and materialize the legacy TE_model wrapper runtime without execution."""

    runtime_base = None if args.runtime_base is None else Path(args.runtime_base)
    result = materialize_legacy_te_model_wrapper(
        args.request,
        runtime_base=runtime_base,
    )
    print("legacy_te_model_wrapper: materialized, not executed")
    print("run_id: {run_id}".format(run_id=result.run_id))
    print("runtime_root: {runtime_root}".format(runtime_root=result.runtime_root))
    print("sandbox_root: {sandbox_root}".format(sandbox_root=result.sandbox_root))
    print("generated_config: {config_path}".format(config_path=result.generated_config_path))
    return 0


def _run_legacy_readiness_command(args: argparse.Namespace) -> int:
    """Probe a materialized legacy runtime for isolated Stage 0 smoke readiness."""

    result = prepare_legacy_te_model_isolated_smoke(Path(args.runtime_root))
    print("legacy_te_model_wrapper: readiness probe complete")
    print("run_id: {run_id}".format(run_id=result.run_id))
    print("status: {status}".format(status=result.status))
    print("sandbox_root: {sandbox_root}".format(sandbox_root=result.sandbox_root))
    print("launch_cwd: {sandbox_root}".format(sandbox_root=result.sandbox_root))
    print("next_stage0_command: {command}".format(command=result.next_stage0_command))
    print("readiness_report: {path}".format(path=result.readiness_report_path))
    if result.blocking_issues:
        print("blocking_issues:")
        for issue in result.blocking_issues:
            print("- {issue}".format(issue=issue))
        return 1
    return 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Run the te_analysis CLI and return a process exit code."""

    parser = _build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    handler = getattr(args, "handler", None)
    if handler is None:
        parser.print_help()
        return 0

    try:
        return int(handler(args))
    except (ExtractionContractError, MissingRiboArtifactError, FileNotFoundError, ValueError) as exc:
        print("te_analysis: error", file=sys.stderr)
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
