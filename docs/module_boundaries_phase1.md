# Phase-1 Module Boundaries for the Rebuilt TE-only Pipeline

## Purpose

This document establishes the strict structural boundaries for phase 1 of the rebuilt TE-only repository.

Phase 1 is intentionally non-algorithmic. It creates explicit module targets, removes misleading active template entrypoints, and makes it harder for future work to collapse back into a mixed-responsibility architecture.

## Active Development Zones

The only active development zones after this change are:

- `te_analysis/`
- `config/`
- `tests/`
- `docs/`

Notes:

- `te_analysis/` is the only active Python package surface.
- `config/` holds only explicit future configuration and schema boundaries.
- `tests/` is reserved for future golden fixtures and boundary validation.
- `docs/` holds architectural authority documents.

## Frozen Reference-Only Zones

The following areas are frozen reference-only zones:

- `raw_motheds/`
- any historical `workflow/` area if introduced later
- old runtime residue directories such as `.snakemake/`, `.nextflow/`, `work/`, `output/`, `intermediates/`, and similar execution leftovers

Rules for frozen zones:

- No new active code may be added there.
- No refactor should treat them as the target architecture.
- They may be read for evidence during later migration phases.
- They must not become the place where “temporary” new logic accumulates.

## Archived Template Surface

`archive/template_scaffolds/` is classified as:

- a reversible archive zone
- a non-runtime zone
- a non-development zone
- not importable by active production modules

The archive exists only to preserve removed placeholders in a reversible way. It is not a fallback implementation area and not a place for future active code.

The following misleading template files were removed from the active package surface and archived under `archive/template_scaffolds/`:

- `te_analysis/dataset.py`
- `te_analysis/code_scffold.py`
- `te_analysis/plots.py`
- `te_analysis/modeling/`
- `notebooks/notebook_scaffold.ipynb`

Reason:

- These files looked like active entrypoints but were template or unrelated scaffold material.
- Leaving them in the active surface would make future migration work drift back into the wrong abstractions.

## Forbidden Cross-Zone Dependencies

Active modules under `te_analysis/` must not import from:

- `raw_motheds/`
- `archive/`
- historical `workflow/` code
- runtime residue directories such as `.snakemake/`, `.nextflow/`, `work/`, `output/`, and `intermediates/`

Reason:

- these zones are reference, archive, or residue zones rather than active package boundaries
- importing across these zones would silently reintroduce mixed-responsibility architecture
- phase-safe migration requires all active logic to enter through the explicit `te_analysis/` module surface

## New Package Boundaries

### `te_analysis/cli.py`

Responsibility:

- The single future entrypoint surface for explicit repository commands.

Not allowed yet:

- command implementations
- hidden shortcuts
- direct algorithm calls
- subprocess execution

Future migration target:

- explicit commands for manifest validation, upstream execution, extraction, compute, QC, and packaging

### `te_analysis/contracts/`

Responsibility:

- Hold explicit contracts instead of hidden conventions.

Submodules:

- `metadata.py`: future normalized metadata contract
- `pairing.py`: future Ribo/RNA pairing contract
- `study_manifest.py`: future study manifest and resolved manifest contract

Not allowed yet:

- CSV parsing
- YAML parsing
- schema validation logic
- fallback heuristics

Future migration target:

- metadata field normalization
- pairing definitions
- manifest structure and validation

### `te_analysis/upstream/`

Responsibility:

- Reserve the boundary between this repository and upstream `.ribo` production.

Submodules:

- `manifest_materializer.py`: future resolved-manifest generation boundary
- `riboflow_runner.py`: future upstream black-box execution wrapper
- `preflight.py`: future explicit upstream readiness checks

Not allowed yet:

- workflow submission
- YAML generation
- environment mutation
- adapter guessing
- read-length inference

Future migration target:

- explicit resolved study manifests
- controlled upstream invocation
- preflight checks that remain scientifically justified

### `te_analysis/extract/`

Responsibility:

- Reserve the future `.ribo` extraction bridge boundary.

Submodules:

- `ribo_counts.py`: future `.ribo` to raw-count interface

Not allowed yet:

- `.ribo` reading
- species detection
- count extraction
- file writing

Future migration target:

- stable extraction interfaces derived from audited legacy extraction paths

### `te_analysis/preprocess/`

Responsibility:

- Reserve future preprocessing boundaries as explicit modules rather than ad hoc scripts.

Submodules:

- `winsorize.py`: future winsorization policy boundary
- `filtering.py`: future filtering and normalization boundary

Not allowed yet:

- winsorization logic
- percentile capping
- CPM normalization
- dummy-gene aggregation
- non-polyA filtering

Future migration target:

- restored winsorization layer
- filtering, normalization, and dummy-gene handling

### `te_analysis/compute/`

Responsibility:

- Reserve the future controlled wrapper around TE computation.

Submodules:

- `te_runner.py`: future TE execution boundary

Not allowed yet:

- R invocation
- workdir setup
- algorithm rewrites
- TE math changes

Future migration target:

- a controlled wrapper around the preserved TE scientific core

### `te_analysis/qc/`

Responsibility:

- Reserve a dedicated QC reporting zone.

Submodules:

- `reporting.py`: future QC summary boundary

Not allowed yet:

- report generation
- log collection
- runtime aggregation

Future migration target:

- explicit QC summaries for extraction, preprocessing, compute, and packaging stages

### `te_analysis/package/`

Responsibility:

- Reserve the final packaging boundary for repository outputs.

Submodules:

- `results.py`: future output assembly boundary

Not allowed yet:

- output merging
- file writing
- manifest generation

Future migration target:

- final result tables
- output manifests
- provenance summaries

## Config and Test Boundaries

### `config/`

Responsibility:

- Hold the future explicit contract surface for pipeline defaults, references, and schemas.

Not allowed yet:

- implicit defaults copied from legacy workflow files
- hidden path assumptions
- ad hoc patch layers

Future migration target:

- `pipeline.defaults.yaml`
- `references.catalog.yaml`
- explicit schema files under `config/schemas/`

### `tests/`

Responsibility:

- Hold future tests and golden fixtures for boundary-safe migration.

Not allowed yet:

- dumping runtime artifacts
- storing uncurated legacy residue

Future migration target:

- golden fixtures for manifests, extraction boundaries, preprocessing inputs, and packaged outputs

## Forbidden Logic in Phase 1

The following are forbidden in this phase:

- algorithm migration from legacy code
- `.ribo` reading implementation
- winsorization implementation
- filtering implementation
- R invocation wiring
- workflow submission wiring
- current-working-directory assumptions
- import-time file IO
- import-time subprocess calls
- import-time YAML generation
- import-time logging side effects
- import-time environment mutation

## What Future Phases Must Respect

Later migration work must place logic only into the module family that matches its responsibility:

- metadata normalization belongs in `te_analysis/contracts/metadata.py`
- pairing logic belongs in `te_analysis/contracts/pairing.py`
- study manifest and resolved manifest logic belong in `te_analysis/contracts/study_manifest.py` and `te_analysis/upstream/manifest_materializer.py`
- upstream `.ribo` production wrappers belong in `te_analysis/upstream/`
- `.ribo` extraction belongs in `te_analysis/extract/ribo_counts.py`
- winsorization belongs in `te_analysis/preprocess/winsorize.py`
- filtering and normalization belong in `te_analysis/preprocess/filtering.py`
- TE execution wrapping belongs in `te_analysis/compute/te_runner.py`
- QC summaries belong in `te_analysis/qc/reporting.py`
- output packaging belongs in `te_analysis/package/results.py`

No later phase should reintroduce a god script that spans multiple layers.
