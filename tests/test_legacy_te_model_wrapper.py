from __future__ import annotations

import importlib
import json
import sys
import tempfile
import types
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from te_analysis.downstream.legacy_te_model import (
    LEGACY_SOURCE_ROOT,
    ExecutionMode,
    MaterializationResult,
    RnaSeqValidationError,
    materialize_legacy_te_model_wrapper,
)
from te_analysis.downstream.legacy_te_model.contracts import WrapperRequest
from te_analysis.downstream.legacy_te_model.validator import validate_request_and_manifest


def _write_json(path: Path, payload: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n")
    return path


def _make_valid_fixture(tmp_root: Path, *, has_rnaseq: bool = True, include_experiments: bool = True) -> tuple[Path, Path]:
    ribo_path = tmp_root / "inputs" / "EXP_A.ribo"
    ribo_path.parent.mkdir(parents=True, exist_ok=True)
    ribo_path.write_text("")

    nonpolya_csv = tmp_root / "sidecars" / "nonpolyA_gene.csv"
    nonpolya_csv.parent.mkdir(parents=True, exist_ok=True)
    nonpolya_csv.write_text("Gene,GENE_true,anno\nGENE1,GENE1,non-poly\n")

    grouping_csv = tmp_root / "sidecars" / "infor_filter.csv"
    grouping_csv.write_text('experiment_alias,cell_line\nEXP_A,HEK293\n')

    request_path = tmp_root / "request.json"
    manifest_path = tmp_root / "handoff_manifest.json"

    experiments = []
    if include_experiments:
        experiments = [
            {
                "experiment_alias": "EXP_A",
                "study_id": "study_a",
                "ribo_path": str(ribo_path),
                "organism": "human",
                "has_rnaseq": has_rnaseq,
            }
        ]

    _write_json(
        manifest_path,
        {
            "manifest_version": "1.0",
            "run_id": "run_ok",
            "input_mode": "experiment_level_ribo",
            "experiments": experiments,
            "all_ribo_path": str(tmp_root / "inputs" / "all.ribo") if not include_experiments else None,
        },
    )
    _write_json(
        request_path,
        {
            "run_id": "run_ok",
            "execution_mode": "legacy_default_counts",
            "handoff_manifest_path": str(manifest_path),
            "sidecars": {
                "nonpolya_csv": str(nonpolya_csv),
                "grouping_csv": str(grouping_csv),
                "sample_selection_csv": None,
            },
            "source_legacy_root": str(LEGACY_SOURCE_ROOT),
        },
    )
    return request_path, manifest_path


def _install_fake_ribopy(*, has_rnaseq: bool) -> None:
    fake_ribopy = types.ModuleType("ribopy")

    class _FakeRibo:
        def __init__(self, ribo_path: str, alias=None):
            self.ribo_path = ribo_path
            self.alias = alias

        def has_rnaseq(self, experiment_id: str) -> bool:
            return has_rnaseq

    fake_ribopy.Ribo = _FakeRibo
    fake_ribopy.api = types.SimpleNamespace(
        alias=types.SimpleNamespace(apris_human_alias=lambda gene_id: gene_id)
    )
    sys.modules["ribopy"] = fake_ribopy


def test_reject_rnaseq_absent_manifest_entry() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_root = Path(tmpdir)
        request_path, manifest_path = _make_valid_fixture(tmp_root, has_rnaseq=False)
        _install_fake_ribopy(has_rnaseq=True)
        try:
            from te_analysis.downstream.legacy_te_model.contracts import load_handoff_manifest, load_wrapper_request

            request = load_wrapper_request(request_path)
            manifest = load_handoff_manifest(manifest_path)
            try:
                validate_request_and_manifest(request, manifest)
            except RnaSeqValidationError as exc:
                assert exc.category.value == "manifest_declaration_failure"
            else:
                raise AssertionError("Expected manifest_declaration_failure for has_rnaseq=false")
        finally:
            sys.modules.pop("ribopy", None)


def test_reject_manifest_ribo_contradiction() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_root = Path(tmpdir)
        request_path, manifest_path = _make_valid_fixture(tmp_root, has_rnaseq=True)
        _install_fake_ribopy(has_rnaseq=False)
        try:
            from te_analysis.downstream.legacy_te_model.contracts import load_handoff_manifest, load_wrapper_request

            request = load_wrapper_request(request_path)
            manifest = load_handoff_manifest(manifest_path)
            try:
                validate_request_and_manifest(request, manifest)
            except RnaSeqValidationError as exc:
                assert exc.category.value == "manifest_inspection_contradiction"
            else:
                raise AssertionError("Expected manifest_inspection_contradiction")
        finally:
            sys.modules.pop("ribopy", None)


def test_reject_missing_gene_column() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_root = Path(tmpdir)
        request_path, _ = _make_valid_fixture(tmp_root, has_rnaseq=True)
        request_data = json.loads(request_path.read_text())
        Path(request_data["sidecars"]["nonpolya_csv"]).write_text("BAD\nX\n")
        _install_fake_ribopy(has_rnaseq=True)
        try:
            try:
                materialize_legacy_te_model_wrapper(request_path, runtime_base=tmp_root / "runtime")
            except Exception as exc:
                assert "Gene" in str(exc)
            else:
                raise AssertionError("Expected missing Gene column failure")
        finally:
            sys.modules.pop("ribopy", None)


def test_reject_missing_cell_line_coverage() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_root = Path(tmpdir)
        request_path, _ = _make_valid_fixture(tmp_root, has_rnaseq=True)
        request_data = json.loads(request_path.read_text())
        Path(request_data["sidecars"]["grouping_csv"]).write_text("experiment_alias,cell_line\nOTHER,HEK293\n")
        _install_fake_ribopy(has_rnaseq=True)
        try:
            try:
                materialize_legacy_te_model_wrapper(request_path, runtime_base=tmp_root / "runtime")
            except Exception as exc:
                assert "does not cover all experiment aliases" in str(exc)
            else:
                raise AssertionError("Expected grouping coverage failure")
        finally:
            sys.modules.pop("ribopy", None)


def test_reject_all_ribo_only_manifest_shape() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_root = Path(tmpdir)
        request_path, _ = _make_valid_fixture(tmp_root, has_rnaseq=True, include_experiments=False)
        _install_fake_ribopy(has_rnaseq=True)
        try:
            try:
                materialize_legacy_te_model_wrapper(request_path, runtime_base=tmp_root / "runtime")
            except Exception as exc:
                assert "all.ribo alone" in str(exc)
            else:
                raise AssertionError("Expected all.ribo-alone rejection")
        finally:
            sys.modules.pop("ribopy", None)


def test_materialize_expected_sandbox_tree_and_config_import_path() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_root = Path(tmpdir)
        request_path, _ = _make_valid_fixture(tmp_root, has_rnaseq=True)
        _install_fake_ribopy(has_rnaseq=True)
        try:
            result = materialize_legacy_te_model_wrapper(request_path, runtime_base=tmp_root / "runtime")
            assert isinstance(result, MaterializationResult)
            runtime_root = tmp_root / "runtime" / "run_ok"
            assert (runtime_root / "handoff" / "handoff_manifest.json").exists()
            assert (runtime_root / "handoff" / "sidecars_manifest.json").exists()
            assert (runtime_root / "handoff" / "wrapper_request.json").exists()
            assert (runtime_root / "logs" / "wrapper_provenance.json").exists()
            assert (runtime_root / "logs" / "materialization.log").exists()
            assert (runtime_root / "sandbox" / "pipeline.bash").exists()
            assert (runtime_root / "sandbox" / "src" / "__init__.py").exists()
            assert (runtime_root / "sandbox" / "trials" / "__init__.py").exists()
            assert (runtime_root / "sandbox" / "trials" / "run_ok" / "__init__.py").exists()
            config_path = runtime_root / "sandbox" / "trials" / "run_ok" / "config.py"
            assert config_path.exists()
            fake_src = types.ModuleType("src")
            fake_src.__path__ = []
            fake_ribo_counts_to_csv = types.ModuleType("src.ribo_counts_to_csv")
            fake_ribo_counts_to_csv.main = lambda *args, **kwargs: None
            original_src = sys.modules.get("src")
            original_ribo_counts_module = sys.modules.get("src.ribo_counts_to_csv")
            sys.modules["src"] = fake_src
            sys.modules["src.ribo_counts_to_csv"] = fake_ribo_counts_to_csv
            sys.path.insert(0, str(runtime_root / "sandbox"))
            try:
                module = importlib.import_module("trials.run_ok.config")
                assert module is not None
            finally:
                sys.path.pop(0)
                if original_src is None:
                    sys.modules.pop("src", None)
                else:
                    sys.modules["src"] = original_src
                if original_ribo_counts_module is None:
                    sys.modules.pop("src.ribo_counts_to_csv", None)
                else:
                    sys.modules["src.ribo_counts_to_csv"] = original_ribo_counts_module
                sys.modules.pop("trials", None)
                sys.modules.pop("trials.run_ok", None)
                sys.modules.pop("trials.run_ok.config", None)
        finally:
            sys.modules.pop("ribopy", None)


def test_winsorized_mode_config_contains_frozen_callback_chain() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_root = Path(tmpdir)
        request_path, _ = _make_valid_fixture(tmp_root, has_rnaseq=True)
        request_data = json.loads(request_path.read_text())
        request_data["execution_mode"] = "legacy_winsorized_counts"
        request_path.write_text(json.dumps(request_data, indent=2) + "\n")
        _install_fake_ribopy(has_rnaseq=True)
        try:
            result = materialize_legacy_te_model_wrapper(request_path, runtime_base=tmp_root / "runtime")
            config_text = result.generated_config_path.read_text()
            assert "from src.utils import get_cds_range_lookup, cap_outliers_cds_only" in config_text
            assert "boundary_lookup = get_cds_range_lookup(ribo)" in config_text
            assert "cap_outliers_cds_only(coverage, gene, boundary_lookup, 99.5).sum()" in config_text
        finally:
            sys.modules.pop("ribopy", None)
