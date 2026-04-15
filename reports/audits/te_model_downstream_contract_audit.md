# TE_model Downstream Contract Audit

## Executive summary

This audit finds that the authoritative original downstream TE workflow is the frozen reference tree at `/home/xrx/my_project/te_analysis/raw_motheds/TE_model`, not the later engineering wrapper at `/home/xrx/my_project/project/src/te_calc`.

The true original execution path is:

1. `pipeline.bash` dispatches stages by number.
2. Stage 0 runs `python -m trials.<trial>.config`.
3. The trial config calls `src.ribo_counts_to_csv.main(...)`.
4. Stage 1 runs `src/ribobase_counts_processing.py` on the flattened raw count CSVs.
5. Stage 2 runs `Rscript src/TE.R <trial_workdir>`.
6. Stage 3 runs `src/transpose_TE.py`.

The original TE_model does **not** require `all.ribo` as its downstream entrypoint. Its Stage 0 scans `./data/ribo/*/ribo/experiments/*.ribo` and opens experiment-level `.ribo` files directly. `all.ribo` is not referenced in the original TE_model code paths audited here.

Winsorization is not a late CSV post-processing step. It lives inside Stage 0 extraction semantics via the `process_coverage_fn` callback passed from a trial config into `src/ribo_counts_to_csv.py`, where coverage is capped before per-gene counts are summed.

A controlled black-box integration is feasible **without splitting the original methodological logic**, but only if the wrapper stages a legacy-compatible sandbox layout inside the active `te_analysis` repo and runs the original scripts there. Direct execution against `raw_motheds/TE_model` should be avoided because the original code is strongly coupled to `cwd`, `./data`, `./trials`, and hard-coded relative filenames.

## Located source paths

### Authoritative original downstream source tree

- `/home/xrx/my_project/te_analysis/raw_motheds/TE_model/README.md`
- `/home/xrx/my_project/te_analysis/raw_motheds/TE_model/pipeline.bash`
- `/home/xrx/my_project/te_analysis/raw_motheds/TE_model/src/ribo_counts_to_csv.py`
- `/home/xrx/my_project/te_analysis/raw_motheds/TE_model/src/ribobase_counts_processing.py`
- `/home/xrx/my_project/te_analysis/raw_motheds/TE_model/src/TE.R`
- `/home/xrx/my_project/te_analysis/raw_motheds/TE_model/src/transpose_TE.py`
- `/home/xrx/my_project/te_analysis/raw_motheds/TE_model/src/utils.py`
- `/home/xrx/my_project/te_analysis/raw_motheds/TE_model/trials/PAX_hela/config.py`

### Secondary engineering/adaptation tree reviewed for comparison only

- `/home/xrx/my_project/project/src/te_calc/te_calculator.py`
- `/home/xrx/my_project/project/src/te_calc/TE.R`
- `/home/xrx/my_project/project/Makefile`

### Why `raw_motheds/TE_model` is the authoritative original source

Evidence:

- `raw_motheds/TE_model/README.md:27-35` documents the original workflow as trial config plus `bash pipeline.bash -t <DIRECTORY_NAME>`.
- `raw_motheds/TE_model/pipeline.bash:23-41` is the concrete stage runner for the original repo.
- `raw_motheds/TE_model/trials/PAX_hela/config.py:1-14` shows the expected trial-level extraction entry pattern used by that runner.
- By contrast, `/home/xrx/my_project/project/src/te_calc/te_calculator.py` is an expanded wrapper that adds species splitting, pairing enforcement, symlink workdirs, and output relocation not present in the original TE_model.

## True execution graph

### Original execution graph

```text
pipeline.bash
  -> Stage 0: python -m trials.<trial>.config
       -> trial config imports src.ribo_counts_to_csv.main
       -> src.ribo_counts_to_csv.main(...)
       -> writes trials/<trial>/ribo_raw.csv and trials/<trial>/rnaseq_raw.csv

  -> Stage 1: python src/ribobase_counts_processing.py
       inputs: trials/<trial>/ribo_raw.csv, trials/<trial>/rnaseq_raw.csv
       outputs: paired count/CPM/quantile CSVs in trials/<trial>/

  -> Stage 2: Rscript src/TE.R trials/<trial>
       inputs: trials/<trial>/ribo_paired_count_dummy.csv
               trials/<trial>/rna_paired_count_dummy.csv
               data/infor_filter.csv
       outputs: trials/<trial>/human_TE_sample_level.rda
                trials/<trial>/human_TE_cellline_all.csv

  -> Stage 3: python src/transpose_TE.py -o trials/<trial>
       input: trials/<trial>/human_TE_cellline_all.csv
       output: trials/<trial>/human_TE_cellline_all_T.csv
```

### Direct evidence

- `raw_motheds/TE_model/pipeline.bash:23-25`
- `raw_motheds/TE_model/pipeline.bash:27-32`
- `raw_motheds/TE_model/pipeline.bash:36-41`
- `raw_motheds/TE_model/trials/PAX_hela/config.py:1-14`

## Minimal required input contract

This section distinguishes the **true minimal contract of the original code** from extra files present in the repo snapshot.

### Required for original Stage 0 extraction path

#### Experiment-level `.ribo` collection

Required evidence:

- `raw_motheds/TE_model/src/ribo_counts_to_csv.py:19-22`
- `raw_motheds/TE_model/src/ribo_counts_to_csv.py:51-58`
- `raw_motheds/TE_model/src/ribo_counts_to_csv.py:85-93`

Observed contract:

- The code scans `./data/ribo/*/ribo/experiments/*.ribo`.
- It groups files by study directory name extracted from the path.
- It opens one experiment-level `.ribo` per experiment.
- RNA-seq is read from experiment-level `.ribo` via `get_rnaseq()` on the matched experiment file path.

Conclusion:

- **Experiment-level `.ribo` files are the true primary input object.**
- **`all.ribo` is not required by the original TE_model path audited here.**

#### Trial config module under `trials/<trial>/config.py`

Required evidence:

- `raw_motheds/TE_model/README.md:27-35`
- `raw_motheds/TE_model/pipeline.bash:23-25`
- `raw_motheds/TE_model/trials/PAX_hela/config.py:1-14`

Observed contract:

- Stage 0 is not launched by a fixed CLI script alone.
- The original runner expects a Python module at `trials/<trial>/config.py`.
- That module must call `src.ribo_counts_to_csv.main(...)`.

#### Sample selection source

Required evidence:

- `raw_motheds/TE_model/src/ribo_counts_to_csv.py:76-82`

Observed contract:

- If `custom_experiment_list` is not supplied, Stage 0 reads `data/paxdb_filtered_sample.csv` and expects at least `experiment_alias`.
- Therefore the repo-level CSV is part of the default original contract.

Minimal interpretation:

- For a controlled wrapper, this dependency can be minimized by generating a trial config that passes `custom_experiment_list`, because the function signature supports that.
- For the **unmodified default original trial pattern**, `data/paxdb_filtered_sample.csv` is required.

#### RNA-seq embedded in the `.ribo` files for paired TE workflow

Required evidence:

- `raw_motheds/TE_model/src/ribo_counts_to_csv.py:50-58`
- `raw_motheds/TE_model/pipeline.bash:29-31`
- `raw_motheds/TE_model/src/ribobase_counts_processing.py:105-135`
- `raw_motheds/TE_model/src/TE.R:15-18`

Observed contract:

- The audited original pipeline path is hard-wired to the paired branch in Stage 1.
- Stage 0 always emits both `ribo_raw.csv` and `rnaseq_raw.csv`.
- Stage 2 consumes paired count-dummy tables only.

Conclusion:

- The original TE workflow requires a **paired Ribo/RNA input state**.
- A ribo-only `.ribo` handoff is not sufficient for the original TE computation path unless the methodology is changed.

#### `data/nonpolyA_gene.csv`

Required evidence:

- `raw_motheds/TE_model/src/ribobase_counts_processing.py:121-128`

Observed contract:

- The paired preprocessing branch unconditionally reads `./data/nonpolyA_gene.csv`.
- There is no CLI argument in the original script to relocate this file.

Conclusion:

- This sidecar is required for the original paired Stage 1 path.

#### `data/infor_filter.csv`

Required evidence:

- `raw_motheds/TE_model/src/TE.R:59-67`

Observed contract:

- Original `src/TE.R` reads `data/infor_filter.csv` from repo-relative `data/`, not from the trial workdir.
- It then groups sample-level TE by `cell_line` and writes `human_TE_cellline_all.csv`.

Conclusion:

- For the original Stage 2 path to succeed unchanged, `data/infor_filter.csv` is required in the runtime root.

### Required directory layout assumptions

Required evidence:

- `raw_motheds/TE_model/src/ribo_counts_to_csv.py:19-22`
- `raw_motheds/TE_model/src/ribo_counts_to_csv.py:51-58`
- `raw_motheds/TE_model/src/ribo_counts_to_csv.py:85-93`
- `raw_motheds/TE_model/pipeline.bash:29-41`
- `raw_motheds/TE_model/src/ribobase_counts_processing.py:122`
- `raw_motheds/TE_model/src/TE.R:59`

Observed layout assumptions:

```text
<runtime_root>/
  data/
    ribo/<study>/ribo/experiments/<experiment>.ribo
    paxdb_filtered_sample.csv
    nonpolyA_gene.csv
    infor_filter.csv
  trials/<trial>/
    config.py
    ribo_raw.csv
    rnaseq_raw.csv
    ribo_paired_count_dummy.csv
    rna_paired_count_dummy.csv
    ...
  src/
    ribo_counts_to_csv.py
    ribobase_counts_processing.py
    TE.R
    transpose_TE.py
  pipeline.bash
```

## Optional inputs and branch conditions

### Optional within Stage 0

#### `process_coverage_fn`

Evidence:

- `raw_motheds/TE_model/src/ribo_counts_to_csv.py:26-47`
- `raw_motheds/TE_model/trials/PAX_hela/config.py:10-14`

Role:

- If absent, Stage 0 uses `get_region_counts(...)` directly.
- If present, Stage 0 pulls per-position coverage and applies custom logic before summing.
- This is the original winsorization insertion point.

#### `filter`

Evidence:

- `raw_motheds/TE_model/src/ribo_counts_to_csv.py:43-46`
- `raw_motheds/TE_model/src/ribo_counts_to_csv.py:109-111`

Role:

- Optional gene subset restriction during Stage 0 extraction.

#### `custom_experiment_list`

Evidence:

- `raw_motheds/TE_model/src/ribo_counts_to_csv.py:76-82`

Role:

- Allows bypassing `data/paxdb_filtered_sample.csv` for experiment selection.
- Important for controlled wrapper design because it reduces dependency on legacy sample tables.

#### `rnaseq_fn`

Evidence:

- `raw_motheds/TE_model/src/ribo_counts_to_csv.py:60-64`

Role:

- Optional RNA-seq per-gene transformation hook.

### Optional pipeline branch

#### `-n` / `nocutoff`

Evidence:

- `raw_motheds/TE_model/pipeline.bash:4-5`
- `raw_motheds/TE_model/pipeline.bash:18-20`
- `raw_motheds/TE_model/pipeline.bash:27-32`

Role:

- Sets Stage 1 cutoffs to zero by calling `ribobase_counts_processing.py` with `--cpm_cut_off 0 --overall_cut_off 0`.

#### Ribo-only preprocessing branch exists in script, but is not the audited TE pipeline path

Evidence:

- `raw_motheds/TE_model/src/ribobase_counts_processing.py:87-102`

Interpretation:

- The preprocessing script supports `mode == "only"`.
- The original pipeline runner audited here always executes the `paired` branch.
- Therefore ribo-only mode exists as a script capability, but **not** as the original end-to-end TE workflow path.

## Intermediate/output artifact graph

### Stage 0 outputs

Evidence:

- `raw_motheds/TE_model/src/ribo_counts_to_csv.py:116-117`
- `raw_motheds/TE_model/trials/PAX_hela/` file listing

Artifacts:

- `trials/<trial>/ribo_raw.csv`
- `trials/<trial>/rnaseq_raw.csv`

### Stage 1 outputs

Evidence:

- `raw_motheds/TE_model/src/ribobase_counts_processing.py:130-135`
- `raw_motheds/TE_model/trials/PAX_hela/` file listing

Artifacts:

- `trials/<trial>/ribo_paired_count_dummy.csv`
- `trials/<trial>/ribo_paired_cpm_dummy_<cutoff>.csv`
- `trials/<trial>/ribo_paired_quantile_dummy_<cutoff>.csv`
- `trials/<trial>/rna_paired_count_dummy.csv`
- `trials/<trial>/rna_paired_cpm_dummy_<cutoff>.csv`
- `trials/<trial>/rna_paired_quantile_dummy_<cutoff>.csv`

### Stage 2 outputs

Evidence:

- `raw_motheds/TE_model/src/TE.R:56-67`
- `raw_motheds/TE_model/trials/PAX_hela/` file listing

Artifacts:

- `trials/<trial>/human_TE_sample_level.rda`
- `trials/<trial>/human_TE_cellline_all.csv`

### Stage 3 outputs

Evidence:

- `raw_motheds/TE_model/src/transpose_TE.py:9-12`
- `raw_motheds/TE_model/trials/PAX_hela/` file listing

Artifacts:

- `trials/<trial>/human_TE_cellline_all_T.csv`

### Real dependency chain

```text
experiment-level .ribo set
  -> ribo_raw.csv + rnaseq_raw.csv
  -> ribo_paired_count_dummy.csv + rna_paired_count_dummy.csv
  -> human_TE_sample_level.rda
  -> human_TE_cellline_all.csv
  -> human_TE_cellline_all_T.csv
```

Important observation:

- `human_TE_sample_level.rda` is not the final human-facing CSV artifact.
- `human_TE_cellline_all.csv` depends on `data/infor_filter.csv` in Stage 2.
- `human_TE_cellline_all_T.csv` is a pure transpose/post-formatting product of Stage 3.

## Exact location and role of winsorization

### Location

Evidence:

- `raw_motheds/TE_model/README.md:13`
- `raw_motheds/TE_model/trials/PAX_hela/config.py:10-14`
- `raw_motheds/TE_model/src/ribo_counts_to_csv.py:26-47`
- `raw_motheds/TE_model/src/utils.py:72-80`

### Role

- Trial config defines `process_coverage_fn`.
- `process_coverage_fn` calls `cap_outliers_cds_only(..., 99.5).sum()`.
- `src.ribo_counts_to_csv.py` switches from `get_region_counts(...)` to `get_coverage(...)`, applies the callback per gene, and only then produces per-gene counts.

### Exact stage placement

Winsorization is:

- inside Stage 0 extraction,
- before `ribo_raw.csv` is written,
- before CPM/dummy-gene/non-polyA filtering,
- before `TE.R`.

It is **not**:

- a late-stage normalization over already finalized raw CSVs,
- a Stage 1 filtering function,
- a TE.R-side operation.

## Path-coupling and legacy-layout dependencies

### Strong `cwd` coupling

Evidence:

- `raw_motheds/TE_model/src/ribo_counts_to_csv.py:20`
- `raw_motheds/TE_model/src/ribo_counts_to_csv.py:52`
- `raw_motheds/TE_model/src/ribo_counts_to_csv.py:80`
- `raw_motheds/TE_model/src/ribo_counts_to_csv.py:85`
- `raw_motheds/TE_model/src/ribobase_counts_processing.py:122`
- `raw_motheds/TE_model/src/TE.R:59`
- `raw_motheds/TE_model/src/utils.py:99`

Observed issues:

- Relative reads from `./data/...` are hard-coded.
- Trial outputs are expected under `trials/<trial>/`.
- `TE.R` mixes workdir-relative inputs with repo-root-relative `data/infor_filter.csv`.
- `utils.py` contains a human FASTA hard-coded as `data/appris_human_v2_selected.fa.gz`.

### Strong filename coupling

Evidence:

- `raw_motheds/TE_model/pipeline.bash:29-31`
- `raw_motheds/TE_model/src/TE.R:16-17`
- `raw_motheds/TE_model/src/transpose_TE.py:9-12`

Observed assumptions:

- `ribo_raw.csv`
- `rnaseq_raw.csv`
- `ribo_paired_count_dummy.csv`
- `rna_paired_count_dummy.csv`
- `human_TE_sample_level.rda`
- `human_TE_cellline_all.csv`

These names are not parameterized in the original workflow.

### Legacy repo pollution risk if run in place

Reason:

- The original code writes directly into `trials/<trial>/`.
- The original code also expects mutable `data/` sidecars at runtime.
- Running it inside `raw_motheds/TE_model` would create new files in the frozen reference tree, which violates current project boundaries.

## Black-box integration feasibility verdict

**Verdict: feasible, with a staged sandbox wrapper.**

### Why feasible

- The original methodology is already separated into a stable script chain:
  - `pipeline.bash`
  - `src/ribo_counts_to_csv.py`
  - `src/ribobase_counts_processing.py`
  - `src/TE.R`
  - `src/transpose_TE.py`
- The pipeline is file-driven and can be satisfied by filesystem staging rather than code rewriting.
- It uses experiment-level `.ribo` inputs directly, which matches the current `te_analysis` handoff boundary better than an `all.ribo`-only contract would.

### What prevents direct in-place reuse

- Hard-coded relative paths.
- Hard-coded legacy directory names (`data`, `trials`).
- Hard-coded sidecar filenames (`data/nonpolyA_gene.csv`, `data/infor_filter.csv`).
- Trial-config driven Stage 0 dispatch.

### Implication

The safe wrapper must not call the original code against the frozen reference tree. It must instead materialize a **legacy-compatible runtime sandbox** under the active `te_analysis` repo and execute the original code there.

## Recommended thin-wrapper boundary

### Recommended boundary

The thinnest safe wrapper is:

1. Create a per-run sandbox inside `te_analysis`.
2. Stage or symlink the original TE_model source files into that sandbox.
3. Stage experiment-level `.ribo` inputs into the sandbox under the exact layout expected by original Stage 0.
4. Stage required sidecars into sandbox `data/`.
5. Generate a run-specific trial config under sandbox `trials/<run_id>/config.py`.
6. Invoke original `pipeline.bash -t <run_id>` from the sandbox root.
7. Collect and manifest outputs back into controlled downstream result directories.

### Why this boundary is preferable

- It preserves original stage decomposition and script semantics.
- It avoids re-implementing winsorization, filtering, or TE.R logic.
- It allows wrapper-side control over all file placement.
- It avoids writes into `raw_motheds/TE_model`.

### Recommended wrapper inputs

From `te_analysis` side, the wrapper should accept:

- a validated handoff manifest containing experiment-level `.ribo` paths,
- required sidecars declared explicitly, including:
  - `nonpolyA_gene.csv`,
  - a TE grouping table compatible with `infor_filter.csv` semantics,
- an explicit run identifier,
- an execution mode describing whether original Stage 0 should run with:
  - raw default counts, or
  - trial-supplied winsorization callback.

### Whether `all.ribo` should be materialized

Audit verdict:

- **Not required for the original TE_model workflow audited here.**
- Therefore the wrapper should **not** treat `all.ribo` as mandatory.
- If later compatibility work reveals another legacy branch needing `all.ribo`, that should be an explicit optional compatibility shim, not the default contract.

## Recommended controlled output directory design

### Recommended controlled output root

Use a dedicated downstream runtime root inside the active repo:

```text
/home/xrx/my_project/te_analysis/data/downstream_runs/
```

### Per-run layout proposal

```text
/home/xrx/my_project/te_analysis/data/downstream_runs/<run_id>/
  handoff/
    handoff_manifest.json
    sidecars_manifest.json

  sandbox/
    pipeline.bash
    src/
    data/
      ribo/
        <study>/ribo/experiments/<experiment>.ribo
      nonpolyA_gene.csv
      infor_filter.csv
      paxdb_filtered_sample.csv
    trials/
      <run_id>/
        config.py
        ribo_raw.csv
        rnaseq_raw.csv
        ribo_paired_count_dummy.csv
        rna_paired_count_dummy.csv
        human_TE_sample_level.rda
        human_TE_cellline_all.csv
        human_TE_cellline_all_T.csv

  outputs/
    raw_legacy_trial_outputs/
    packaged/
      te_sample_level.rda
      te_cellline.csv
      te_cellline_transposed.csv
      output_manifest.json

  logs/
    pipeline.stdout.log
    pipeline.stderr.log
    wrapper_provenance.json
```

### Directory policy

- `handoff/`
  - immutable input contract and sidecar declarations.
- `sandbox/`
  - legacy-compatible execution root for the original black-box code.
  - safe to delete/rebuild per run.
- `outputs/raw_legacy_trial_outputs/`
  - preserved copy of original trial outputs for auditability.
- `outputs/packaged/`
  - stable wrapper-facing outputs exposed to the rest of `te_analysis`.
- `logs/`
  - all command logs and wrapper provenance.

### Why this layout is safe

- It keeps all generated files inside the active repo.
- It isolates each run by `<run_id>`.
- It prevents pollution of repo root and frozen legacy trees.
- It separates staged inputs, transient execution residue, and packaged outputs.

## Risks / unknowns / follow-up checks

### Risk 1: Original Stage 2 grouping sidecar semantics are under-specified

Evidence:

- `raw_motheds/TE_model/src/TE.R:59-67` uses `data/infor_filter.csv`.
- The file schema appears to require at least `experiment_alias` and `cell_line`.

Follow-up:

- Confirm whether future studies require tissue/grouping semantics beyond the two visible columns.

### Risk 2: Human-specific assumptions may leak into supposedly generic runs

Evidence:

- `raw_motheds/TE_model/src/utils.py:99-103` uses `data/appris_human_v2_selected.fa.gz`.
- `raw_motheds/TE_model/src/TE.R` writes outputs named `human_TE_*`.

Interpretation:

- The original TE_model snapshot is not fully abstracted over organism naming or references.
- A wrapper can still treat the methodology as black-box, but should record these assumptions and avoid silently rebranding them.

### Risk 3: The original trial/config layer is part of the method surface

Evidence:

- `raw_motheds/TE_model/pipeline.bash:23-25`
- `raw_motheds/TE_model/trials/PAX_hela/config.py:1-14`

Interpretation:

- Winsorization policy enters through trial config, not a centralized CLI flag.
- The wrapper must therefore own config generation carefully if it wants deterministic run provenance.

### Risk 4: The secondary engineering wrapper (`project/src/te_calc`) is useful as a compatibility reference, but should not replace the original audit target

Reason:

- It demonstrates one way to decouple hard-coded filenames using symlink workdirs.
- However, it is already a modified orchestration layer, not the original TE_model source of truth.

### Final recommendation

Proceed with a thin wrapper around the original TE_model **only through a staged sandbox runtime inside `te_analysis`**. Do not split winsorization/filtering/TE.R into new local implementations at this stage. The next implementation step can be a wrapper that materializes the sandbox layout above and invokes the original stage chain unchanged.
