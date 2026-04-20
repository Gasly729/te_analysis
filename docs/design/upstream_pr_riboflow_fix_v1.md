# Fix Groovy Interpolation in `samtools -@` Calls

## Proposed Title

`Fix groovy interpolation in samtools -@ calls (15 occurrences)`

## Problem

`riboflow/RiboFlow.groovy` currently mixes two syntaxes for `task.cpus`:

- correct: `${task.cpus}`
- incorrect: `{task.cpus}`

In Groovy triple-quoted shell blocks, bare `{task.cpus}` is not interpolated. It reaches the shell literally, so `samtools` receives `-@` with an invalid argument and fails at runtime.

Observed failure in `te_analysis`:

```text
[E::hts_open_format] Failed to open file -@
samtools idxstats: failed to open "-@": No such file or directory
```

## Affected Lines

The patch changes exactly these 15 occurrences in `riboflow/RiboFlow.groovy`:

- 260
- 261
- 321
- 322
- 358
- 359
- 553
- 1172
- 1173
- 1528
- 1529
- 1585
- 1586
- 1624
- 1625

Representative context:

```diff
- && samtools index -@ {task.cpus} ${sample}.${index}.filter.bam \
- && samtools idxstats -@ {task.cpus} ${sample}.${index}.filter.bam  > \
+ && samtools index -@ ${task.cpus} ${sample}.${index}.filter.bam \
+ && samtools idxstats -@ ${task.cpus} ${sample}.${index}.filter.bam  > \
```

## Minimal Reproduction

This reproduction uses a synthetic Groovy/Nextflow-style shell block and does not depend on any `te_analysis` data.

1. Create a minimal script with one process:

```groovy
process repro {
  cpus 4
  script:
  """
  samtools idxstats -@ {task.cpus} fake.bam
  """
}
```

2. Run it in any environment where `samtools` is on `PATH`.

Expected behavior:

- `{task.cpus}` is passed literally.
- `samtools` treats the malformed argument as a file target and aborts.

After the fix:

```groovy
samtools idxstats -@ ${task.cpus} fake.bam
```

the shell receives the numeric CPU value as intended.

## Why This Is Safe

- The patch only adds the missing `$` in already-existing `task.cpus` references.
- No command structure, file path, or workflow topology changes.
- The file already uses the correct `${task.cpus}` form in sibling `samtools sort` calls, so this patch only makes the inconsistent `index`/`idxstats` calls match the working pattern.

## Reproduction in Our Local Trace

The failure surfaced after `snakescale` advanced past `check_adapter` and `classify_studies` into `run_riboflow`, which shells out to `nextflow riboflow/RiboFlow.groovy`.

Local evidence:

- upstream clone HEAD still equals `b918e75`
- fixed lines confirmed in `/tmp/snakescale_upstream/riboflow/RiboFlow.groovy:260,261,321,322,358,359,553,1172,1173,1528,1529,1585,1586,1624,1625`
- `te_analysis` run log previously reported `samtools idxstats: failed to open "-@"`

## Suggested PR Body

This fixes 15 `samtools index` / `samtools idxstats` invocations in `riboflow/RiboFlow.groovy` that used `{task.cpus}` instead of `${task.cpus}`.

In Groovy shell blocks, `{task.cpus}` is not interpolated, so the literal token reaches `samtools` and causes runtime failures such as:

```text
samtools idxstats: failed to open "-@": No such file or directory
```

The patch is intentionally minimal: it only adds the missing `$` and aligns these calls with nearby `samtools sort -@ ${task.cpus}` usages that already work.
