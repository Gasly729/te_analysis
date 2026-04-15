"""Compatibility shim for `python -m te_analysis.cli` from the repository root.

Responsibility:
- delegate CLI execution to the active implementation under `src/te_analysis/cli.py`

Non-responsibility:
- no business-logic duplication
- no extraction logic
- no hidden path discovery beyond the fixed local source layout
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
from typing import Optional, Sequence


def _load_active_cli_module():
    """Load the active CLI module from the `src/` package surface."""

    src_cli_path = Path(__file__).resolve().parents[1] / "src" / "te_analysis" / "cli.py"
    spec = importlib.util.spec_from_file_location("_te_analysis_src_cli", src_cli_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Could not resolve the active CLI module under src/te_analysis/cli.py.")

    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Delegate execution to the active CLI implementation."""

    module = _load_active_cli_module()
    return int(module.main(argv))


if __name__ == "__main__":
    raise SystemExit(main())
