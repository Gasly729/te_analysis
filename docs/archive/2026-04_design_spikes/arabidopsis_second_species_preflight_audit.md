# Arabidopsis Second-Species Preflight Audit

## Verified facts

- `src/te_analysis/run_species_te_chain.py` 当前真实串联的是三段：
  1. `aggregate_species_te.py --prepare-only`
  2. `run_species_downstream.py`
  3. canonical CSV intake check
- `aggregate_species_te.py` 仍然是 prepare-only。
  - 证据：
    - 顶层 docstring 明确写 `This module only materializes inputs.`
    - `main()` 中有硬校验：`if not args.prepare_only: raise ValueError(...)`
- `run_species_downstream.py` 当前真实支持：
  - `--species-root` / `--runtime-root`
  - `--trial`
  - `--stage2-mode shared|serial-fallback`
- `run_species_te_chain.py` 当前把 canonical success gate **硬编码**成：
  - `CANONICAL_CSV_NAME = "human_TE_cellline_all.csv"`
- `run_species_downstream.py` 当前也把 Stage 2/3 输出名硬编码成：
  - `human_TE_sample_level.rda`
  - `human_TE_cellline_all.csv`
  - `human_TE_cellline_all_T.csv`
- 但这不会让 Arabidopsis 因命名假设立刻失败。
  - 证据：
    - `vendor/TE_model/src/TE.R` 本身就把 Stage 2 结果写成：
      - `human_TE_sample_level.rda`
      - `human_TE_cellline_all.csv`
    - `vendor/TE_model/src/transpose_TE.py` 本身就读取：
      - `human_TE_cellline_all.csv`
      - 并写出 `human_TE_cellline_all_T.csv`
- 当前 canonical analysis intake 仍然只能是：
  - `human_TE_cellline_all.csv`
- `_T` 文件不能作为默认 canonical intake。
  - 证据：
    - 现有 result contract 已明确排除
    - 当前 `Homo_sapiens` 的 `_T` 文件存在重复行名

- 当前仓库里，能确认落在 canonical `.ribo` 搜索路径上的非人类 experiment-level `.ribo`，只发现了 `Arabidopsis thaliana`。
  - 已确认 study：
    - `GSE50597`
    - `GSE109122`
  - 已确认 experiment 数：
    - `GSE50597`: 6
    - `GSE109122`: 4
  - 合计：10 个 experiment-level `.ribo`
- 当前 metadata 中还有 Arabidopsis 的：
  - `GSE132441`
  - `GSE43703`
  但在当前仓库 canonical 搜索根下没有找到对应 experiment-level `.ribo` 实物。

- `GSE50597` 当前已验证资产：
  - canonical study root:
    - `vendor/snakescale/output/GSE50597`
  - 目录存在：
    - `fastqc/`
    - `ribo/`
    - `rnaseq/`
    - `stats/`
  - experiment-level `.ribo` 数：6
  - canonical root 下 `.ribo` 总字节数：`96,729,759`
- `GSE109122` 当前已验证资产：
  - canonical study root:
    - `vendor/snakescale/output/GSE109122`
  - 目录存在：
    - `fastqc/`
    - `ribo/`
    - `rnaseq/`
    - `stats/`
  - experiment-level `.ribo` 数：4
  - canonical root 下 `.ribo` 总字节数：`59,680,343`

- 当前没有现成的 Arabidopsis species prepare/runtime tree。
  - 已验证：
    - `data/processed/te_species/` 下未发现 `Arabidopsis_thaliana` 目录
    - 也未发现对应的 runtime/vendor/TE_model/trials 物化结果
- 当前 `Homo_sapiens` 已知成功 runtime 形状包括：
  - `runtime/vendor/TE_model/data/ribo/...`
  - `runtime/vendor/TE_model/trials/<trial>/config.py`
  - Stage 1 outputs
  - 最终 Stage 2/3 outputs
- Arabidopsis 目前尚未证明拥有这一 runtime 形状。

- 最关键的下游合同证据：
  - `vendor/TE_model/src/TE.R` 会读取 `data/infor_filter.csv`
  - 然后执行：
    - `merge(infor, t(human_TE), by.x = "experiment_alias", by.y = 0)`
    - 再按 `cell_line` 聚合
- 对 Arabidopsis 当前候选 experiments 的只读匹配结果是：
  - `GSE50597`: `matched_rows = 0`
  - `GSE109122`: `matched_rows = 0`
  - `GSE132441`: `matched_rows = 0`
  - `GSE43703`: `matched_rows = 0`
- 这说明当前 shared `vendor/TE_model/data/infor_filter.csv` 对 Arabidopsis 候选 experiment_alias **零覆盖**。

## Candidate choice

`Arabidopsis_thaliana` 是当前最合适的第二物种候选，但要明确限定为：

- `GSE50597`
- `GSE109122`

理由是：

- 在当前仓库 canonical `.ribo` 搜索根下，Arabidopsis 是唯一能确认有非人类 experiment-level `.ribo` 实物的物种
- 它已经有两个 study，且两个 study 都具备和 `Homo_sapiens` 成功例子相似的 study-root 目录骨架
- `GSE132441` 和 `GSE43703` 目前只停留在 metadata 记录层，没有发现对应 `.ribo` 实物，因此不适合当下的 bounded smoke

## Asset sufficiency

对“现在是否已经有足够 confirmed `.ribo` 和 species-prepare 输入资产”这个问题，必须拆成两层回答：

- 对 `.ribo` 资产本身：
  - **足够**
  - 已确认有 10 个 experiment-level `.ribo`
  - 分布在 2 个 study：`GSE50597` 和 `GSE109122`
  - 两个 study 都有完整的 `fastqc/ribo/rnaseq/stats` 目录骨架
- 对 species prepare/runtime 完整性：
  - **不够**
  - 当前没有现成的 `data/processed/te_species/Arabidopsis_thaliana`
  - 也没有现成的 Arabidopsis runtime/vendor-style ribo mapping
  - 也没有现成的 Arabidopsis trial config / Stage 1 outputs

因此，Arabidopsis 当前是“原始 study 资产足够，但 species prepare/runtime completeness 仍未证明”的状态。

## Earliest likely blocker

当前最早、也最有证据支持的 blocker 只有一个：

- **downstream contract mismatch: shared `vendor/TE_model/data/infor_filter.csv` 对 Arabidopsis candidate experiments 零覆盖**

这不是猜测，而是当前文件直接支持的事实：

- `TE.R` 明确要求 `data/infor_filter.csv`
- 并明确以 `experiment_alias` 作为 merge key
- 对 Arabidopsis 4 个候选 studies 的实验号检查结果全部是 `matched_rows = 0`

因此：

- Arabidopsis 不会因为 `human_*` 文件名假设而立刻失败
- 也不是先卡在 `run_species_te_chain.py` 的参数层
- 如果现在直接跑整链，prepare 很可能可以走下去
- 但一旦进入 shared vendor 的 Stage 2 聚合语义，就没有已验证的 `experiment_alias -> cell_line` bridge

结论：

- 这是**已证明的当前最早下游合同 blocker**
- 不是单纯的最可能推断

## Route decision

- **B. fill minimal prepare/runtime conditions first**

## Why not the other two routes

### Why not A

不应立即执行 bounded smoke。

原因不是因为 Arabidopsis 没有 `.ribo`，而是因为当前已经有更早、更明确的 downstream 合同缺口：

- `infor_filter.csv` 对候选 Arabidopsis experiments 零覆盖

在这种前提下直接跑整链，最可能只是把已知 blocker 再执行一遍，而不是产生新的高信息增益。

### Why not C

当前没有证据表明需要先 patch `run_species_te_chain.py` 这个单物种入口。

相反，代码级事实已经说明：

- 它的 `human_TE_cellline_all.csv` 命名假设和 shared vendor 自己的输出命名是对齐的
- Arabidopsis 不会因为入口命名假设而比 `infor_filter` 更早失败

所以现在先 patch 单物种入口，不能解除当前已证明的最早 blocker。

## Minimal next action

单一步骤建议：

- **先补齐 shared `vendor/TE_model/data/infor_filter.csv` 对 Arabidopsis 候选 experiments（`GSE50597` + `GSE109122`）的最小 `experiment_alias` 覆盖条件，再考虑执行 bounded smoke。**

这是当前最小、最直接、也最贴近已证明 blocker 的下一步动作。它优先级高于真正发起 Arabidopsis 整链 smoke。
