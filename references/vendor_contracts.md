# Vendor Contracts (speed-reference)

**Status**: T0 canonical speed-reference per `module_contracts_v1 §M13`.
This file aggregates the reverse-engineered contracts for `vendor/snakescale`
and `vendor/TE_model` into a single lookup surface. Authoritative details
remain in the underlying docs; every fact here is line-anchored to vendor
source.

## 0. Pinned versions

| Submodule | SHA | Upstream |
|---|---|---|
| `vendor/snakescale` | `b918e75f877262dca96665d18c3b472675f30a6d` | <https://github.com/RiboBase/snakescale> |
| `vendor/TE_model` | `0b42e3f756e20b9954548b65ff8a64ae063d9a89` | <https://github.com/CenikLab/TE_model> |

Rationale and verification: see `docs/vendor_sha_recommendation.md`.
Refresh SHAs only via explicit submodule bump commits; never rebase vendors
(`module_contracts §M8/M9`).

---

## 1. snakescale (upstream)

Source of truth: `docs/snakescale_contract.md` (full tables).

### 1.1 Launch command

```bash
snakemake -p --cores N --config studies="['<study>']"
# cwd = vendor/snakescale
```

- Declared in README:110 (`vendor/snakescale/README.md:110-111`)
- Schema validator entry: `Snakefile:14,17`
- Exit-code propagation: `subprocess.run(..., check=False)` per `M2.MUST.3`

### 1.2 L1 orchestrator config (`config/config.yaml`)

Required keys (from `schemas/config.schema.yaml:75-78`): `studies`,
`riboflow_config`, `threads`. See `docs/snakescale_contract.md §1.1` for the
full 7-row field table.

### 1.3 L2 per-study `project.yaml`

Path: `input/project/{GSE}/{study}.yaml` (`Snakefile:34,87,96,146,177,205,774`).

`Snakefile:36` skips `generate_yaml()` whenever this file already exists —
this is the hook our `te_analysis.run_upstream` uses to inject pre-staged
yaml without touching `db/db.sqlite3`.

All fields consumed by RiboFlow are enumerated in
`docs/snakescale_contract.md §1.2`. Our dynamic overrides in
`te_analysis.stage_inputs` cover (per plan K1 §2):

- `clip_arguments`, `rnaseq.clip_arguments`
- `deduplicate`, `rnaseq.deduplicate`
- `do_rnaseq`
- `input.reference.{filter,transcriptome,regions,transcript_lengths}`
- `input.fastq_base`, `input.fastq`
- `rnaseq.fastq_base`, `rnaseq.fastq`
- `output.{output,intermediates}.base`

All other fields inherit the vendor template verbatim (template-override
strategy; `M1.MUSTNOT.6`).

### 1.4 FASTQ directory / naming convention

`generate_yaml.py:262,273,279` hard-codes:

```text
{download_path}/{GSE}/{GSM}/{SRR}_1.fastq.gz
```

Where `download_path` is the CLI arg (Snakefile passes `"input/fastq/"`;
our symlink layer writes under `<study-dir>/staged_fastq/{GSE}/{GSM}/...`
and then `run_upstream` symlinks `<study-dir>/project.yaml` into
`vendor/snakescale/input/project/{GSE}/{study}.yaml`).

Paired-end (`_2.fastq.gz`) is **not** explicit in vendor Snakefile
(`Snakefile:171,202` hardcode `_1`). Our J1 stores R2 paths in
`fastq_path_r2`, symlinks both, but `input.fastq[GSM]` lists R1 only
(see `docs/backlog.md` paired-end entry).

### 1.5 Runtime dependencies owned by vendor

- Bowtie2 references: `vendor/snakescale/reference/` populated via
  `scripts/download_reference.py --target reference --yaml scripts/references.yaml`
  (README:56-59). Not tracked; user provisions per run.
- `db/db.sqlite3`: unused in our pipeline (bypassed via pre-staged
  `input/project/{GSE}/{study}.yaml`).

---

## 2. TE_model (downstream)

Source of truth: `docs/te_model_contract.md` (full tables).

### 2.1 Launch command (Stage 0-3)

```bash
bash pipeline.bash -t <trial_name>
# cwd = vendor/TE_model
```

Stage breakdown (`pipeline.bash:1-44`):

| stage | command | purpose |
|---|---|---|
| 0 | `python -m trials.{trial}.config` | `main()` from `src/ribo_counts_to_csv.py` — flatten `.ribo` -> CSV |
| 1 | `python src/ribobase_counts_processing.py -i ribo_raw.csv -r rnaseq_raw.csv -m paired -o trials/{trial}` | CPM + quantile + dummy-gene |
| 2 | `Rscript src/TE.R trials/{trial}` | CLR->ILR regression |
| 3 | `python src/transpose_TE.py -o trials/{trial}` | transpose final CSV |

### 2.2 TE.R inputs

- `trials/{trial}/ribo_paired_count_dummy.csv` (`TE.R:16`)
- `trials/{trial}/rna_paired_count_dummy.csv` (`TE.R:17`)
- `data/infor_filter.csv` — **cwd-relative**, must be `vendor/TE_model/`
  (`TE.R:59`). Ships with vendor; our pipeline leaves it untouched.

### 2.3 TE.R outputs

| path | meaning | source |
|---|---|---|
| `trials/{trial}/human_TE_sample_level.rda` | sample-level TE (CLR) | `TE.R:57` |
| `trials/{trial}/human_TE_cellline_all.csv` | cell_line-aggregated TE | `TE.R:67` |
| `trials/{trial}/human_TE_cellline_all_T.csv` | transposed CSV | `transpose_TE.py:10-12` |

The `human_` prefix is hardcoded; `te_analysis.run_downstream` renames to
`{organism}_*` at copy time (`te_model_contract §6.3`).

### 2.4 `main()` signature (Stage 0)

```python
# vendor/TE_model/src/ribo_counts_to_csv.py:76
main(workdir, sample_filter, ribo_dedup, rna_seq_dedup,
     process_coverage_fn=None, filter=None,
     custom_experiment_list=None, rnaseq_fn=None)
```

Key: when `custom_experiment_list` is non-empty, `sample_filter` and
`data/paxdb_filtered_sample.csv` are both ignored (`ribo_counts_to_csv.py:77-82`).
Our `te_analysis.run_downstream` generates
`trials/{study}/config.py` that calls `main()` with the run-level
experiments from `data/raw/metadata.csv` — zero writes to
`vendor/TE_model/data/paxdb_filtered_sample.csv` (satisfies
`M8/M9.MUSTNOT.1`; `te_model_contract §6.2` option a).

### 2.5 `.ribo` input layout

`ribo_counts_to_csv.py:19-20`:

```text
./data/ribo/{study}/ribo/experiments/{experiment}.ribo
./data/ribo/{study}_dedup/ribo/experiments/{experiment}.ribo  # dedup variant
```

The snakescale output path aligns with this (`snakescale_contract §4`),
so no additional symlinks are needed between upstream and downstream.

---

## 3. Contract references back to project code

| Where our code touches vendor | File:line | Vendor anchor |
|---|---|---|
| `stage_inputs.py` project.yaml template load | K1 §VENDOR_TEMPLATE | `vendor/snakescale/project.yaml` |
| `stage_inputs.py` clip_arguments port | K1 `_build_clip_arguments` | `generate_yaml.py:32-67,159-162` |
| `stage_inputs.py` reference paths | K1 `_resolve_references` | `generate_yaml.py:177-187` + `scripts/references.yaml` |
| `stage_inputs.py` input.fastq key = Ribo GSM | K1 `_build_fastq_maps` | `generate_yaml.py:262-300` |
| `run_upstream.py` snakemake command | L1 `build_command` | `vendor/snakescale/README.md:110` |
| `run_upstream.py` input/project/ symlink | L1 `_inject_project_yaml` | `vendor/snakescale/Snakefile:36` |
| `run_downstream.py` pipeline.bash call | L2 `main` | `vendor/TE_model/pipeline.bash:1-44` |
| `run_downstream.py` Stage 0 config.py generator | L2 `_write_trial` | `vendor/TE_model/README.md:28-34`, `src/ribo_counts_to_csv.py:76` |

---

## 4. Open issues tracked in backlog

See `docs/backlog.md` and `docs/te_model_contract.md §6` for:

- nonpolyA_gene.csv species applicability (T6 deferred)
- model_results.txt doc-vs-code mismatch (decided to use
  `human_TE_cellline_all_T.csv` presence as Stage 3 success signal)
- classify_studies gate in snakescale (we do NOT mirror in Python; M2.MUSTNOT.1)
