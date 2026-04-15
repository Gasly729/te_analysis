"""Compatibility package surface for legacy root-level imports.

Responsibility:
- keep the root-level `te_analysis` package importable from the repository root
- avoid import-time side effects while the active implementation lives under `src/`

Non-responsibility:
- no environment loading
- no logging setup
- no configuration side effects
"""

from pathlib import Path


_ROOT_PACKAGE_DIR = Path(__file__).resolve().parent
_SRC_PACKAGE_DIR = _ROOT_PACKAGE_DIR.parents[0] / "src" / "te_analysis"

__path__ = [str(_ROOT_PACKAGE_DIR)]
if _SRC_PACKAGE_DIR.exists():
    __path__.append(str(_SRC_PACKAGE_DIR))
