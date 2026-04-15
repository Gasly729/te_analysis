# Legacy TE_model Wrapper Design Stub

This directory is reserved for the future implementation of the design-only `legacy_te_model_wrapper` contract.

## Status

Design only.

Not wired into production.

No runnable execution path is defined here yet.

## Intended responsibility

A future implementation in this directory is expected to provide only the controlled thin-wrapper boundary for the original legacy downstream workflow in `/home/xrx/my_project/te_analysis/raw_motheds/TE_model`.

It is expected to own:

- contract validation,
- sandbox materialization,
- trial config generation,
- provenance capture,
- stable output packaging.

It is not expected to own:

- reimplementation of the legacy methodology,
- new winsorization logic,
- direct in-place execution inside the frozen legacy tree,
- broader TEC or unrelated downstream extensions.

## Source specification

Authoritative v1 design spec:

- `/home/xrx/my_project/te_analysis/reports/designs/legacy_te_model_wrapper_spec.md`
- `/home/xrx/my_project/te_analysis/reports/designs/legacy_te_model_wrapper_spec.json`

## Notes for later implementation

The future implementation should treat experiment-level `.ribo` as the primary handoff object and should reject RNA-seq-absent handoff for original black-box TE mode.
