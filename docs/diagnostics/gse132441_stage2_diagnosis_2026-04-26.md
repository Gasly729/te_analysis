# GSE132441 downstream Stage 2 只读诊断（2026-04-26）

工作区：`/home/xrx/my_project/te_analysis`  
诊断范围：只读检查 GSE132441 downstream 在 TE_model R Stage 2 中断后未产出 TE 表的现场状态。  
禁动确认：本次没有重跑 downstream，没有启动 R/Rscript/snakemake/nextflow，没有删除文件，没有修改 `vendor/`，没有修改 `data/processed/te/`。

## 1. 现场快照

### 1.1 起点校验

| 校验项 | 结果 |
|---|---:|
| 当前工作目录为 `/home/xrx/my_project/te_analysis` | 通过 |
| 顶层 `git status --short` 含预期非 vendor 改动 | 通过 |
| `vendor/snakescale` dirty | 通过 |
| `data/processed/te/GSE125086/GSE125086_TE.csv` 存在 | 通过 |
| `vendor/snakescale/output/GSE132441/ribo/all.ribo` 存在 | 通过 |
| `vendor/TE_model/trials/GSE132441/ribo_paired_quantile_dummy_0.csv` 存在 | 通过 |
| `data/processed/te/GSE132441/GSE132441_TE.csv` 不存在 | 通过 |

顶层工作区状态：

```text
 M Makefile
 M README.md
 M src/te_analysis/run_downstream.py
 M tests/test_run_downstream.py
?? reports/project_alignment_2026-04-26.md
?? scripts/run_gse132441_downstream.sh
```

`vendor/snakescale` 状态：

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

### 1.2 `vendor/TE_model/trials/GSE132441/` 当前文件

当前只看到 4 个矩阵文件；`ribo_raw.csv`、`rnaseq_raw.csv`、count dummy 文件和 `config.py` 现在不在该目录下。目录 mtime 为 `2026-04-26 15:54:23.331523364 +0800`，早于本次对齐文档 `reports/project_alignment_2026-04-26.md` 的 mtime `2026-04-26 15:55:25.577928093 +0800`。这说明当前 trial 现场已经不是 2026-04-24 运行刚结束时的完整中间现场。

```text
vendor/TE_model/trials/GSE132441/rna_paired_cpm_dummy_0.csv        712309 bytes  2026-04-24 19:20:47.3710908050
vendor/TE_model/trials/GSE132441/rna_paired_quantile_dummy_0.csv   616920 bytes  2026-04-24 19:20:47.4750908550
vendor/TE_model/trials/GSE132441/ribo_paired_quantile_dummy_0.csv  476221 bytes  2026-04-24 19:20:47.1690907090
vendor/TE_model/trials/GSE132441/ribo_paired_cpm_dummy_0.csv       478328 bytes  2026-04-24 19:20:47.0940906740
```

### 1.3 `data/processed/te/GSE132441/` 当前文件

```text
data/processed/te/GSE132441/runtime_overrides/TE.serial.patched.20260424_192048.R  2433 bytes  2026-04-24 19:20:48.3100912500
data/processed/te/GSE132441/logs/TE.serial.patch.20260424_192048.log               351 bytes   2026-04-24 19:20:48.3110912500
```

未发现：

```text
data/processed/te/GSE132441/GSE132441_TE.csv
```

### 1.4 `vendor/snakescale/output/GSE132441/ribo/` `.ribo` 清单

```text
vendor/snakescale/output/GSE132441/ribo/experiments/GSM3863561.ribo  3254868 bytes  2026-04-24 18:01:39.3875294750
vendor/snakescale/output/GSE132441/ribo/experiments/GSM3863558.ribo  3268905 bytes  2026-04-24 18:01:36.6905545380
vendor/snakescale/output/GSE132441/ribo/experiments/GSM3863556.ribo  3286582 bytes  2026-04-24 18:01:35.7305634730
vendor/snakescale/output/GSE132441/ribo/all.ribo                    9360433 bytes  2026-04-24 18:01:42.7344984510
```

## 2. 中间矩阵形态对照表

采集方法：对每个 CSV 先用 `pandas.read_csv(..., dtype=str)` 读取 header/第一列，再用 `pandas.read_csv(..., index_col=0)` 读取数值矩阵并计算 NA、Inf、全零行列和负值行。未写文件。

### 2.1 GSE132441

| 文件 | 状态 | shape | 第一列名 | 第一列前 5 个值 | NA 比例 | Inf 比例 | 全零行数 | 全零列数 | 含负值行数 |
|---|---:|---:|---|---|---:|---:|---:|---:|---:|
| `ribo_raw.csv` | 缺失 | NA | NA | NA | NA | NA | NA | NA | NA |
| `rnaseq_raw.csv` | 缺失 | NA | NA | NA | NA | NA | NA | NA | NA |
| `ribo_paired_count_dummy.csv` | 缺失 | NA | NA | NA | NA | NA | NA | NA | NA |
| `rna_paired_count_dummy.csv` | 缺失 | NA | NA | NA | NA | NA | NA | NA | NA |
| `ribo_paired_cpm_dummy_0.csv` | 存在 | `19110 x 3` | `transcript` | `AT1G01010.1`, `AT1G01020.1`, `AT1G01030.1`, `AT1G01040.1`, `AT1G01050.1` | 0 | 0 | 17938 | 0 | 0 |
| `rna_paired_cpm_dummy_0.csv` | 存在 | `19110 x 3` | `Unnamed: 0` | `AT1G01010.1`, `AT1G01020.1`, `AT1G01030.1`, `AT1G01040.1`, `AT1G01050.1` | 0 | 0 | 8542 | 0 | 0 |
| `ribo_paired_quantile_dummy_0.csv` | 存在 | `19110 x 3` | `transcript` | `AT1G01010.1`, `AT1G01020.1`, `AT1G01030.1`, `AT1G01040.1`, `AT1G01050.1` | 0 | 0 | 17938 | 0 | 0 |
| `rna_paired_quantile_dummy_0.csv` | 存在 | `19110 x 3` | `Unnamed: 0` | `AT1G01010.1`, `AT1G01020.1`, `AT1G01030.1`, `AT1G01040.1`, `AT1G01050.1` | 0 | 0 | 8542 | 0 | 0 |

判断：

- 第一列值是 Arabidopsis transcript-like ID，例如 `AT1G01010.1`，不是人类 gene symbol。
- 4 个现存矩阵没有 NA、Inf 或负值。
- Ribo 矩阵全零行非常多：`17938 / 19110`。
- RNA 矩阵全零行也很多：`8542 / 19110`。
- Stage 2 R 脚本实际读取的是 `ribo_paired_count_dummy.csv` 和 `rna_paired_count_dummy.csv`，但这两个文件当前缺失。因此当前现场不能完整复核 R Stage 2 的真实输入矩阵。

### 2.2 GSE125086 对照

`vendor/TE_model/trials/GSE125086/` 当前不存在，因此 §3.6 对照矩阵未采集到。

| 文件 | 状态 |
|---|---:|
| `vendor/TE_model/trials/GSE125086/ribo_raw.csv` | 未采集到，原因：trial 目录不存在 |
| `vendor/TE_model/trials/GSE125086/rnaseq_raw.csv` | 未采集到，原因：trial 目录不存在 |
| `vendor/TE_model/trials/GSE125086/ribo_paired_count_dummy.csv` | 未采集到，原因：trial 目录不存在 |
| `vendor/TE_model/trials/GSE125086/rna_paired_count_dummy.csv` | 未采集到，原因：trial 目录不存在 |
| `vendor/TE_model/trials/GSE125086/ribo_paired_cpm_dummy_0.csv` | 未采集到，原因：trial 目录不存在 |
| `vendor/TE_model/trials/GSE125086/rna_paired_cpm_dummy_0.csv` | 未采集到，原因：trial 目录不存在 |
| `vendor/TE_model/trials/GSE125086/ribo_paired_quantile_dummy_0.csv` | 未采集到，原因：trial 目录不存在 |
| `vendor/TE_model/trials/GSE125086/rna_paired_quantile_dummy_0.csv` | 未采集到，原因：trial 目录不存在 |

已确认 GSE125086 的最终参考产物存在：

```text
data/processed/te/GSE125086/GSE125086_TE.csv
```

但当前没有 vendor trial 中间矩阵可用于同口径对照。

## 3. R 脚本断点定位

### 3.1 `"transfer data from clr to ilr"` 所在位置

搜索结果：

```text
vendor/TE_model/src/TE.R:28:  print("transfer data from clr to ilr")
vendor/TE_model/src/TE.R:29:  ### transfer data from clr to ilr
```

### 3.2 断点后 30 行上下文

以下为 `vendor/TE_model/src/TE.R` 第 28 行起的上下文摘录：

```r
    28	  print("transfer data from clr to ilr")
    29	  ### transfer data from clr to ilr
    30	  ### This transformation is crucial as it allows the compositional data 
    31	  ### to be decomposed into an array of uncorrelated variables 
    32	  ### while preserving relative proportions. 
    33	  RIBO_ilr <- clr2ilr(pr_RIBO@logratio)
    34	  RNA_ilr <- clr2ilr(pr_RNA@logratio)
    35	  RIBO_ilr <- as.data.frame(t(RIBO_ilr))
    36	  RNA_ilr <- as.data.frame(t(RNA_ilr))
    37	  # out <- data.frame(matrix(ncol = 0, nrow = nrow(RIBO_ilr) + 1))
    38	  ### calculate proportional regression
    39	  # for (i in 1:ncol(RIBO_ilr)) {
    40	  #   print(i)
    41	  #   m <- summary(lm(RIBO_ilr[, i] ~ RNA_ilr[, i]))
    42	  #   out[, i] <- data.frame(as.numeric(ilr2clr(resid(m))))
    43	  # }
    44	  print("calculate proportional regression")
    45	  out <- foreach(i = 1:ncol(RIBO_ilr), .combine = "cbind", .packages = c("compositions")) %dopar% {
    46	    ### compositional linear regression
    47	    m <- summary(lm(RIBO_ilr[, i] ~ RNA_ilr[, i]))
    48	    ### define the residuals as TE and transfer the data back to clr
    49	    data.frame(as.numeric(ilr2clr(resid(m))))
    50	  }
    51	
    52	  colnames(out) <- rownames(RIBO)
    53	  rownames(out) <- colnames(RIBO)
    54	  return(out)
    55	}
    56	human_TE <- TE_clr(RIBO, RNA)
    57	save(human_TE, file = paste(args[1], "/human_TE_sample_level.rda", sep = ""))
    58	
```

日志最后一行是：

```text
[1] "transfer data from clr to ilr"
```

日志没有出现下一条：

```text
[1] "calculate proportional regression"
```

因此最后可见断点位于 `TE.R` 第 33-34 行 `clr2ilr(...)` 之前或之中，而不是后面的 `human_TE` 保存或 `cellline_all` 写出阶段。

### 3.3 同一 R 文件中相关硬编码字面量

搜索 `human_TE`、`HELA`、`homo_sapiens`、`cellline_all` 的结果：

```text
56:human_TE <- TE_clr(RIBO, RNA)
57:save(human_TE, file = paste(args[1], "/human_TE_sample_level.rda", sep = ""))
61:df <- merge(infor, t(human_TE), by.x = "experiment_alias", by.y = 0)
67:write.csv(df_cell_line_fin, paste(args[1], "/human_TE_cellline_all.csv", sep = ""))
```

未在 `vendor/TE_model/src/TE.R` 中找到 `HELA` 或 `homo_sapiens` 字面量。

## 4. alias 一致性比对

### 4.1 wrapper 注入逻辑

`src/te_analysis/run_downstream.py` 对非人类物种生成 runtime config 时注入：

```python
import ribopy

def _identity_alias(transcript):
    return transcript

ribopy.api.alias.apris_human_alias = _identity_alias
```

触发条件：

```python
if organism.strip().lower() == "homo sapiens":
    return ""
```

GSE132441 metadata 中的物种字符串为：

```text
Arabidopsis thaliana
```

因此 GSE132441 会走非人类 alias patch，把 `apris_human_alias` 替换成 identity alias。该 patch 只作用于 Python Stage 0 的 ribopy transcript alias，不向 R Stage 2 传递物种字符串。

### 4.2 wrapper 输出命名逻辑

`run_downstream.py` 的 `_copy_products(...)` 逻辑：

```python
org = organism.strip().lower().replace(" ", "_")
...
shutil.copy2(src, out_dir / name.replace("human_", f"{org}_"))
...
canonical = out_dir / f"{study}_TE.csv"
canonical_df = _require_nonempty_csv(trial_dir / "human_TE_cellline_all.csv", "canonical TE CSV")
```

对 GSE132441，wrapper 侧物种 alias 为：

```text
arabidopsis_thaliana
```

wrapper 期望先从 R 侧拿到：

```text
human_TE_cellline_all.csv
human_TE_cellline_all_T.csv
human_TE_sample_level.rda
```

再复制为：

```text
arabidopsis_thaliana_TE_cellline_all.csv
arabidopsis_thaliana_TE_cellline_all_T.csv
arabidopsis_thaliana_TE_sample_level.rda
GSE132441_TE.csv
```

### 4.3 R 脚本输出命名期望

`vendor/TE_model/src/TE.R` 硬编码输出：

```text
human_TE_sample_level.rda
human_TE_cellline_all.csv
```

### 4.4 一致性结论

文件名层面：当前 wrapper 与 R 脚本是有意兼容的。

| 位置 | 字符串 |
|---|---|
| metadata 物种 | `Arabidopsis thaliana` |
| wrapper 复制 alias | `arabidopsis_thaliana` |
| R Stage 2 内部变量 | `human_TE` |
| R Stage 2 输出文件 | `human_TE_sample_level.rda`, `human_TE_cellline_all.csv` |
| wrapper canonical 输入 | `human_TE_cellline_all.csv` |
| wrapper canonical 输出 | `GSE132441_TE.csv` |

不一致点：R 侧没有真实物种参数，且内部输出名仍是 `human_*`。不过这不是当前最后日志断点的直接证据，因为运行尚未到第 57 行 `save(human_TE, ...)` 或第 67 行 `write.csv(...)`。

## 5. 进程与系统信号

### 5.1 `/tmp/gse132441_downstream.log`

日志行数：

```text
66 /tmp/gse132441_downstream.log
```

mtime：

```text
/tmp/gse132441_downstream.log  2501 bytes  2026-04-24 19:26:04.908924164 +0800
```

最后 200 行实际等于完整日志：

```text
Processed GSM3863561
Processed GSM3863556
Processed GSM3863558
####preprocessing raw ribo data####
####preprocessing raw rna data####
####dummy gene####
####generate pre-final table####
####remove polyA genes####
####generate final table####
Warning message:
package ‘propr’ was built under R version 4.2.3 
Welcome to compositions, a package for compositional data analysis.
Find an intro with "? compositions"


Attaching package: ‘compositions’

The following objects are masked from ‘package:stats’:

    anova, cor, cov, dist, var

The following object is masked from ‘package:graphics’:

    segments

The following objects are masked from ‘package:base’:

    %*%, norm, scale, scale.default

Warning message:
package ‘compositions’ was built under R version 4.2.3 
Failed to connect to bus: Operation not permitted (consider using --machine=<user>@.host --user to connect to bus of other user)
── Attaching packages ─────────────────────────────────────── tidyverse 1.3.2 ──
✔ ggplot2 3.5.1     ✔ purrr   1.0.2
✔ tibble  3.2.1     ✔ dplyr   1.1.4
✔ tidyr   1.3.1     ✔ stringr 1.5.1
✔ readr   2.1.5     ✔ forcats 1.0.0
── Conflicts ────────────────────────────────────────── tidyverse_conflicts() ──
✖ dplyr::filter() masks stats::filter()
✖ dplyr::lag()    masks stats::lag()
Warning messages:
1: In system("timedatectl", intern = TRUE) :
  running command 'timedatectl' had status 1
2: package ‘ggplot2’ was built under R version 4.2.3 
3: package ‘tibble’ was built under R version 4.2.3 
4: package ‘tidyr’ was built under R version 4.2.3 
5: package ‘readr’ was built under R version 4.2.3 
6: package ‘purrr’ was built under R version 4.2.3 
7: package ‘dplyr’ was built under R version 4.2.3 
8: package ‘stringr’ was built under R version 4.2.3 
9: package ‘forcats’ was built under R version 4.2.3 

Attaching package: ‘foreach’

The following objects are masked from ‘package:purrr’:

    accumulate, when

Warning message:
package ‘foreach’ was built under R version 4.2.3 
[1]     3 19111
Alert: Fixing permutations to active random seed.
Alert: Use 'updateCutoffs' to calculate FDR.
Alert: Fixing permutations to active random seed.
Alert: Use 'updateCutoffs' to calculate FDR.
[1] "transfer data from clr to ilr"
```

关键词扫描：

| 关键词 | 结果 |
|---|---:|
| `Killed` | 未出现 |
| `Error` | 未出现 |
| `Traceback` | 未出现 |
| `std::bad_alloc` | 未出现 |
| `OOM` | 未出现 |
| `segfault` | 未出现 |

### 5.2 dmesg

采集命令无权限读取 kernel buffer：

```text
dmesg: read kernel buffer failed: Operation not permitted
```

结论：未采集到 dmesg OOM/R kill 证据，原因是无权限；未使用 sudo。

### 5.3 journalctl

按要求采集：

```bash
journalctl --since "1 days ago" --no-pager | grep -iE 'killed|oom'
```

结果没有匹配行，仅提示当前用户看不到其他用户和系统消息：

```text
Hint: You are currently not seeing messages from other users and the system.
      Users in groups '4294967295', 'systemd-journal' can see all messages.
      Pass -q to turn off this notice.
```

补充按运行时间窗口采集：

```bash
journalctl --since "2026-04-24 19:00:00" --until "2026-04-24 20:00:00" --no-pager | grep -iE 'killed|oom'
```

同样没有匹配行，仅有同一权限提示。因此当前可见 journal 中没有 OOM/kill 证据，但该结论受 journal 权限限制。

## 6. 初步根因归类

以下排序只基于当前只读证据，不包含修复建议。

### 1. R 进程被外部信号 kill（OOM/超时）

支持证据：

- 日志在 `TE.R` 第 28 行 `"transfer data from clr to ilr"` 后截断，没有 R `Error`、Python `Traceback` 或后续 wrapper 输出。
- 日志没有出现第 44 行 `"calculate proportional regression"`，说明进程大概率停在 `clr2ilr(pr_RIBO@logratio)` / `clr2ilr(pr_RNA@logratio)` 附近。
- `TE.R` 已打印维度 `[1] 3 19111`，即 3 个样本、约 19111 个特征；ILR/矩阵转换可能形成较大的中间对象。
- 当前没有残留 R 进程，且没有 Stage 2 输出文件。

反对证据：

- `/tmp/gse132441_downstream.log` 中没有 `Killed`、`OOM`、`std::bad_alloc` 或 `segfault`。
- `dmesg` 无权限，journal 可见范围有限，未能确认系统级 kill。
- `vendor/TE_model/trials/GSE132441/` 当前缺少 Stage 2 实际读取的 count dummy 文件，无法复核输入矩阵是否足以触发内存问题。

置信度：中等。

### 2. 3 样本下 ILR 后续协方差/残差回归秩亏

支持证据：

- R 打印维度为 `3 x 19111`，样本数极少。
- 现存 CPM/quantile 矩阵显示大量全零行：ribo 为 `17938 / 19110`，RNA 为 `8542 / 19110`。
- R 断点位于 ILR 转换之前或之中；如果 compositional transform 后矩阵退化，后续回归也容易出现秩亏或不可估计。

反对证据：

- 日志没有 R `Error`，也没有到达第 44 行 `"calculate proportional regression"`，所以当前更像 ILR 阶段中断，而不是已进入回归阶段后失败。
- 现有矩阵没有 NA、Inf 或负值。
- Stage 2 实际读取的 count dummy 文件当前缺失，不能确认 count 矩阵的零结构与现存 CPM/quantile 完全一致。

置信度：中等偏低。

### 3. vendor R 代码 bug

支持证据：

- `TE.R` 对所有物种硬编码读取 `data/infor_filter.csv`，并硬编码 `human_TE_*` 输出名。
- `TE.R` 在第 33-49 行进行 compositional transform 和并行 foreach 回归，缺少输入维度、零行、秩亏、异常对象大小等显式检查。
- 当前日志截断位置靠近 `clr2ilr(...)`，该段没有防御式错误处理。

反对证据：

- GSE125086 已经在同一大框架下产出过 TE 表，说明 vendor R 代码不是对所有输入都必然失败。
- 当前没有直接 R error stack，不能把中断具体归因到代码 bug。

置信度：中等偏低。

### 4. Arabidopsis transcript ID 与 mapping 表不匹配

支持证据：

- 现存矩阵第一列是 Arabidopsis transcript ID，例如 `AT1G01010.1`。
- R 脚本后续读取 `data/infor_filter.csv` 并按 `experiment_alias` merge；该文件命名和 TE_model 语义明显偏人类 reference。
- Stage 0 需要 runtime alias patch 才能绕过 `apris_human_alias` 对 Arabidopsis transcript ID 的假设。

反对证据：

- 当前日志还没有到第 59-67 行的 `infor_filter.csv` merge 和 `human_TE_cellline_all.csv` 写出阶段。
- R Stage 2 当前可见断点在 `clr2ilr(...)` 附近，不是 gene/transcript mapping 或 metadata merge 位置。
- Stage 0 已经处理完 3 个样本，说明 `.ribo` schema 和基础 transcript ID 读取至少没有在 Python 侧立即失败。

置信度：低到中等。

### 5. R Stage 2 硬编码 human 命名导致非人类输出失败

支持证据：

- R 文件硬编码 `human_TE`、`human_TE_sample_level.rda`、`human_TE_cellline_all.csv`。
- GSE132441 的真实物种为 `Arabidopsis thaliana`。

反对证据：

- wrapper 明确以 `human_TE_cellline_all.csv` 作为 canonical 输入，再复制成 `arabidopsis_thaliana_*` 和 `GSE132441_TE.csv`；因此文件名层面当前是兼容的。
- 日志没有运行到 `save(human_TE, ...)` 或 `write.csv(... human_TE_cellline_all.csv ...)`。
- 当前没有任何证据显示失败发生在输出命名阶段。

置信度：低。

### 6. 纯 R runtime 环境问题

支持证据：

- 日志中有 R 包版本 warning 和 `timedatectl` bus warning。
- `foreach` / `doParallel` 参与 Stage 2，历史上 shared 模式有并行/socket 风险。

反对证据：

- 这些 warning 在 R 启动和包加载阶段出现，后续已经进入 TE_model 计算。
- 日志没有 package load failure。
- GSE125086 已经用同一类环境产出过 TE 表。

置信度：低。

## 7. 诊断结论与下一步需采集证据

当前最重要的诊断结论：

1. GSE132441 的 `.ribo` 输入存在，Stage 0 至少曾处理完 3 个样本。
2. 日志最后可见位置对应 `vendor/TE_model/src/TE.R` 第 28 行，下一步是第 33-34 行 `clr2ilr(...)`。
3. 没有看到 R/Python 显式错误，也没有看到日志内 kill/OOM 字样。
4. dmesg 无权限，journal 可见范围有限，因此系统级 kill/OOM 证据目前未能确认或排除。
5. 当前 `vendor/TE_model/trials/GSE132441/` 已不是完整 Stage 2 输入现场：Stage 2 读取的 count dummy 文件缺失，只剩 4 个 CPM/quantile 矩阵。
6. 现存矩阵显示 Arabidopsis transcript ID、无 NA/Inf/负值，但全零行比例很高。
7. R 的 `human_*` 输出命名与当前 wrapper 的复制逻辑在文件名层面一致，不是当前断点的最强解释。

下一步只需要再采集的证据：

- 捕获下一次 Stage 2 运行的真实退出码。
- 在不覆盖旧日志的前提下保存完整 stdout/stderr，并确认是否有 shell 层面的 `Killed`。
- 在 Stage 2 运行时记录进程资源使用峰值，尤其是 RSS/内存和运行时长。
- 在完整现场存在时重新采集 `ribo_paired_count_dummy.csv` 和 `rna_paired_count_dummy.csv` 的同口径矩阵形态。
- 如果权限允许，采集运行时间窗口内的系统 OOM/killer 记录。
- 在不修改 vendor R 源码的前提下，确认 `clr2ilr(pr_RIBO@logratio)` 和 `clr2ilr(pr_RNA@logratio)` 之前的对象维度与稀疏/零结构。

本报告不提供修复方案。
