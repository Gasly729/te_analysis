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
