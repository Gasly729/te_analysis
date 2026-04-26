# T6 — 6 个"SUCCESS 但 .ribo 未见"study 取证

**日期**：2026-04-21

## 结论一览

| study | 判定 | 根因 |
|-------|------|------|
| GSE43703 | [ran_but_no_ribo] | classify_studies 判 invalid：所有 Ribo-Seq adapter hit rate = 0% + consensus_adapter=null |
| GSE132441 | [ran_but_no_ribo] | classify_studies 判 invalid：所有 Ribo-Seq adapter hit rate = 0% + consensus_adapter=null |
| GSE48140 | [ran_but_no_ribo] | generate_yaml 报 "More than one organism detected"，study 进入 ERROR_STUDIES_LIST，DAG = 1 job (all only)，run_riboflow 从未执行 |
| GSE69602 | [ran_but_no_ribo] | classify_studies 判 invalid：大量 Ribo-Seq SRR adapter hit rate = 0% + consensus_adapter=null |
| GSE112705 | [ran_but_no_ribo] | classify_studies 判 invalid：所有 Ribo-Seq adapter hit rate = 0% + consensus_adapter=null |
| GSE105082 | [ran_but_no_ribo] | classify_studies 判 invalid：Ribo-Seq adapter hit rate 0.5~0.8%（低于阈值）+ consensus_adapter=null |

**注**：`batch_master.log` 记录的 SUCCESS 是 snakemake 的 exit=0，
不代表 riboflow 成功产出 .ribo，仅意味着 snakemake DAG 完整执行了（包括写
`riboflow_status.txt = "Study X failed."`）。

---

## 各 study 详细取证

### GSE43703（Arabidopsis thaliana，4 Ribo + 4 RNA）

最后成功的 rule：`classify_studies`（23:15:21）
`run_riboflow` shell：执行了，但 `valid_set` 为空 → `nextflow` 未调用，直接写 `failed.`

失败路径：

```
adapter check: all 8 SRR → 0.0% adapter hit rate
guess_adapters: consensus_adapter = null, detected_adapters = []
classify_studies: has_low_adapter=false 但 low_adapter_files 含全部 SRR
  → 判定：low adapter + no guessable adapter + not all_uneven_lengths → invalid
riboflow_status: "Study GSE43703 failed."
```

RNA-Seq rnaseq.consensus_adapter = CTGTAGGCACCATCAAT（正常），Ribo-Seq 的才是问题。

### GSE132441（Arabidopsis thaliana，3 Ribo + 3 RNA）

同 GSE43703。adapter hit rate = 0%，Ribo consensus_adapter=null。

RNA-Seq consensus_adapter = AGATCGGAAGAGCACACGTCTGAACTCCAGTCAC（正常），
Ribo-Seq 无法猜 adapter。

### GSE48140（Caenorhabditis elegans，6 Ribo + 6 RNA）

最后成功的 rule：无（DAG 仅有 all rule，1/1 完成）

根因：snakemake 配置文件解析阶段（`generate_yaml` 调用时）报错：

```
Currently Generating YAML File for: GSE48140
More than one organism detected.
```

generate_yaml 在数据库里发现 GSE48140 有多个 organism 记录，直接抛出，
study 进入 `ERROR_STUDIES_LIST`，被从 `STUDIES` 列表移除，
snakemake DAG 不含 GSE48140 任何 rule。

需要检查 db 里 GSE48140 的 organism 字段。

### GSE69602（Homo sapiens，70 Ribo + 46 RNA）

同 GSE43703 模式，但规模更大。大量 SRR 的 adapter hit rate = 0%，
`consensus_adapter=null`，`classify_studies` 判 invalid。

### GSE112705（Homo sapiens，20 Ribo + 20 RNA）

同 GSE43703 模式。全部 Ribo-Seq SRR adapter hit rate = 0%。
RNA-Seq `consensus_adapter = TAGCCCCAAACCCAC`（非标准，疑似 smRNA adapter）。

### GSE105082（Homo sapiens，13 Ribo + 11 RNA）

adapter hit rate 仅 0.5~0.8%（Ribo），低于分类阈值。
`has_low_adapter=true`，`consensus_adapter=null`（无法从低命中率推断 adapter 序列）。
classify_studies 判 invalid。

---

## 共同根因分类

### 类型 A：adapter 命中率低（5 study）

GSE43703, GSE132441, GSE69602, GSE112705, GSE105082

这些 study 的 Ribo-Seq reads 可能是预裁剪（pre-clipped）的，
或 adapter 序列与 snakescale 默认 adapter 不同。

snakescale classify_studies 规则：
- 若 `low_adapter_files` 非空 AND `consensus_adapter=null` AND `not all_uneven_lengths`
  → invalid（无法确定 adapter 配置，不能继续）

**这不是 pipeline bug，是数据 QC 过滤**。这些 study 需要手动指定 adapter 序列，
或者设置 `override=True` 跳过 adapter 检查（有污染风险）。

### 类型 B：multi-organism（1 study）

GSE48140：数据库里 organism 字段有多个值，generate_yaml 保护性退出。
需检查 db 记录并修正。

---

## 重启建议

| study | 可否重启 | 重启前必做 |
|-------|---------|-----------|
| GSE43703 | 有条件 | 手动查 Ribo-Seq adapter 序列；或配置 override=True |
| GSE132441 | 有条件 | 同上 |
| GSE69602 | 有条件 | 同上 |
| GSE112705 | 有条件 | 同上 |
| GSE105082 | 有条件 | 同上（adapter 命中率极低，override 可能产出低质量结果） |
| GSE48140 | 有条件 | 修正 db 中 organism 记录（或在 generate_yaml 强制单一物种） |
