"""te_analysis.config — load configs/paths.toml and resolve absolute paths.

Single responsibility: parse the TOML file into dict[str, dict[str, Path]]
with every path anchored at the repository root. Performs no validation,
no mkdir, no existence checks (callers are responsible).
"""
from __future__ import annotations

from pathlib import Path
from typing import Final

try:
    import tomllib  # py >= 3.11
except ModuleNotFoundError:  # pragma: no cover - py 3.10 fallback
    import tomli as tomllib  # type: ignore[import-not-found,no-redef]

REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[2]
_PATHS_TOML: Final[Path] = REPO_ROOT / "configs" / "paths.toml"
_REQUIRED_SECTIONS: Final[frozenset[str]] = frozenset({"data", "vendor", "references"})


def load_paths(toml_path: Path | None = None) -> dict[str, dict[str, Path]]:
    """Load paths.toml and return {section: {key: absolute Path}}.

    Parameters
    ----------
    toml_path : Path | None
        Override TOML source; defaults to ``REPO_ROOT / configs / paths.toml``.

    Raises
    ------
    FileNotFoundError
        If ``toml_path`` does not exist.
    KeyError
        If any of the required top-level sections is missing.
    """
    target = toml_path if toml_path is not None else _PATHS_TOML
    with target.open("rb") as fh:
        raw = tomllib.load(fh)
    missing = _REQUIRED_SECTIONS - raw.keys()
    if missing:
        raise KeyError(f"paths.toml missing required sections: {sorted(missing)}")
    return {
        section: {key: (REPO_ROOT / value).resolve() for key, value in body.items()}
        for section, body in raw.items()
    }
