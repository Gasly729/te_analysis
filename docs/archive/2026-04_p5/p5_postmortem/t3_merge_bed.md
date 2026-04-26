# T3 — GSE123564 rnaseq_merge_bed stderr 抄录

**日期**：2026-04-21

## work dir 信息

失败 processes（均 exit=143，SIGTERM）：

| work dir hash | process | exit |
|---------------|---------|------|
| e3/f9e6ff | rnaseq_merge_bed (7) | 143 |
| b2/1eea0a | rnaseq_merge_bed (10) | 143 |
| 0a/657136 | rnaseq_merge_bed (8) | 143 |
| 96/374dc6 | rnaseq_merge_bed (9) | 143 |
| 42/48d9e0 | rnaseq_merge_bed (6) | 143 |
| 8c/541332 | rnaseq_merge_bed (5) | 143 |
| c2/8d1f09 | put_rnaseq_into_ribo (4) | 143 |

## .command.err 原文（逐条转录）

### rnaseq_merge_bed (7) — work/e3/f9e6ff...

```
+ cat GSM3507222.1.with_sample_index.bed
+ sort -k1,1 -k2,2n -k3,3n
```

（无后续输出，进程被 SIGTERM 打断）

### rnaseq_merge_bed (10) — work/b2/1eea0a...

```
+ cat GSM3507221.1.with_sample_index.bed
+ sort -k1,1 -k2,2n -k3,3n
```

### rnaseq_merge_bed (8) — work/0a/657136...

```
+ cat GSM3507228.1.with_sample_index.bed
+ sort -k1,1 -k2,2n -k3,3n
```

### rnaseq_merge_bed (9) — work/96/374dc6...

```
+ cat GSM3507223.1.with_sample_index.bed
+ sort -k1,1 -k2,2n -k3,3n
```

### rnaseq_merge_bed (6) — work/42/48d9e0...

```
+ cat GSM3507224.1.with_sample_index.bed
+ sort -k1,1 -k2,2n -k3,3n
```

### rnaseq_merge_bed (5) — work/8c/541332...

```
+ cat GSM3507225.1.with_sample_index.bed
+ sort -k1,1 -k2,2n -k3,3n
```

### put_rnaseq_into_ribo (4) — work/c2/8d1f09...

```
+ ribopy rnaseq set -n GSM3507230 -a GSM3507230.merged.pre_dedup.bed -f bed --force GSM3507230.ribo
```

## 诊断

所有失败 process 的 stderr 均停在正常的 shell trace（`set -x` 产生的 `+` 行），
无任何程序错误信息。exit=143 = 128 + 15（SIGTERM）。

**结论：rnaseq_merge_bed 和 put_rnaseq_into_ribo 均被外部 SIGTERM 中断，
不是程序 bug。触发原因是上游 nohup 父进程死亡后，nextflow 的
`WARN: Killing pending tasks` 机制向所有运行中的 task 发送 SIGTERM。**

rnaseq_merge_bed 上游的所有 process（10/10 ✔）已成功完成，
本 task 本身逻辑正常，只需重跑即可通过。
