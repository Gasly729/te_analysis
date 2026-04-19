# Backlog

Feature requests explicitly rejected during sprint. Format per
te_analysis_module_contracts_v1.md §18.

## <YYYY-MM-DD> <feature name>
- Source task: T?
- Trigger scenario: ...
- Affected modules: ...
- Contract basis: ...
- Revisit trigger: ...

## 2026-04-19 Relocate vendor contracts to references/vendor_contracts.md
- Source task: T0 / J3
- Trigger scenario: `sprint_plan_v1.md §1 / §4 T0` nominates
  `references/vendor_contracts.md` as the canonical T0 output path,
  but the content currently lives split across `docs/snakescale_contract.md`,
  `docs/te_model_contract.md`, `docs/vendor_sha_recommendation.md`.
- Affected modules: docs, references/
- Contract basis: pure form / DoD compliance; current split does not block
  any implementation task.
- Revisit trigger: T13 Docs Finalize (module_contracts §M12 reconciles
  doc layout before `v0.1-mvp` tag).

## 2026-04-19 Resolve 3 unresolved SRX from H2 pysradb pass
- Source task: T3 / J1 verify
- Trigger scenario: H2 `_srr_enrichment_report.md` lists 3 SRX (e.g.
  SRX399822, SRX399824) with no SRR mapping; plus 11 metadata rows
  carry empty `run`, and 10 rows have `run` set but no disk FASTQ.
  Combined impact: 21/4168 = 0.50% coverage loss.
- Affected modules: data layer (not code)
- Contract basis: T3 DoD §3 threshold is "all fastq_path point to real
  files"; J1 delivered 99.50% (>=99% relaxed threshold). Under MUST NOT
  "don't silently hide failures" (module_contracts §M7) we keep the
  empty cells explicit and reported, rather than synthesizing paths.
- Revisit trigger: T14 baseline lock — if any focus study (GSE132441
  / GSE105082) is hit, re-query via entrez-direct as secondary source.

## 2026-04-19 tests/ line budget exceeds GC-1 (post-T11 baseline)
- Source task: T12 (legacy purge)
- Trigger scenario: Sum of `tests/*.py` now 98 (smoke) + 130 (stage_inputs)
  + 88 (schema) + 39 (config) + 91 (run_upstream) + 136 (run_downstream) ≈
  582 lines vs GC-1 per-module ceilings M10=150 + M11=100 = 250.
- Affected modules: tests/
- Contract basis: GC-1 budgets each test module independently; per-file ceilings
  are honored (M11=98 ≤ 100, M10=130 ≤ 150). Aggregate overshoot is a by-product
  of covering multiple DoD branches per module, not duplicated coverage.
- Revisit trigger: T12 formal legacy purge — decide whether to merge
  test_stage_inputs.py + test_stage_inputs_schema.py or accept as-is.

## 2026-04-19 scripts/ line budget exceeds GC-1
- Source task: T12
- Trigger scenario: `scripts/` aggregates to 473 lines (enrich_metadata_srr 139 +
  align_fastq_paths 174 + verify_t3_metadata 160) vs the "~100" budget implied
  by top_level §2 (`scripts/` is "一次性运维脚本可丢弃").
- Affected modules: scripts/
- Contract basis: top_level §2 calls `scripts/` disposable; module_contracts §M12
  does not ceiling it. Files served one-shot enrichment/alignment/verification
  during H2 / J1 / J3 and are now idle (never referenced by main path).
- Revisit trigger: T12 — decide whether to (a) `git rm` entirely (reproducibility
  hazard if H2/J1 need rerun), (b) relocate to `archive/scripts/`, or
  (c) keep verbatim as reproducibility audit trail.

## 2026-04-19 T9 downstream baseline drift vs pre-J1 fixture
- Source task: T9 (GSE105082 downstream E2E) / T6 follow-up
- Trigger scenario: Commit `afe6138` (T9 green) produced
  `homo_sapiens_TE_cellline_all_T.csv` with shape (10842, 1) vs
  the pre-J1 fixture `tests/fixtures/gse105082/baseline_outputs/
  human_TE_cellline_all_T.csv` (10862, 1). Gene-set diff: common 10740,
  new_only 88, old_only 107. On the 10740 common genes, values diverged:
  max |Δ| = 2.12, mean |Δ| = 0.120, median |Δ| = 0.100.
- Affected modules: M3 (run_downstream) product / M11 smoke fixture.
- Contract basis: drift is attributable to (i) J1 metadata.csv realignment
  (fastq_path → disk truth, +R2 column, run-level enrichment changed the
  paxdb/CPM quality-filter gene set) and (ii) `propr` permutation
  stochasticity (TE.R uses `p = 100` without seeding at invocation). Neither
  vendor path is modifiable. Smoke fixture was refreshed at T11 against
  the post-J1 products; the pre-J1 `baseline_outputs/` tree is retained
  for T14 audit trail.
- Revisit trigger: **T14 baseline freeze (blocking)** — at tag `v0.1-mvp`,
  either (a) adopt the post-J1 products as the authoritative baseline and
  delete `baseline_outputs/`, or (b) if upstream Ribo-seq inputs change
  again, rerun T9 and re-freeze t9_products/.

## 2026-04-19 paired-end staging in T4 stage_inputs.py — RESOLVED in K1
- Source task: J1 / T4 prep
- Trigger scenario: 336 run-level rows carry non-empty `fastq_path_r2`
  (paired-end FASTQ).
- Resolution (Commit K1 `acea46c`): T4 materializes BOTH R1 and R2 symlinks
  under `<out>/staged_fastq/{GSE}/{GSM}/{SRR}_[12].fastq.gz`, but
  `input.fastq[GSM]` and `rnaseq.fastq[GSM]` lists hold **only R1 paths**
  (snakescale `Snakefile:171,202` hardcodes `_1.fastq.gz`). R2 is available
  for future snakescale support without rerunning stage_inputs.
- Follow-up: if snakescale grows explicit R2 handling, extend the lists in
  `_build_fastq_maps()` — no data migration needed.
