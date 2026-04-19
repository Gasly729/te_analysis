# metadata.csv Schema

TODO(T3): Fill per te_analysis_module_contracts_v1.md §M7.

## Run-level enrichment (H2)

Since Commit H2, `data/raw/metadata.csv` is a **run-level flat table**
(one row per SRR) with two enrichment columns appended to the original 27:

- `run` — SRA run accession (e.g. `SRR8718520`), populated by
  `scripts/enrich_metadata_srr.py` via `pysradb.SRAweb().srx_to_srr()`.
- `fastq_path` — declarative path relative to `data/raw/`, format
  `fastq/{study_name}/{experiment_alias}/{run}_1.fastq.gz`, matching
  `vendor/snakescale/scripts/generate_yaml.py:262-279` layout.

Rationale, fanout distribution, and unresolved-SRX handling are documented
in `docs/srr_resolution_design_v2.md`. Full field-level schema (all 29
columns) will be specified as part of T3.
