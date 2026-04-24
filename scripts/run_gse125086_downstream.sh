#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
rscript_bin="${RSCRIPT_BIN:-/home/xrx/miniconda3/envs/snakemake-ribo/bin/Rscript}"
mpl_config_dir="${MPLCONFIGDIR:-/tmp/matplotlib-te-analysis}"
trial_dir="${repo_root}/vendor/TE_model/trials/GSE125086"

cleanup_trial() {
  rm -rf "${trial_dir}"
}

trap cleanup_trial EXIT
cleanup_trial

mkdir -p "${mpl_config_dir}"
export MPLCONFIGDIR="${mpl_config_dir}"

PYTHONPATH="${repo_root}/src" python -m te_analysis.run_downstream \
  --study-dir "${repo_root}/vendor/snakescale/output/GSE125086" \
  --out-dir "${repo_root}/data/processed/te/GSE125086" \
  --rscript-bin "${rscript_bin}" \
  --stage2-mode serial-fallback \
  --no-cutoff
