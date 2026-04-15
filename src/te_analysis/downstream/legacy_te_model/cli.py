from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from .contracts import LegacyTeModelContractError, MaterializationResult
from .materialize import materialize_legacy_te_model_wrapper


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m te_analysis.downstream.legacy_te_model.cli",
        description="Validate and materialize the non-executing legacy TE_model wrapper runtime.",
    )
    parser.add_argument("--request", required=True, help="Absolute path to a wrapper request JSON file.")
    parser.add_argument(
        "--runtime-base",
        help="Optional absolute runtime base override. Intended for tests or isolated dry runs.",
    )
    return parser


def _format_summary(result: MaterializationResult) -> str:
    payload = result.as_dict()
    payload["message"] = "materialized, not executed"
    return json.dumps(payload, indent=2, sort_keys=False)


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    runtime_base = None if args.runtime_base is None else Path(args.runtime_base)
    result = materialize_legacy_te_model_wrapper(args.request, runtime_base=runtime_base)
    print(_format_summary(result))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except LegacyTeModelContractError as exc:
        print(f"{exc.code}: {exc}", file=sys.stderr)
        raise SystemExit(2)
