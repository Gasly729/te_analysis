# `te_analysis` 物种级 TE 聚合层实现规格

## 1. 已验证事实

1. 当前仓库中已有的下游 wrapper 只有 [src/te_analysis/run_downstream.py](/home/xrx/my_project/te_analysis/src/te_analysis/run_downstream.py)，它的职责是：
   - 为单个 `study` 生成 `vendor/TE_model/trials/{study}/config.py`
   - 调用 `bash pipeline.bash -t {study}`
   - 把 `human_TE_*` 产物复制到 `data/processed/te/{study}/`
   - 不包含任何 organism-level 聚合逻辑
2. `vendor/TE_model` 的固定下游阶段是：
   - Stage 0: `ribo_counts_to_csv.py`
   - Stage 1: `ribobase_counts_processing.py`
   - Stage 2: `TE.R`
   - Stage 3: `transpose_TE.py`
3. Stage 0 读取的是 experiment 级 `.ribo` 文件，路径模式为 `vendor/TE_model/data/ribo/{study}/ribo/experiments/{experiment_alias}.ribo`，而不是 `all.ribo`。
4. Stage 0 的代码会扫描 `./data/ribo/*/ribo/experiments/*.ribo`，因此底层文件发现逻辑在代码层面支持跨多个 `study` 扫描。
5. Stage 0 在给定 `custom_experiment_list` 时，会绕过 `data/paxdb_filtered_sample.csv`，直接按显式的 `experiment_alias` 列表选样。
6. Stage 1 只消费 Stage 0 生成的 `ribo_raw.csv` 与 `rnaseq_raw.csv`，本身不做 organism 分组。
7. Stage 2 会先生成 `human_TE_sample_level.rda`，然后读取 `vendor/TE_model/data/infor_filter.csv`，按 `experiment_alias -> cell_line` 合并并最终 `group_by(cell_line)`，输出 `human_TE_cellline_all.csv`。
8. `vendor/TE_model/data/infor_filter.csv` 当前只有 `experiment_alias` 与 `cell_line` 两列，没有 `organism` 列。
9. Stage 3 只是把 `human_TE_cellline_all.csv` 转置成 `human_TE_cellline_all_T.csv`，不会改变分组语义。
10. 当前 `data/processed/te/` 只有一个样例目录 [data/processed/te/GSE105082](/home/xrx/my_project/te_analysis/data/processed/te/GSE105082)，其中产物为：
    - `homo_sapiens_TE_sample_level.rda`
    - `homo_sapiens_TE_cellline_all.csv`
    - `homo_sapiens_TE_cellline_all_T.csv`
11. 当前仓库未找到任何 `te_<organism>.csv` 成品。
12. 已有审计结论 [docs/te_analysis_species_te_contract_audit.md](/home/xrx/my_project/te_analysis/docs/te_analysis_species_te_contract_audit.md) 已明确给出三选一判断：如果目标是稳定产出 `te_<organism>.csv`，不能只靠扩配置或轻扩当前 wrapper，必须新增明确的聚合层。
13. 已有主规划 [docs/te_analysis_next_phase_master_plan.md](/home/xrx/my_project/te_analysis/docs/te_analysis_next_phase_master_plan.md) 已将“物种级 TE 聚合闭环”列为下一阶段主线之一，并要求先明确合同，再决定实现入口。

## 2. 设计目标

本规格只定义“新增 organism-level 聚合层”应该怎么做，不涉及代码实现。

设计目标：

1. 在 **不修改 `vendor/TE_model`** 的前提下，稳定产出 `te_<organism>.csv`。
2. 不回退到重新实现 vendor 已经完成的 TE 计算。
3. 不把已经按 `cell_line` 折叠后的结果误当成 organism-level 结果。
4. 明确输入合同、输出合同、失败模式和工程落点，使后续实现可以最小代价接入当前仓库。
5. 保留可追溯性：最终 organism-level 结果必须能回答“用了哪些 study、哪些 experiment、哪些 cell line、哪些条目被排除”。

本规格中的内容分三类：

- `已验证事实`：已有仓库证据直接支持。
- `设计决策`：本规格推荐的实现路线。
- `待后续实现验证的问题`：当前仓库无法只靠现证据完全钉死，但实现前必须先确认。

## 3. 候选输入层比较

### 候选 A：直接以 experiment-level `.ribo` 为聚合层输入

定义：

- 聚合层直接从 `.ribo` 开始，自行重做 Stage 0、Stage 1，甚至重做 TE 计算。

优点：

- 原始输入最完整。
- 理论上可以完全控制 experiment 选择和跨 study 合并逻辑。

缺点：

- 会重复实现 vendor 已有流程，工程代价最高。
- 会重新引入 Stage 0/1 的合同与依赖，扩大实现面。
- 无法满足“新增的是聚合层，而不是重写 vendor TE 流程”的目标。

判断：

- 不推荐。

### 候选 B：以 Stage 0/1 的 count 矩阵为输入

定义：

- 聚合层读取 `ribo_raw.csv`、`rnaseq_raw.csv` 或 Stage 1 输出的 paired count / CPM / quantile 表，再独立计算 organism-level TE。

优点：

- 比 `.ribo` 更接近可计算表格。
- 避免重新读取 ribo 文件。

缺点：

- 仍然要重新定义或复刻 vendor 在 `TE.R` 中的 TE 计算语义。
- 一旦和 vendor TE 定义偏离，就会得到不可比的结果。
- 本质上仍然不是“聚合已有 TE”，而是“另起一套 TE 计算入口”。

判断：

- 不推荐作为主方案。

### 候选 C：以 `human_TE_sample_level.rda` 为输入

定义：

- 聚合层以 study 级 `*_TE_sample_level.rda` 为上游输入，再在 vendor 外部完成 organism-level 聚合。

优点：

- 这是 vendor 已完成 TE 计算后、且尚未被 `cell_line` 折叠前的最近边界。
- 保留 experiment/sample 级 TE 粒度，最适合做跨 study 的 organism-level 汇总。
- 不需要重写 Stage 0/1/2 的 TE 计算逻辑。
- 可以把 `cell_line` 从“分组轴”降为“伴随元数据”，避免信息丢失。

缺点：

- 当前仓库只证明 `.rda` 文件存在，尚未只读确认其内部对象结构与可解析性。
- 实现层需要处理 R 数据格式读取问题。

判断：

- **推荐主方案。**

### 候选 D：以 `human_TE_cellline_all.csv` 为输入

定义：

- 聚合层从 `cell_line` 级 CSV 再向上汇总到 organism-level。

优点：

- 文件最容易读。
- 当前已有一个样例产物可直接观察。

缺点：

- `cell_line` 折叠已经发生，experiment-level 差异不可逆丢失。
- 跨 study 同名 `cell_line` 可能已经被 vendor 混在一起，无法再正确回溯。
- 这会把 vendor 的 `cell_line` 语义强行升级成 `organism` 语义，方法学风险最高。

判断：

- 不推荐。

### 候选输入层结论

设计决策：

- 主方案选择 **C. `human_TE_sample_level.rda`**。

选择理由：

1. 它是离目标最近、但尚未发生 `cell_line` 聚合的信息边界。
2. 它最大限度复用 vendor 现有 TE 计算，避免语义漂移。
3. 它保留了跨 study organism-level 聚合所需的 experiment 粒度。
4. 它把新增层限定为真正的“聚合层”，而不是“第二套 TE 计算层”。

待后续实现验证的问题：

- 必须先确认 `*_TE_sample_level.rda` 的对象结构、行列朝向和 experiment 标识方式，再进入实现。

## 4. 推荐聚合层方案

设计决策：

- 在 `run_downstream.py` 之后新增一个 **独立的 organism-level 聚合入口**。
- 该入口不参与 vendor trial 生成，不改写 vendor 输入目录，不替代 study 级下游。
- 它的职责只有一件事：
  - 读取多个 study 的 `*_TE_sample_level.rda`
  - 校验 metadata 映射
  - 在 organism 维度上做显式聚合
  - 输出 `te_<organism>.csv` 与 companion metadata / QC 报告

主方案的逻辑边界：

```text
.ribo
  -> vendor Stage 0/1/2
  -> {study}/{organism}_TE_sample_level.rda
  -> species aggregation layer
  -> te_<organism>.csv
```

不采用的边界：

- 不从 `.ribo` 重新开始
- 不从 count 矩阵重算 TE
- 不从 `cellline_all.csv` 逆向猜 organism-level

## 5. 输入合同

### 5.1 主输入

设计决策：

- 聚合层的主输入是多个 study 级的 `*_TE_sample_level.rda` 文件。

最小输入路径约定：

- `data/processed/te/{study}/{organism}_TE_sample_level.rda`

最小输入集合要求：

1. 所有输入文件必须属于同一个 `organism`。
2. 每个输入文件必须能映射回唯一的 `study`。
3. 聚合层不得静默接受混入的第二物种。

### 5.2 必需 companion metadata

设计决策：

- 聚合层除主输入外，还必须读取一份 experiment 映射表。
- 该映射表的最小来源应优先来自：
  - `data/raw/metadata.csv`
  - `vendor/TE_model/data/infor_filter.csv`

最小必需字段：

- `experiment_alias`
- `study_name`
- `organism`

建议保留字段：

- `cell_line`
- `source_study_dir`
- `sample_level_te_path`

字段用途：

- `experiment_alias`：连接 sample-level TE 与元数据
- `study_name`：跨 study 聚合与 QC 统计
- `organism`：输入纯度校验
- `cell_line`：不作为最终分组轴，但作为 companion metadata 保留

### 5.3 organism-level 定义

设计决策：

- organism-level 定义为：
  - 在同一 `organism` 下，收集所有通过校验的 experiment/sample-level TE 向量
  - 以 `gene` 为对齐轴
  - 对每个 gene 在所有有效 experiment 上做一次显式聚合

聚合统计规则：

- 主值：按 gene 取 **median** 作为默认 organism-level TE
- 支撑统计：同时记录每个 gene 的
  - `n_experiments`
  - `n_studies`

为什么默认用 median：

- 这是设计决策，不是现有事实。
- 相比 mean，median 对跨 study 异质性和极端值更稳健。
- vendor 自身已经在 `cell_line` 层做过 mean；organism-level 不应再盲目沿用该策略。

### 5.4 多 study 合并规则

设计决策：

1. 合并单位是 experiment/sample-level TE，而不是 `cell_line`。
2. 同一 organism 下多个 study 的 experiment 可以共同进入聚合。
3. `cell_line` 信息保留在 companion metadata，不进入主输出分组轴。
4. 聚合层不尝试自动做条件矫正或批次校正；它只做透明的 organism-level 汇总。

### 5.5 重复与冲突处理

设计决策：

- 去重主键优先使用 `experiment_alias`。

规则：

1. 同一个 `experiment_alias` 若在多个输入文件中重复出现，默认判为冲突并失败，不静默保留其一。
2. 同 study 内重复记录，若无法证明是同一条 canonical 输入，也判为冲突。
3. 同物种不同条件样本不去重，不自动合并，只作为独立 experiment 参与 organism-level 汇总。
4. `cell_line` 差异不用于拆分主输出，但必须保留在 companion metadata。

待后续实现验证的问题：

- 若 `*_TE_sample_level.rda` 内部不存在稳定的 `experiment_alias` 维度，则需要先定义一层解析映射，再实现聚合。

## 6. 输出合同

### 6.1 输出目录

设计决策：

- 新增独立输出根目录：
  - `data/processed/te_species/{organism}/`

原因：

- 避免把 organism-level 结果继续混在 study 级目录下。
- 把“study 级 vendor 产物”和“species 级聚合产物”做物理分层。

### 6.2 主输出文件

设计决策：

- 主输出文件名：
  - `data/processed/te_species/{organism}/te_{organism}.csv`

其中 `{organism}` 采用当前项目已存在的 slug 约定：

- 小写
- 空格替换为下划线

### 6.3 主输出文件语义

设计决策：

- 文件按 `gene` 为行。
- 最小必备列为：
  - `te`
  - `n_experiments`
  - `n_studies`

推荐索引：

- 行索引为 `gene`

列语义：

- `te`：该 gene 在当前 organism 下的 organism-level 聚合 TE 主值
- `n_experiments`：贡献该 gene 聚合值的有效 experiment 数
- `n_studies`：贡献该 gene 聚合值的 study 数

为什么不把主输出设计成单列矩阵：

- 仅保留一个数值列会丢掉最关键的支持度信息。
- organism-level 汇总天然需要 companion support count，避免把稀疏与稳定信号混为一谈。

### 6.4 companion metadata / QC 输出

设计决策：

- 主输出之外，必须同时落盘两类 companion 文件。

1. `te_{organism}.samples.tsv`

路径：

- `data/processed/te_species/{organism}/te_{organism}.samples.tsv`

最小字段：

- `experiment_alias`
- `study_name`
- `organism`
- `cell_line`
- `sample_level_te_path`
- `include_status`
- `exclude_reason`

作用：

- 明确哪些 experiment 被纳入
- 明确哪些 experiment 被排除以及原因

2. `te_{organism}.qc.tsv`

路径：

- `data/processed/te_species/{organism}/te_{organism}.qc.tsv`

最小字段：

- `metric`
- `value`

最小指标建议：

- `organism`
- `n_input_files`
- `n_input_experiments`
- `n_included_experiments`
- `n_excluded_experiments`
- `n_studies`
- `n_genes_output`
- `aggregation_stat`

原因：

- organism-level 聚合不是单纯转文件，必须有一份可机器读取的 QC 摘要。

## 7. 工程落点

设计决策：

- 不扩 `run_downstream.py` 为主入口。
- 新增独立入口文件：
  - `src/te_analysis/aggregate_species_te.py`

### 为什么不直接扩 `run_downstream.py`

1. `run_downstream.py` 当前是单 study thin wrapper，职责已经明确。
2. organism-level 聚合是多 study、强校验、强 metadata 的后处理任务，工程语义与 study 级 vendor wrapper 不同。
3. 如果把它塞进 `run_downstream.py`，会让一个文件同时承担：
   - vendor trial 生成
   - study 级执行
   - study 级拷贝
   - species 级聚合
   这会直接破坏当前最小职责边界。
4. 未来很可能需要独立运行“重聚合”而不重跑 vendor，下游应支持单独执行。

### 推荐入口职责

`aggregate_species_te.py` 只负责：

1. 收集目标 organism 的多个 `*_TE_sample_level.rda`
2. 读取并校验 companion metadata
3. 执行 organism-level 聚合
4. 输出 `te_{organism}.csv` 与 companion 文件
5. 对失败条件给出 machine-readable 报错

### 与现有入口的关系

- `run_downstream.py` 负责产出 study 级 TE 中间产物
- `aggregate_species_te.py` 负责把多个 study 级中间产物汇总成 organism-level 成品

这是串联关系，不是替代关系。

## 8. 失败模式与验收标准

### 8.1 失败模式

必须显式处理以下失败：

1. 输入 `.ribo` 缺失
   - 含义：上游 study 尚未形成可用下游输入，导致对应 `*_TE_sample_level.rda` 不存在
   - 聚合层行为：不尝试补跑；只把该 study 记为缺失输入

2. sample-level TE 缺失
   - 含义：`data/processed/te/{study}/{organism}_TE_sample_level.rda` 不存在
   - 聚合层行为：若目标输入集合为空则直接失败；若仅部分 study 缺失则记录并按实现策略决定是否允许部分聚合

3. metadata 映射不全
   - 含义：存在 sample-level experiment 无法映射到 `organism` 或 `study_name`
   - 聚合层行为：默认失败，不允许静默跳过

4. 同名样本冲突
   - 含义：同一个 `experiment_alias` 在输入集中重复出现且来源不唯一
   - 聚合层行为：失败

5. 输出为空
   - 含义：聚合后没有任何 gene 行
   - 聚合层行为：失败

6. 非法 organism 混入
   - 含义：输入集合中出现第二个 organism，或文件名 organism 与 metadata organism 不一致
   - 聚合层行为：失败

7. sample-level TE 不可解析
   - 含义：`.rda` 文件存在但无法解析出稳定的 gene × experiment 结构
   - 聚合层行为：失败，并回到“先确认 `.rda` 合同”的实现前置审计

### 8.2 验收标准

实现完成后至少应满足：

1. 给定同一 organism 的多个 study 级 `*_TE_sample_level.rda`，能稳定生成一个 `te_{organism}.csv`
2. 主输出非空
3. 主输出至少包含 `te`、`n_experiments`、`n_studies`
4. companion `samples.tsv` 能列出所有纳入与排除的 experiment
5. companion `qc.tsv` 能给出最小 QC 摘要
6. 输入混物种、样本冲突、元数据缺失时会显式失败，而不是静默降级

## 9. 不推荐方案

1. 不推荐直接改 `vendor/TE_model`
   - 这违反本轮设计边界，也会让本仓行为继续依赖 vendor 私有约定。

2. 不推荐把 `human_TE_cellline_all.csv` 再聚合成 organism-level
   - 这一步已经丢失了 experiment 粒度，无法保证跨 study 聚合正确。

3. 不推荐以 Stage 0/1 count 矩阵为主输入
   - 这会把聚合层变成另一套 TE 计算层。

4. 不推荐把 organism-level 聚合塞进 `run_downstream.py`
   - 这会混淆 study 级 vendor wrapper 和 species 级后处理职责。

5. 不推荐静默容忍 metadata 缺失或 mixed-organism 输入
   - 物种级输出若无严格输入校验，最终会直接污染科学分析层。

## 10. 最终建议

主方案只推荐一个：

- **新增独立入口 `src/te_analysis/aggregate_species_te.py`**
- **主输入选择 `data/processed/te/{study}/{organism}_TE_sample_level.rda`**
- **输出到 `data/processed/te_species/{organism}/te_{organism}.csv`**

推荐理由可以压缩成一句话：

- `.rda` 是当前离 organism-level 最近、且尚未被 `cell_line` 折叠的信息边界；因此最稳妥的新增层，不是重做 vendor，也不是复用 `cellline_all.csv`，而是在 sample-level TE 之后新增一个独立、可校验、可追溯的 organism-level 聚合入口。

待后续实现前必须先做的唯一高优先级核验是：

- 只读确认 `*_TE_sample_level.rda` 的对象结构、experiment 维度和基因轴是否稳定可解析。
