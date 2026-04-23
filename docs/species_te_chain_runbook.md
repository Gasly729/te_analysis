# Species TE Chain RUNBOOK

## 这个顶层入口解决什么问题

这份 RUNBOOK 说明当前单物种受控整链入口如何把三段已存在的逻辑正式串起来：

1. `aggregate_species_te.py --prepare-only`
2. `run_species_downstream.py --stage2-mode ...`
3. canonical `human_TE_cellline_all.csv` intake check

它不是新的“大而全 pipeline”，也不是全物种 orchestrator。它只是一个极薄的单物种 orchestration layer，用来把当前已验证的 species baseline 变成可复现的操作入口。

## 什么时候用它

应在以下场景使用：

- 你要对**单个物种**执行当前正式 species 链路
- 你希望把 prepare、downstream、canonical output intake 作为一个受控入口串起来
- 当前 analysis intake 只需要 canonical `human_TE_cellline_all.csv`

当前 canonical baseline 是：

- organism: `Homo_sapiens`
- trial: `homo_sapiens_species_te_prepare`
- Stage 2 mode: `serial-fallback`

## 什么时候不要用它

以下情况不要用这个入口：

- 你要做全物种批量编排
- 你要修改 shared `vendor/TE_model`
- 你要把 `_T` 文件作为默认 canonical analysis intake
- 你要重构现有 Stage 2/3 数学逻辑
- 你要替代 `aggregate_species_te.py` 或 `run_species_downstream.py`

## 它和现有两个入口的关系

### `aggregate_species_te.py`

- 仍然负责 prepare-only
- 仍然只写 species runtime 的 inputs / trials / manifests
- 不执行 vendor code

### `run_species_downstream.py`

- 仍然负责 Stage 2/3
- 仍然是 species downstream 的直接执行入口
- 当前链路入口只是把它作为下游执行步骤串起来

## Canonical command

先进入项目环境：

```bash
source ~/miniconda3/etc/profile.d/conda.sh
conda activate te_analysis
cd /home/xrx/my_project/te_analysis
export PYTHONPATH=src
```

当前 `Homo_sapiens` canonical command：

```bash
python -m te_analysis.run_species_te_chain \
  --organism Homo_sapiens \
  --out-dir data/processed/te_species/Homo_sapiens \
  --trial homo_sapiens_species_te_prepare \
  --metadata data/raw/metadata.csv \
  --stage2-mode serial-fallback \
  --prepare \
  --run-downstream \
  --check-output
```

## 参数解释

- `--organism`
  - 物种名；prepare 步骤和默认 trial 名都会从它派生
- `--out-dir`
  - species root；当前 canonical 例子里是 `data/processed/te_species/Homo_sapiens`
- `--trial`
  - downstream / output check 使用的 trial 名
  - 如果同时跑 `--prepare`，当前不支持自定义 trial 名；只能等于默认 `<organism_slug>_species_te_prepare`
- `--metadata`
  - 传给 `aggregate_species_te.py` 的 metadata 路径
- `--ribo-glob`
  - 可重复；直接透传给 prepare 步骤
- `--study`
  - 可重复；直接透传给 prepare 步骤
- `--stage2-mode`
  - 只支持 `shared` / `serial-fallback`
  - 默认是 `serial-fallback`
- `--prepare`
  - 跑 species prepare
- `--run-downstream`
  - 跑 species Stage 2/3
- `--check-output`
  - 只做 canonical `human_TE_cellline_all.csv` intake check

## Canonical success gate

当前默认 success gate **只基于** canonical CSV：

- `human_TE_cellline_all.csv`

当前 intake check 只验证：

- 文件存在
- 非 0 字节
- pandas 可读
- 行列数都大于 0
- 列名唯一
- 没有全 NA 行/列
- 没有全零行/列

当前 success gate **不依赖**：

- `human_TE_cellline_all_T.csv`

原因很明确：

- `_T` 文件是便捷转置视图
- 当前已知它可能有重复行名
- 因此它不能作为默认 canonical analysis intake

## 推荐使用方式

### 只跑 prepare

```bash
python -m te_analysis.run_species_te_chain \
  --organism Homo_sapiens \
  --out-dir data/processed/te_species/Homo_sapiens \
  --metadata data/raw/metadata.csv \
  --prepare
```

### 只跑 downstream

```bash
python -m te_analysis.run_species_te_chain \
  --organism Homo_sapiens \
  --out-dir data/processed/te_species/Homo_sapiens \
  --trial homo_sapiens_species_te_prepare \
  --stage2-mode serial-fallback \
  --run-downstream
```

### 只跑 output check

```bash
python -m te_analysis.run_species_te_chain \
  --organism Homo_sapiens \
  --out-dir data/processed/te_species/Homo_sapiens \
  --trial homo_sapiens_species_te_prepare \
  --check-output
```

## Success criteria

这个顶层入口返回成功前，至少要满足：

- 如果跑了 `--prepare`
  - prepare 步骤正常结束
- 如果跑了 `--run-downstream`
  - downstream 步骤正常结束
- 如果跑了 `--check-output`
  - canonical `human_TE_cellline_all.csv` 通过 intake check

## Known failure signals

- `--prepare` 与自定义 `--trial` 同时使用
  - 当前会直接报错，因为 prepare 阶段不支持自定义 trial 命名
- canonical CSV 缺失或空文件
- canonical CSV 存在重复列名
- canonical CSV 存在全 NA 行/列
- canonical CSV 存在全零行/列
- `shared` 模式在当前主机上再次触发 `serverSocket` / `PSOCK` 错误

## 当前已知边界

- 当前入口只保证单物种受控链路
- 当前 canonical baseline 仍是 `Homo_sapiens + serial-fallback`
- 当前 analysis intake 使用 `human_TE_cellline_all.csv`
- 当前不宣称所有物种都能直接复用
