# Legacy TE Final Positive Baseline

Baseline name: `legacy_te_final_positive_smoke`

Canonical run:
- `run_id`: `verify_gse105082_hela_triplet_stage2`
- `target_stage`: `3`
- `study`: `GSE105082`
- `grouping`: `HeLa`
- `cohort`: `GSM2817679`, `GSM2817680`, `GSM2817681`

Why this cohort:
- all three inputs are experiment-level `.ribo`
- all three report `has_rnaseq = true`
- all three are APPRIS-compatible under the legacy alias path
- all three come from one study and are already labeled `HeLa` in legacy grouping sidecars

Stage-2 minimum sample conclusion:
- legacy `TE.R` effectively requires at least two matched samples
- single-sample Stage 2 failure is an expected methodological boundary, not a wrapper bug
- do not patch `TE.R` for single-sample support; use a multi-sample Stage-2-eligible cohort

Stage-3 final output conclusion:
- legacy `transpose_TE.py` is the real Stage 3 entrypoint
- Stage 3 consumes `human_TE_cellline_all.csv` and writes `human_TE_cellline_all_T.csv`
- Stage 3 is a postprocessing step: transpose the Stage-2 cell-line table and strip transcript suffixes with regex `\.(.*)`
- the proven final output has shape `10862 x 1` with the single column `HeLa`
- the proven final output preserves duplicate gene identifiers after suffix stripping; this is a legacy output semantic, not a new wrapper guarantee

Bounded commands:
```bash
REPO_ROOT=/home/xrx/my_project/te_analysis
RUN_ID=verify_gse105082_hela_triplet_stage2
RUNTIME_ROOT="$REPO_ROOT/data/downstream_runs/$RUN_ID"
REQUEST="$RUNTIME_ROOT/inputs/wrapper_request.json"
SANDBOX_ROOT="$RUNTIME_ROOT/sandbox"
TRIAL_ROOT="$SANDBOX_ROOT/trials/$RUN_ID"

source ~/miniconda3/etc/profile.d/conda.sh
conda activate snakemake-ribo
cd "$REPO_ROOT"

PYTHONPATH=src python -m te_analysis.downstream.legacy_te_model.cli --request "$REQUEST"
PYTHONPATH=src python -c "from te_analysis.downstream.legacy_te_model import prepare_legacy_te_model_isolated_smoke; prepare_legacy_te_model_isolated_smoke('$RUNTIME_ROOT')"

cd "$SANDBOX_ROOT"
MPLCONFIGDIR=/tmp/mplconfig_$RUN_ID python -m "trials.$RUN_ID.config"
python src/ribobase_counts_processing.py -i "trials/$RUN_ID/ribo_raw.csv" -r "trials/$RUN_ID/rnaseq_raw.csv" -m "paired" -o "trials/$RUN_ID"
Rscript src/TE.R "trials/$RUN_ID"
python src/transpose_TE.py -o "trials/$RUN_ID"
```

Expected Stage-2 outputs:
- `human_TE_sample_level.rda`
- `human_TE_cellline_all.csv`

Expected Stage-3 output:
- `human_TE_cellline_all_T.csv`

Minimal validation:
```bash
ls -lh "$TRIAL_ROOT"/human_TE_sample_level.rda "$TRIAL_ROOT"/human_TE_cellline_all.csv "$TRIAL_ROOT"/human_TE_cellline_all_T.csv
Rscript -e "load('$TRIAL_ROOT/human_TE_sample_level.rda'); cat(class(human_TE), '\n'); cat(paste(dim(human_TE), collapse='x'), '\n')"
head -5 "$TRIAL_ROOT/human_TE_cellline_all.csv"
head -5 "$TRIAL_ROOT/human_TE_cellline_all_T.csv"
```

Final output contract:
- `human_TE_cellline_all_T.csv` must exist under `data/downstream_runs/verify_gse105082_hela_triplet_stage2/sandbox/trials/verify_gse105082_hela_triplet_stage2/`
- the file must be non-empty
- when loaded with `pandas.read_csv(..., index_col=0)`, shape must be exactly `10862 x 1`
- the only output column must be `HeLa`
- the output column axis must not contain duplicates
- the row identifiers must be non-null
- the output must equal `human_TE_cellline_all.csv` transposed with transcript suffixes stripped via regex `\.(.*)`
- because the real legacy Stage-3 artifact strips transcript suffixes without deduplication, duplicate gene identifiers remain in the final row index; this is an observed legacy semantic and is intentionally locked as-is

Runtime-local note:
- `data/downstream_runs/verify_gse105082_hela_triplet_stage2/compatibility_note.md`
