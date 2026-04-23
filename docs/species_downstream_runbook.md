# Species Downstream RUNBOOK

## Purpose

这份 RUNBOOK 只覆盖当前已经验证过的 species downstream Stage 2/3 执行路径。它的目标是把现有 `species prepare output` 接到 shared `vendor/TE_model` 的代码层上，完成 species trial 的 Stage 2 和 Stage 3。

当前已验证的 canonical example 是：

- species root: `data/processed/te_species/Homo_sapiens`
- trial: `homo_sapiens_species_te_prepare`
- Stage 2 mode: `serial-fallback`

## Preconditions

执行前必须满足以下条件：

- 已完成 `aggregate_species_te.py --prepare-only`
- species root 已存在，例如 `data/processed/te_species/Homo_sapiens`
- species runtime trial 已存在：
  - `data/processed/te_species/Homo_sapiens/runtime/vendor/TE_model/trials/homo_sapiens_species_te_prepare`
- 该 trial 下必须已有非空 Stage 1 输入：
  - `ribo_paired_count_dummy.csv`
  - `rna_paired_count_dummy.csv`
- shared vendor code root 必须存在：
  - `vendor/TE_model`
- 当前入口依赖的解释器路径必须可用：
  - R: `/home/xrx/miniconda3/envs/snakemake-ribo/bin/Rscript`
  - Python: `/home/xrx/miniconda3/envs/te_analysis/bin/python`

如果只传 `--species-root`，代码会自动在该 species root 下发现 runtime trial config。当前入口也支持直接传 `--runtime-root`，但这不是当前 `Homo_sapiens` 例子的 canonical 调用方式。

## When to use `shared`

`shared` 是代码支持的 Stage 2 模式，含义是：

- 不生成 patched `TE.R`
- 直接在 shared `vendor/TE_model` 的 `cwd` 下调用：
  - `Rscript src/TE.R <absolute species trial dir>`

只有在以下条件满足时才应使用 `shared`：

- 当前主机上的 shared vendor Stage 2 可以原生通过
- 没有已知的 `PSOCK/socket` 失败

当前仓库中，`shared` 模式在 `Homo_sapiens` 上曾真实触发：

- `Error in serverSocket(port = port) : creation of server socket failed`

因此在当前这台主机上，`Homo_sapiens` 不应优先使用 `shared`。

## When to use `serial-fallback`

`serial-fallback` 是项目自有的 Stage 2 执行策略，含义是：

- 从 shared `vendor/TE_model/src/TE.R` 读取源码
- 在 species root 下生成 runtime-owned patched 副本
- 最小补丁只做：
  - 移除 `library(doParallel)`
  - 移除 `makeCluster(...)`
  - 移除 `registerDoParallel(...)`
  - 移除 `stopCluster(...)`
  - 把 `%dopar%` 改为 `%do%`
- Stage 2 仍然使用 shared vendor 作为 `cwd`
- Stage 3 仍然使用 shared `src/transpose_TE.py`

以下情况应使用 `serial-fallback`：

- shared Stage 2 在当前主机上报 `serverSocket` / `PSOCK` 类错误
- 不允许修改 shared `vendor/TE_model` tracked files
- 已有 species Stage 1 产物可直接复用

当前 `Homo_sapiens` 主线闭环就是通过 `serial-fallback` 完成的。

## Exact execution command template

先进入项目环境：

```bash
source ~/miniconda3/etc/profile.d/conda.sh
conda activate te_analysis
cd /home/xrx/my_project/te_analysis
export PYTHONPATH=src
```

当前已验证的 `Homo_sapiens` canonical command：

```bash
python -m te_analysis.run_species_downstream \
  --species-root data/processed/te_species/Homo_sapiens \
  --trial homo_sapiens_species_te_prepare \
  --stage2-mode serial-fallback \
  --rscript-bin /home/xrx/miniconda3/envs/snakemake-ribo/bin/Rscript \
  --python-bin /home/xrx/miniconda3/envs/te_analysis/bin/python
```

当前 CLI 支持的关键参数：

- `--species-root`
  - species 根目录，不是 runtime trial 目录
- `--runtime-root`
  - runtime 根目录，与 `--species-root` 二选一
- `--trial` / `--trial-name`
  - 指定 trial 名称；如果自动发现到多个 trial，必须显式给出
- `--stage2-mode`
  - 仅支持 `shared` 和 `serial-fallback`
- `--vendor-root`
  - shared vendor root，默认是 `vendor/TE_model`
- `--rscript-bin`
  - Stage 2 使用的 `Rscript`
- `--python-bin`
  - Stage 3 使用的 Python
- `--skip-stage3`
  - 只跑 Stage 2，不继续跑 Stage 3

## How to inspect logs

日志统一写到：

- `<species-root>/logs/`

当前 `Homo_sapiens` 已验证示例对应：

- serial patch summary:
  - `data/processed/te_species/Homo_sapiens/logs/TE.serial.patch.20260421_211333.log`
- Stage 2:
  - `data/processed/te_species/Homo_sapiens/logs/homo_sapiens_species_te_prepare.stage2.serial-fallback.20260421_211333.log`
- Stage 3:
  - `data/processed/te_species/Homo_sapiens/logs/homo_sapiens_species_te_prepare.stage3.serial-fallback.20260421_211333.log`

最常用检查命令：

```bash
tail -50 data/processed/te_species/Homo_sapiens/logs/TE.serial.patch.20260421_211333.log
tail -50 data/processed/te_species/Homo_sapiens/logs/homo_sapiens_species_te_prepare.stage2.serial-fallback.20260421_211333.log
tail -50 data/processed/te_species/Homo_sapiens/logs/homo_sapiens_species_te_prepare.stage3.serial-fallback.20260421_211333.log
```

日志中应能明确看到：

- Stage 2 使用的 shared vendor `cwd`
- Stage 2 使用的 patched `TE.R` 路径
- Stage 3 使用的 shared `src/transpose_TE.py`

## How to confirm success

成功标准不是 exit code，而是 species trial 目录里出现非空最终文件。

当前 `Homo_sapiens` 的 trial 路径是：

- `data/processed/te_species/Homo_sapiens/runtime/vendor/TE_model/trials/homo_sapiens_species_te_prepare`

必须确认以下文件存在且非零：

- `human_TE_sample_level.rda`
- `human_TE_cellline_all.csv`
- `human_TE_cellline_all_T.csv`

推荐检查命令：

```bash
ls -lh \
  data/processed/te_species/Homo_sapiens/runtime/vendor/TE_model/trials/homo_sapiens_species_te_prepare/human_TE_sample_level.rda \
  data/processed/te_species/Homo_sapiens/runtime/vendor/TE_model/trials/homo_sapiens_species_te_prepare/human_TE_cellline_all.csv \
  data/processed/te_species/Homo_sapiens/runtime/vendor/TE_model/trials/homo_sapiens_species_te_prepare/human_TE_cellline_all_T.csv
```

## Expected outputs

最终输出写回 species trial 目录，而不是 shared vendor trial 目录。

当前 canonical output paths：

- `data/processed/te_species/Homo_sapiens/runtime/vendor/TE_model/trials/homo_sapiens_species_te_prepare/human_TE_sample_level.rda`
- `data/processed/te_species/Homo_sapiens/runtime/vendor/TE_model/trials/homo_sapiens_species_te_prepare/human_TE_cellline_all.csv`
- `data/processed/te_species/Homo_sapiens/runtime/vendor/TE_model/trials/homo_sapiens_species_te_prepare/human_TE_cellline_all_T.csv`

## Known failure signals

以下信号应被直接判为失败或未完成：

- Stage 1 输入缺失或空文件：
  - `ribo_paired_count_dummy.csv`
  - `rna_paired_count_dummy.csv`
- `shared` 模式下 Stage 2 报：
  - `serverSocket(port = port)`
  - `creation of server socket failed`
- Stage 2 返回后没有生成：
  - `human_TE_sample_level.rda`
  - `human_TE_cellline_all.csv`
- Stage 3 返回后没有生成：
  - `human_TE_cellline_all_T.csv`
- `serial patch` 日志不存在，或没有记录最小替换摘要

## Explicit do-not-do list

- 不要修改 `vendor/TE_model` tracked files
- 不要修改 `vendor/snakescale`
- 不要重跑 Stage 0/1，除非 species trial 的 Stage 1 输入不存在
- 不要把 `serial-fallback` 实现成 persistent full vendor copy
- 不要把 `human_TE_cellline_all_T.csv` 当成唯一主键严格唯一的矩阵，未审计重复标签前不要直接依赖其行名唯一性
- 不要只看 shell exit code 判断成功
