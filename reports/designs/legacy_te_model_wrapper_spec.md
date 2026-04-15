# Legacy TE_model Thin-Wrapper Specification

## Executive decision

This document freezes the v1 thin-wrapper interface for controlled black-box integration of the original downstream workflow located at `/home/xrx/my_project/te_analysis/raw_motheds/TE_model`.

### Design status

- **Audit-proven facts** in this document are derived from:
  - `/home/xrx/my_project/te_analysis/reports/audits/te_model_downstream_contract_audit.md`
  - `/home/xrx/my_project/te_analysis/reports/audits/te_model_downstream_contract_audit.json`
- **Implementation choices for `te_analysis`** are explicit design decisions made here to reduce ambiguity for a later implementation.
- **Open issues** are intentionally separated and are not silently treated as resolved facts.

### Final v1 decision

The original `raw_motheds/TE_model` downstream will be integrated only through a **controlled sandboxed thin wrapper**.

The wrapper will:

- accept **experiment-level `.ribo`** as the primary handoff object,
- reject RNA-seq-absent handoff for original black-box TE mode,
- materialize a legacy-compatible runtime sandbox under `te_analysis`,
- preserve raw legacy outputs separately from stable packaged outputs,
- avoid any reimplementation of winsorization, filtering, or `TE.R` logic.

The wrapper will **not**:

- execute in place inside the frozen legacy tree,
- require `all.ribo` by default,
- claim ribo-only TE support,
- generalize the original methodology beyond audited assumptions.

## Wrapper boundary

### Wrapper name

The wrapper name is frozen as:

- `legacy_te_model_wrapper`

Recommended future package location:

- `src/te_analysis/downstream/legacy_te_model/`

### Responsibility boundary

#### What the wrapper owns

The wrapper owns only the integration boundary around the original legacy pipeline:

- input contract validation,
- rejection before execution,
- sandbox materialization under `data/downstream_runs/<run_id>/sandbox/`,
- generation of the run-specific `trials/<run_id>/config.py`,
- provenance capture,
- stable output packaging,
- separation of transient legacy runtime residue from packaged outputs.

#### What the wrapper does not own

The wrapper deliberately does **not** own:

- the internal method semantics of Stage 0 extraction,
- winsorization math,
- dummy-gene logic,
- non-polyA filtering logic,
- CLR/ILR regression logic in `TE.R`,
- direct changes to `raw_motheds/TE_model`,
- broader TEC or other downstream extensions,
- organism-generalized reinterpretation of legacy outputs.

### Boundary statement

The v1 wrapper is an **integration-and-contract layer**, not a method implementation layer.

## Input contract

### Canonical wrapper request

The wrapper request is defined as a design-level contract with the following fields:

```text
wrapper_name: legacy_te_model_wrapper
run_id: <string>
execution_mode: legacy_default_counts | legacy_winsorized_counts
handoff_manifest_path: <absolute path>
sidecars:
  nonpolya_csv: <absolute path>
  grouping_csv: <absolute path>
  sample_selection_csv: <absolute path, optional>
source_legacy_root: /home/xrx/my_project/te_analysis/raw_motheds/TE_model
runtime_root: /home/xrx/my_project/te_analysis/data/downstream_runs/<run_id>
```

### Required fields

#### `run_id`

Requirements:

- non-empty string,
- unique per logical run,
- filesystem-safe,
- must match regex: `^[A-Za-z0-9][A-Za-z0-9._-]{2,127}$`.

Design choice:

- `run_id` becomes both the runtime namespace and the legacy trial directory name.
- Therefore it must be valid as `trials/<run_id>/` without shell escaping tricks.

#### `execution_mode`

Allowed enum:

- `legacy_default_counts`
- `legacy_winsorized_counts`

Any other value must be rejected.

#### `handoff_manifest_path`

This is the primary input contract object for the wrapper.

Requirements:

- absolute path,
- JSON file,
- immutable snapshot for one run,
- must enumerate **experiment-level `.ribo`** inputs explicitly,
- must not rely on directory scanning alone as the logical contract.

### Handoff manifest schema

The wrapper handoff manifest must contain at minimum:

```json
{
  "manifest_version": "1.0",
  "run_id": "example_run",
  "input_mode": "experiment_level_ribo",
  "experiments": [
    {
      "experiment_alias": "GSM123456",
      "study_id": "study_a",
      "ribo_path": "/abs/path/to/GSM123456.ribo",
      "organism": "human",
      "has_rnaseq": true
    }
  ]
}
```

#### Required handoff manifest semantics

- `manifest_version`
  - required string
  - v1 must be `1.0`
- `run_id`
  - must equal wrapper request `run_id`
- `input_mode`
  - v1 must be `experiment_level_ribo`
- `experiments`
  - non-empty array
  - each row represents one experiment-level `.ribo`

#### Required experiment record fields

- `experiment_alias`
  - unique within the manifest
  - must match grouping sidecar key semantics
- `study_id`
  - required
  - used to materialize legacy layout: `data/ribo/<study_id>/ribo/experiments/<experiment>.ribo`
- `ribo_path`
  - absolute path
  - must point to an existing `.ribo` file
- `organism`
  - required string
  - v1 accepted set is intentionally narrow; see rejection rules
- `has_rnaseq`
  - required boolean
  - must be `true` for v1 black-box TE mode

### Experiment-level `.ribo` collection requirements

Audit-proven facts:

- original Stage 0 reads experiment-level `.ribo`, not `all.ribo`,
- original paired TE path expects RNA-seq information retrievable from experiment `.ribo` inputs.

Implementation choices for `te_analysis`:

- the wrapper will treat the handoff manifest as authoritative,
- the wrapper will require that each listed `.ribo` is materializable into the sandbox under a study-scoped path,
- the wrapper will reject manifests where one `experiment_alias` maps to more than one `.ribo` input.

### Requirement for embedded RNA-seq

The wrapper requires a paired Ribo/RNA input state for v1 black-box TE mode.

This means:

- every experiment record must declare `has_rnaseq: true`,
- wrapper validation must perform a mandatory **dual validation** before execution:
  - manifest-level declaration: every experiment record must declare `has_rnaseq: true`,
  - wrapper-side read-only verification: the wrapper must inspect the actual `.ribo` file content and verify that RNA-seq content is present for the same experiment before execution,
- validation succeeds only if both the manifest declaration and the `.ribo` inspection are positive,
- implementation may choose the concrete inspection routine later, but it may not legally skip `.ribo` inspection in v1,
- wrapper validation must reject any handoff where one or more `.ribo` objects are known or observed to lack RNA-seq content,
- ribo-only handoff is out of scope for v1.

### Required sidecars

The wrapper requires the following sidecars:

- `nonpolya_csv`
- `grouping_csv`

The following sidecar is conditionally optional:

- `sample_selection_csv`

Design choice:

- if the generated legacy trial config passes `custom_experiment_list`, `sample_selection_csv` is optional,
- if implementation later chooses not to pass `custom_experiment_list`, then `sample_selection_csv` becomes mandatory,
- v1 spec freezes the preferred design as **passing `custom_experiment_list`**, so `sample_selection_csv` remains optional.

## Rejection rules

The wrapper must reject inputs **before any runtime materialization** when any rule below is violated.

### Manifest-level rejection rules

- reject if `handoff_manifest_path` is missing
- reject if manifest is not valid JSON
- reject if `manifest_version != "1.0"`
- reject if manifest `run_id` does not equal request `run_id`
- reject if `input_mode != "experiment_level_ribo"`
- reject if `experiments` is empty

### `.ribo` input rejection rules

- reject if any `ribo_path` does not exist
- reject if any `ribo_path` is not an experiment-level `.ribo`
- reject if `.ribo` suffix is absent
- reject if the same `experiment_alias` appears more than once
- reject if the same `.ribo` path is mapped to conflicting `study_id` values
- reject if `study_id` is empty or ambiguous
- reject if two records would materialize to the same sandbox path

### RNA-seq rejection rules

- reject if any experiment record has `has_rnaseq != true`
- reject if the handoff is explicitly described as ribo-only
- reject if the caller attempts to use black-box TE mode on RNA-seq-absent `.ribo` inputs

### `all.ribo` rejection rules

- reject if `all.ribo` is provided as the sole input object and no experiment-level `.ribo` records are present
- reject if the caller attempts to substitute one `all.ribo` path for the required `experiments[]` list

Clarification:

- `all.ribo` may exist elsewhere in the project,
- but it is not part of the v1 required wrapper contract,
- and it cannot satisfy the handoff by itself.

### Sidecar rejection rules

- reject if `nonpolya_csv` is missing
- reject if `grouping_csv` is missing
- reject if required columns are absent from either sidecar
- reject if `grouping_csv` has duplicate `experiment_alias` rows unless a later version explicitly defines dedup semantics
- reject if `grouping_csv` lacks coverage for one or more experiment aliases present in the handoff manifest
- reject if `sample_selection_csv` is supplied but lacks required schema

### Execution mode rejection rules

- reject if `execution_mode` is not one of the frozen enum values
- reject if `legacy_winsorized_counts` is requested together with a custom non-legacy winsorization policy
- reject if a caller requests a new counting mode not present in the original audited method surface

### Organism / legacy-assumption rejection rules

Audit-proven facts:

- original code and naming contain human-specific assumptions,
- hard-coded references and output names are not fully organism-agnostic.

v1 design choice:

- accept only manifests where all experiment records share the same `organism`,
- reject mixed-organism handoff,
- reject organisms not explicitly approved by the implementation configuration,
- the default approved v1 assumption is `human` unless later implementation evidence broadens this safely.

## Sidecar schemas

### `nonpolya_csv`

Audit-proven facts:

- original paired preprocessing reads `./data/nonpolyA_gene.csv`,
- the audited legacy file header is `Gene,GENE_true,anno`.

v1 sidecar schema requirement:

- CSV file
- required column: `Gene`
- optional columns:
  - `GENE_true`
  - `anno`

Semantics:

- `Gene` is the authoritative identifier used for exclusion matching against gene rows in the count tables.
- Additional columns may be preserved for provenance but are not required for v1 validation.

Rejection rules:

- reject if `Gene` column is absent
- reject if all `Gene` values are empty

### `grouping_csv`

Audit-proven facts:

- original `TE.R` reads `data/infor_filter.csv`,
- observed columns are `experiment_alias` and `cell_line`.

v1 sidecar schema requirement:

- CSV file
- required columns:
  - `experiment_alias`
  - `cell_line`
- optional columns:
  - implementation-specific provenance columns

Semantics:

- one row per experiment alias expected by Stage 2 grouping,
- `experiment_alias` must match handoff manifest records exactly,
- `cell_line` is the legacy grouping label consumed by black-box output aggregation.

Rejection rules:

- reject if either required column is absent
- reject if `experiment_alias` contains duplicates
- reject if any experiment alias in the handoff manifest is missing from `grouping_csv`
- reject if `cell_line` is empty for any required row

### `sample_selection_csv`

Audit-proven facts:

- original Stage 0 defaults to `data/paxdb_filtered_sample.csv` when `custom_experiment_list` is not provided,
- only `experiment_alias` is clearly required by the default selection path.

v1 design choice:

- preferred implementation should avoid requiring this file by generating `custom_experiment_list` in `trials/<run_id>/config.py`.
- therefore this sidecar is optional in v1.

If provided, minimum schema:

- required column:
  - `experiment_alias`
- optional columns:
  - any study metadata retained for provenance

## Sandbox materialization contract

### Runtime root

All wrapper-generated artifacts must stay inside:

```text
/home/xrx/my_project/te_analysis/data/downstream_runs/<run_id>/
```

This is a hard requirement.

### Required directory tree

The wrapper must materialize the following structure conceptually:

```text
/home/xrx/my_project/te_analysis/data/downstream_runs/<run_id>/
  handoff/
    handoff_manifest.json
    sidecars_manifest.json
    wrapper_request.json

  sandbox/
    pipeline.bash
    src/
      __init__.py
    data/
      ribo/
        <study_id>/ribo/experiments/<experiment_alias>.ribo
      nonpolyA_gene.csv
      infor_filter.csv
      paxdb_filtered_sample.csv                  # optional in v1
    trials/
      __init__.py
      <run_id>/
        __init__.py
        config.py

  outputs/
    raw_legacy_trial_outputs/
    packaged/
      te_sample_level.rda
      te_cellline.csv
      te_cellline_transposed.csv
      output_manifest.json

  logs/
    materialization.log
    pipeline.stdout.log
    pipeline.stderr.log
    wrapper_provenance.json
```

### Symlink vs copy rules

v1 design choice:

- original legacy source files may be **symlinked** into `sandbox/` if implementation guarantees read-only source preservation,
- input `.ribo` files may be **symlinked** into `sandbox/data/ribo/...` by default,
- sidecars should be **copied** into sandbox canonical names to ensure immutable run-local provenance,
- generated files under `trials/<run_id>/` must be newly created inside the runtime root,
- packaged outputs must be copied from legacy trial outputs into stable filenames.

Reasoning:

- symlinking source and large `.ribo` inputs minimizes duplication,
- copying small sidecars prevents later external edits from silently changing run meaning,
- packaging should be stable even if sandbox is later deleted.

### Minimal Python module/package materialization rules

Because the original Stage 0 entrypoint is executed as `python -m trials.<run_id>.config`, the sandbox must be materialized in a way that is compatible with Python module execution.

The wrapper must therefore ensure all of the following:

- the module launch working directory is the sandbox root,
- `sandbox/trials/__init__.py` must exist,
- `sandbox/trials/<run_id>/__init__.py` must exist,
- `sandbox/src/__init__.py` must exist,
- `sandbox/trials/<run_id>/config.py` must exist and be importable as `trials.<run_id>.config`,
- sandbox `src/` and `trials/` must be top-level entries directly under the sandbox root,
- the generated trial config must be executable without requiring packaging, installation, or path mutation outside the sandbox root.

This spec intentionally freezes only the minimum rules required for reliable module resolution. It does not introduce a broader packaging framework.

### `trials/<run_id>/config.py` semantics

The wrapper-generated trial config is part of the controlled integration surface.

It must:

- import original legacy Stage 0 entry functions from sandbox `src/`,
- set `workdir` to the generated `trials/<run_id>/` directory,
- define the selected legacy execution behavior based on `execution_mode`,
- pass `custom_experiment_list` derived from the handoff manifest,
- avoid introducing any new method semantics beyond the selected legacy mode.

For `legacy_default_counts`:

- `process_coverage_fn` must be absent or equivalent to the original default non-custom counting path.

For `legacy_winsorized_counts`:

- `process_coverage_fn` must follow the audited callback/function chain observed in `raw_motheds/TE_model/trials/PAX_hela/config.py:10-14`,
- the callback chain is:
  - `process_coverage_fn(coverage, gene, ribo)`
  - `boundary_lookup = get_cds_range_lookup(ribo)`
  - `cap_outliers_cds_only(coverage, gene, boundary_lookup, 99.5).sum()`
- coverage must be obtained by the original Stage 0 `get_coverage(...)` path before the callback is applied,
- CDS-only capping must happen before aggregation to a scalar count,
- the capping percentile is frozen at `99.5` for v1 because that is the concrete audited trial callback evidence,
- the wrapper may not substitute `cap_outliers`, may not cap after summation, may not change the percentile, may not switch to a different region than CDS, and may not introduce extra wrapper-defined transformations before or after the capping-and-sum step,
- if later implementation cannot reproduce this exact callable chain inside the generated legacy trial config, it must reject `legacy_winsorized_counts` rather than silently reinterpret it.

Clarification:

- the audited evidence supports one exact legacy callback pattern from `trials/PAX_hela/config.py`,
- the spec freezes that pattern as the v1 meaning of `legacy_winsorized_counts`,
- this does not claim that every historical legacy trial used the same callback, only that v1 wrapper semantics are intentionally pinned to this audited pattern.

### Provenance files required at materialization time

The wrapper must write:

- `handoff/handoff_manifest.json`
  - exact input manifest snapshot used for the run
- `handoff/sidecars_manifest.json`
  - absolute source paths, copied target paths, checksums if implementation later supports them
- `handoff/wrapper_request.json`
  - normalized request after validation
- `logs/wrapper_provenance.json`
  - wrapper name, wrapper spec version, source legacy root, execution mode, run_id, timestamps, materialization policy

## Output contract

### Raw legacy outputs

The wrapper must preserve raw outputs generated by the legacy pipeline separately from packaged outputs.

Required preservation location:

```text
/home/xrx/my_project/te_analysis/data/downstream_runs/<run_id>/outputs/raw_legacy_trial_outputs/
```

At minimum, this preserved set must include if generated:

- `ribo_raw.csv`
- `rnaseq_raw.csv`
- `ribo_paired_count_dummy.csv`
- `rna_paired_count_dummy.csv`
- `ribo_paired_cpm_dummy_<cutoff>.csv`
- `rna_paired_cpm_dummy_<cutoff>.csv`
- `ribo_paired_quantile_dummy_<cutoff>.csv`
- `rna_paired_quantile_dummy_<cutoff>.csv`
- `human_TE_sample_level.rda`
- `human_TE_cellline_all.csv`
- `human_TE_cellline_all_T.csv`
- generated `config.py`

### Packaged stable outputs

The wrapper-facing canonical outputs live under:

```text
/home/xrx/my_project/te_analysis/data/downstream_runs/<run_id>/outputs/packaged/
```

Canonical filenames are frozen as:

- `te_sample_level.rda`
- `te_cellline.csv`
- `te_cellline_transposed.csv`
- `output_manifest.json`

### Canonical output mapping

The stable mapping is:

- legacy `human_TE_sample_level.rda`
  -> packaged `te_sample_level.rda`
- legacy `human_TE_cellline_all.csv`
  -> packaged `te_cellline.csv`
- legacy `human_TE_cellline_all_T.csv`
  -> packaged `te_cellline_transposed.csv`

### `output_manifest.json` minimum schema

```json
{
  "wrapper_name": "legacy_te_model_wrapper",
  "spec_version": "1.0",
  "run_id": "example_run",
  "execution_mode": "legacy_default_counts",
  "runtime_root": "/home/xrx/my_project/te_analysis/data/downstream_runs/example_run",
  "raw_legacy_outputs_dir": "/.../outputs/raw_legacy_trial_outputs",
  "packaged_outputs": {
    "te_sample_level_rda": "/.../outputs/packaged/te_sample_level.rda",
    "te_cellline_csv": "/.../outputs/packaged/te_cellline.csv",
    "te_cellline_transposed_csv": "/.../outputs/packaged/te_cellline_transposed.csv"
  }
}
```

## Run modes

### `legacy_default_counts`

Definition:

- Use the original Stage 0 extraction path without a custom legacy winsorization callback.

Operational meaning:

- the generated trial config must select the legacy non-custom counting behavior,
- no new wrapper-defined preprocessing stage is allowed,
- downstream Stage 1, Stage 2, and Stage 3 semantics remain unchanged.

### `legacy_winsorized_counts`

Definition:

- Use the original Stage 0 extraction path with the exact audited `process_coverage_fn` pattern frozen in this spec: `boundary_lookup = get_cds_range_lookup(ribo)` followed by `cap_outliers_cds_only(coverage, gene, boundary_lookup, 99.5).sum()`.

Operational meaning:

- the generated trial config must encode the exact audited callback chain defined in the `trials/<run_id>/config.py` semantics section above,
- winsorization remains inside Stage 0 extraction,
- no separate wrapper-side winsorization stage may be introduced.

### Not allowed as run modes

The following are explicitly out of scope for v1:

- ribo-only TE mode
- direct `all.ribo` compatibility mode
- mixed-organism batch mode
- wrapper-native alternate filtering mode
- wrapper-native alternate TE regression mode

## Logging and provenance

### Required logs

The wrapper implementation must capture at minimum:

- `logs/materialization.log`
- `logs/pipeline.stdout.log`
- `logs/pipeline.stderr.log`
- `logs/wrapper_provenance.json`

### `wrapper_provenance.json` minimum fields

- `wrapper_name`
- `spec_version`
- `run_id`
- `execution_mode`
- `legacy_source_root`
- `sandbox_root`
- `raw_outputs_root`
- `packaged_outputs_root`
- `materialization_policy`
- `sidecar_targets`
- `timestamps`

### Provenance principles

- provenance must distinguish source paths from sandbox-local staged paths,
- provenance must record whether each staged artifact was copied or symlinked,
- provenance must record the exact generated `config.py` path,
- provenance must not claim biological or methodological interpretation beyond file-contract facts.

## Failure semantics

### Validation failure semantics

If validation fails before materialization:

- no sandbox execution is allowed,
- failure must be reported as a contract violation,
- failure caused by RNA-seq validation must distinguish:
  - manifest-declaration failure,
  - `.ribo` inspection failure,
  - manifest/inspection contradiction,
- the error message must identify the exact missing or invalid field/path.

### Materialization failure semantics

If validation passes but sandbox setup fails:

- no attempt should be made to run the legacy pipeline,
- failure must identify the exact path or copy/symlink step that failed,
- partially created runtime roots may remain for debugging, but must be clearly marked incomplete in provenance.

### Execution-phase failure semantics

This spec does not implement execution yet, but v1 behavior is frozen conceptually:

- legacy subprocess failure must not be rewritten as success,
- partial legacy outputs may be preserved under `outputs/raw_legacy_trial_outputs/` for debugging,
- packaged outputs must only be created for artifacts that are actually generated and verified.

## Non-goals

The following are explicit non-goals for v1:

- no direct in-place execution inside `/home/xrx/my_project/te_analysis/raw_motheds/TE_model`
- no ribo-only TE black-box mode
- no requirement that `all.ribo` be present by default
- no use of `all.ribo` as the sole required input object
- no new internal reimplementation of original Stage 0, Stage 1, Stage 2, or Stage 3 logic
- no new standalone winsorization stage
- no species-generalization claims beyond audited assumptions
- no production integration wiring in this specification task
- no expansion into TEC or unrelated downstream methods

## Open issues for later implementation

### Open issue 1: Exact approved organism allowlist

Audit-proven facts:

- legacy code contains human-specific assumptions,
- organism generalization is not fully audited.

Unresolved implementation question:

- whether v1 should hard-freeze `human` only,
- or support a small explicit allowlist after additional evidence review.

### Open issue 2: Whether `sample_selection_csv` should ever be staged in v1

Preferred design choice:

- use `custom_experiment_list` and avoid making `paxdb_filtered_sample.csv` mandatory.

Unresolved implementation question:

- whether implementation wants to also stage a generated `paxdb_filtered_sample.csv` for maximal legacy observability, even when not strictly required.

### Open issue 3: Stable checksum policy

Design choice:

- provenance should ideally record checksums for staged files.

Unresolved implementation question:

- whether checksums are mandatory in v1 implementation or only recommended.

### Open issue 4: Canonical failure code taxonomy

This spec freezes failure categories conceptually, but not exact machine-readable error codes.

A later implementation may define:

- validation errors,
- materialization errors,
- legacy subprocess errors,
- packaging errors,

as a more detailed code system without changing the core wrapper contract.
