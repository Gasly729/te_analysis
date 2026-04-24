#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cores="${CORES:-4}"
conda_sh="${CONDA_SH:-${HOME}/miniconda3/etc/profile.d/conda.sh}"
python_bin="${PYTHON_BIN:-${HOME}/miniconda3/envs/te_analysis/bin/python}"

if [[ -f "${conda_sh}" ]]; then
  # shellcheck source=/dev/null
  set +u
  source "${conda_sh}"
  conda activate snakemake-ribo
  set -u
fi

export PYTHONPATH="${repo_root}/src${PYTHONPATH:+:${PYTHONPATH}}"
export XDG_CACHE_HOME="${XDG_CACHE_HOME:-/tmp/snakemake-cache}"
export TMPDIR="${TMPDIR:-/tmp}"

"${python_bin}" -m te_analysis.stage_inputs \
  --metadata "${repo_root}/data/raw/metadata.csv" \
  --study GSE132441 \
  --out "${repo_root}/data/interim/snakescale/GSE132441"

"${python_bin}" -m te_analysis.run_upstream \
  --study-dir "${repo_root}/data/interim/snakescale/GSE132441" \
  --cores "${cores}" \
  --nolock \
  --snakemake-arg=--rerun-triggers \
  --snakemake-arg=mtime
