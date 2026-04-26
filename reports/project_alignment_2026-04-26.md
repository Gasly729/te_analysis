# te_analysis 项目状态对齐（2026-04-26）

检查时间：2026-04-26，Asia/Shanghai  
工作区：`/home/xrx/my_project/te_analysis`

这份文档对齐当前仓库、产物、运行入口和未完成事项。重点结论是：**GSE125086 已经作为端到端参考跑通；GSE132441 上游已经跑通并产出 `.ribo`，但 downstream/TE_model 还没有产出最终 TE 表。**

## 1. 当前总览

| 模块 | 当前状态 | 证据 | 备注 |
|---|---:|---|---|
| GSE105082 TE reference | 完成 | `data/processed/te/GSE105082/homo_sapiens_TE_cellline_all.csv`，shape `(1, 10842)` | 作为已有参考成果保留 |
| GSE125086 upstream | 完成 | `vendor/snakescale/output/GSE125086/ribo/all.ribo`，35,177,552 bytes | snakescale 侧已有 6 个实验 `.ribo` |
| GSE125086 downstream | 完成 | `data/processed/te/GSE125086/GSE125086_TE.csv`，shape `(1, 19737)` | 当前最可靠的端到端参考路径 |
| GSE132441 upstream | 完成 | `vendor/snakescale/output/GSE132441/ribo/all.ribo`，9,360,433 bytes | `riboflow_status.txt` 显示 succeeded |
| GSE132441 downstream | 未完成 | `data/processed/te/GSE132441/GSE132441_TE.csv` 不存在 | R 段停在 `"transfer data from clr to ilr"` 后未产生最终 TE 表 |
| 一条命令复现入口 | 已有但 GSE132441 尚未成功闭环 | `make downstream-gse132441` / `bash scripts/run_gse132441_downstream.sh` | 入口存在，当前需要继续排 downstream |
| vendor 源码提交约束 | 需要继续谨慎 | `vendor/snakescale` 当前 dirty；`vendor/TE_model` 无 tracked diff | 不应提交 vendor 源码改动 |
| 参考成果保护 | 正常 | `data/processed/te/GSE105082/` 和 `data/processed/te/GSE125086/` 均存在 | 未发现被删除 |

## 2. 数据集状态

### 2.1 已有 TE 产物

| 路径 | 大小 | shape | 状态 |
|---|---:|---:|---|
| `data/processed/te/GSE105082/homo_sapiens_TE_cellline_all.csv` | 332,888 bytes | `(1, 10842)` | 存在 |
| `data/processed/te/GSE105082/homo_sapiens_TE_cellline_all_T.csv` | 267,610 bytes | 未重算 | 存在 |
| `data/processed/te/GSE105082/homo_sapiens_TE_sample_level.rda` | 1,121,580 bytes | RDA | 存在 |
| `data/processed/te/GSE125086/GSE125086_TE.csv` | 247,823 bytes | `(1, 19737)` | 存在，canonical 输出 |
| `data/processed/te/GSE125086/homo_sapiens_TE_cellline_all.csv` | 287,301 bytes | `(1, 19737)` | 存在 |
| `data/processed/te/GSE125086/homo_sapiens_TE_cellline_all_T.csv` | 167,032 bytes | 未重算 | 存在 |
| `data/processed/te/GSE125086/homo_sapiens_TE_sample_level.rda` | 73,180 bytes | RDA | 存在 |

### 2.2 snakescale `.ribo` 产物

| Study | `all.ribo` | 实验 `.ribo` 数 | 当前含义 |
|---|---:|---:|---|
| GSE125086 | 35,177,552 bytes | 6 | 已接到 downstream 并出 TE |
| GSE132441 | 9,360,433 bytes | 3 | upstream 完成，downstream 未完成 |
| GSE50597 | 95,598,299 bytes | 6 | 有 `.ribo`，尚未纳入当前主线收尾 |
| GSE109122 | 59,003,503 bytes | 4 | 有 `.ribo`，尚未纳入当前主线收尾 |
| GSE65885 | 229,302,331 bytes | 27 | 有 `.ribo`，尚未纳入当前主线收尾 |
| GSE123564 | 未看到 `all.ribo` | 10 | 有实验 `.ribo`，未看到合并产物 |

### 2.3 GSE132441 upstream 细节

`vendor/snakescale/log/riboflow_status/GSE132441/riboflow_status.txt`：

```text
Study GSE132441 succeeded.
```

`vendor/snakescale/log/success/GSE132441/modifications.log`：

```text
There are no experiments with a low adapter presence.
All Ribo-Seq files had a fixed length.
```

GSE132441 当前 `.ribo` 输入已经满足 downstream 入口的基本文件条件：

- `vendor/snakescale/output/GSE132441/ribo/all.ribo`
- `vendor/snakescale/output/GSE132441/ribo/experiments/GSM3863556.ribo`
- `vendor/snakescale/output/GSE132441/ribo/experiments/GSM3863558.ribo`
- `vendor/snakescale/output/GSE132441/ribo/experiments/GSM3863561.ribo`

## 3. GSE132441 downstream 当前断点

当前入口：

```bash
bash scripts/run_gse132441_downstream.sh
```

或：

```bash
make downstream-gse132441
```

最近一次日志：`/tmp/gse132441_downstream.log`

日志显示已经完成的部分：

- Stage 0 处理了 3 个样本：
  - `Processed GSM3863561`
  - `Processed GSM3863556`
  - `Processed GSM3863558`
- 已生成 ribo/rna raw 和配对中间表：
  - `ribo_raw.csv`
  - `rnaseq_raw.csv`
  - `ribo_paired_count_dummy.csv`
  - `rna_paired_count_dummy.csv`
  - `ribo_paired_cpm_dummy_0.csv`
  - `rna_paired_cpm_dummy_0.csv`
  - `ribo_paired_quantile_dummy_0.csv`
  - `rna_paired_quantile_dummy_0.csv`
- TE_model R 段已经进入 CLR/ILR 相关计算，最后日志停在：

```text
[1] "transfer data from clr to ilr"
```

当前未生成：

- `vendor/TE_model/trials/GSE132441/human_TE_cellline_all.csv`
- `data/processed/te/GSE132441/GSE132441_TE.csv`
- `data/processed/te/GSE132441/arabidopsis_thaliana_TE_cellline_all.csv`

当前判断：`.ribo` schema 至少已经被 Stage 0 接受，3 个样本也完成了初步处理；现在阻塞点更像是 TE_model R Stage 2 的运行中断或资源/数值问题。还没有证据表明必须修改 `vendor/TE_model` 的 R 源码，但如果复现后确认必须改 vendor R 代码，应先停下来对齐。

## 4. 代码和入口改动状态

当前顶层工作区改动：

```text
 M Makefile
 M README.md
 M src/te_analysis/run_downstream.py
 M tests/test_run_downstream.py
?? scripts/run_gse132441_downstream.sh
```

这些改动的意图：

| 文件 | 作用 |
|---|---|
| `src/te_analysis/run_downstream.py` | 复用 GSE125086 downstream 路径；自动把 `vendor/snakescale/output/<study>` 注入为 TE_model runtime ribo 输入；为非人类物种生成 runtime alias patch；支持 serial fallback；复制 canonical `<STUDY>_TE.csv` |
| `scripts/run_gse132441_downstream.sh` | GSE132441 downstream 的一条命令入口 |
| `Makefile` | 增加 `downstream-gse132441` target |
| `README.md` | 增加 GSE132441 downstream 运行说明 |
| `tests/test_run_downstream.py` | 覆盖 ribo input 注入、非人类 alias patch、产物复制和 main 流程 |

当前已验证：

```bash
PYTHONPATH=src python -m pytest tests/test_run_downstream.py -q
```

结果：

```text
11 passed in 0.74s
```

## 5. vendor 和 runtime 状态

### 5.1 vendor/TE_model

`vendor/TE_model` 当前没有 tracked diff，但有 runtime/untracked 内容：

```text
?? data/HELA_ribo_files/
?? data/HELA_ribo_files_shim_manifest.tsv
```

另外，TE_model runtime 中已经有 GSE132441 的 trial 中间文件：

```text
vendor/TE_model/trials/GSE132441/config.py
vendor/TE_model/trials/GSE132441/ribo_raw.csv
vendor/TE_model/trials/GSE132441/rnaseq_raw.csv
vendor/TE_model/trials/GSE132441/ribo_paired_count_dummy.csv
vendor/TE_model/trials/GSE132441/rna_paired_count_dummy.csv
vendor/TE_model/trials/GSE132441/ribo_paired_cpm_dummy_0.csv
vendor/TE_model/trials/GSE132441/rna_paired_cpm_dummy_0.csv
vendor/TE_model/trials/GSE132441/ribo_paired_quantile_dummy_0.csv
vendor/TE_model/trials/GSE132441/rna_paired_quantile_dummy_0.csv
```

`vendor/TE_model/data/ribo/GSE132441` 是 runtime symlink，指向：

```text
/home/xrx/my_project/te_analysis/vendor/snakescale/output/GSE132441
```

### 5.2 vendor/snakescale

`vendor/snakescale` 当前 dirty：

```text
 M riboflow/RiboFlow.groovy
?? .nextflow.log.1
?? .nextflow.log.2
?? .nextflow.log.3
?? .nextflow.log.4
?? .nextflow.log.5
?? .nextflow.log.6
?? .nextflow.log.7
?? .nextflow.log.8
?? .nextflow.log.9
?? docs/p5_ribo_manifest.tsv
```

这部分需要特别小心：用户约束是不提交 vendor 源码。当前 `riboflow/RiboFlow.groovy` 是 tracked source diff，不应混入本轮非 vendor 提交。

## 6. 进程、锁和空间

当前没有发现残留的：

- `GSE132441`
- `te_analysis.run_downstream`
- `TE.serial.patched`
- `Rscript`

snakemake lock 仍存在：

```text
vendor/snakescale/.snakemake/locks/0.input.lock   26691 bytes   2026-04-21 01:01:50
vendor/snakescale/.snakemake/locks/0.output.lock  1495 bytes    2026-04-21 01:01:50
```

这些 lock 的时间早于本次 GSE132441 downstream 检查，且 downstream 不走 snakemake；当前看起来不是 downstream 新产生的锁。

空间状态：

```text
data/processed/te              2.5M
vendor/snakescale/output       1.2G
vendor/snakescale/intermediates 639G
vendor/TE_model/trials         118M
```

磁盘：

```text
/home/xrx/my_project/te_analysis  48T total, 43T used, 2.8T available, 95% used
```

风险：`vendor/snakescale/intermediates` 占用非常大。继续批量运行前，最好先定义哪些中间文件可重建、哪些产物必须保留，避免误删参考成果。

## 7. 当前阻塞和下一步建议

### P0：继续收敛 GSE132441 downstream

目标仍是：

```text
data/processed/te/GSE132441/GSE132441_TE.csv
```

建议下一次运行直接复现：

```bash
bash scripts/run_gse132441_downstream.sh > /tmp/gse132441_downstream.log 2>&1
```

运行后检查：

```bash
tail -n 120 /tmp/gse132441_downstream.log
find data/processed/te/GSE132441 -maxdepth 2 -type f -printf '%p\t%s bytes\n'
find vendor/TE_model/trials/GSE132441 -maxdepth 1 -type f -name '*TE*' -printf '%p\t%s bytes\n'
```

如果还是停在 `"transfer data from clr to ilr"`，下一步应该围绕 R Stage 2 定位：

1. 确认进程退出码和是否被系统终止。
2. 保留 `/tmp/gse132441_downstream.log`，不要覆盖旧日志前先复制一份带时间戳的日志。
3. 检查是否是内存、数值异常、样本数、矩阵维度或 Arabidopsis transcript alias 导致的问题。
4. 如果定位到必须修改 `vendor/TE_model/src/TE.R` 或其他 vendor R 源码，先暂停并对齐。

### P1：保持 GSE125086 作为主参考路径

GSE125086 是目前最稳定的端到端样板。任何 GSE132441 downstream 修复都应尽量复用：

```bash
bash scripts/run_gse125086_downstream.sh
```

当前 GSE125086 输出：

```text
data/processed/te/GSE125086/GSE125086_TE.csv
```

shape：

```text
(1, 19737)
```

### P2：不要提交 vendor 源码

当前非 vendor 改动可以作为本轮候选提交范围；vendor 目录只应视为 runtime 或外部依赖。尤其要避免提交：

```text
vendor/snakescale/riboflow/RiboFlow.groovy
```

### P3：空间清理另开任务

当前磁盘 95% 使用，`vendor/snakescale/intermediates` 639G。建议不要在 GSE132441 TE 表出来前做大规模清理；等下游闭环后，再制定保留清单：

- 必留：`data/processed/te/GSE105082/`
- 必留：`data/processed/te/GSE125086/`
- 必留：目标 study 的 `.ribo` 和关键日志
- 可评估清理：可重建 intermediates、重复 FASTQ staging、旧 Nextflow 日志

## 8. 当前验收清单

| 验收项 | 当前结果 |
|---|---:|
| `data/processed/te/GSE132441/GSE132441_TE.csv` 存在且非空 | 未达成 |
| GSE132441 至少一个样本出 TE 值 | 未达成 |
| 一条命令可复现 | 入口已存在，但运行未闭环 |
| GSE105082 产物仍在 | 达成 |
| GSE125086 产物仍在 | 达成 |
| 无新的 downstream 残留进程 | 达成 |
| 无新的 downstream snakemake lock | 达成 |
| 非 vendor downstream 单测通过 | 达成 |

## 9. 最短行动建议

下一步最短路径：

1. 重新跑 `bash scripts/run_gse132441_downstream.sh > /tmp/gse132441_downstream.log 2>&1`。
2. 如果能出 `GSE132441_TE.csv`，立即记录 shape，并检查 GSE105082/GSE125086 仍在。
3. 如果再次停在 ILR 阶段，集中定位 TE_model R Stage 2，不先改 vendor R 源码。
4. 确认产物后再整理提交范围，只提交非 vendor 代码、脚本、README 和测试。
