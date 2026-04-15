"""Typed settings models for the local architecture skeleton.

Responsibility:
- define explicit path and profile containers for the new wrapper layer

Non-responsibility:
- no environment loading
- no path autodiscovery
- no file IO
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RepositoryPaths:
    """Explicit repository path bundle for wrapper code."""

    project_root: Path
    src_root: Path
    configs_root: Path
    data_root: Path
    staged_fastq_root: Path
    handoff_root: Path


@dataclass(frozen=True)
class PipelineProfiles:
    """Named profile bundle for the new wrapper layer."""

    default_profile: str
    upstream_profile: str
    downstream_profile: str
