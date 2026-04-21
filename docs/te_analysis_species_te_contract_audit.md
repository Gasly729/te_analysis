# `run_downstream.py` 与 `vendor/TE_model` 物种级 TE 合同审计

## 审计范围

- 项目根目录：`/home/xrx/my_project/te_analysis`
- 只读检查：
  - [src/te_analysis/run_downstream.py](/home/xrx/my_project/te_analysis/src/te_analysis/run_downstream.py)
  - `src/te_analysis/` 下所有与 downstream / trial / te / aggregate / wrapper / materialize 相关文件
  - [vendor/TE_model/pipeline.bash](/home/xrx/my_project/te_analysis/vendor/TE_model/pipeline.bash)
  - [vendor/TE_model/src/ribo_counts_to_csv.py](/home/xrx/my_project/te_analysis/vendor/TE_model/src/ribo_counts_to_csv.py)
  - [vendor/TE_model/src/ribobase_counts_processing.py](/home/xrx/my_project/te_analysis/vendor/TE_model/src/ribobase_counts_processing.py)
  - [vendor/TE_model/src/TE.R](/home/xrx/my_project/te_analysis/vendor/TE_model/src/TE.R)
  - [vendor/TE_model/src/transpose_TE.py](/home/xrx/my_project/te_analysis/vendor/TE_model/src/transpose_TE.py)
  - [vendor/TE_model/trials](/home/xrx/my_project/te_analysis/vendor/TE_model/trials)
  - [vendor/TE_model/data/infor_filter.csv](/home/xrx/my_project/te_analysis/vendor/TE_model/data/infor_filter.csv)
  - [vendor/TE_model/data/paxdb_filtered_sample.csv](/home/xrx/my_project/te_analysis/vendor/TE_model/data/paxdb_filtered_sample.csv)
  - [data/processed/te](/home/xrx/my_project/te_analysis/data/processed/te)
  - [vendor/TE_model/data/ribo](/home/xrx/my_project/te_analysis/vendor/TE_model/data/ribo)
  - [logs/t9_run_downstream.log](/home/xrx/my_project/te_analysis/logs/t9_run_downstream.log)

## 1. 已验证事实

1. `src/te_analysis/` 下未找到除 `run_downstream.py` 之外的 downstream / aggregate / wrapper / materialize 入口文件；当前相关文件只有 `run_downstream.py`、`config.py`、`run_upstream.py`、`stage_inputs.py`。
2. `run_downstream.py` 的 CLI 只接受一个 `--study-dir`，并用该目录名作为 `study`，随后只从 `metadata.csv` 中筛出 `study_name == study.split("_", 1)[0]` 的记录来构造 experiment 列表。[run_downstream.py:31-41](/home/xrx/my_project/te_analysis/src/te_analysis/run_downstream.py:31)
3. `run_downstream.py` 会把 trial 目录写成 `vendor/TE_model/trials/{study}`，并生成 `config.py`，其中唯一可变核心参数是 `custom_experiment_list=[...]`。[run_downstream.py:44-54](/home/xrx/my_project/te_analysis/src/te_analysis/run_downstream.py:44)
4. `run_downstream.py` 固定执行 `bash pipeline.bash -t {study}`，没有提供多 study trial 名、聚合模式或 grouping 轴参数。[run_downstream.py:80-88](/home/xrx/my_project/te_analysis/src/te_analysis/run_downstream.py:80)
5. `run_downstream.py` 最终只会复制 3 个文件：`human_TE_cellline_all.csv`、`human_TE_cellline_all_T.csv`、`human_TE_sample_level.rda`，并仅做 `human_ -> {organism}_` 的文件名前缀替换，不改变文件内容语义。[run_downstream.py:27-28](/home/xrx/my_project/te_analysis/src/te_analysis/run_downstream.py:27) [run_downstream.py:57-66](/home/xrx/my_project/te_analysis/src/te_analysis/run_downstream.py:57)
6. `pipeline.bash` 的真实阶段顺序是：
   - Stage 0：`python -m trials.$pipeline_dir.config`
   - Stage 1：`python src/ribobase_counts_processing.py`
   - Stage 2：`Rscript src/TE.R`
   - Stage 3：`python src/transpose_TE.py`
   [pipeline.bash:23-42](/home/xrx/my_project/te_analysis/vendor/TE_model/pipeline.bash:23)
7. Stage 0 的 `main()` 在提供 `custom_experiment_list` 时，不会读取 `data/paxdb_filtered_sample.csv` 选样，而是直接采用该 experiment 列表。[ribo_counts_to_csv.py:76-82](/home/xrx/my_project/te_analysis/vendor/TE_model/src/ribo_counts_to_csv.py:76)
8. Stage 0 扫描输入文件的硬编码路径是 `./data/ribo/*/ribo/experiments/*.ribo`，并按路径中的第 4 层目录名识别 `study`，按文件名识别 `experiment_alias`。[ribo_counts_to_csv.py:84-94](/home/xrx/my_project/te_analysis/vendor/TE_model/src/ribo_counts_to_csv.py:84)
9. Stage 0 读取单个样本时，直接打开 `./data/ribo/{study}/ribo/experiments/{experiment}.ribo`；代码没有读取 `all.ribo` 的语句，因此最小必需输入是 experiment 级 `.ribo` 文件，不是 `all.ribo`。[ribo_counts_to_csv.py:19-22](/home/xrx/my_project/te_analysis/vendor/TE_model/src/ribo_counts_to_csv.py:19) [ribo_counts_to_csv.py:51-55](/home/xrx/my_project/te_analysis/vendor/TE_model/src/ribo_counts_to_csv.py:51)
10. Stage 0 从同一个 experiment `.ribo` 文件里同时提取 ribo counts 和 RNA-seq counts；RNA 不是从单独的外部 RNA count 文件读入的。[ribo_counts_to_csv.py:19-22](/home/xrx/my_project/te_analysis/vendor/TE_model/src/ribo_counts_to_csv.py:19) [ribo_counts_to_csv.py:51-58](/home/xrx/my_project/te_analysis/vendor/TE_model/src/ribo_counts_to_csv.py:51)
11. Stage 0 在收集 experiment 时是“按现有文件求交集”而不是“按配置强校验”；如果 `custom_experiment_list` 中某些 experiment 没有对应 `.ribo` 文件，它们不会触发显式报错，只会因未匹配到 glob 结果而不进入 `study_experiments`。[ribo_counts_to_csv.py:84-99](/home/xrx/my_project/te_analysis/vendor/TE_model/src/ribo_counts_to_csv.py:84)
12. `logs/t9_run_downstream.log` 显示 `run_downstream` 对 `GSE105082` 记录了 `N=24`，但 Stage 0 实际只打印了 13 个 `Processed GSM...`，这与“只处理当前目录下确实存在的 experiment `.ribo`”一致。[logs/t9_run_downstream.log](/home/xrx/my_project/te_analysis/logs/t9_run_downstream.log)
13. `vendor/TE_model/README.md` 明确说明默认流程是修改 `data/paxdb_filtered_sample.csv` 指定样本，但 `main(..., custom_experiment_list=...)` 也被支持，语义是覆盖默认样本选择来源。[README.md:28-46](/home/xrx/my_project/te_analysis/vendor/TE_model/README.md:28)
14. Stage 1 只消费 Stage 0 生成的 `ribo_raw.csv` 与 `rnaseq_raw.csv`，输出 paired count / CPM / quantile 表；这里没有 organism 分组逻辑。[ribobase_counts_processing.py:105-135](/home/xrx/my_project/te_analysis/vendor/TE_model/src/ribobase_counts_processing.py:105)
15. Stage 2 先计算 `human_TE_sample_level.rda`，随后读取固定路径 `data/infor_filter.csv`，用 `experiment_alias` 合并 sample-level TE，再 `group_by(cell_line)` 求均值，输出 `human_TE_cellline_all.csv`。[TE.R:56-67](/home/xrx/my_project/te_analysis/vendor/TE_model/src/TE.R:56)
16. Stage 2 中没有 `organism` 列参与聚合，也没有任何按 study、sample 或 organism 切换 grouping 轴的参数入口；唯一显式分组轴是 `cell_line`。[TE.R:59-67](/home/xrx/my_project/te_analysis/vendor/TE_model/src/TE.R:59)
17. `vendor/TE_model/data/infor_filter.csv` 当前列只有 `experiment_alias` 与 `cell_line`，没有 `organism` 列。[vendor/TE_model/data/infor_filter.csv](/home/xrx/my_project/te_analysis/vendor/TE_model/data/infor_filter.csv)
18. Stage 3 只是把 `human_TE_cellline_all.csv` 转置成 `human_TE_cellline_all_T.csv`，不会改变分组语义。[transpose_TE.py:9-12](/home/xrx/my_project/te_analysis/vendor/TE_model/src/transpose_TE.py:9)
19. `data/processed/te/` 当前只有 `GSE105082` 的 3 个产物：
   - `homo_sapiens_TE_cellline_all.csv`
   - `homo_sapiens_TE_cellline_all_T.csv`
   - `homo_sapiens_TE_sample_level.rda`
   目录中未找到任何 `te_<organism>.csv`。
20. 现有样例 `homo_sapiens_TE_cellline_all.csv` 的索引是 `HeLa`，不是 organism；对应转置文件的列名也是 `HeLa`，再次证明现有成品语义是 `cell_line` 级，不是物种级。
21. `vendor/TE_model/trials/` 当前只有 `GSE105082` 与 `PAX_hela` 两类样例 trial，没有现成的跨 study 同物种聚合 trial，也没有物种级命名样例。
22. `vendor/TE_model/data/ribo/GSE105082` 是一个已存在的输入根目录，其下满足 `ribo/experiments/*.ribo` 目录层级；这与 Stage 0 的 glob 规则一致。

## 2. 当前推断

1. Stage 0 从代码能力上天然支持“一次消费多个 study 的 `.ribo`”，前提是这些 `.ribo` 都被放在 `vendor/TE_model/data/ribo/{study}/ribo/experiments/` 下，且 `custom_experiment_list` 中的 experiment 名能在这些目录里被扫到。
2. `custom_experiment_list` 的真实作用不是“给 Stage 0 传 study”，而是“把 vendor 默认的 `paxdb_filtered_sample.csv` 选样入口替换成显式 experiment_alias 列表”。
3. 只要 `custom_experiment_list` 塞入跨 study、同物种的 experiment_alias，Stage 0 和 Stage 1 理论上都能跑出合并后的 raw / normalized 矩阵；代码层面这两步并不强制单 study。
4. 真正阻断物种级输出的主缺口不在 Stage 0 或 Stage 1，而在 Stage 2：vendor 当前把 sample-level TE 硬编码聚合到 `cell_line`，并且依赖 `data/infor_filter.csv` 提供 `experiment_alias -> cell_line` 映射。
5. 即便把多个 study 的同物种样本一起送进 vendor，现有逻辑也只会得到“多个 cell line / tissue 行”的 `human_TE_cellline_all.csv`，不会自然收敛成单个 organism 行。
6. 仅扩 trial/config 不足以得到真正的物种级 `te_<organism>.csv`，因为 config 只能决定 experiment 选择与 flatten 参数，不能改变 `TE.R` 的分组轴。
7. 如果未来坚持“零改 vendor/TE_model”，那物种级输出最稳妥的落点将是 vendor 之后新增一层显式聚合逻辑，而不是依赖 wrapper 临时篡改 `infor_filter.csv` 的 `cell_line` 含义。
8. 当前 `run_downstream.py` 更准确的定位是“被设计成单 study wrapper”，而不是“代码天然只允许单 study”。Stage 0 vendor 能跨 study，但这个 wrapper 的 CLI、trial 命名和 metadata 读取方式都把使用姿势锁死在单 study。

## 3. 待确认问题

1. 若未来要做真正的物种级 `te_<organism>.csv`，聚合输入应以 `human_TE_sample_level.rda` 为准，还是以 Stage 1 的 count / normalized 矩阵为准，仓库内没有现成规范。
2. `human_TE_sample_level.rda` 的对象结构、列名稳定性、是否便于外部安全读取，当前仓库未提供解析示例。
3. 跨 study 聚合时，`data/infor_filter.csv` 是否覆盖所有目标 experiment_alias，仓库内未见系统性校验逻辑。
4. 若多个 study 的同名 `cell_line` 实际实验条件不同，vendor 现有 `group_by(cell_line)` 会直接平均；这个语义是否科学可接受，仓库内没有说明。
5. 对非 human 物种，`ribobase_counts_processing.py` 中 `data/nonpolyA_gene.csv` 的适用性是否成立，仓库内无明确界定。
6. 若要在不改 vendor 代码的前提下复用 `TE.R` 做 organism 聚合，是否允许通过准备一份临时映射文件把 `cell_line` 列人为改写成 organism，当前仓库没有正式合同支持这种做法。
7. 若要做多 study trial，trial 命名、输出目录命名、输入 manifest 命名是否需要脱离 `study` 语义，当前 `run_downstream.py` 没有这类约定。

## 4. 物种级 TE 最小输入契约

### 4.1 最小必需输入文件

- 必需：每个 experiment 的 `.ribo` 文件。
  - 路径模式：`vendor/TE_model/data/ribo/{study}/ribo/experiments/{experiment_alias}.ribo`
- 非 Stage 0 最小必需：`all.ribo`
  - 当前代码没有读取 `all.ribo`，它不是 vendor Stage 0 的直接输入要求。
- Stage 2 必需：`data/infor_filter.csv`
  - 至少需要 `experiment_alias` 与 `cell_line` 两列。
- trial 必需：`vendor/TE_model/trials/{trial_name}/config.py`
  - 必须调用 `src.ribo_counts_to_csv.main(...)`。

### 4.2 最小必需目录结构

```text
vendor/TE_model/
├── data/
│   ├── ribo/
│   │   └── {study}/
│   │       └── ribo/
│   │           └── experiments/
│   │               ├── {experiment_1}.ribo
│   │               └── {experiment_2}.ribo
│   └── infor_filter.csv
└── trials/
    └── {trial_name}/
        └── config.py
```

### 4.3 `custom_experiment_list` 的真实合同

- 它是 Stage 0 的显式 experiment 选择器。
- 提供它时，vendor 不再依赖 `data/paxdb_filtered_sample.csv` 作为选样入口。
- 它只决定“想处理哪些 experiment_alias”，不保证这些 experiment 一定存在。
- 真正会被处理的 experiment，仍取决于它们是否能在 `data/ribo/*/ribo/experiments/*.ribo` 中被 glob 到。

### 4.4 trial/config 的真实要求

- 最小形式是：
  - `workdir`
  - `sample_filter`
  - `ribo_dedup`
  - `rna_seq_dedup`
  - 可选 `custom_experiment_list`
- 其中真正决定样本集合的是：
  - 默认路径：`data/paxdb_filtered_sample.csv`
  - 或显式覆盖：`custom_experiment_list`
- trial/config 本身没有 organism 聚合参数，也没有 grouping 轴参数。

### 4.5 分组轴合同

- Stage 0：按 experiment 读取 `.ribo`，输出 experiment 级 raw counts 矩阵。
- Stage 1：仍是 experiment 级 count / CPM / quantile 处理。
- Stage 2：
  - 先得到 sample-level TE：`human_TE_sample_level.rda`
  - 再通过 `data/infor_filter.csv` 里的 `experiment_alias -> cell_line` 映射，聚合成 `cell_line` 级矩阵。
- Stage 3：只转置 `cell_line` 级矩阵。

结论：vendor 当前的最终显式分组轴是 `cell_line`，不是 `organism`。

### 4.6 最终输出文件语义

- `human_TE_sample_level.rda`
  - sample / experiment 级 TE 中间产物。
- `human_TE_cellline_all.csv`
  - `cell_line × gene` 的 TE 矩阵。
- `human_TE_cellline_all_T.csv`
  - `gene × cell_line` 的 TE 矩阵。
- `run_downstream.py` 复制到 `data/processed/te/{study}/` 时，只重命名文件前缀为 `{organism}_`，不把 `cell_line` 级结果变成 organism 级结果。

## 5. 核心问题逐项回答

### A. 输入合同

1. Stage 0 最小输入到底是什么？
   - 是 experiment 级 `.ribo` 文件，路径必须满足 `data/ribo/{study}/ribo/experiments/{experiment}.ribo`。

2. 是否可以一次消费多个 study 的 `.ribo`？
   - 从 Stage 0 代码能力看，可以。
   - 原因是它扫描 `data/ribo/*/ribo/experiments/*.ribo`，再按 experiment_alias 反推所属 study。

3. `custom_experiment_list` 的真实作用是什么？
   - 它是显式 experiment 选择器，用来绕过 `paxdb_filtered_sample.csv`。
   - 它不提供 grouping 语义，也不提供 organism 语义。

4. `.ribo` 必须放在哪个目录层级才能被 vendor 正常扫到？
   - `vendor/TE_model/data/ribo/{study}/ribo/experiments/{experiment_alias}.ribo`

### B. 分组合同

5. vendor 最终是按什么分组输出的？
   - 已验证是 `cell_line`。

6. `data/infor_filter.csv` 在最终分组中扮演什么角色？
   - 它提供 `experiment_alias -> cell_line` 映射。
   - `TE.R` 用它把 sample-level TE 合并后再按 `cell_line` 均值聚合。

7. 如果输入是跨 study 同物种样本，vendor 现有逻辑会自然得到物种级输出吗？
   - 不会。
   - 它只会把这些样本继续按 `cell_line` 聚合，除非所有样本恰好共享同一个 `cell_line` 标签。

### C. 聚合能力判断

8. 当前 `run_downstream.py` 是“只能单 study”，还是“目前只按单 study 使用过”？
   - 两者都成立，但重点不同。
   - 从 wrapper 合同看，它被实现成单 study 入口。
   - 从 vendor Stage 0 能力看，底层 flatten 逻辑并不天然限制单 study。

9. 如果想得到 `te_<organism>.csv`，最可能缺的是哪一层？
   - 不是单纯配置层。
   - 也不只是当前这种薄 wrapper 轻微扩展就能稳妥解决。
   - 主缺口在“显式聚合层”。

10. 三选一结论
   - **C. 必须新增聚合层。**

## 6. 结论

### 6.1 现有逻辑能否直接支持物种级 TE 聚合

不能直接支持。

原因不是 Stage 0 不能吃多 `.ribo`，而是 vendor 的最终聚合语义硬编码在 `TE.R`，并且该语义是 `cell_line`，不是 `organism`。

### 6.2 缺口最可能落在哪一层

- 配置层不是主缺口。
  - config 只能选 experiment 和设置 flatten 参数，不能改最终 grouping 轴。
- wrapper 层有次级缺口。
  - 当前 wrapper 只面向单 study，也没有 multi-study trial 或 manifest 合同。
- 但真正决定是否能得到 `te_<organism>.csv` 的主缺口，是 vendor 之后缺少一个明确的 organism-level 聚合层。

### 6.3 推荐下一步

推荐结论：**C. 必须新增聚合层。**

更具体地说：

1. 可以复用现有 vendor 逻辑做 Stage 0 到 sample-level TE 计算。
2. 不能把 `human_TE_cellline_all.csv` 直接当作物种级结果。
3. 应先明确 organism-level 聚合规则，再新增一层显式聚合实现，输入优先考虑 sample-level TE 与受控的 experiment-to-organism 映射，而不是继续把 vendor 的 `cell_line` 输出硬掰成 organism 输出。

## 7. 审计结论一句话版本

- Stage 0 天然支持多 `.ribo`，但 vendor 最终分组轴不是 organism，而是 `cell_line`；因此若目标是稳定产出 `te_<organism>.csv`，三选一结论是 **C. 必须新增聚合层**。
