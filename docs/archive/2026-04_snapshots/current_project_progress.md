# 当前项目进度

## 状态摘要

截至 2026-04-21，项目已经跨过了最初的 species-level execution-entrypoint gap，并且进一步完成了 `Homo_sapiens` 主线的 serial-fallback 闭环。`Homo_sapiens` 的 species prepare output 现在已经可以通过项目自有的薄桥接入口，被发现并交给 shared `vendor/TE_model` 去执行 Stage 2/3；其中 shared vendor 原生 Stage 2 仍会触发已知 PSOCK/socket 失败，但项目自有 serial Stage 2 fallback 已经在不修改 shared vendor tracked files 的前提下跑通了主线最终输出。

## 已验证事项

- 上游 / prepare 层：
  - `src/te_analysis/aggregate_species_te.py` 按设计就是 prepare-only。
  - `data/processed/te_species/Homo_sapiens/runtime/vendor/TE_model` 当前包含：
    - `data/ribo/...`
    - `trials/homo_sapiens_species_te_prepare/config.py`
    - 非空的 Stage 0/1 outputs
- species 执行桥接：
  - 新增了一个薄入口：`src/te_analysis/run_species_downstream.py`
  - 它不会修改 shared vendor 文件。
  - 它会解析 species runtime/trial 路径，校验 Stage 1 products，并直接调用 shared `vendor/TE_model` 的 Stage 2/3。
- 小规模 HeLa isolated 验证：
  - small HeLa isolated serial Stage 2/3 已经在 isolated runtime 中真实完成。
  - 这证明 Stage 2 的数学逻辑本身可以在 serial workaround 下完成。
- Homo sapiens species 主线桥接验证：
  - 新的 species bridge 已经对以下路径真实执行：
    - `data/processed/te_species/Homo_sapiens/runtime/vendor/TE_model/trials/homo_sapiens_species_te_prepare`
  - shared-vendor Stage 2 命令已被真实调用：
    - `/home/xrx/miniconda3/envs/snakemake-ribo/bin/Rscript src/TE.R <absolute species trial path>`
  - 这次尝试在产出 Stage 2 outputs 之前失败，报的是已知 PSOCK 错误：
    - `Error in serverSocket(port = port) : creation of server socket failed`
- Homo sapiens species 主线 serial-fallback 验证：
  - `run_species_downstream.py` 已支持 `--stage2-mode serial-fallback`
  - 运行时会从 shared `vendor/TE_model/src/TE.R` 生成项目自有 patched 副本，而不是修改 shared vendor
  - Stage 2 使用：
    - shared vendor 作为 `cwd`
    - runtime-generated patched `TE.R`
    - species trial 的绝对路径作为输入
  - Stage 3 继续使用 shared `vendor/TE_model/src/transpose_TE.py`
  - `Homo_sapiens` 主线最终已真实产出非空文件：
    - `human_TE_sample_level.rda`
    - `human_TE_cellline_all.csv`
    - `human_TE_cellline_all_T.csv`

## 当前主线状态

- single-study / local chain：
  - 已经存在真实可跑通的 upstream 成功路径。
  - small isolated downstream serial closure 已经在 HeLa 上证明过。
- species prepare：
  - `Homo_sapiens` 的 species prepare output 真实存在且非空。
  - Stage 1 文件已存在：
    - `ribo_raw.csv`
    - `rnaseq_raw.csv`
    - `ribo_paired_count_dummy.csv`
    - `rna_paired_count_dummy.csv`
- species execution：
  - 原来缺失的 execution-entrypoint gap 已经由项目自有代码补上。
  - shared vendor Stage 2 在当前主机上仍然无法在不做 serial workaround 的前提下完成。
  - 但项目自有 serial fallback 已经把 `Homo_sapiens` species Stage 2/3 跑通。
- species 最终输出：
  - `Homo_sapiens` 已产出：
    - `human_TE_sample_level.rda`
    - `human_TE_cellline_all.csv`
    - `human_TE_cellline_all_T.csv`
  - 这意味着“从 species prepare output 到物种级 TE 表”的主线执行闭环，已经在 `Homo_sapiens` 上完成。

## 新增代码

- `src/te_analysis/run_species_downstream.py`
  - 一个薄的 species Stage 2/3 bridge
  - 复用 shared `vendor/TE_model` 作为 code layer
  - 消费现有 species prepare output
  - 不重跑 Stage 0/1
  - 不调用 `pipeline.bash`
  - 当前已支持 `--stage2-mode shared` 和 `--stage2-mode serial-fallback`
- `tests/test_run_species_downstream.py`
  - 覆盖 runtime discovery
  - 覆盖 Stage 1 validation
  - 覆盖 shared-vendor Stage 2/3 command construction
  - 覆盖 runtime-generated serial patched `TE.R`

## 证据路径

- species runtime：
  - `data/processed/te_species/Homo_sapiens/runtime/vendor/TE_model`
- species trial：
  - `data/processed/te_species/Homo_sapiens/runtime/vendor/TE_model/trials/homo_sapiens_species_te_prepare`
- species Stage 2 bridge log：
  - `data/processed/te_species/Homo_sapiens/logs/homo_sapiens_species_te_prepare.stage2.shared.20260421_204003.log`
- species Stage 2 serial-fallback patch log：
  - `data/processed/te_species/Homo_sapiens/logs/TE.serial.patch.20260421_211333.log`
- species Stage 2 serial-fallback run log：
  - `data/processed/te_species/Homo_sapiens/logs/homo_sapiens_species_te_prepare.stage2.serial-fallback.20260421_211333.log`
- species Stage 3 serial-fallback run log：
  - `data/processed/te_species/Homo_sapiens/logs/homo_sapiens_species_te_prepare.stage3.serial-fallback.20260421_211333.log`
- species 最终输出：
  - `data/processed/te_species/Homo_sapiens/runtime/vendor/TE_model/trials/homo_sapiens_species_te_prepare/human_TE_sample_level.rda`
  - `data/processed/te_species/Homo_sapiens/runtime/vendor/TE_model/trials/homo_sapiens_species_te_prepare/human_TE_cellline_all.csv`
  - `data/processed/te_species/Homo_sapiens/runtime/vendor/TE_model/trials/homo_sapiens_species_te_prepare/human_TE_cellline_all_T.csv`
- small HeLa 成功的 isolated Stage 2/3 输出：
  - `data/processed/official_hela_smoke/runtime/TE_model_runtime/trials/HELA_zenodo_smoke_small/human_TE_sample_level.rda`
  - `data/processed/official_hela_smoke/runtime/TE_model_runtime/trials/HELA_zenodo_smoke_small/human_TE_cellline_all.csv`
  - `data/processed/official_hela_smoke/runtime/TE_model_runtime/trials/HELA_zenodo_smoke_small/human_TE_cellline_all_T.csv`

## 解释

项目已经从“species prepare 已存在但无法执行”，推进到了“species prepare 已经能通过专门桥接入口接上执行链，并且在项目自有 serial fallback 下完成主线闭环”。这说明主线的核心工程缺口不是算法本身，而是执行语义与运行环境兼容性。当前我们已经证明：

- shared vendor 原生 Stage 2 仍受宿主机 PSOCK/socket 限制
- 但只要把 Stage 2 改为项目自有的 runtime-generated serial patched `TE.R`，主线 `Homo_sapiens` 可以真实完成 Stage 2/3
- shared vendor tracked files 无需修改
- `aggregate_species_te.py` 仍可保持 prepare-only 设计

## 推荐下一步

在当前闭环已经成立的基础上，下一步应该把工作重心从“能不能跑通”转到“如何冻结主线合同与操作方式”，并保持以下约束：

- shared `vendor/TE_model` 保持不变
- 不把 full vendor clone 变成默认 pipeline
- 不重写 Stage 2 数学
- species execution 仍然只是对现有 Stage 1 outputs 的薄桥接
- 优先补 RUNBOOK 和最小可用入口说明
- 明确 `shared` 与 `serial-fallback` 两种 Stage 2 模式的适用场景

具体来说，下一步更值得聚焦两个问题：

1. 如何把当前已经验证过的 species serial-fallback 执行路径固化为明确的操作文档与失败分流规则？
2. 如何把已经产出的 species-level TE 结果接入后续科学分析层，而不再反复回到 Stage 2/3 执行问题？

## 文档指针

当前与 species downstream 闭环直接相关的正式文档如下：

- `docs/species_downstream_runbook.md`
- `docs/species_te_result_contract.md`
- `docs/homo_sapiens_species_serial_fallback_audit.md`
- `docs/species_te_chain_runbook.md`

## 受控整链入口

当前单物种受控整链入口已经补上：

- `src/te_analysis/run_species_te_chain.py`

它当前只做薄串联：

1. `aggregate_species_te.py --prepare-only`
2. `run_species_downstream.py --stage2-mode ...`
3. canonical `human_TE_cellline_all.csv` intake check

当前 canonical baseline 仍然是：

- `Homo_sapiens`
- `serial-fallback`

当前 canonical analysis intake 明确使用：

- `human_TE_cellline_all.csv`

而不是：

- `human_TE_cellline_all_T.csv`
