#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
rscript_bin="${RSCRIPT_BIN:-/home/xrx/miniconda3/envs/snakemake-ribo/bin/Rscript}"
mpl_config_dir="${MPLCONFIGDIR:-/tmp/matplotlib-te-analysis}"

mkdir -p "${mpl_config_dir}"
export MPLCONFIGDIR="${mpl_config_dir}"

PYTHONPATH="${repo_root}/src" python -m te_analysis.run_downstream \
  --study-dir "${repo_root}/vendor/snakescale/output/GSE132441" \
  --out-dir "${repo_root}/data/processed/te/GSE132441" \
  --rscript-bin "${rscript_bin}" \
  --stage2-mode serial-fallback \
  --no-cutoff
