from __future__ import annotations

import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from te_analysis.handoff.handoff_builder import (
    build_handoff_manifest,
    serialize_handoff_manifest,
)
from te_analysis.handoff.ribo_manifest import SidecarReference, SidecarRole, SidecarScope
from te_analysis.handoff.validators import validate_handoff_manifest


def test_handoff_manifest_construction_and_serialization() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        study_root = Path(tmpdir) / "GSE_TEST"
        experiments_dir = study_root / "ribo" / "experiments"
        experiments_dir.mkdir(parents=True)
        (experiments_dir / "EXP_A.ribo").write_text("")
        (experiments_dir / "EXP_B.ribo").write_text("")
        (study_root / "ribo" / "all.ribo").write_text("")

        pairing_path = study_root / "pairing.tsv"
        pairing_path.write_text("pairing")
        shared_root = Path(tmpdir) / "shared"
        shared_root.mkdir()
        nonpoly_path = shared_root / "nonpoly.tsv"
        nonpoly_path.write_text("nonpoly")

        manifest = build_handoff_manifest(
            study_root=study_root,
            study_sidecars=(
                SidecarReference(
                    role=SidecarRole.PAIRING_REFERENCE,
                    scope=SidecarScope.STUDY,
                    path=Path("pairing.tsv"),
                ),
            ),
            shared_sidecars=(
                SidecarReference(
                    role=SidecarRole.NONPOLYA_REFERENCE,
                    scope=SidecarScope.SHARED,
                    path=Path("nonpoly.tsv"),
                ),
            ),
            shared_sidecar_root=shared_root,
            validate=True,
        )

        assert manifest.study_id == "GSE_TEST"
        assert manifest.experiment_ids == ("EXP_A", "EXP_B")
        assert manifest.aggregate_ribo_path is not None
        assert len(manifest.experiment_ribo_files) == 2
        assert len(manifest.study_sidecars) == 1
        assert len(manifest.shared_sidecars) == 1
        assert manifest.validation.is_valid

        serialized = serialize_handoff_manifest(manifest)
        assert '"study_id": "GSE_TEST"' in serialized
        assert '"experiment_ids": [' in serialized
        assert '"study_sidecars": [' in serialized
        assert '"shared_sidecars": [' in serialized


def test_validator_requires_experiment_level_ribo_and_rejects_all_ribo_only() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        study_root = Path(tmpdir) / "GSE_ONLY_ALL"
        ribo_root = study_root / "ribo"
        ribo_root.mkdir(parents=True)
        (ribo_root / "all.ribo").write_text("")

        manifest = build_handoff_manifest(
            study_root=study_root,
            validate=True,
        )

        assert not manifest.validation.is_valid
        messages = [issue.message for issue in manifest.validation.issues]
        assert any("experiment-level `.ribo` artifact" in message for message in messages)
        assert any("`all.ribo` alone is not sufficient" in message for message in messages)


def test_missing_required_sidecars_fail_validation() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        study_root = Path(tmpdir) / "GSE_MISSING_SIDECAR"
        experiments_dir = study_root / "ribo" / "experiments"
        experiments_dir.mkdir(parents=True)
        (experiments_dir / "EXP_A.ribo").write_text("")

        manifest = build_handoff_manifest(
            study_root=study_root,
            study_sidecars=(
                SidecarReference(
                    role=SidecarRole.PAIRING_REFERENCE,
                    scope=SidecarScope.STUDY,
                    path=Path("missing_pairing.tsv"),
                    required=True,
                ),
            ),
            validate=True,
        )

        assert not manifest.validation.is_valid
        codes = [issue.code for issue in manifest.validation.issues]
        assert "missing-required-sidecar" in codes


def test_study_scoped_and_shared_sidecars_remain_distinct() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        study_root = Path(tmpdir) / "GSE_SCOPE"
        experiments_dir = study_root / "ribo" / "experiments"
        experiments_dir.mkdir(parents=True)
        (experiments_dir / "EXP_A.ribo").write_text("")

        study_manifest = study_root / "study_manifest.yaml"
        study_manifest.write_text("study")
        shared_root = Path(tmpdir) / "shared"
        shared_root.mkdir()
        downstream_cfg = shared_root / "downstream.yaml"
        downstream_cfg.write_text("cfg")

        manifest = build_handoff_manifest(
            study_root=study_root,
            study_sidecars=(
                SidecarReference(
                    role=SidecarRole.STUDY_MANIFEST,
                    scope=SidecarScope.STUDY,
                    path=study_manifest,
                ),
            ),
            shared_sidecars=(
                SidecarReference(
                    role=SidecarRole.DOWNSTREAM_RUN_CONFIG,
                    scope=SidecarScope.SHARED,
                    path=downstream_cfg,
                ),
            ),
            validate=False,
        )

        assert manifest.study_sidecars[0].scope is SidecarScope.STUDY
        assert manifest.shared_sidecars[0].scope is SidecarScope.SHARED

        validation = validate_handoff_manifest(manifest)
        assert validation.is_valid
