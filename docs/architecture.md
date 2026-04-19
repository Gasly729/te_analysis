# Architecture (TL;DR)

This repo is a CCDS wrapper. It does **not** reimplement any upstream logic.

- Upstream execution: `vendor/snakescale` (submodule, zero edits)
- Downstream execution: `vendor/TE_model` (submodule, zero edits)
- Our code: `metadata.csv → project.yaml + FASTQ symlinks`, that's it
- Entry: `make all STUDY=<GSE>`

Full architecture: see `te_analysis_top_level_design_v1.md` (outside repo).
