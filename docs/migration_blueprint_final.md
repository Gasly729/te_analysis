# Final Migration Blueprint for the TE-only Pipeline

本蓝图以以下两份审计报告为主证据，不再把当前任务扩展为新一轮全仓库普查：

- 新仓库审计：`/home/xrx/my_project/te_analysis/docs/repo_census_and_migration_audit.md`
- 老仓库审计：`/home/xrx/my_project/te_analysis/docs/legacy_repo_forensic_audit.md`

目标是在当前统一服务器上，重建一个可维护、可验证、TE-only 的新管线；保留科学核心，冻结历史参考区，拒绝把旧仓库的结构债和运行残留重新复制进来。

## 1. Executive Decision Summary

最终决策如下：

- 新仓库 `te_analysis` 继续作为唯一主动开发仓库；`raw_motheds/` 整体视为冻结参考区，不是未来活跃架构。
- 未来主架构应分成六个活动层：`contracts`、`upstream`、`extract`、`preprocess`、`compute`、`package/qc`，并由一个显式 CLI 和显式 manifest 驱动。
- `TE.R` 继续作为数学金标准，不能在迁移初期重写；只允许包裹其输入输出和工作目录适配层。
- 老仓库中真正值得迁移的是职责，不是目录；尤其是 `.ribo` 提取、样本配对校验、CPM/dummy gene/non-polyA 处理和 TE.R 调用链。
- `workflow/snakescale/Snakefile`、`pipeline.bash`、`run_round2_nonstandard_gse.py` 这类 god workflow / god script 不能原样迁入；只能拆解其职责后重建薄壳。
- winsorization 必须恢复为新架构中的显式生产层。证据表明它不在老仓库当前活跃生产路径里，但参考区 `TE_model` 明确保留了 winsorization 相关实现模式。
- 老式 `project.yaml` + 多层 `modification.yaml` + `_modified.yaml` 的配置体系必须被一个“单一权威 study manifest + 机器物化 resolved manifest”的设计替代。
- 当前模板/占位文件应视为待归档对象，而不是未来实现基础：`te_analysis/dataset.py`、`te_analysis/code_scffold.py`、`te_analysis/modeling/train.py`、`te_analysis/modeling/predict.py`、`te_analysis/plots.py`、`notebooks/notebook_scaffold.ipynb`。

## 2. Non-Negotiable Design Principles

以下原则是新架构的硬约束：

1. 新仓库只服务 TE-only 目标，不再扩展为“泛分析脚手架”或“混合历史工作目录”。
2. `raw_motheds/` 是冻结参考区，只读使用，只能提炼算法与契约，不能把其目录结构当成未来正式结构。
3. `TE.R` 是数学金标准；迁移初期禁止改动其 CLR/ILR 数学定义，只允许增加输入包装、命名修复和工作目录隔离。
4. winsorization 是生产必需层，不允许继续作为“隐含 trial 回调”存在；生产运行若缺少 winsorization policy，必须直接失败。
5. 任何模块都不得依赖当前工作目录；所有路径必须经 manifest 或配置对象显式注入。
6. 任何模块都不得在 import 时写文件、跑命令、生成 YAML、修改状态或读取大数据。
7. 业务语义不得继续编码在文件后缀里；`_dedup`、`_test`、`_modified`、`_all` 之类语义必须转成 manifest 字段。
8. 运行结果、缓存、日志、workdir、`.snakemake`、`.nextflow`、中间 `.ribo`、临时 symlink 目录都不得污染源码区。
9. 每个阶段都必须有显式输入契约、输出契约和最小验证规则，不能再靠“文件名正好存在”驱动。
10. 旧代码只能按“保留算法 / 包裹黑盒 / 拆分重构 / 归档丢弃”四类处理，不允许整目录平移。
11. 服务器路径可以出现在清晰的 manifest 中，但不能硬编码在 Python/R/Shell/Groovy 代码里。
12. 迁移顺序必须优先保护科学一致性，再处理上游编排便利性；先守住 TE 数学和计数链，再谈自动化。

## 3. Final Target Repository Architecture

### 3.1 Final Architecture on This Server

建议的最终仓库结构如下：

```text
te_analysis/
├── docs/
│   ├── repo_census_and_migration_audit.md
│   ├── legacy_repo_forensic_audit.md
│   └── migration_blueprint_final.md
├── config/
│   ├── schemas/
│   │   ├── metadata.schema.yaml
│   │   ├── pairing.schema.yaml
│   │   ├── study_manifest.schema.yaml
│   │   ├── te_run.schema.yaml
│   │   └── output_manifest.schema.yaml
│   ├── pipeline.defaults.yaml
│   ├── references.catalog.yaml
│   └── studies/
│       └── <study>.yaml
├── data/
│   ├── external/
│   ├── raw/
│   ├── interim/
│   └── processed/
├── references/
│   └── manifests/
├── tests/
├── te_analysis/
│   ├── cli.py
│   ├── config.py
│   ├── contracts/
│   ├── upstream/
│   ├── extract/
│   ├── preprocess/
│   ├── compute/
│   ├── qc/
│   └── package/
└── raw_motheds/
    ├── snakescale/
    ├── riboflow/
    └── TE_model/
```

### 3.2 Active Development Zones

主动开发区应仅包括：

- `te_analysis/`
- `config/`
- `tests/`
- `docs/`

其中：

- `data/` 是运行数据区，不是源码开发区。
- `references/` 只存轻量契约说明、参考 manifest 或固定说明，不存未来核心算法实现。

### 3.3 Frozen Reference-Only Zones

以下区域应冻结为 reference-only：

- `raw_motheds/snakescale/`
- `raw_motheds/riboflow/`
- `raw_motheds/TE_model/`
- `raw_motheds/` 下的嵌套 `.git/`、`.snakemake/`、trial 输出、历史 CSV/RDA、参考下载目录

冻结含义：

- 可读、可摘取方法、可对照审计。
- 不作为新代码写入位置。
- 不作为未来运行时工作目录。
- 不再接受“顺手修一版参考脚本”的做法。

### 3.4 Placeholder / Template File Decisions

以下文件应视为占位或误导性模板，后续应归档或被真实模块替换：

- `te_analysis/dataset.py`：归档/替换
- `te_analysis/code_scffold.py`：归档/替换
- `te_analysis/modeling/train.py`：归档
- `te_analysis/modeling/predict.py`：归档
- `te_analysis/plots.py`：归档
- `notebooks/notebook_scaffold.ipynb`：归档或完全重写

建议把它们统一移动到后续的 `archive/template_scaffolds/`，而不是继续留在主包中冒充正式入口。

### 3.5 Modules That Must Exist Before Serious Migration

在开始真正迁移前，至少必须先建立这些空壳模块与边界：

- `te_analysis/cli.py`
- `te_analysis/contracts/metadata.py`
- `te_analysis/contracts/pairing.py`
- `te_analysis/contracts/study_manifest.py`
- `te_analysis/upstream/manifest_materializer.py`
- `te_analysis/upstream/riboflow_runner.py`
- `te_analysis/extract/ribo_counts.py`
- `te_analysis/preprocess/winsorize.py`
- `te_analysis/preprocess/filtering.py`
- `te_analysis/compute/te_runner.py`
- `te_analysis/qc/reporting.py`
- `te_analysis/package/results.py`
- `tests/golden/`

如果这些边界层不存在，迁移会再次滑回“先堆脚本，后补边界”的历史模式。

## 4. Legacy-to-New Responsibility Mapping

| 旧职责 | 主要旧来源 | 新落点 | 处理决策 | 说明 |
|---|---|---|---|---|
| metadata 解析与 accession 映射 | `project/src/data/download_sra.py`；`raw_motheds/snakescale/scripts/generate_yaml.py` | `te_analysis/contracts/metadata.py` | 拆分重构 | 保留 accession 与字段语义；重写下载执行壳层 |
| Ribo/RNA pairing 定义 | `generate_yaml.py`；`project/src/te_calc/te_calculator.py::build_sample_pairing` | `te_analysis/contracts/pairing.py` | 保留算法并重构接口 | pairing 语义必须成为显式契约 |
| study 级运行配置物化 | `generate_yaml.py`；`project.yaml`；`modification.yaml`；`*_modified.yaml` | `te_analysis/upstream/manifest_materializer.py` | 从头创建 | 保留“物化 resolved manifest”概念，废弃多层 YAML 漫灌 |
| 上游 `.ribo` 生产黑盒 | `raw_motheds/riboflow/RiboFlow.groovy`；`nextflow.config` | `te_analysis/upstream/riboflow_runner.py` | 只包裹，不重写 | `.ribo` 生产仍视为外部稳定内核 |
| adapter/length/可运行性预检 | `raw_motheds/snakescale/Snakefile`；`guess_adapters.py` | `te_analysis/upstream/preflight.py` | 选择性拆出 | 只保留仍然对当前服务器必要的检查 |
| `.ribo` → 原始 count 提取 | `raw_motheds/TE_model/src/ribo_counts_to_csv.py`；`project/src/te_calc/te_calculator.py::stage0_extract` | `te_analysis/extract/ribo_counts.py` | 保留算法并拆分 | 提取逻辑与 IO、并发、物种拆分分离 |
| winsorization/capping | `raw_motheds/TE_model/src/utils.py`；`trials/PAX_hela/config.py`；`README.md` | `te_analysis/preprocess/winsorize.py` | 保留方法并正式化 | 从 trial 回调升级为正式生产层 |
| CPM/dummy gene/non-polyA 过滤 | `project/src/te_calc/te_calculator.py::stage1_preprocess`；`raw_motheds/TE_model/src/ribobase_counts_processing.py` | `te_analysis/preprocess/filtering.py` | 保留算法并拆分 | 纯函数化；CLI 和文件写出外移 |
| CLR/ILR TE 计算 | `project/src/te_calc/TE.R`；`raw_motheds/TE_model/src/TE.R` | `te_analysis/compute/te_runner.py` + 保留 `TE.R` | 包裹而不改数学 | `TE.R` 继续为核心算法工件 |
| TE 后处理与跨物种合并 | `project/src/te_calc/te_calculator.py::stage3_postprocess`；`merge_cross_species_te`；`transpose_TE.py` | `te_analysis/package/results.py` | 拆分重构 | 统一物种命名、结果打包、输出清单 |
| QC 报告 | 上游 SnakeScale QC + 下游过滤副产物 | `te_analysis/qc/reporting.py` | 从头创建 | 老逻辑分散，必须重建为正式模块 |
| 顶层 CLI/阶段控制 | `Makefile`；`pipeline.bash`；`run_round2_nonstandard_gse.py` | `te_analysis/cli.py` | 从头创建 | 禁止继续使用 god shell driver |

### 4.1 Legacy Files Whose Algorithmic Core Is Worth Preserving

- `project/src/te_calc/TE.R`
- `project/src/te_calc/te_calculator.py` 中的 `stage0_extract`、`build_sample_pairing`、`validate_and_align_columns`、`stage1_preprocess`、`stage3_postprocess`
- `raw_motheds/snakescale/scripts/generate_yaml.py` 中的 organism normalization、pairing 语义、YAML 物化思路
- `raw_motheds/TE_model/src/ribo_counts_to_csv.py`
- `raw_motheds/TE_model/src/utils.py` 中的 `intevl`、`cap_outliers`、`cap_outliers_cds_only`
- `raw_motheds/TE_model/src/ribobase_counts_processing.py` 中的 CPM / dummy gene / combine 逻辑

### 4.2 Legacy Files That Should Be Wrapped, Not Copied

- `raw_motheds/riboflow/RiboFlow.groovy`
- `raw_motheds/riboflow/nextflow.config`
- `raw_motheds/riboflow/project.yaml`
- `project/src/te_calc/TE.R`
- `data/interim/modified_project/*/*_modified.yaml` 这一“物化配置产物”的概念

### 4.3 Legacy Files or Patterns That Must Not Be Migrated

- `workflow/snakescale/Snakefile` 的 god-workflow 结构
- `scripts/run_round2_nonstandard_gse.py` 的绝对路径、环境路径、磁盘阈值写死模式
- `pipeline.bash` 的 stage 编号壳层
- `Snakefile.bak*`、`config.yaml*.bak`、`test_run*.log`
- `.snakemake/`、`.nextflow/`、`work/`、`output/`、`intermediates/`
- trial 目录驱动正式生产的模式
- 通过文件名后缀隐藏业务状态的模式

## 5. Scientific Core Preservation Plan

需要被明确保护的稳定科学核心是：

- metadata / pairing contract
- extraction bridge
- winsorization
- filtering / dummy gene / non-polyA
- CLR/ILR TE computation
- TE results packaging

保护策略如下：

1. 把 `TE.R` 当作 gold standard，不先改算法，只先为其建立安全输入输出壳层。
2. 下游 preprocessing 必须以老仓库 `stage1_preprocess` 与 `ribobase_counts_processing.py` 的共同交集为准，而不是从头重写“更优版”。
3. `.ribo` 消费契约以 `.ribo` 文件和内置 RNA-seq 绑定关系为准，不退回脆弱的纯表格拼接。
4. pairing 需要在三个层次都保留：manifest 定义、`.ribo` 绑定、TE 前再校验。
5. 多物种拆分必须保留，不能把不同物种 count matrix 直接拼在一起再做过滤。
6. 任何科学层迁移都必须配一组 golden fixtures 或对照输出，先对齐结果，再谈重构形状。

## 6. Winsorization Restoration Plan

### 6.1 Evidence That Winsorization Is Missing from the Active Production Path

证据链足够明确：

- 老仓库审计明确记录：对当前老仓库活动生产路径的源码检索，未发现实际执行中的 `winsor|winsorize|winsorization` 实现。
- 对 `project/src`、`project/workflow`、`project/scripts` 的针对性检索没有找到活动 winsorization 代码。
- 老仓库当前实际下游入口 `project/src/te_calc/te_calculator.py` 的 Stage 0/1/2/3 链条包含提取、配对、过滤、TE.R 调用，但不包含显式 winsorization 层。

因此结论是：winsorization 在当前活跃生产路径中缺失，不能假设它“隐含地仍在执行”。

### 6.2 Evidence for Winsorization-Related Code in the Reference Zone

参考区 `raw_motheds/TE_model` 提供了足够强的恢复依据：

- `raw_motheds/TE_model/README.md` 明确写出：“The main code for winsorization is `src/ribo_counts_to_csv.py`”，并指向标准 99.5 percentile capping 的 trial 配置。
- `raw_motheds/TE_model/src/ribo_counts_to_csv.py` 提供 `process_coverage_fn` 回调位点，允许在 coverage 聚合前做 capping/winsorization。
- `raw_motheds/TE_model/src/utils.py` 保留 `cap_outliers()` 与 `cap_outliers_cds_only()`。
- `raw_motheds/TE_model/trials/PAX_hela/config.py` 明确示例了 `process_coverage_fn()` 调用 `cap_outliers_cds_only(..., 99.5).sum()`。

因此结论是：虽然老仓库当前生产路径里缺失 winsorization，但参考区保留了旧方法实现模式，足以作为恢复新架构时的主要方法证据。

### 6.3 Responsibility of the New Winsorization Layer

新 `winsorize.py` 必须承担以下职责：

- 接收 extraction bridge 产出的单样本 transcript/gene coverage 信息，而不是在最终 TE 或 CPM 层再补救。
- 基于 `intevl()` 定义的 usable read length 区间，在 Ribo-seq coverage 上执行 winsorization。
- 默认实现 CDS-only capping，并把标准生产默认值设为 `99.5 percentile`。
- 只对 Ribo-seq coverage 聚合路径启用标准 winsorization；RNA-seq 默认保持现有 CDS count 提取方式，除非后续另有方法学证据。
- 把 winsorization policy 写入 resolved manifest 和输出 provenance，不允许默默使用默认值而不留痕。
- 产出最少 QC 指标，例如：每样本被 capped 的位点比例、每基因 capping 前后总和变化摘要、是否触发异常高比例截断。

### 6.4 Precise Insertion Stage in the New TE-only Architecture

winsorization 的精确位置必须是：

`metadata/pairing contract` → `upstream orchestration contract` → `.ribo extraction bridge` → `winsorization` → `filtering / dummy gene / non-polyA` → `CLR/ILR TE computation` → `QC` → `output packaging`

更细化地说：

- 在 `.ribo` 被打开之后；
- 在 usable length window 已确定之后；
- 在 gene-level ribo count 最终求和写出之前；
- 在 Stage 1 的 CPM normalization / dummy gene / non-polyA 之前。

不应把 winsorization 放在：

- metadata/pairing 之前；
- 最终 count matrix 写出之后再做；
- CPM 之后；
- TE.R 之后。

### 6.5 Production Policy

新架构中的生产规则应是：

- `winsorization.enabled: true` 为 TE-only 正式运行默认且必需。
- `winsorization.method: cds_only_percentile_cap`
- `winsorization.percentile: 99.5`
- 若 study manifest 试图关闭 winsorization，则只能进入研究/回归比较模式，不能进入默认生产模式。

## 7. Configuration and Contract Plan

### 7.1 Contracts Missing Today

当前最缺的是这些显式契约：

- `metadata` 输入 schema
- `pairing` schema
- `study manifest` schema
- `resolved upstream manifest` schema
- `te run` schema
- `output manifest` schema
- `nonpolyA` 资源声明 schema
- `reference catalog` schema

### 7.2 Recommended Schemas and Manifests

建议新仓库正式定义：

- `config/schemas/metadata.schema.yaml`
  - 定义 `study_name`、`experiment_alias`、`experiment_accession`、`corrected_type`、`matched_RNA-seq_experiment_alias`、`organism` 等必需字段
- `config/schemas/pairing.schema.yaml`
  - 定义 ribo sample、rna sample、pair_id、study、organism、evidence source
- `config/schemas/study_manifest.schema.yaml`
  - 定义一个 study 的全部正式运行输入
- `config/schemas/te_run.schema.yaml`
  - 定义 extraction、winsorization、filtering、TE.R、QC、packaging 的参数
- `config/schemas/output_manifest.schema.yaml`
  - 定义最终输出文件、物种、样本数、过滤摘要、provenance
- `config/references.catalog.yaml`
  - 定义当前统一服务器上的参考资源位置和版本
- `config/pipeline.defaults.yaml`
  - 定义全局默认阈值，但不覆盖每 study 的明确字段
- `config/studies/<study>.yaml`
  - 唯一人工维护的 study 级权威 manifest

### 7.3 Clean Replacement for the Old Multi-Layer Config Behavior

旧模式的问题是：

- `project.yaml` 是模板；
- `modification.yaml` 是散落 patch；
- `_modified.yaml` 是机器物化结果；
- 真实控制面不透明，优先级也难追踪。

新模式应替换为两层，而不是三层以上：

1. `study manifest`
   - 唯一人工编辑文件
   - 明确写出样本、配对、物种、reference、dedup、adapter、read-length、winsorization、filtering、输出目标

2. `resolved manifest`
   - 机器根据 `study manifest + pipeline.defaults.yaml + references.catalog.yaml` 物化生成
   - 专供上游黑盒运行和下游处理消费
   - 任何人不得手工编辑

这保留了“物化最终配置”的好处，但去掉了散落 patch 与隐式优先级地狱。

## 8. Proposed New Module Blueprint

建议的新模块职责如下：

- `te_analysis/cli.py`
  - 提供 `validate-metadata`、`materialize-study`、`run-upstream`、`extract-counts`、`run-te`、`package-results`
- `te_analysis/contracts/metadata.py`
  - 读取、校验、标准化 metadata
- `te_analysis/contracts/pairing.py`
  - 生成并校验 Ribo/RNA pairing table
- `te_analysis/contracts/study_manifest.py`
  - 解析、校验 study manifest 与 resolved manifest
- `te_analysis/upstream/manifest_materializer.py`
  - 把权威 study manifest 物化为上游可消费配置
- `te_analysis/upstream/riboflow_runner.py`
  - 作为 RiboFlow 黑盒包装器，负责调用、日志位置和输出定位
- `te_analysis/upstream/preflight.py`
  - 放仍然必要的 adapter/read-length/reference 可运行性预检
- `te_analysis/extract/ribo_counts.py`
  - 负责 `.ribo` 打开、物种识别、样本提取、Ribo/RNA count 导出
- `te_analysis/preprocess/winsorize.py`
  - 负责 coverage-level winsorization
- `te_analysis/preprocess/filtering.py`
  - 负责 CPM normalization、dummy gene、non-polyA 过滤
- `te_analysis/compute/te_runner.py`
  - 创建安全 workdir、调用 `TE.R`、收集输出、修正命名兼容层
- `te_analysis/qc/reporting.py`
  - 输出每个阶段的 QC 摘要
- `te_analysis/package/results.py`
  - 统一生成 `te_{species}.csv`、`te_results_final.csv` 和 output manifest

## 9. Migration Order

推荐迁移顺序如下：

1. 先建立 contracts 和 manifest schema
   - 这是后续所有模块避免再次失控的基础
2. 先迁移下游科学核心
   - `TE.R` 包装层
   - Stage 1 filtering/dummy/non-polyA
   - 结果打包层
3. 再迁移 `.ribo` extraction bridge
   - 先恢复稳定 `.ribo` → raw counts 路径
4. 紧接着恢复 winsorization
   - 用参考区 `TE_model` 的方法模式正式落到 `winsorize.py`
5. 再落 pairing 合同与 TE 前对齐校验
   - 确保 manifest pairing、`.ribo` 绑定和 TE 前样本列一致
6. 再做 QC 层
   - 让每一步都有可见诊断输出
7. 最后才包裹上游 RiboFlow/SnakeScale 接口
   - 把最脏、最依赖环境的部分放到后面
8. 最后处理下载、专项补跑、磁盘保护等运维辅助能力

### 9.1 What Should Be Migrated First to Minimize Scientific Risk

最先迁移的不是 Snakemake，也不是下载器，而是：

- `TE.R` 包装层
- filtering/dummy gene/non-polyA 层
- `.ribo` extraction + winsorization 层

原因是这三层直接决定 TE 数值结果，科学风险最高，但也最容易做结果对照。

### 9.2 What Should Be Deferred

以下内容应后置：

- adapter guessing 的自动化细节
- 下载器与 Entrez 访问壳层
- round2/nonstandard 之类专项运维脚本
- 老式 disk guard、SLURM、本地 conda 路径逻辑
- 任何对 RiboFlow 内核本身的重写企图

## 10. Top Migration Risks

最可能的失败方式有：

1. 把 `raw_motheds/` 误当作未来目录结构直接复制。
2. 先迁移 `Snakefile` 或补跑脚本，结果把旧债整体带入新仓库。
3. 忽略 winsorization 缺失事实，导致重建后的 TE-only 管线继续丢失方法学必需层。
4. 在迁移早期就改写 `TE.R` 数学逻辑，破坏与历史金标准的一致性。
5. 延续 `project.yaml + modification.yaml + modified yaml` 的多层配置习惯，再次制造隐藏控制面。
6. 保留 `_dedup`、`_modified`、`_all` 这类后缀业务逻辑，导致契约继续不可见。
7. 把 cwd 假设、绝对路径、环境路径写回代码，而不是放进 manifest。
8. 把 runtime residue、历史 `.ribo`、workdir、logs 混进新仓库活动区。
9. 忽视多物种拆分，再次把不同参考体系的 count 混在一起做过滤。
10. 把 `run_round2_nonstandard_gse.py` 当作工程资产迁入，重建出第二个维护灾难。

## 11. Immediate Next Actions

蓝图落地的第一批动作应是：

1. 建立 `config/`、`tests/`、`te_analysis/contracts/`、`te_analysis/preprocess/`、`te_analysis/compute/`、`te_analysis/extract/` 空壳目录与模块。
2. 写出 `study_manifest.schema.yaml`、`te_run.schema.yaml`、`references.catalog.yaml` 的首版。
3. 把 `TE.R` 放入受控包装层，并定义固定输入输出适配接口。
4. 从 `TE_model` 提取 winsorization 原语和 `intevl()` 逻辑，正式设计 `winsorize.py`。
5. 把 `stage1_preprocess` 和 `ribobase_counts_processing.py` 的共同逻辑拆成纯函数并设计 golden test。
6. 标记当前模板文件为待归档对象，停止再把它们当正式入口使用。

## 12. Open Questions

以下问题不阻碍本蓝图定稿，但会影响后续实现细节：

- `TE_model/README.md` 提到标准 capping 位于 `trials/PAX_cap/config.py`，但当前参考区快照中直接看到的是 `PAX_hela/config.py` 示例；需在真正编码前确认是否还存在更权威的 `PAX_cap` 配置快照。
- `TE.R` 目前沿用 `human_TE_*` 命名，即使处理非 human 物种；新包装层需要决定是兼容保留还是仅在外层重命名。
- 哪些 adapter/length 预检在当前统一服务器环境下仍然必需，哪些只是历史 SnakeScale 债务，需要在实际实现前做一次小范围定界。
- `nonpolyA` 资源的权威来源、版本和适用物种范围需要单独写进 `references.catalog.yaml`。
- 某些非标准物种 study 的参考可用性是否足以进入首批迁移范围，仍需后续按 study 清单确认。
