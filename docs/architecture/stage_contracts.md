# Stage Contracts

## Stage table

| Stage | Layer | Method owner | Primary input | Primary output | Config owner |
| --- | --- | --- | --- | --- | --- |
| local staged FASTQ | upstream | local wrapper | `data/raw/fastq/` | validated local FASTQ set | `configs/pipeline/*.yaml` |
| SnakeScale orchestration | upstream | SnakeScale | validated local FASTQ + study config | resolved upstream run config | `configs/upstream/snakescale.yaml` |
| RiboFlow execution | upstream | RiboFlow | resolved upstream run config | experiment-level `.ribo` + optional `all.ribo` | `configs/upstream/riboflow.yaml` |
| handoff manifest | handoff | local wrapper | upstream `.ribo` outputs + sidecars | explicit handoff manifest | `configs/pipeline/te_only.yaml` |
| downstream extraction | downstream | TE_model semantics | experiment-level `.ribo` collection + sidecars | downstream raw count tables | `configs/downstream/te_model.yaml` |
| downstream winsorization | downstream | TE_model semantics | extracted downstream coverage/count objects | winsorized downstream count objects | `configs/downstream/winsorization.yaml` |
| downstream filtering | downstream | TE_model semantics | winsorized count objects | filtered / dummy-gene adjusted tables | `configs/downstream/te_model.yaml` |
| downstream TE compute | downstream | TE_model semantics | filtered count tables | TE outputs | `configs/downstream/te_model.yaml` |

## Contract rules

### Upstream rules

- Upstream consumes externally prepared FASTQ files only.
- Upstream local wrappers may invoke reference backends, but must not import backend code into the active package surface.
- Upstream must treat experiment-level `.ribo` files as the durable downstream handoff target.

### Handoff rules

- Handoff is an explicit contract layer, not an implicit filesystem convention.
- Handoff must record experiment-level `.ribo` artifacts first.
- `all.ribo` may be recorded as an optional aggregate artifact, not as the sole downstream API.
- Handoff may include required sidecar references for sample selection, pairing, and downstream support tables.

### Downstream rules

- Downstream begins at `.ribo` consumption, not at FASTQ processing.
- Winsorization is represented as a documented downstream stage.
- Filtering is downstream.
- TE computation is downstream.
- Result packaging is downstream.

## Config ownership

### `configs/pipeline/`

Owns project-level mode selection, path roots, and layer-wide defaults.

### `configs/upstream/`

Owns wrapper-facing upstream backend selection and upstream execution policy.

### `configs/downstream/`

Owns wrapper-facing downstream stage ordering and downstream reference backend bindings.

## Backend/reference rule

Reference backends remain:

- `raw_motheds/snakescale`
- `raw_motheds/riboflow`
- `raw_motheds/TE_model`

New code should target the local wrapper contracts first and treat backend paths as explicit adapter inputs.
