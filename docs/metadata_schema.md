# metadata.csv Schema

**Status**: T3 schema contract (green since J2). Companion to
`te_analysis_module_contracts_v1.md §M7` and `srr_resolution_design_v2.md`.

## 0. Shape & invariants

- **File**: `data/raw/metadata.csv`
- **Shape**: 30 columns × 4168 data rows (as of Commit J1)
- **Header layout**: row 0 is the literal tag line
  `Curated Data,,,,,,,information from GEO,,,,,,,,,,,,,,,,,,,,,,`;
  row 1 is the column header; data starts at row 2.
- **Granularity**: **run-level flat table** (one row per SRA run accession).
  This is the authoritative SSOT; no sidecar files (per
  `te_analysis_top_level_design_v1.md §9` cut-list and
  `te_analysis_module_contracts_v1.md §M7.MUSTNOT.3`).
- **Primary key**: composite `(experiment_alias, run)`. For rows where `run`
  is empty (unresolved SRX), the primary key degrades to `experiment_alias`
  alone — such rows are excluded from downstream staging.

## 1. Full field table (30 columns)

Columns 1-27 are pre-existing curated fields. Columns 28-30 are
enrichment columns added by project tooling.

| # | column | type | req | description | source | downstream use |
|---|---|---|---|---|---|---|
| 1 | `experiment_alias` | str | ✓ | GEO GSM accession (or ERX/SRX for non-GEO) | curated | key in `input.fastq[...]` / `rnaseq.fastq[...]` |
| 2 | `cell_line` | str | — | cell line designation | curated | reference / reporting only |
| 3 | `study_id_index` | str | ✓ | curated study ordering index | curated | internal |
| 4 | `organism` | str | ✓ | raw organism string from GEO | curated | mapped → snakescale reference key |
| 5 | `matched_RNA-seq_experiment_alias` | str | ✓ (Ribo) | pair key — the matched RNA-Seq `experiment_alias` for a Ribo-Seq row | curated | Ribo/RNA pairing (acts as `pair_id`) |
| 6 | `corrected_type` | enum | ✓ | `Ribo-Seq` \| `RNA-Seq` | curated | routes row to `input.fastq` vs `rnaseq.fastq` |
| 7 | `_empty_col` | — | — | legacy empty column | curated | none |
| 8 | `source_name_GEO` | str | — | GEO source_name field | curated | reporting |
| 9 | `cell_info_GEO` | str | — | GEO cell info field | curated | reporting |
| 10 | `experiment_accession` | str | ✓ | SRA experiment accession (SRX/ERX) | curated | pysradb key for H2 enrichment |
| 11 | `study_name` | str | ✓ | GSE accession (e.g. `GSE128216`) | curated | L1 `config.yaml.studies[]` |
| 12 | `title` | str | — | study title | curated | reporting |
| 13 | `sample_accession` | str | — | SRA sample accession (SRS) | curated | reporting |
| 14 | `library_strategy` | str | ✓ | SRA library strategy (e.g. `RNA-Seq`) | curated | cross-check with `corrected_type` |
| 15 | `library_layout` | enum | ✓ | `SINGLE` \| `PAIRED` | curated | validates `fastq_path_r2` presence |
| 16 | `library_construction_protocol` | str | — | free-form protocol text | curated | reporting |
| 17 | `platform` | str | ✓ | sequencing platform (e.g. `ILLUMINA`) | curated | reporting |
| 18 | `platform_parameters` | str | — | free-form instrument params | curated | reporting |
| 19 | `xref_link` | str | — | cross-reference URL | curated | reporting |
| 20 | `experiment_attribute` | str | — | free-form attribute | curated | reporting |
| 21 | `submission_accession` | str | — | SRA submission accession (SRA) | curated | reporting |
| 22 | `sradb_updated` | str | — | SRAdb timestamp | curated | reporting |
| 23 | `group` | str | — | curation group label | curated | internal |
| 24 | `threep_adapter` | str | ✓ (Ribo) | 3' adapter sequence | curated | snakescale `clip_arguments` |
| 25 | `fivep_adapter` | str | — | 5' adapter sequence | curated | snakescale `clip_arguments` |
| 26 | `threep_umi_length` | int-str | — | 3' UMI length | curated | snakescale `clip_arguments` |
| 27 | `fivep_umi_length` | int-str | — | 5' UMI length | curated | snakescale `clip_arguments` |
| 28 | `run` | str | — | SRA run accession (SRR/ERR) | **H2 pysradb** | symlink target name / snakescale fastq key |
| 29 | `fastq_path` | str | — | R1 FASTQ path, relative to `data/raw/` | **J1 disk scan** | T4 symlink source |
| 30 | `fastq_path_r2` | str | — | R2 FASTQ path for paired-end; empty for single-end | **J1 disk scan** | T4 symlink source (paired) |

**"req" semantics**:

- ✓ = required for a row to be usable by T4 `stage_inputs.py`
- ✓ (Ribo) = required only for `corrected_type == 'Ribo-Seq'` rows
- — = optional / informational

## 2. Null / empty value semantics

| column | empty meaning | handling downstream |
|---|---|---|
| `run` | H2 pysradb could not resolve SRX → SRR mapping | T4 skips row; counted in `_srr_enrichment_report.md` |
| `fastq_path` | J1 disk scan did not locate R1 (either `run` empty, or file not yet staged) | T4 skips row; counted in `_fastq_align_report.md` |
| `fastq_path_r2` | single-end sample (or paired R2 not on disk) | T4 passes only R1 to snakescale |

## 3. Composite primary key

- **Canonical**: `(experiment_alias, run)`
- **Rationale**: single `experiment_alias` can map to multiple SRA runs
  (fanout up to 1:84 in this dataset; see `srr_resolution_design_v2.md §3.4`).
  `run` alone is globally unique in SRA, but keeping the composite form
  preserves experiment-level grouping semantics.

## 4. pair_id semantics

The top-level design mentions a `pair_id` column for linking Ribo-Seq to
its matched RNA-Seq sample. This project **reuses the curated
`matched_RNA-seq_experiment_alias` column** instead of introducing a
separate `pair_id` field:

- A Ribo-Seq row's `matched_RNA-seq_experiment_alias` names the
  `experiment_alias` of its paired RNA-Seq row in the same study.
- RNA-Seq rows leave `matched_RNA-seq_experiment_alias` empty.
- T3 verification (J3) ensures 1:1 bidirectional closure: every Ribo-Seq
  pointer resolves to a real RNA-Seq row in the same `study_name`.

## 5. Field mapping to snakescale

Refer to `docs/snakescale_contract.md §5` for the full mapping. Key hooks:

| metadata column | snakescale project.yaml field |
|---|---|
| `study_name` | `config.yaml.studies[]` / `{gse_only}` path key |
| `experiment_alias` + `corrected_type` | key in `input.fastq[...]` or `rnaseq.fastq[...]` |
| `matched_RNA-seq_experiment_alias` | pair lookup for `rnaseq.fastq` assembly |
| `organism` | `input.reference.{filter,regions,transcript_lengths,transcriptome}` |
| `threep_adapter` / `*_umi_length` | `clip_arguments` |
| `run` + `fastq_path` (+ `fastq_path_r2`) | value in `input.fastq[experiment_alias]` list |

## 6. Change history

| commit | change |
|---|---|
| pre-H2 | 27 curated columns; experiment-level (2644 rows) |
| H2 (`e06d6ad`) | +`run`, +`fastq_path` (declarative); expanded to 4168 run-level rows |
| J1 (`9470bb2`) | `fastq_path` rewritten to real disk paths; +`fastq_path_r2` (paired-end) |

## 7. Validator contract (T3 / J3 verification)

`scripts/verify_t3_metadata.py` performs:

- Column count == 30
- `corrected_type ∈ {'Ribo-Seq', 'RNA-Seq'}`
- `library_layout == 'PAIRED'` ⇔ `fastq_path_r2` non-empty (when `fastq_path` is non-empty)
- `matched_RNA-seq_experiment_alias` bidirectional closure within same `study_name`
- GSE132441 / GSE105082 row-count sanity checks
