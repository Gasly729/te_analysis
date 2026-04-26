# Backlog

Feature requests explicitly rejected during sprint. Format per
te_analysis_module_contracts_v1.md §18.

## <YYYY-MM-DD> <feature name>
- Source task: T?
- Trigger scenario: ...
- Affected modules: ...
- Contract basis: ...
- Revisit trigger: ...

## 2026-04-20 backlog #8 upstream resolution research
- Source task: T8 / Session O / O1 + O6
- Trigger scenario: Session N confirmed a vendor typo in
  `vendor/snakescale/riboflow/RiboFlow.groovy`, but the project still needed
  a path decision between upstream PR / local patch / SHA switch.
- Affected modules: `vendor/snakescale` governance only; no code changes in this repo.
- Contract basis: `te_analysis_module_contracts_v1.md:318-324`,
  `te_analysis_top_level_design_v1.md:416`,
  `te_analysis_sprint_plan_v1.md:240`.
- Revisit trigger: use `docs/design/backlog_8_resolution_plan_v1.md`;
  current recommendation is path a (upstream PR). Path b is rejected as
  unconstitutional; path c is unavailable because upstream `main` still equals
  locked SHA `b918e75`.

## 2026-04-20 classify_studies invalidation audit
- Source task: T8 / Session O / O2
- Trigger scenario: Session N observed that many studies may fail
  `classify_studies` when `override=False`, especially pre-clipped Ribo-seq
  inputs lacking explicit `threep_adapter`.
- Affected modules: data risk only; no repo code changes.
- Contract basis: `vendor/snakescale/Snakefile:769-949` and
  `docs/snakescale_contract.md:90-99`.
- Revisit trigger: `/tmp/t8_invalid_studies_audit.csv` contains the per-study
  audit. Current static estimate: 120 Ribo studies total, 87 strict invalid
  (`0%` adapter coverage), 89 partial invalid (`<100%` adapter coverage).

## 2026-04-20 Method F codification design
- Source task: T8 / Session O / O4
- Trigger scenario: Method F is validated but still enacted by ad-hoc shell.
- Affected modules: M1 / M2 future design only.
- Contract basis: backlog #9 follow-up after #8 is resolved.
- Revisit trigger: implement from
  `docs/design/method_f_codification_v1.md`; current recommendation is a new
  helper module `src/te_analysis/stage_snakescale_injection.py`.

## 2026-04-20 contract testing gap analysis
- Source task: T8 / Session O / O5
- Trigger scenario: 42 tests were all green, yet T8 still failed at three
  different contract layers outside the current test boundary.
- Affected modules: tests/ design only.
- Contract basis: T12 test-structure review; vendor boundary remains untested.
- Revisit trigger: use `docs/design/contract_testing_gap_v1.md` as the input
  for the first testing subtask in T12.

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

## 2026-04-19 T8 upstream E2E blocked by stage_inputs ↔ snakescale input-format mismatch — RESOLVED in N via method F
- Source task: T8 (GSE132441 upstream E2E) attempted in session M.
- Resolution (session N Phase B, commit `<N1>`): Two compounding gaps were
  identified and addressed without vendor edits:
    (i) **path-visibility gap**: T4 stages symlinks under
        `data/interim/snakescale/{STUDY}/staged_fastq/…` but snakemake runs
        with `cwd=vendor/snakescale/` and resolves yaml paths like
        `staged_fastq/{GSE}/…` relative to that cwd. Fix (one-shot in
        session N, not yet in T4 code): symlink
        `vendor/snakescale/staged_fastq/{GSE} → data/interim/snakescale/{STUDY}/staged_fastq/{GSE}`.
    (ii) **format-mismatch gap**: Snakefile:237 `download_fastq_files.output`
        is `{dir}/{accession}_1.fastq` (uncompressed); stage_inputs materialises
        `_1.fastq.gz`. Fix: create empty `_1.fastq` placeholders with mtime
        older than the `.gz` symlink. Snakefile:242/245 then short-circuits
        (both "file exists" checks satisfied → no prefetch, no mv). gzip_fastq
        sees output `.gz` newer than input `.fastq` → marked up-to-date.
- Verification: Phase B single-GSM probe (`GSE132441_probe`) showed
  13-job plan (vs 25 before) with `download_fastq_files` / `gzip_fastq`
  absent from execution set; `snakemake --until check_adapter` completed
  all 6 check_adapter jobs successfully reading the real `.gz` via zcat.
- Alternative rejected: `--omit-from download_fastq_files` (method E) —
  snakemake 9.19 semantics is "skip rule AND downstream" (help line:420–424),
  which prunes the entire DAG → "Nothing to be done".
- Follow-up: method F is currently orchestrated by one-shot bash; long-term
  migration into `stage_inputs.py` / `run_upstream.py` is recorded as
  backlog #9 (deferred out of GC-1 scope).

## 2026-04-19 T8 blocked by vendor RiboFlow.groovy groovy-interpolation typo
- Source task: T8 Phase C (session N)
- Trigger scenario: After method F cleared the stage_inputs/Snakefile gap,
  `snakemake --config studies="['GSE132441']" override=True` advanced the
  DAG through `check_adapter` → `classify_studies` → `run_riboflow`, which
  invokes `nextflow riboflow/RiboFlow.groovy`. The `filter` nextflow process
  failed with:
    `[E::hts_open_format] Failed to open file -@`
    `samtools idxstats: failed to open "-@": No such file or directory`
- Root cause: **vendor typo** in `vendor/snakescale/riboflow/RiboFlow.groovy`
  at lines 260, 261, 321, 322, 358, 359, 553, 1172, 1173, 1528, 1529, 1585,
  1586, 1624, 1625 (15 occurrences). All `samtools index` and
  `samtools idxstats` invocations use `-@ {task.cpus}` **without the leading
  `$`**. Groovy only interpolates `${...}`; bare `{task.cpus}` reaches bash
  as a literal token → samtools receives `-@` as a filename and aborts.
  Sibling `samtools sort -@ ${task.cpus}` calls are correct at lines 254,
  259, 315, 320, 356, 552, 1171, 1527, 1584, 1622.
- Affected modules: vendor/snakescale (RiboFlow.groovy, tracked content of
  submodule SHA `b918e75…`).
- Contract basis: per top_level §2 and GC-0, `vendor/snakescale/` is
  immutable; submodule SHA is locked at `b918e75f877262dca96665d18c3b472675f30a6d`.
  No in-tree patch permitted.
- Revisit trigger: **T14 baseline lock (blocking upstream E2E deliverable)**.
  Candidate mitigations for session O+:
    (a) submit upstream PR to RiboBase/snakescale fixing the 15 lines;
        revendor after merge.
    (b) maintain a local patch file under `vendor_patches/snakescale.patch`
        applied at repo init (changes the "vendor immutable" contract).
    (c) switch to a snakescale fork/SHA that has the typo fixed (survey needed).
  No decision in session N.
- Files retained for forensic review:
  - `/tmp/t8_full_override.log` (full run with override=True)
  - `vendor/snakescale/log/failed/GSE132441/modifications.log`
  - `vendor/snakescale/.snakemake/log/2026-04-20T100824.299319.snakemake.log`

## 2026-04-19 method-F scaffolding not yet codified in stage_inputs/run_upstream
- Source task: T8 Phase B (session N)
- Trigger scenario: The two symlinks + empty-placeholder + mtime setup
  required for method F are currently enacted by an ad-hoc shell/python
  block in session N. If T4 / T5 are expected to produce a snakescale-ready
  tree end-to-end, this logic must migrate in.
- Needed operations (concise):
    1. After `stage_inputs` writes `{out}/staged_fastq/...`, for each
       `_1.fastq.gz` symlink, `touch -d '1 hour ago' <same_path>_1.fastq`
       (empty placeholder with older mtime), then `touch -h <.gz>` to
       ensure symlink mtime is now.
    2. `run_upstream` must add a second symlink besides project.yaml:
       `vendor/snakescale/staged_fastq/{GSE} → {out}/staged_fastq/{GSE}`
       (idempotent, unlink-and-relink pattern per K1).
- Affected modules: M1 `stage_inputs.py`, M2 `run_upstream.py`.
- Contract basis: GC-1 (tests/src budget) + M1 MUST list; neither currently
  declares this behaviour, which is why session M's T8 attempt failed.
- Revisit trigger: resolving backlog #8 (vendor typo) unblocks full E2E;
  at that point method-F scaffolding must be codified rather than shell-scripted.
- Deferred out of session N per task constraint "不扩 stage_inputs.py".

## 2026-04-19 paired-end staging in T4 stage_inputs.py — RESOLVED in K1
- Trigger scenario: `run_upstream --study-dir data/interim/snakescale/GSE132441
  --cores 32` → snakemake plan is correct (25 jobs, dry-run clean), but live
  execution of `rule download_fastq_files` fails with `SpawnedJobError` at
  all 6 SRR accessions (e.g. SRR9257373). Root cause: the rule output is
  `{dir}/{accession}_1.fastq` (uncompressed), and when neither that nor
  `{accession}.fastq` exists on disk it invokes `prefetch + fasterq-dump`
  (network download), which the dev machine cannot satisfy.
- Observed: T4 materialises **`_1.fastq.gz`** symlinks (matching
  snakescale's post-`gzip_fastq` output naming), but the upstream rule
  `download_fastq_files` pre-`gzip_fastq` expects the **raw `_1.fastq`**
  to already exist (or it downloads). Snakefile:242, Snakefile:245.
- Affected modules: M1 `stage_inputs.py` staging contract vs M8 snakescale
  Snakefile semantics. Not a vendor bug.
- Contract basis: vendor/snakescale/Snakefile is immutable per GC-0.
  stage_inputs.py's contract doc claims `_1.fastq.gz` matches snakescale
  input; audit shows it matches only post-download-and-gzip, not the
  pre-download input slot.
- Revisit trigger: **T14 baseline lock (blocking T8 deliverable)**. Three
  candidate mitigations to weigh:
    (a) touch empty `_1.fastq` next to each `_1.fastq.gz` symlink so
        `download_fastq_files` short-circuits (output[0] exists → skip)
        and subsequent `gzip_fastq` is made up-to-date via `snakemake
        --touch`. **Risk**: gzip_fastq rerun would replace our real .gz
        with gzip(empty); needs careful mtime staging.
    (b) materialise real decompressed `_1.fastq` (disk cost ~4× gz size;
        for GSE132441 6 SRR × ~1 GB → +24 GB).
    (c) extend T4 stage_inputs.py to produce both forms (touch plain +
        symlink gz + mtime order).
  Decision to defer until session N so T4/T5 contracts can be re-read
  against Snakefile with fresh eyes.
- Files still clean post-attempt: symlink at
  `vendor/snakescale/input/project/GSE132441/GSE132441.yaml` left in place
  (run_upstream idempotency); no vendor tracked SHA moved; snakescale
  `.snakemake/log/2026-04-20T094238.184529.snakemake.log` retained for
  forensic review.

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
