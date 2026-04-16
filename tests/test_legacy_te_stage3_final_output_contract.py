from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
BASELINE_PATH = ROOT / "configs" / "downstream" / "legacy_te_stage2_positive_baseline.json"


def _load_baseline() -> dict[str, object]:
    return json.loads(BASELINE_PATH.read_text())


def test_stage3_final_output_contract_is_locked_to_runtime_artifact() -> None:
    baseline = _load_baseline()
    run_id = str(baseline["run_id"])
    runtime_root = ROOT / "data" / "downstream_runs" / run_id
    trial_root = runtime_root / "sandbox" / "trials" / run_id
    stage2_path = trial_root / "human_TE_cellline_all.csv"
    stage3_path = trial_root / "human_TE_cellline_all_T.csv"
    contract = baseline["final_output_contract"]

    assert stage3_path.exists(), f"Missing Stage 3 output: {stage3_path}"
    assert stage3_path.stat().st_size > 0, f"Stage 3 output is empty: {stage3_path}"
    try:
        relative_stage3_path = stage3_path.relative_to(runtime_root)
    except ValueError:
        raise AssertionError(
            f"Stage 3 output must stay under the controlled runtime root: {stage3_path}"
        )
    assert relative_stage3_path.as_posix() == contract["path_relative_to_runtime"], (
        "Stage 3 output path drifted away from the frozen baseline contract."
    )

    stage2_df = pd.read_csv(stage2_path, index_col=0)
    stage3_df = pd.read_csv(stage3_path, index_col=0)

    expected_shape = tuple(contract["shape"])
    assert stage3_df.shape == expected_shape, (
        f"Unexpected Stage 3 shape {stage3_df.shape}; expected {expected_shape}."
    )
    assert list(stage3_df.columns) == contract["column_names"], (
        f"Unexpected Stage 3 columns {list(stage3_df.columns)}; "
        f"expected {contract['column_names']}."
    )
    assert stage3_df.columns.is_unique, "Stage 3 output columns must be unique."
    assert int(stage3_df.index.isna().sum()) == contract["index_null_count"], (
        "Stage 3 output contains null row identifiers."
    )

    expected_stage3_df = stage2_df.T.copy()
    expected_stage3_df.index = expected_stage3_df.index.str.replace(r"\.(.*)", "", regex=True)
    assert stage3_df.equals(expected_stage3_df), (
        "Stage 3 output no longer matches the frozen Stage-2-to-Stage-3 transpose contract."
    )

    duplicate_gene_count = int(stage3_df.index.duplicated().sum())
    assert duplicate_gene_count == contract["duplicate_gene_identifier_count"], (
        f"Unexpected duplicate gene identifier count {duplicate_gene_count}; "
        f"expected {contract['duplicate_gene_identifier_count']}."
    )
    duplicate_families = stage3_df.index[stage3_df.index.duplicated(keep=False)].unique().tolist()
    assert duplicate_families == contract["duplicate_gene_identifier_families"], (
        f"Unexpected duplicate gene identifier families {duplicate_families}; "
        f"expected {contract['duplicate_gene_identifier_families']}."
    )
