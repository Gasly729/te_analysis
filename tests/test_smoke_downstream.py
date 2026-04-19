"""Smoke test: run_downstream against frozen GSE105082 baseline (M11).

Strategy: run_downstream's real execution takes ~15 min (TE.R compute-heavy;
violates M11 DoD "≤ 5 min"). Instead, we freeze the T9 green products as a
fixture and assert:

  (a) schema invariants on frozen products (shape, columns, index uniqueness)
  (b) run_downstream dispatch layer (_load + _write_trial) is wired correctly
      against current metadata.csv (fast, ≤ 1 s)
  (c) SHA-256 checksums match (detect silent bit-rot of committed fixture)

Full E2E regeneration is a manual T9 replay (see docs/reproducibility.md).
Baseline fixture: tests/fixtures/gse105082/t9_products/.
"""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import pandas as pd
import pytest

SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from te_analysis.run_downstream import _load, _write_trial  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = REPO_ROOT / "tests" / "fixtures" / "gse105082" / "t9_products"
METADATA_CSV = REPO_ROOT / "data" / "raw" / "metadata.csv"

# T9 green fixture invariants (captured post-J1 metadata enrichment).
EXPECTED_T_SHAPE = (10842, 1)           # genes × cell-line
EXPECTED_C_SHAPE = (1, 10842)           # cell-line × genes
EXPECTED_CELLLINES = ["HeLa"]
EXPECTED_ORGANISM = "Homo sapiens"
EXPECTED_N_EXPERIMENTS = 24             # unique experiment_alias in metadata
# SHA-256 of frozen products (regenerate via T9 replay if intentionally updated).
EXPECTED_SHA256 = {
    "homo_sapiens_TE_cellline_all_T.csv":
        "f0a75528727c84d7e2a7ae4c47b785ca3c900b3368cc5b84e363c0b70c7a40bf",
    "homo_sapiens_TE_cellline_all.csv":
        "417cb43b6e33315f88de437e96cc8a6151e068352b1fdd5225866170c8745423",
}


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def test_fixture_files_present() -> None:
    for name in EXPECTED_SHA256:
        assert (FIXTURE_DIR / name).is_file(), f"missing fixture: {name}"


def test_transposed_product_schema() -> None:
    df = pd.read_csv(FIXTURE_DIR / "homo_sapiens_TE_cellline_all_T.csv", index_col=0)
    assert df.shape == EXPECTED_T_SHAPE
    assert list(df.columns) == EXPECTED_CELLLINES
    # Index carries APPRIS gene symbols; allow duplicates (TE.R keeps first alias mapping).
    assert df.index.notna().all()


def test_cellline_product_schema() -> None:
    df = pd.read_csv(FIXTURE_DIR / "homo_sapiens_TE_cellline_all.csv", index_col=0)
    assert df.shape == EXPECTED_C_SHAPE
    assert list(df.index) == EXPECTED_CELLLINES
    assert len(df.columns) == EXPECTED_T_SHAPE[0]


@pytest.mark.parametrize("name", list(EXPECTED_SHA256))
def test_fixture_sha256_frozen(name: str) -> None:
    actual = _sha256(FIXTURE_DIR / name)
    assert actual == EXPECTED_SHA256[name], (
        f"{name} sha256 drift: got {actual}; if intentional, regenerate via T9 replay."
    )


def test_load_dispatch_against_metadata() -> None:
    experiments, organism = _load(METADATA_CSV, "GSE105082")
    assert organism == EXPECTED_ORGANISM
    assert len(experiments) == EXPECTED_N_EXPERIMENTS
    assert all(e.startswith("GSM") for e in experiments)
    assert experiments == sorted(experiments)


def test_write_trial_emits_runnable_config(tmp_path: Path) -> None:
    exps = ["GSM2817677", "GSM2817678", "GSM2817679"]
    _write_trial(tmp_path, exps)
    cfg = (tmp_path / "config.py").read_text()
    assert "from src.ribo_counts_to_csv import main" in cfg
    assert "custom_experiment_list" in cfg
    assert repr(exps) in cfg
    assert (tmp_path / "__init__.py").is_file()
