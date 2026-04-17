"""Phase-1 boundary package for upstream orchestration wrappers.

Responsibility:
- Reserve module boundaries for manifest materialization and upstream runners.

Non-responsibility in phase 1:
- No workflow execution, subprocess wiring, or runtime side effects.
"""

from pathlib import Path


_ROOT_PACKAGE_DIR = Path(__file__).resolve().parent
_SRC_PACKAGE_DIR = _ROOT_PACKAGE_DIR.parents[1] / "src" / "te_analysis" / "upstream"

__path__ = [str(_ROOT_PACKAGE_DIR)]
if _SRC_PACKAGE_DIR.exists():
    __path__.append(str(_SRC_PACKAGE_DIR))
