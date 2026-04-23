# Homo_sapiens Species Serial-Fallback Audit

## 审计对象

本审计只覆盖当前已经验证过的 `Homo_sapiens` species serial-fallback 结果集，不覆盖其他 species，也不重新执行 pipeline。

## 1. Exact inspected paths

### 代码与文档

- `src/te_analysis/run_species_downstream.py`
- `tests/test_run_species_downstream.py`
- `docs/current_project_progress.md`

### species root

- `data/processed/te_species/Homo_sapiens`

### logs

- `data/processed/te_species/Homo_sapiens/logs/TE.serial.patch.20260421_211333.log`
- `data/processed/te_species/Homo_sapiens/logs/homo_sapiens_species_te_prepare.stage2.serial-fallback.20260421_211333.log`
- `data/processed/te_species/Homo_sapiens/logs/homo_sapiens_species_te_prepare.stage3.serial-fallback.20260421_211333.log`

### outputs

- `data/processed/te_species/Homo_sapiens/runtime/vendor/TE_model/trials/homo_sapiens_species_te_prepare/human_TE_sample_level.rda`
- `data/processed/te_species/Homo_sapiens/runtime/vendor/TE_model/trials/homo_sapiens_species_te_prepare/human_TE_cellline_all.csv`
- `data/processed/te_species/Homo_sapiens/runtime/vendor/TE_model/trials/homo_sapiens_species_te_prepare/human_TE_cellline_all_T.csv`

## 2. Exact inspected command snippets

以下命令是本次审计实际使用的只读检查片段：

```bash
ls -lh \
  docs/current_project_progress.md \
  src/te_analysis/run_species_downstream.py \
  tests/test_run_species_downstream.py
```

```bash
ls -lh \
  data/processed/te_species/Homo_sapiens/runtime/vendor/TE_model/trials/homo_sapiens_species_te_prepare/human_TE_sample_level.rda \
  data/processed/te_species/Homo_sapiens/runtime/vendor/TE_model/trials/homo_sapiens_species_te_prepare/human_TE_cellline_all.csv \
  data/processed/te_species/Homo_sapiens/runtime/vendor/TE_model/trials/homo_sapiens_species_te_prepare/human_TE_cellline_all_T.csv
```

```bash
tail -50 data/processed/te_species/Homo_sapiens/logs/TE.serial.patch.20260421_211333.log
tail -50 data/processed/te_species/Homo_sapiens/logs/homo_sapiens_species_te_prepare.stage2.serial-fallback.20260421_211333.log
tail -50 data/processed/te_species/Homo_sapiens/logs/homo_sapiens_species_te_prepare.stage3.serial-fallback.20260421_211333.log
```

```bash
python - <<'PY'
from pathlib import Path
import pandas as pd

trial = Path('data/processed/te_species/Homo_sapiens/runtime/vendor/TE_model/trials/homo_sapiens_species_te_prepare')
cell = pd.read_csv(trial / 'human_TE_cellline_all.csv', index_col=0)
cell_t = pd.read_csv(trial / 'human_TE_cellline_all_T.csv', index_col=0)

transposed = cell.transpose().copy()
transposed.index = transposed.index.str.replace(r'\.(.*)', '', regex=True)
print(cell.shape)
print(cell_t.shape)
print(cell.index.is_unique, cell.columns.is_unique)
print(cell_t.index.is_unique, cell_t.columns.is_unique)
print((transposed.to_numpy() == cell_t.to_numpy()).all())
print(transposed.index.duplicated().sum())
PY
```

## 3. Actual observed output sizes/shapes

### Verified facts

- `human_TE_sample_level.rda`
  - 存在
  - 非零
  - 文件大小：`3.5M`
- `human_TE_cellline_all.csv`
  - 存在
  - 非零
  - 文件大小：`935K`
  - 形状：`4 x 11158`
  - 行索引唯一：是
  - 列名唯一：是
  - 全 NA 列：`0`
  - 全 NA 行：`0`
  - 全零列：`0`
  - 全零行：`0`
- `human_TE_cellline_all_T.csv`
  - 存在
  - 非零
  - 文件大小：`869K`
  - 形状：`11158 x 4`
  - 行索引唯一：否
  - 列名唯一：是
  - 全 NA 列：`0`
  - 全 NA 行：`0`
  - 全零列：`0`
  - 全零行：`0`

### Verified fact: transpose consistency

对 `human_TE_cellline_all.csv` 做转置，并应用 shared vendor `transpose_TE.py` 同样的索引清洗规则后：

- 形状与 `human_TE_cellline_all_T.csv` 一致
- 列顺序一致
- 行顺序一致
- 数值逐元素一致

因此可以确认：

- `human_TE_cellline_all_T.csv` 确实是当前 shared vendor 转置逻辑的结果

### Verified fact: duplicate row names in `_T`

`human_TE_cellline_all_T.csv` 存在重复行名。

已验证事实：

- 重复行名总数：`16`
- 例子包括：
  - `H1`
  - `H3`
  - `HLA`
  - `MT`

## 4. Logs and execution evidence

### Verified facts

- patch log 记录了这次 serial patch 的最小替换摘要：
  - `library(doParallel)` removed: `1`
  - `makeCluster(...)` removed: `1`
  - `registerDoParallel(...)` removed: `1`
  - `%dopar% -> %do%`: `1`
  - `stopCluster(...)` removed: `1`
- patch log 明确记录了：
  - source `TE.R` 来自 shared `vendor/TE_model/src/TE.R`
  - patched `TE.R` 写到了 species root 下的 runtime-owned 路径
- Stage 2 log 中已验证：
  - `cwd=/home/xrx/my_project/te_analysis/vendor/TE_model`
  - 实际调用的是 runtime-generated patched `TE.R`
  - 输入 trial 路径是 species trial 的绝对路径
  - 日志中未见：
    - `serverSocket`
    - `Traceback`
    - 明确文件缺失错误
- Stage 3 log 中已验证：
  - 调用的是 shared `src/transpose_TE.py`
  - `cwd` 仍是 shared `vendor/TE_model`
  - 日志中未见 traceback

### Inference

- Stage 2 log 本身没有 finish marker，因此“clean completion”不是由日志单独证明的。
- 但结合以下事实，可以合理推断本次 Stage 2 已完成到足以进入 Stage 3：
  - `human_TE_sample_level.rda` 存在且非零
  - `human_TE_cellline_all.csv` 存在且非零
  - Stage 3 log 存在，且 Stage 3 输出文件非零

### Unknown / not checked

- 本次没有检查 `human_TE_sample_level.rda` 的内部对象名称和对象维度
- 本次没有检查数值的生物学合理性
- 本次没有检查 statistical model 的质量，只检查结构完整性

## 5. Structural consistency verdict

### Verified facts

- canonical CSV `human_TE_cellline_all.csv` 结构完整
- `_T` 文件确实来自当前 shared vendor 转置逻辑
- canonical CSV 与 `_T` 都不存在整列全空 / 全零问题

### Inference

- 以当前工程标准看，这组结果已经足以作为“受控下游分析”的输入
- 但分析入口应优先使用 `human_TE_cellline_all.csv`
- `_T` 文件不能在未处理重复行名的前提下，被默认当作唯一 feature ID 矩阵

### Unknown / not checked

- 没有检查下游科学分析层对重复 feature 标签的容忍度

## 6. Explicit remaining gaps

- `human_TE_sample_level.rda` 的内部 schema 仍未做对象级审计
- `human_TE_cellline_all_T.csv` 存在重复行名，不能默认视作唯一 feature table
- 当前结果只对 `Homo_sapiens` 的当前 trial 做了结构审计，不代表其他物种自动成立
- shared `vendor/TE_model` 的 `shared` 模式在当前主机上仍有已知 PSOCK/socket 风险

## 7. Final recommendation

- **READY_FOR_CONTROLLED_DOWNSTREAM_ANALYSIS**

理由只基于本次已验证事实：

- species serial-fallback 主线已真实闭环
- 三个最终输出文件均存在且非零
- canonical CSV 结构完整，且没有明显的空矩阵 / 全零矩阵问题
- `_T` 文件的重复行名问题已被定位并可控，不影响把 canonical CSV 作为主消费对象
