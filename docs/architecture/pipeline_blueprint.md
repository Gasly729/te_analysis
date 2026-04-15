# Pipeline Blueprint

## Core decision

The new local `te_analysis` architecture preserves the audited method split:

- upstream method boundary: `FASTQ -> .ribo`
- downstream method boundary: `.ribo -> TE`

The new engineering structure adds a clearer three-layer wrapper:

- `upstream/`
- `handoff/`
- `downstream/`

## Architecture statement

```text
externally prepared FASTQ
-> data/raw/fastq/
-> upstream local wrapper
-> SnakeScale / RiboFlow reference backend
-> experiment-level .ribo collection
-> handoff manifest + sidecar tables
-> downstream local wrapper
-> TE_model reference backend
-> TE outputs
```

## Ownership model

### Upstream ownership

- Method owner: `raw_motheds/snakescale` and `raw_motheds/riboflow`
- Local wrapper owner: `src/te_analysis/upstream/`
- Local role: stage inputs, materialize configs, validate local files, invoke reference backend safely

### Handoff ownership

- Method owner: local architecture only
- Local wrapper owner: `src/te_analysis/handoff/` and `src/te_analysis/pipeline/io_contracts.py`
- Local role: define experiment-level `.ribo` collection, sidecar manifest, and validation boundary

### Downstream ownership

- Method owner: `raw_motheds/TE_model`
- Local wrapper owner: `src/te_analysis/downstream/`
- Local role: wrap `.ribo` extraction, explicit winsorization stage, filtering stage, TE compute stage, and result packaging stage

## Main handoff object

The main handoff object is not `all.ribo` alone.

The formal handoff is:

- an experiment-level `.ribo` collection
- an optional aggregate `all.ribo`
- required sidecar references such as study manifest, pairing references, sample selection tables, and downstream support tables

## What remains in `raw_motheds/`

The following remain backend reference implementations only:

- `raw_motheds/snakescale/`
- `raw_motheds/riboflow/`
- `raw_motheds/TE_model/`

They are not the new primary architecture, not the new import surface, and not the new config surface.

## What becomes the new local wrapper layer

The new primary local architecture lives under:

- `src/te_analysis/pipeline/`
- `src/te_analysis/upstream/`
- `src/te_analysis/handoff/`
- `src/te_analysis/downstream/`
- `src/te_analysis/adapters/`

This wrapper layer owns:

- path abstraction
- stage registration
- explicit contracts
- explicit config ownership
- safe script entrypoints
- future migration targets

## Non-goals of this skeleton

This skeleton does not yet:

- migrate SnakeScale logic
- migrate RiboFlow logic
- migrate `.ribo` extraction code
- migrate winsorization code
- migrate filtering code
- wire `TE.R`
- reproduce TE outputs
