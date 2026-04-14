# Contracts Boundary Note

The `te_analysis/contracts/` package defines schema and validation boundaries for the rebuilt TE-only pipeline.

Rules:

- contracts define schemas and validation boundaries
- contracts do not execute workflows
- contracts do not download data
- contracts do not read `.ribo`
- contracts must remain side-effect free
