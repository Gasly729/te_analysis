# Migration Plan

## Phase order

### Phase A: architecture skeleton

- create local wrapper docs
- create `src/te_analysis` package skeleton
- create explicit config ownership
- create wrapper scripts and boundary tests

### Phase B: upstream wrapper migration

- wrap local staged FASTQ validation
- wrap SnakeScale config materialization
- wrap RiboFlow invocation
- standardize upstream output staging into the handoff layer

### Phase C: handoff contract migration

- define explicit handoff manifest schema
- validate experiment-level `.ribo` collections
- validate required downstream sidecars

### Phase D: downstream wrapper migration

- wrap `.ribo` extraction boundary
- promote winsorization to an explicit downstream stage
- wrap filtering
- wrap TE compute
- wrap result packaging

## Reference backend policy

During all phases:

- `raw_motheds/` remains read-only reference backend material
- no direct code movement from `raw_motheds/` into the active package should happen without wrapper placement and contract review

## Explicit deferrals

This repository skeleton intentionally defers:

- biological logic migration
- `.ribo` parsing implementation
- winsorization implementation
- filtering implementation
- TE runtime wiring
- final CLI execution behavior
