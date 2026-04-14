# Legacy Repository Forensic Audit

## 1. Executive Summary

这个仓库并不是一个单一、整洁、边界清晰的“遗留 TE 仓库”，而是一个已经叠加了多轮迁移、补丁、补跑、结果保留和运行残留的混合体。静态审计结果表明，它至少包含以下几层同时存在的历史层：

- 顶层 `Makefile` 驱动的 CCDS 风格统一入口层。
- `workflow/snakescale/` 下的 Snakemake 编排层。
- `workflow/snakescale/riboflow/RiboFlow.groovy` 的 Nextflow/RiboFlow 真正执行层。
- `src/te_calc/te_calculator.py` + `src/te_calc/TE.R` 的下游 TE 计算层。
- `scripts/run_round2_nonstandard_gse.py` 所代表的二轮补跑/非标准物种专项调度层。
- 大量已存在的输出、缓存、运行日志、`.snakemake`、`.nextflow`、`work/`、`output/`、`intermediates/`、`.ribo` 文件与补丁化 YAML。

从“实际可执行路径”看，这个仓库当前最可信的生产路径不是 README 里宣称的简化图，而是：

`metadata.csv` / `srx_to_srr_mapping.csv` → `src/data/download_sra.py` → FASTQ → `workflow/snakescale/Snakefile` → `generate_yaml.py` 生成 study YAML → `modify_yaml` 叠加 trial-like 修改 → `run_riboflow` 调用 `RiboFlow.groovy` → per-sample `.ribo` + `all.ribo` → `.ribo` 被移动/汇总到 `data/processed/ribo_files/` → `src/te_calc/te_calculator.py` Stage 0/1/2/3 → `te_{species}.csv` → `te_results_final.csv`。

结论：

- 这个仓库**不是适合直接复用的单体管线**。
- 它是**多个历史层重叠的工作目录**。
- 其中科学核心可以迁移，但工程壳层、路径约束、修改机制和运行残留**不适合原样复制**。

## 2. Top-Level Structure Reality Check

### 实际顶层目录与文件

主要顶层项目包括：

- `Makefile`
- `README.md`
- `SETUP_AND_GUIDE.md`
- `environment.yaml`
- `requirements.txt`
- `setup_project.sh`
- `link_real_data.sh`
- `data/`
- `docs/`
- `logs/`
- `md/`
- `models/`
- `notebooks/`
- `references/`
- `reports/`
- `scripts/`
- `src/`
- `workflow/`
- `.venv/`
- `.vscode/`
- `.git/`
- `test_run.log`
- `test_run_v2.log`

### 活跃代码目录

从静态分析看，最可能仍然参与实际执行的活跃目录是：

- `src/te_calc/`
- `src/data/`
- `workflow/snakescale/`
- `scripts/`
- `data/external/`
- `data/processed/`
- `data/interim/`

其中：

- `src/te_calc/` 是下游 TE 科学核心和主执行入口。
- `src/data/` 是上游下载和元数据准备入口。
- `workflow/snakescale/` 是上游 RiboFlow 编排主战场。
- `scripts/` 中至少有一个强耦合补跑入口 `run_round2_nonstandard_gse.py`。

### 历史残留 / 运行残留 / 工程混杂目录

以下目录或文件明显包含运行残留、历史产物或维护过程中的副产物：

- `logs/`
- `workflow/snakescale/logs/`
- `workflow/snakescale/nextflow_logs/`
- `workflow/snakescale/.snakemake/`
- `workflow/snakescale/.nextflow/`
- `workflow/snakescale/work/`
- `workflow/snakescale/output/`
- `workflow/snakescale/intermediates/`
- `data/processed/ribo_files/`
- `data/processed/_te_workdir_*`
- `data/processed/round2_logs/`
- `data/processed/runner_logs/`
- `test_run.log`
- `test_run_v2.log`

这些目录说明当前仓库本身已经兼具：

- 源码仓库
- 工作目录
- 结果缓存目录
- 运行历史归档目录

三种角色，没有真正隔离。

### 独立子项目 / 嵌入外部项目痕迹

存在明显的嵌入式外部工作流痕迹：

- `workflow/snakescale/riboflow/nextflow.config`
- `workflow/snakescale/riboflow/RiboFlow.groovy`

这表明 `riboflow` 并不是顶层原生实现，而是被嵌入进来作为一个独立执行内核。

同时还存在大量备份与变体：

- `workflow/snakescale/Snakefile.bak`
- `workflow/snakescale/Snakefile.bak2`
- `workflow/snakescale/Snakefile.bak3`
- `workflow/snakescale/config.yaml.bak`
- `workflow/snakescale/config.yaml.fullrun.bak`
- `workflow/snakescale/scripts/generate_yaml.py.bak`

这说明仓库曾通过“复制文件 + 直接改副本”的方式迭代，而不是稳定抽象配置层。

### 运行残留证据

静态命令输出确认至少存在以下典型 runtime residue：

- `.snakemake`
- `.nextflow`
- `work/`
- `nextflow_logs/`
- `logs/`
- `output/`
- `intermediates/`
- `__pycache__/`
- 已存在 `.ribo` 文件
- 已存在 TE 中间工作目录 `_te_workdir_*`

结论：这个仓库必须被视为**运行现场快照**，不是纯源码仓库。

## 3. Actual Execution Path Reconstruction

### 真实有证据支持的阶段图

根据 `Makefile`、`Snakefile`、`generate_yaml.py`、`RiboFlow.groovy`、`run_round2_nonstandard_gse.py`、`te_calculator.py` 和现有输出目录交叉验证，当前最可信的实际执行路径如下：

### 阶段 0：元数据与下载准备

入口候选：

- `make download_prepare`
- `python -m src.data.download_sra --prepare`

真实输入：

- `data/external/metadata/metadata.csv`

真实输出：

- `data/external/srx_to_srr_mapping.csv`
- `data/external/sradownloader_input.txt`

关键行为：

- 从 `metadata.csv` 提取 `experiment_accession`。
- 通过 Entrez 批量做 SRX/ERX → SRR/ERR 映射。
- 写出映射表和下载输入文件。

### 阶段 1：FASTQ 下载 / 准备

入口候选：

- `make download_fetch`
- `python -m src.data.download_sra --download --outdir data/raw/fastq`
- `make link_data`
- `bash link_real_data.sh`

真实输入来源有两类：

- 下载生成到 `data/raw/fastq/`
- 服务器现存归档通过软链接进入 `data/raw/`

这里说明上游输入并不只有一种获取方式，存在“下载模式”和“链接现成数据模式”双轨。

### 阶段 2：Snakemake 编排层

真实入口：

- `make run_snakescale`
- `make run_local`
- `scripts/run_round2_nonstandard_gse.py` 内部调用 Snakemake

真实主文件：

- `workflow/snakescale/Snakefile`

从规则提取结果可见，规则顺序核心为：

- `check_adapter`
- `check_adapter_stats`
- `check_lengths`
- `guess_adapter`
- `modify_yaml`
- `classify_studies`
- `run_riboflow`

这说明真实路径不是“CSV 直接到 RiboFlow”，而是中间还有**样本长度、adapter 检测与 YAML 修改叠加层**。

### 阶段 3：study YAML 生成

真实执行点：

- `workflow/snakescale/scripts/generate_yaml.py`
- 由 `Snakefile` 在 import 时和规则中共同驱动

真实输入：

- `workflow/snakescale/project.yaml` 模板
- `data/external/srx_to_srr_mapping.csv`
- `data/external/metadata/metadata.csv`
- `workflow/snakescale/scripts/references.yaml`
- `data/raw/fastq/`

真实输出：

- `data/interim/project/{GSE}/{study}.yaml`

关键逻辑：

- study 名中 `_dedup` 和 `_test` 有特殊语义。
- Ribo 和 RNA 配对通过 `matched_RNA-seq_experiment_alias` 建立。
- YAML 的 `input.fastq` 与 `rnaseq.fastq` 共用 Ribo GSM key，实现后续 sample-name join。

### 阶段 4：YAML 修改层

真实执行点：

- `Snakefile` 的 `modify_yaml` rule

真实输入：

- `{study}_adapter.yaml`
- `{study}_length.yaml`
- `{study}_guess.yaml`
- `data/interim/modifications/{study}/modification.yaml`
- 原始 project YAML

真实输出：

- `data/interim/modified_project/{study}/{study}_modified.yaml`
- 以及原始 project 目录中的 `_modified.yaml`

结论：**真正被 RiboFlow 使用的通常不是原始 YAML，而是 modified YAML**。这是仓库里最重要的隐藏控制面之一。

### 阶段 5：RiboFlow / Nextflow 真执行层

真实入口：

- `Snakefile` 的 `run_riboflow`
- shell 命令为：
  `nextflow riboflow/RiboFlow.groovy -params-file {study_yaml} -profile {params.profile}`

真实内核：

- `workflow/snakescale/riboflow/RiboFlow.groovy`

真实顺序可重建为：

- clip
- filter
- transcriptome_alignment
- quality_filter
- bam_to_bed
- merge_bed
- deduplicate（可选）
- `ribopy create`
- `ribopy rnaseq set`
- `ribopy merge`

### 阶段 6：`.ribo` 生成

`.ribo` 生成位置：

- per-sample `.ribo` 在 RiboFlow 的 `create_ribo` 过程中生成。
- study 级 `all.ribo` 在 `merge_ribos` 阶段生成。

已确认真实输出目录：

- `workflow/snakescale/output/{GSE}/ribo/all.ribo`

补跑脚本 `run_round2_nonstandard_gse.py` 还会将其移动到：

- `data/processed/ribo_files/{GSE}.ribo`

因此对下游 TE 而言，**稳定消费目录是 `data/processed/ribo_files/`，不是 workflow 输出目录**。

### 阶段 7：`.ribo` 提取为原始计数矩阵

真实入口：

- `src/te_calc/te_calculator.py`
- `stage0_extract()`

真实行为：

- 遍历 `ribo_dir/*.ribo`
- 使用 `ribopy.Ribo` 打开文件
- `get_region_counts(region_name="CDS", sum_lengths=True, sum_references=False)` 提取 Ribo-seq CDS 计数
- `get_rnaseq()` 提取内置 RNA-seq CDS 计数
- 按物种拆分输出

真实输出：

- `ribo_raw_{species}.csv`
- `rnaseq_raw_{species}.csv`
- `infor_filter_{species}.csv`

### 阶段 8：配对验证 / 对齐

真实位置：

- `te_calculator.py` 中 `build_sample_pairing()`
- `validate_and_align_columns()`
- `stage1_preprocess()` 前半段作为 Stage 0.5

真实作用：

- 使用 `metadata.csv` + `srx_to_srr_mapping.csv` 重新建立 Ribo↔RNA 配对字典。
- 若 count 矩阵列名与配对字典不一致则丢弃无法匹配的列。
- 若未提供 metadata/mapping，则退化为“共同列名 inner 匹配”。

### 阶段 9：过滤 / 归一化 / dummy gene

真实位置：

- `te_calculator.py` 的 `stage1_preprocess()`

真实逻辑：

- `CPM_normalize()`
- `dummy_gene_df()`
- `combine_dummy_gene()`
- 可选 `nonpolya_csv` 过滤

真实输出：

- `ribo_paired_count_dummy_{species}.csv`
- `rna_paired_count_dummy_{species}.csv`
- `ribo_paired_cpm_dummy_{species}_{cutoff}.csv`
- `rna_paired_cpm_dummy_{species}_{cutoff}.csv`
- quantile 版文件

### 阶段 10：CLR/ILR TE 计算

真实位置：

- `src/te_calc/TE.R`
- `te_calculator.py` 的 `stage2_run_te_r()`

真实调用方式：

- 先在 `data/processed/_te_workdir_{species}` 下建立符号链接
- 再运行 `Rscript TE.R <work_dir>`

真实输入：

- `ribo_paired_count_dummy.csv`
- `rna_paired_count_dummy.csv`
- 可选 `infor_filter.csv`

真实输出：

- `human_TE_sample_level.rda`
- `human_TE_cellline_all.csv`（若信息文件存在）

### 阶段 11：后处理与最终输出

真实位置：

- `stage3_postprocess()`
- `merge_cross_species_te()`

真实输出：

- `te_{species}.csv`
- `te_results_final.csv`

### 关于 winsorization

本次静态审计中，**未在当前仓库可检索到任何实际执行中的 winsorization 实现**。对全仓库 `winsor|winsorize|winsorization` 检索无结果。

因此结论是：

- 当前仓库中 winsorization 要么已经被移除，
- 要么存在于外部上游系统（例如未内嵌的 SnakeScale/RiboFlow 版本、历史仓库或外部脚本），
- 要么只存在于文档/口述需求而非本仓库实际执行路径中。

这必须在迁移规划中明确标记为 **未确认，不可臆测**。

## 4. Entrypoints and Drivers

### `Makefile`

角色：顶层人工入口。

它控制：

- 初始化目录
- 链接真实数据
- 准备下载映射
- 下载 FASTQ
- 启动 Snakemake
- 启动 TE 计算
- 绘图

审计判断：

- 它是**人类操作主入口**。
- 但并非所有真实生产路径都必须经由它，因为二轮补跑脚本绕过了它的一部分控制。

### `workflow/snakescale/Snakefile`

角色：上游 workflow 编排主入口。

它真正控制：

- study YAML 的生成
- adapter/length 检测
- modified YAML 的产出
- RiboFlow 的 Nextflow 调用
- `all.ribo` 生成路径

审计判断：

- 这是**上游真实执行入口**。
- 同时它也是一个“god workflow”。

### `workflow/snakescale/riboflow/RiboFlow.groovy`

角色：真正执行 Ribo/RNA 流程的核心引擎。

它真正控制：

- reads 修剪
- rRNA/tRNA 过滤
- transcriptome alignment
- MAPQ 过滤
- BED 转换
- dedup
- `.ribo` 创建
- RNA-seq 注入 `.ribo`
- 合并成 `all.ribo`

审计判断：

- 这是**`.ribo` 生成的权威实现**。

### `src/data/download_sra.py`

角色：下载准备与下载执行入口。

它真正控制：

- 从 `metadata.csv` 抽取 accession
- 通过 Entrez 做 SRX/ERX→SRR/ERR 映射
- 生成 `srx_to_srr_mapping.csv`
- 生成 `sradownloader_input.txt`
- 调用 `sradownloader`

审计判断：

- 这是**元数据到 FASTQ 的真实上游入口**。

### `src/te_calc/te_calculator.py`

角色：下游 TE 主入口。

它真正控制：

- `.ribo` 提取
- 物种拆分
- 配对验证
- 过滤/CPM/dummy gene
- 调用 `TE.R`
- 后处理
- 跨物种合并

审计判断：

- 这是**最终 TE 输出的权威入口**。

### `src/te_calc/TE.R`

角色：科学核心算法脚本。

它真正控制：

- CLR
- ILR
- 逐 ILR 分量回归
- 残差回转为 CLR TE
- cell_line 聚合

审计判断：

- 这是**TE 数学定义的核心权威实现**。

### `scripts/run_round2_nonstandard_gse.py`

角色：二轮补跑专项驱动。

它真正控制：

- 非标准物种 queue 构建
- FASTQ preflight 检查
- 每 GSE 临时 config 生成
- 批量 Snakemake 执行
- `all.ribo` 向 `data/processed/ribo_files/` 的转移
- 多物种 warning 排除
- 最终 TE 批处理
- 磁盘保护阈值

审计判断：

- 这是**高优先级现实入口**，因为它代表维护者后来真正用来跑“补丁化生产任务”的方式。
- 它不是科学核心，但揭示了最多的技术债与真实控制面。

## 5. Critical File-by-File Review

### 1. `Makefile`

- path: `Makefile`
- file type: Makefile
- role: 顶层人工调度器
- entrypoint/helper/library status: entrypoint
- key functions/classes: make targets
- imports/dependencies: `python3`, `Rscript`, `snakemake`, shell, `sbatch`
- inputs:
  - `data/external/metadata/metadata.csv`
  - `data/raw/fastq/`
  - `workflow/snakescale/`
  - `.ribo` 目录或 count matrix
- outputs:
  - logs
  - workflow outputs
  - TE outputs
- side effects:
  - 运行 shell
  - 清理目录
  - 提交 SLURM 任务
- hard-coded assumptions:
  - cwd 必须是项目根目录
  - `workflow/snakescale` 固定存在
  - `logs/slurm` 固定写入
- migration value: reference only
- recommendation: 保留目标语义，**不要直接迁移实现**。

### 2. `src/data/download_sra.py`

- path: `src/data/download_sra.py`
- file type: Python
- role: 元数据解析、SRX→SRR 映射、调用下载器
- entrypoint/helper/library status: entrypoint
- key functions/classes:
  - `extract_accessions`
  - `entrez_srx_to_srr`
  - `entrez_ers_to_srr`
  - `write_outputs`
  - `run_sradownloader`
  - `main`
- imports/dependencies:
  - `argparse`
  - `subprocess`
  - Entrez 网络访问
  - `sradownloader`
- inputs:
  - `metadata.csv`
- outputs:
  - `srx_to_srr_mapping.csv`
  - `sradownloader_input.txt`
  - FASTQ files
- side effects:
  - 外部网络请求
  - 文件写入
  - 执行下载工具
- hard-coded assumptions:
  - 项目根自动探测逻辑
  - 默认输出路径固定在 CCDS 目录布局
- migration value: split/refactor
- recommendation: 保留 accession 解析与映射逻辑，重写下载执行壳层。

### 3. `workflow/snakescale/Snakefile`

- path: `workflow/snakescale/Snakefile`
- file type: Snakemake
- role: 上游 DAG 编排中心
- entrypoint/helper/library status: entrypoint
- key functions/classes:
  - Snakemake rules: `check_adapter`, `check_adapter_stats`, `check_lengths`, `guess_adapter`, `modify_yaml`, `classify_studies`, `run_riboflow`
- imports/dependencies:
  - `yaml`, `pandas`, `Bio.SeqIO`
  - `generate_yaml`
  - `guess_adapter`
  - Nextflow
- inputs:
  - `config.yaml`
  - metadata CSVs
  - FASTQ files
  - project template
  - references
- outputs:
  - modified YAMLs
  - logs
  - Nextflow outputs
  - `all.ribo`
- side effects:
  - import 时即尝试生成 YAML
  - 写 log
  - 写 modification outputs
  - 运行 Nextflow
- hard-coded assumptions:
  - cwd 必须是 `workflow/snakescale/`
  - 相对路径大量依赖 `../../data/...`
  - 模板 `project.yaml` 必须在当前目录
- migration value: split/refactor
- recommendation: 不可整体迁移；需拆出 study 发现、YAML 生成、修改叠加和执行提交逻辑。

### 4. `workflow/snakescale/scripts/generate_yaml.py`

- path: `workflow/snakescale/scripts/generate_yaml.py`
- file type: Python
- role: study 级 YAML 生成器
- entrypoint/helper/library status: helper with CLI-like role
- key functions/classes:
  - `normalize_organism`
  - `resolve_fastq_paths`
  - `generate_clip_sequence`
  - `generate_yaml`
- imports/dependencies:
  - `pandas`, `yaml`, `glob`
- inputs:
  - `metadata.csv`
  - `srx_to_srr_mapping.csv`
  - `references.yaml`
  - FASTQ directory
  - `project.yaml`
- outputs:
  - `data/interim/project/{GSE}/{study}.yaml`
- side effects:
  - 自动建目录
  - print warning
- hard-coded assumptions:
  - `metadata.csv` 用 `header=1`
  - species alias 字典硬编码
  - FASTQ 命名模式硬编码
  - study suffix `_dedup` / `_test` 有业务语义
  - `reference_folder="reference"`
- migration value: preserve algorithm
- recommendation: 这是**metadata parsing + pairing + YAML materialization** 的最佳来源之一，应保留核心逻辑后重构壳层。

### 5. `workflow/snakescale/riboflow/RiboFlow.groovy`

- path: `workflow/snakescale/riboflow/RiboFlow.groovy`
- file type: Groovy / Nextflow DSL1
- role: 实际 reads→`.ribo` 执行内核
- entrypoint/helper/library status: entrypoint
- key functions/classes:
  - processes for clip/filter/alignment/bam_to_bed/dedup/create/merge/put_rnaseq
- imports/dependencies:
  - Nextflow runtime
  - cutadapt
  - bowtie2
  - samtools
  - bedtools
  - ribopy
  - riboflow commands
- inputs:
  - FASTQ
  - transcriptome/filter references
  - annotation/lengths
  - params yaml
- outputs:
  - BEDs
  - BAMs
  - per-sample `.ribo`
  - `all.ribo`
- side effects:
  - 大量中间文件写入
  - publishDir 输出
  - 对 `.ribo` 原地注入 RNA-seq
- hard-coded assumptions:
  - params schema 固定
  - `do_rnaseq`/`rnaseq` 节点必须并存
  - sample-name join 作为配对核心
- migration value: wrap without rewriting
- recommendation: `.ribo` 生成与 RNA 注入逻辑应作为外部稳定黑盒引用，**不要在新仓库中手抄重写**。

### 6. `src/te_calc/te_calculator.py`

- path: `src/te_calc/te_calculator.py`
- file type: Python
- role: 下游 TE 主程序
- entrypoint/helper/library status: entrypoint + mixed library
- key functions/classes:
  - `stage0_extract`
  - `build_sample_pairing`
  - `validate_and_align_columns`
  - `CPM_normalize`
  - `dummy_gene_df`
  - `combine_dummy_gene`
  - `stage1_preprocess`
  - `stage2_run_te_r`
  - `stage3_postprocess`
  - `merge_cross_species_te`
  - `main`
- imports/dependencies:
  - `pandas`, `numpy`, `ribopy`, `bioinfokit`, `subprocess`
- inputs:
  - `.ribo` files
  - metadata/mapping CSV
  - optional non-polyA CSV
- outputs:
  - raw count CSVs
  - paired dummy CSVs
  - `_te_workdir_*`
  - `.rda`
  - `te_{species}.csv`
  - `te_results_final.csv`
- side effects:
  - 覆写 `ribo_raw*.csv` / `rnaseq_raw*.csv`
  - 建 symlink workdir
  - 调用 Rscript
- hard-coded assumptions:
  - APPRIS transcript ID 格式
  - species detection 依赖 transcript naming convention
  - R 输出对象名永远叫 `human_TE`
  - `TE.R` 固定文件名和固定输入文件名
- migration value: preserve algorithm + split/refactor
- recommendation: 科学核心高度可迁移，但必须拆分 IO、pairing、species split、R invocation、merge layers。

### 7. `src/te_calc/TE.R`

- path: `src/te_calc/TE.R`
- file type: R
- role: CLR/ILR 科学核心
- entrypoint/helper/library status: scientific core entrypoint
- key functions/classes:
  - `TE_clr`
- imports/dependencies:
  - `propr`, `compositions`, `tidyverse`, `foreach`, `doParallel`
- inputs:
  - `ribo_paired_count_dummy.csv`
  - `rna_paired_count_dummy.csv`
  - optional `infor_filter.csv`
- outputs:
  - `human_TE_sample_level.rda`
  - `human_TE_cellline_all.csv`
- side effects:
  - 启动并行 cluster
  - 读写当前工作目录固定命名文件
- hard-coded assumptions:
  - 输入文件名固定
  - 输出对象和输出文件名保留 `human_` 前缀，即使处理非 human 物种
- migration value: preserve algorithm
- recommendation: 作为算法金标准保留，不要随意改数学逻辑；只包裹更安全的工作目录适配层。

### 8. `scripts/run_round2_nonstandard_gse.py`

- path: `scripts/run_round2_nonstandard_gse.py`
- file type: Python
- role: 二轮补跑调度器
- entrypoint/helper/library status: entrypoint
- key functions/classes:
  - `build_queue`
  - `preflight_check`
  - `write_temp_config`
  - `run_snakemake`
  - `preserve_final_ribo`
  - `prepare_te_inputs`
  - `run_te_calculation`
  - `main`
- imports/dependencies:
  - `yaml`, `pandas`, `subprocess`, local conda binaries
- inputs:
  - metadata CSV
  - mapping CSV
  - base config
  - existing FASTQ roots
- outputs:
  - temp configs
  - round2 logs
  - moved `.ribo`
  - summary/state files
- side effects:
  - 强硬编码项目路径与解释器路径
  - 可能删除/移动 output/intermediate
  - 生成 TE 输入 symlink 目录
- hard-coded assumptions:
  - `PROJECT_ROOT = /home/xrx/my_project/project`
  - conda env 固定路径
  - `FREE_SPACE_STOP_GB = 1024`
  - `LOCAL_CORES = 48`
  - `RAW_DATA_ROOT = /home/xrx/raw_data/TE_ribo-seq`
- migration value: reference only
- recommendation: 不应直接迁移，但它揭示了真实生产保护逻辑、disk guard、补跑控制策略和 `.ribo` 汇总方式。

### 9. `data/interim/modifications/*/modification.yaml`

- path: `data/interim/modifications/{study}/modification.yaml`
- file type: YAML
- role: 隐式 trial/config 控制层
- entrypoint/helper/library status: control surface
- key functions/classes: N/A
- imports/dependencies: 由 `modify_yaml` 消费
- inputs: study-specific manual edits
- outputs: 影响 `_modified.yaml`
- side effects: 改变 read length、MAPQ、adapter、reference 元数据等
- hard-coded assumptions: 每 study 单独补丁
- migration value: reference only
- recommendation: 不应原样迁移，但需要提炼为显式 schema。

### 10. `data/interim/modified_project/*/*_modified.yaml`

- path: `data/interim/modified_project/{study}/{study}_modified.yaml`
- file type: YAML
- role: 真正喂给 RiboFlow 的物化参数文件
- entrypoint/helper/library status: runtime materialized config
- key functions/classes: N/A
- inputs: 原始 project yaml + modifications + adapter/length/guess yaml
- outputs: Nextflow 参数文件
- side effects: 直接控制生产运行
- hard-coded assumptions:
  - `root_meta` 指向 modified yaml 本体
  - 相对路径严格依赖 workflow cwd
- migration value: wrap without rewriting
- recommendation: 新架构应保留“物化后的单研究配置文件”这一概念，但不可继续依赖多层散落 YAML 合并。

## 6. Hidden Contracts and Naming Conventions

### cwd 假设

多个关键模块依赖当前工作目录：

- `Makefile` 默认从项目根运行。
- `workflow/snakescale/Snakefile` 假设 cwd 为 `workflow/snakescale/`。
- `generate_yaml.py` 假设 `project.yaml` 在当前目录。
- `Snakefile` 使用大量 `../../data/...`。
- `TE.R` 假设工作目录下固定文件名存在。

结论：cwd 是隐藏契约，不满足就会静默找错路径。

### 后缀逻辑

明确发现以下命名编码业务逻辑：

- `_dedup`
  - study 名后缀，控制 `deduplicate=True/False`
- `_test`
  - 被 `generate_yaml.py` 识别为允许的 study 后缀
- `_modified`
  - 表示修改后 YAML，往往才是 RiboFlow 真正输入
- `_all`
  - `.ribo` 或文件 stem 特殊含义，在 TE 侧会去掉 `_all`
- `all.ribo`
  - study 级合并 `.ribo`
- `_te_workdir_{species}`
  - TE.R 适配工作目录
- `human_TE_*`
  - 即使非 human 物种也沿用该前缀

### 隐式 metadata schema

`metadata.csv` 的关键隐式约束：

- 真实 header 在第二行，读取必须 `header=1`
- `experiment_alias` 是 GSM 主键
- `experiment_accession` 是 SRX/ERX
- `corrected_type` 区分 Ribo/RNA
- `matched_RNA-seq_experiment_alias` 是配对锚点

### 隐式文件布局契约

- FASTQ 默认在 `data/raw/fastq/` 扁平放置
- `.ribo` 中间输出先在 `workflow/snakescale/output/{GSE}/ribo/all.ribo`
- 后续常被转移到 `data/processed/ribo_files/{GSE}.ribo`
- modification 与 modified_project 两套目录必须并行存在

### species/reference 假设

- `generate_yaml.py` 的 `ORGANISM_ALIAS` 是强人工字典
- `references.yaml` 的键必须和归一化物种名匹配
- transcript ID 格式被用来反推出物种
- APPRIS pipe format 被默认视为 human/mouse 可区分来源

结论：species 处理并不通用，强依赖人工编码和参考命名。

## 7. Technical Debt and Failure Modes

### god scripts / god workflows

最明显的 god 级文件：

- `workflow/snakescale/Snakefile`
- `scripts/run_round2_nonstandard_gse.py`
- `src/te_calc/te_calculator.py`

它们都混合了：

- IO
- config
- business logic
- orchestration
- logging
- side effects
- environment assumptions

### 重复逻辑

发现的重复 / 镜像逻辑包括：

- 多个 `Snakefile.bak*`
- 多个 `config.yaml*`
- `generate_yaml.py` 与备份版
- 文档中对流程的多份叙述与实际代码并不完全同步
- Ribo/RNA 配对逻辑在 YAML 层、`.ribo` 层、TE 对齐层重复出现

### IO 与业务逻辑混杂

最明显位置：

- `te_calculator.py`
  - 既做算法、又做文件发现、又做 symlink workdir、又做 R 调用、又做 merge
- `run_round2_nonstandard_gse.py`
  - 既做 queue、又做磁盘保护、又做 Snakemake、又做 `.ribo` 归档、又做 TE 批跑
- `Snakefile`
  - import 时就执行 YAML 生成与日志写出

### 导入期副作用 / 强副作用

- `Snakefile` 在顶层执行 YAML 生成循环和状态日志写入，不只是 rule 定义。
- `modify_yaml` 会物化新配置，改变后续行为。
- `te_calculator.py` Stage 1 在 pairing 模式下会直接覆写 raw CSV。

### 硬编码问题

高风险硬编码包括：

- `/home/xrx/my_project/project`
- `/home/xrx/raw_data/TE_ribo-seq`
- `/home/xrx/miniconda3/envs/snakemake-ribo/bin/...`
- 默认 `compute` 分区、`50` jobs、`30` latency
- `FREE_SPACE_STOP_GB = 1024`
- `LOCAL_CORES = 48`
- `human_TE_sample_level.rda` 命名

### 人类/物种特异性

- `cell_line` 分组强耦合人类实验命名
- transcript ID 规则面向少数物种
- `ORGANISM_ALIAS` 手工表非通用
- `nonpolyA` 过滤假设依赖文库策略

### 死代码 / 一次性代码嫌疑

高疑似项：

- `Snakefile.bak*`
- `config.yaml.bak` / `config.yaml.fullrun.bak`
- 某些 `docs/`、`md/archive/` 只记录过程
- `test_run*.log`
- 大量 round2 输出日志
- 部分现存 `.ribo` 如 `all.ribo` / 单样本 `.ribo` 并存，存在冗余

### 嵌入输出和仓库污染

仓库中存在大量真实运行产物，导致：

- 难区分源码与数据
- 难区分历史成功输出与当前有效输出
- 任何 naive copy 都可能带走 TB 级中间残留和错误上下文

## 8. Where the Scientific Core Actually Lives

### metadata parsing

最佳来源：

- `workflow/snakescale/scripts/generate_yaml.py`
- `src/data/download_sra.py`
- `src/te_calc/te_calculator.py::build_sample_pairing`

建议：

- 上游 accession 提取与 mapping 来自 `download_sra.py`
- study/Ribo/RNA 业务配对语义来自 `generate_yaml.py`
- 下游强约束样本对齐来自 `build_sample_pairing`

### pairing

最佳来源：

- `generate_yaml.py`
- `RiboFlow.groovy` sample-name join
- `te_calculator.py::build_sample_pairing`
- `te_calculator.py::validate_and_align_columns`

结论：

- YAML 层负责**定义配对**
- `.ribo` 层负责**物理绑定配对**
- TE 层负责**再校验配对**

### `.ribo` extraction

最佳来源：

- `te_calculator.py::extract_counts_from_ribo`
- `te_calculator.py::stage0_extract`

### winsorization

最佳来源：

- **当前仓库内未确认存在**

结论：

- 不应从本仓库直接迁移 winsorization 代码，因为未找到权威实现。
- 需要回溯外部旧仓库或上游系统补证。

### filtering

最佳来源：

- `te_calculator.py::dummy_gene_df`
- `te_calculator.py::combine_dummy_gene`
- `te_calculator.py::stage1_preprocess`

### TE calculation

最佳来源：

- `src/te_calc/TE.R`
- `te_calculator.py::stage2_run_te_r`
- `te_calculator.py::stage3_postprocess`

## 9. Migration Asset Classification

### preserve algorithm

- `src/te_calc/TE.R`
- `te_calculator.py` 中 Stage 1 的 CPM/dummy/non-polyA 逻辑
- `te_calculator.py` 中 `.ribo` 提取逻辑
- `generate_yaml.py` 中 metadata pairing / species normalization 主逻辑

### wrap without rewriting

- `RiboFlow.groovy` 作为 `.ribo` 生成黑盒
- modified YAML 物化概念
- `.ribo` → count matrix 入口契约

### split/refactor

- `te_calculator.py`
- `Snakefile`
- `download_sra.py`
- 样本配对校验层

### reference only

- `Makefile`
- `scripts/run_round2_nonstandard_gse.py`
- `docs/`、`md/PIPELINE_DETAILS.md`
- 各类 logs / summary / state files
- `modification.yaml` 具体内容

### archive/discard

- `Snakefile.bak*`
- `config.yaml*.bak`
- `test_run*.log`
- 大量 `round2_logs`
- `.snakemake`、`.nextflow`、`work/`、`intermediates/` 等运行残留

### unknown

- winsorization 实现
- 某些 modification 合并优先级细节
- 某些非标准物种参考是否真正经过生产验证

## 10. Top Migration Risks

1. 误把 `README` 当成真实流程，而忽略 `modify_yaml` 与二轮补跑入口。
2. 直接复制整个仓库，把大量运行残留、无效输出和历史日志一起带入新仓库。
3. 忽略 `metadata.csv` 的 `header=1` 特性，导致元数据解析错位。
4. 忽略 `_dedup`、`_test`、`_modified`、`_all` 等后缀语义。
5. 只迁移 `generate_yaml.py`，却漏掉 `modify_yaml` 这层真实控制面。
6. 只消费 `workflow/snakescale/output/.../all.ribo`，忽略实际生产常用的 `data/processed/ribo_files/` 汇总目录。
7. 把 TE 层的多物种分拆修复丢掉，重新引入跨物种结构零问题。
8. 直接改写 `TE.R` 数学核心，破坏与 CenikLab 原方法的一致性。
9. 保留硬编码绝对路径和本地 conda 路径，导致新仓库不可移植。
10. 认为 winsorization 在当前仓库中已实现并盲目迁移，实际会迁移到一个不存在的模块。
11. 忽略 `.ribo` 内 sample-name 物理绑定的配对优势，退回脆弱的元数据表 join。
12. 将 `run_round2_nonstandard_gse.py` 当成可复用工程模块，而不是补丁化运维脚本。

## 11. Recommended Extraction Order

建议迁移抽取顺序如下：

1. **先抽科学金标准**
   - `TE.R`
   - Stage 1 preprocessing 逻辑

2. **再抽 `.ribo` 消费契约**
   - `extract_counts_from_ribo`
   - `stage0_extract`
   - 物种拆分策略

3. **再抽配对逻辑**
   - `generate_yaml.py` 中 Ribo↔RNA 映射生成
   - `build_sample_pairing`
   - `validate_and_align_columns`

4. **再定义新配置 schema**
   - 将 `project.yaml` + `modification.yaml` + `_modified.yaml` 合并成一套显式 schema

5. **最后才接上游 `.ribo` 生产壳层**
   - 对接外部 RiboFlow / SnakeScale
   - 不迁移老 `Snakefile` 原样实现

6. **运维脚本最后处理**
   - 仅提炼 disk guard、resume、queue 思路
   - 不直接迁移补跑脚本实现

## 12. Open Questions / Unknowns

以下内容无法通过本次静态只读审计完全确认：

- 当前仓库中 winsorization 是否完全外置，还是被历史上移除。
- `modify_yaml` 中多种 modification YAML 合并的最终优先级细节是否在所有 study 上一致。
- `references.yaml` 中所有物种参考是否都完整可用，还是部分只是占位。
- `Snakefile.bak*` 和 `config.yaml*.bak` 哪一版曾经对应正式生产跑批。
- 某些 `.ribo` 文件是否为重复内容或人工拷贝结果，而非独立 study 产出。
- `human_TE_*` 命名在非 human 物种上的沿用，是否被其他下游脚本隐式依赖。
- 部分 round2 补跑 study 是否已经被新主流程吸收，还是仍依赖专项脚本。

## 13. Appendix

### file counts

静态命令已确认：

- 仓库含大量目录与文件，且同时包含源码、日志、结果和缓存。
- 具体计数见 validation 输出。

### key command outputs

关键证据包括：

- `find . -maxdepth 2 -print | sort`
- `find . -type f | wc -l`
- `find . -type d | wc -l`
- `find . -type l -ls`
- 入口点检索结果
- `Snakefile` 规则名提取结果

### function inventory

关键函数库存：

- `download_sra.py`
  - `extract_accessions`
  - `entrez_srx_to_srr`
  - `entrez_ers_to_srr`
  - `write_outputs`
  - `run_sradownloader`
- `generate_yaml.py`
  - `normalize_organism`
  - `resolve_fastq_paths`
  - `generate_clip_sequence`
  - `generate_yaml`
- `te_calculator.py`
  - `stage0_extract`
  - `build_sample_pairing`
  - `validate_and_align_columns`
  - `stage1_preprocess`
  - `stage2_run_te_r`
  - `stage3_postprocess`
  - `merge_cross_species_te`

### path anomalies

高风险路径异常：

- 大量 `../../data/...` 相对路径
- 脚本中嵌入 `/home/xrx/...` 绝对路径
- workflow 输出和 processed 汇总目录并存
- modified YAML 与原 project YAML 同时存在

### nested repo notes

未发现嵌套 `.git` 仓库证据；但存在嵌入式外部工作流代码：

- `workflow/snakescale/riboflow/`

### runtime residue notes

确认存在：

- `.snakemake`
- `.nextflow`
- `work/`
- `output/`
- `intermediates/`
- `nextflow_logs/`
- `logs/`
- `__pycache__/`
- 已生成 `.ribo`
- 已生成 TE 中间工作目录

这些内容说明当前仓库在法证意义上更像“活跃工作现场镜像”，而不是干净源码归档。
