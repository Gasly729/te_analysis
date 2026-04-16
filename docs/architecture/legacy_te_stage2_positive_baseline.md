# Legacy TE Stage-2 Positive Baseline

Baseline name: `legacy_te_stage2_positive_smoke`

Canonical run:
- `run_id`: `verify_gse105082_hela_triplet_stage2`
- `target_stage`: `2`
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
```

Expected Stage-2 outputs:
- `human_TE_sample_level.rda`
- `human_TE_cellline_all.csv`

Minimal validation:
```bash
ls -lh "$TRIAL_ROOT"/human_TE_sample_level.rda "$TRIAL_ROOT"/human_TE_cellline_all.csv
Rscript -e "load('$TRIAL_ROOT/human_TE_sample_level.rda'); cat(class(human_TE), '\n'); cat(paste(dim(human_TE), collapse='x'), '\n')"
head -5 "$TRIAL_ROOT/human_TE_cellline_all.csv"
```

Out of scope:
- Stage 3 is not part of this baseline

Runtime-local note:
- `data/downstream_runs/verify_gse105082_hela_triplet_stage2/compatibility_note.md`
