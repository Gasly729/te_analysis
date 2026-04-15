"""Orchestration blueprint models for the local wrapper layer.

Responsibility:
- hold orchestration metadata without executing backend logic

Non-responsibility:
- no subprocess calls
- no stage execution
- no scheduler integration
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .models import StageDefinition


@dataclass(frozen=True)
class PipelineOrchestratorBlueprint:
    """Static orchestrator container for stage metadata and config roots."""

    project_root: Path
    config_roots: tuple[Path, ...]
    stages: tuple[StageDefinition, ...]
