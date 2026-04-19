# TE_model Input Contract (reverse-engineered)

## 0. 溯源

- Vendor path: `vendor/TE_model`
- Commit SHA locked at recon: `0b42e3f756e20b9954548b65ff8a64ae063d9a89`
- Upstream: <https://github.com/CenikLab/TE_model>
- Entry point: `pipeline.bash` (`vendor/TE_model/pipeline.bash:1-44`) — 4-stage bash pipeline
- Stage sequence:
  1. `python -m trials.{trial}.config` (`pipeline.bash:24`) — 作者要求在 `trials/{trial}/config.py` 中调用 `main()` from `src/ribo_counts_to_csv.py`
  2. `python src/ribobase_counts_processing.py -i trials/{trial}/ribo_raw.csv -r trials/{trial}/rnaseq_raw.csv -m paired -o trials/{trial}` (`pipeline.bash:29-31`)
  3. `Rscript src/TE.R trials/{trial}` (`pipeline.bash:37`)
  4. `python src/transpose_TE.py -o trials/{trial}` (`pipeline.bash:41`)

## 1. TE.R 输入文件契约

`vendor/TE_model/src/TE.R` 是 CLR→ILR→回归→ILR→CLR 的翻译效率计算核心（68 行）。

### 1.1 CLI

```text
Rscript src/TE.R <workdir>
```

- `workdir` 在 `TE.R:9-13` 通过 `commandArgs(trailingOnly = TRUE)` 读取，缺省 `.`。

### 1.2 workdir 中的输入文件

| 路径（相对 workdir） | 来源 | 必需 | 出处 |
|---|---|---|---|
| `ribo_paired_count_dummy.csv` | Stage 2 (`ribobase_counts_processing.py`) 产出 | 是 | `TE.R:16` |
| `rna_paired_count_dummy.csv` | Stage 2 产出 | 是 | `TE.R:17` |

### 1.3 workdir **外**的必需输入

| 路径 | 用途 | 必需 | 出处 |
|---|---|---|---|
| `data/infor_filter.csv` | 按 `experiment_alias` 合并 TE → `cell_line` 分组聚合 | **是**（硬编码相对路径） | `TE.R:59` |

`data/infor_filter.csv` **相对于 R 进程的 CWD**，即 `pipeline.bash` 的调用目录（作者假设在 `vendor/TE_model/` 根）。该 CSV 至少需列 `experiment_alias`, `cell_line`；实际文件见 `vendor/TE_model/data/infor_filter.csv`。

### 1.4 TE.R 产出

| 产出路径（相对 workdir） | 内容 | 出处 |
|---|---|---|
| `human_TE_sample_level.rda` | 样本级 TE 矩阵（genes × experiments；clr scale）| `TE.R:57` |
| `human_TE_cellline_all.csv` | cell_line 聚合后的 TE 矩阵（cell_lines × genes） | `TE.R:67` |

## 2. transpose_TE.py 输入 / 输出

`vendor/TE_model/src/transpose_TE.py` (13 行):

- **CLI**: `python src/transpose_TE.py -o <workdir>` (`transpose_TE.py:6`)
- **输入**: `{workdir}/human_TE_cellline_all.csv` (`transpose_TE.py:9`)
- **输出**: `{workdir}/human_TE_cellline_all_T.csv`（转置 + 按正则 `\.(.*)` 清洗 index；`transpose_TE.py:10-12`)

## 3. ribobase_counts_processing.py（Stage 2）

`vendor/TE_model/src/ribobase_counts_processing.py` (137 行) 将原始 counts → CPM → quantile → dummy-gene 合并。

### 3.1 CLI

```text
python src/ribobase_counts_processing.py \
    -i <ribo_raw.csv> -r <rnaseq_raw.csv> \
    -m paired \
    -o <workdir> \
    [-c <cpm_cutoff=1>] [-a <overall_cutoff=70>]
```

（`ribobase_counts_processing.py:16-23`）

### 3.2 Workdir **外**必需输入

| 路径 | 用途 | 必需 | 出处 |
|---|---|---|---|
| `./data/nonpolyA_gene.csv` | paired 模式下过滤非 polyA 基因 | 是（paired 模式） | `ribobase_counts_processing.py:122` |

### 3.3 产出（paired 模式，`ribobase_counts_processing.py:130-135`）

- `ribo_paired_count_dummy.csv`, `ribo_paired_cpm_dummy_{overall_cutoff}.csv`, `ribo_paired_quantile_dummy_{overall_cutoff}.csv`
- `rna_paired_count_dummy.csv`, `rna_paired_cpm_dummy_{overall_cutoff}.csv`, `rna_paired_quantile_dummy_{overall_cutoff}.csv`

## 4. ribo_counts_to_csv.py（Stage 0）

`vendor/TE_model/src/ribo_counts_to_csv.py` (117 行) 将 `.ribo` 文件 → `ribo_raw.csv` + `rnaseq_raw.csv`。作者要求**在 trial 目录的 `config.py` 中调用 `main()`**（README:28-34）。

### 4.1 必需输入

| 资源 | 用途 | 出处 |
|---|---|---|
| `./data/ribo/{study}/ribo/experiments/{experiment}.ribo` | 按 (experiment, study) 组装 | `ribo_counts_to_csv.py:19-20` |
| `./data/ribo/{study}_dedup/ribo/experiments/{experiment}.ribo` | dedup 变体（若 `ribo_dedup=True`）| `ribo_counts_to_csv.py:20` |
| `./data/paxdb_filtered_sample.csv` | 默认 experiment 过滤源（README:45-46） | README |

### 4.2 API

`main(workdir, sample_filter, ribo_dedup, rna_seq_dedup, process_coverage_fn=None, filter=None, custom_experiment_list=None, rnaseq_fn=None)` （README:42-48）

## 5. 我方 run_downstream.py 落地映射

| 我方环境 | → TE_model 期望 | 最小转换 | 置信度 |
|---|---|---|---|
| snakescale 产出 `.ribo` 文件（`data/ribo/{study}/ribo/experiments/{GSM}.ribo`，见 `snakescale_contract.md` §4） | `data/ribo/{study}/ribo/experiments/{GSM}.ribo` | **路径直接可用**（作者硬编码即我方布局） | 高 |
| `data/raw/metadata.csv` 的 `experiment_alias` + `cell_line` | `data/infor_filter.csv` 的 `experiment_alias` + `cell_line` | 字段重命名 / subset 子集（`TE.R:59-61`） | 高 |
| 我方 trial 目录（每次 run）| `trials/{trial}/` 下 `config.py` + 4 个 csv | stage_inputs 生成 `config.py`，或 run_downstream 直接调 `ribo_counts_to_csv.main()` 绕过 `config.py` | 中 |
| 运行根 CWD | `vendor/TE_model/` （由于作者硬编码 `./data/infor_filter.csv` / `./data/nonpolyA_gene.csv` / `./data/ribo/...`） | `subprocess.run(..., cwd="vendor/TE_model")` | 高 |
| 最终产物 | `trials/{trial}/human_TE_cellline_all_T.csv` | 从 `vendor/TE_model/trials/{trial}/` 拷贝至 `data/processed/te/{STUDY}/`（module_contracts §M3）| 高 |

## 6. 已知开放问题

1. **CWD 硬绑定**：`TE.R:59`、`ribobase_counts_processing.py:122`、`ribo_counts_to_csv.py:19-20` 均用形如 `./data/...` 的相对路径。我方 `run_downstream.py` **必须以 `cwd=vendor/TE_model/` 启动子进程**，不能从仓库根调用。此约束限制了 stage_inputs 的产物布局。
2. **`paxdb_filtered_sample.csv` 的版本一致性**：README:30 要求 "Update the sample information in the file `data/paxdb_filtered_sample.csv` to the specific samples you are currently working with." → 作者建议**就地修改** vendor/TE_model/data/paxdb_filtered_sample.csv。**这与我方 "零改动 vendor" 硬约束冲突**（module_contracts §M8/M9）。落地方案：
   - (a) 我方 `stage_inputs.py` 生成 sample filter（pandas 过滤器函数）作为 `custom_experiment_list` 传入 `main()`（`ribo_counts_to_csv.py:main` 签名支持，见 README:42），跳过 `paxdb_filtered_sample.csv`；或
   - (b) 将我方 `metadata.csv` 的子集拷贝写入一个 **trial-local** csv，然后让 `main()` 通过 `sample_filter` lambda 读取（需要 T6 验证）。
3. **`human_TE_*` 命名是否跨物种**：`TE.R:56,67` 将输出命名为 `human_TE_*`，即使 RIBO 实为其他物种。由于"零改动 vendor"，我方需在 `run_downstream.py` **wrapping 层**按 `metadata.csv.organism` 重命名落盘路径（`data/processed/te/{STUDY}/te_{organism}_*.csv` 类推）。
4. **`nonpolyA_gene.csv` 的物种适用性**：作者仅在 paired 模式下使用（`ribobase_counts_processing.py:122`），且 **未按 organism 分路径**。若物种非 human/mouse，此过滤器语义不成立。作者未显式要求；T6 实现前需用户决策 non-human 分支。
5. **Stage 0 `config.py` 约定**：作者约定每个 trial 目录包含 `config.py` 调用 `ribo_counts_to_csv.main()`（README:28-34）；`pipeline.bash:24` 以 `python -m trials.{dir}.config` 导入。若我方动态生成 trial 目录，则需同时写 `config.py` 并确保 `trials/{dir}/__init__.py` 存在。**替代方案**：`run_downstream.py` 直接导入 `ribo_counts_to_csv.main` 并在 Python 内执行 Stage 0，完全绕过 `pipeline.bash` 的 Stage 0 分支，然后从 Stage 1 起调 `pipeline.bash -s 1`。待 T6 决策。
6. **`model_results.txt` 终止信号**：README:35 提到 "You'll know you're done when you see a `model_results.txt` file in the directory." 然而 `TE.R` 与 `transpose_TE.py` **均未产出此文件**（代码中无 `model_results.txt` 字面量）。**README 与代码不一致** — 建议我方以 `human_TE_cellline_all_T.csv` 存在作为 Stage 3 成功信号。
