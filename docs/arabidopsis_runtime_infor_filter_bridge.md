# Arabidopsis Runtime `infor_filter.csv` Bridge

## Purpose

This note freezes the minimal runtime-local `infor_filter.csv` bridge added for the bounded `Arabidopsis_thaliana` smoke candidate.

Current bounded scope:

- `GSE50597`
- `GSE109122`

This bridge exists to close the already proven earliest downstream contract blocker without modifying any tracked file under shared `vendor/TE_model`.

## Source-Verified Minimal Contract

The minimal contract is verified from shared `vendor/TE_model/src/TE.R`.

Relevant code path:

```r
infor <- read.csv("data/infor_filter.csv")
df <- merge(infor, t(human_TE), by.x = "experiment_alias", by.y = 0)
df_cell_line <- df %>%
  group_by(cell_line) %>%
  summarize(across(where(is.numeric), mean))
```

Verified consequences:

- `TE.R` reads `data/infor_filter.csv` relative to the execution `cwd`
- the merge key is `experiment_alias`
- the grouping key is `cell_line`

Therefore, the minimal row-level contract consumed by `TE.R` is:

- `experiment_alias`
- `cell_line`

Shared `vendor/TE_model/data/infor_filter.csv` currently contains:

- `Unnamed: 0`
- `experiment_alias`
- `cell_line`

The runtime-local bridge preserves this shared column shape and overlays only the missing candidate experiment rows.

## Metadata Provenance

The bridge does not guess values.

It reads project metadata from:

- `data/raw/metadata.csv`

using the same header convention already used elsewhere in the project:

- `pd.read_csv(..., header=1, dtype=str, keep_default_na=False)`

For the runtime-local bridge, the project-owned code only synthesizes:

- `experiment_alias`
- `cell_line`

from metadata rows matching the trial `custom_experiment_list`.

## Where the Bridge Is Written

The bridge is materialized by project-owned code in:

- `src/te_analysis/run_species_downstream.py`

When `--infor-filter-mode runtime-local` is selected, the bridge is written to:

- `<runtime-root>/data/infor_filter.csv`

For a normal species prepare tree, that means:

- `<species-root>/runtime/vendor/TE_model/data/infor_filter.csv`

The bridge log is written to:

- `<species-root>/logs/infor_filter.bridge.<timestamp>.log`

## Execution Semantics

When `--infor-filter-mode shared` is used:

- Stage 2 runs with `cwd = shared vendor/TE_model`
- shared `vendor/TE_model/data/infor_filter.csv` is used directly

When `--infor-filter-mode runtime-local` is used:

- the runtime-local bridge is materialized first
- Stage 2 runs with `cwd = <runtime-root>`
- Stage 2 still executes shared vendor code via script path:
  - shared `vendor/TE_model/src/TE.R`
  - or the project-owned serial patched copy derived from that source
- Stage 3 still executes shared vendor:
  - `vendor/TE_model/src/transpose_TE.py`

This keeps vendor code immutable while letting `TE.R` resolve `data/infor_filter.csv` from the runtime-local execution root.

## Why This Does Not Violate Vendor Immutability

This bridge does **not**:

- edit `vendor/TE_model/data/infor_filter.csv`
- edit `vendor/TE_model/src/TE.R`
- edit `vendor/TE_model/src/transpose_TE.py`
- change vendor submodule SHA

Instead, it:

- reads the shared vendor file as the base
- overlays project-owned runtime rows
- writes only into the species runtime tree

So the shared vendor repository remains the source of truth for code and base data, while the bounded Arabidopsis smoke gets a runtime-local compatibility layer.

## Scope Boundary

This bridge is intentionally narrow.

It is **not**:

- a general all-organism metadata migration
- a rewrite of Stage 2 math
- a change to `aggregate_species_te.py`
- a full runtime clone of shared vendor

It only makes the current bounded Arabidopsis candidate bridgeable for the next step:

- a bounded species smoke using project-owned runtime inputs plus shared vendor code.
