# Repository Census and Migration Audit

## 1. Executive Summary

当前仓库**不是空仓库**，也**不是已完成的 TE-only CCDS 项目**，而是三类内容并存的混合体：

- **CCDS 样板骨架**
  - 根目录具备 `data/`、`docs/`、`models/`、`notebooks/`、`references/`、`reports/`、`te_analysis/`、`pyproject.toml`、`pixi.toml`、`Makefile`、`README.md` 等典型 Cookiecutter Data Science 结构。
  - 但 `te_analysis/` 中的 Python 模块基本都是模板占位代码，不包含真实 TE 管线实现。

- **历史参考项目集合 `raw_motheds/`**
  - `raw_motheds/snakescale/`：Snakemake 工作流，用于从 RiboBase sqlite 元数据生成 RiboFlow 参数、下载 fastq、做 adapter/length 预检查并调用 Nextflow RiboFlow。
  - `raw_motheds/riboflow/`：独立 Nextflow 项目，负责把 Ribo-seq / RNA-seq 原始测序数据处理成 `.ribo` 文件。
  - `raw_motheds/TE_model/`：旧 TE 计算仓库，含从 `.ribo` 提取计数、winsorization/过滤、R 中 CLR/ILR TE 计算和若干 trial 脚本。
  - 这些目录是**未来迁移的重要参考**，但**不应被视为当前新仓库结构本身**。

- **历史运行残留 / 非理想纳入物**
  - `raw_motheds/*/.git/` 嵌套 git 仓库。
  - `raw_motheds/snakescale/.snakemake/` 运行状态目录。
  - `raw_motheds/snakescale/reference/` 大量参考索引文件。
  - `raw_motheds/snakescale/db/db.sqlite3` 数据库文件。
  - `raw_motheds/TE_model/trials/` 中已有中间产物/结果 CSV/RDA。

结论：

- 当前仓库**已部分搭好 CCDS 外壳，但尚未完成 TE-only 重构**。
- 仓库**适合进入架构规划阶段**，但还**不适合直接视为可维护的新管线**。
- 现有真实可复用逻辑分散在历史参考代码中，且职责混杂、路径假设强、输入契约不清，需要在 CCDS 结构下重新拆分和包装。

## 2. Repository Tree Overview

### 2.1 顶层结构概览

仓库根目录：`/home/xrx/my_projects/te_analysis`

顶层目录共 10 个：

- `.git/`
- `.windsurf/`
- `data/`
- `docs/`
- `models/`
- `notebooks/`
- `raw_motheds/`
- `references/`
- `reports/`
- `te_analysis/`

顶层重要文件：

- `.env`
- `.gitignore`
- `LICENSE`
- `Makefile`
- `README.md`
- `pixi.toml`
- `pyproject.toml`

### 2.2 当前 CCDS 相关目录现状

已存在且符合 CCDS 命名习惯：

- `data/`
  - `data/raw/`
  - `data/interim/`
  - `data/processed/`
  - `data/external/`
- `docs/`
- `models/`
- `notebooks/`
- `references/`
- `reports/`
  - `reports/figures/`
- `te_analysis/`

判断：

- **外层骨架基本具备 CCDS 风格。**
- 但这些目录中的大多数尚无 TE 管线真实实现。
- 根 README 展示的是模板式项目组织说明，而非当前真实状态的准确文档。

### 2.3 重要嵌套目录

#### 当前新仓库目录

- `te_analysis/`
  - `__init__.py`
  - `config.py`
  - `dataset.py`
  - `code_scffold.py`
  - `plots.py`
  - `modeling/__init__.py`
  - `modeling/train.py`
  - `modeling/predict.py`

- `notebooks/`
  - `notebook_scaffold.ipynb`

#### 参考目录：`raw_motheds/`

- `raw_motheds/snakescale/`
  - `Snakefile`
  - `Snakefile_unitmetadata`
  - `config/config.yaml`
  - `schemas/config.schema.yaml`
  - `scripts/*.py`
  - `envs/environment.yaml`
  - `project.yaml`
  - `docs/Snakefile.md`
  - `db/db.sqlite3`
  - `reference/`
  - `riboflow/`（局部副本）
  - `.snakemake/`（运行残留）

- `raw_motheds/riboflow/`
  - `RiboFlow.groovy`
  - `nextflow.config`
  - `configs/*.config`
  - `project.yaml`
  - `project_umi.yaml`
  - `environment.yaml`
  - `docker/*`
  - `README.md`

- `raw_motheds/TE_model/`
  - `src/*.py`
  - `src/TE.R`
  - `pipeline.bash`
  - `trials/*`
  - `data/*`
  - `other_scr/*`
  - `riboflow_scr/*.yaml`
  - `README.md`

### 2.4 CCDS 标准目录缺失情况

严格从 CCDS 模板习惯和一个可维护的 TE-only 项目需要来看：

已存在但内容不足：

- `docs/`：存在，但此前为空。
- `references/`：存在，但无项目级参考文档。
- `data/` 子目录：存在，但无当前项目输入契约与样例。
- `reports/`：存在，但无审计/分析产物。

结构上缺失或未明确建立的关键目录/模块概念：

- **专门的 workflow/orchestration 目录**
  - 例如 `workflow/`、`pipelines/` 或 `te_analysis/workflows/` 不存在。
- **专门的 CLI 入口目录/模块**
  - 没有明确的 TE-only 管线命令入口，例如 `te_analysis/cli.py`。
- **专门的 metadata contract 层**
  - 没有 `metadata.py`、`schema/`、`contracts/` 等。
- **专门的 bridge layer（提取 + pairing + winsorization）模块**
  - 当前仓库不存在清晰的 `extract.py`、`pairing.py`、`winsorize.py`。
- **专门的 TE computation 模块**
  - 当前 `te_analysis/` 内不存在真实 TE 计算代码。
- **项目级配置目录**
  - 没有 `config/` 目录承载 YAML/TOML 配置、模式定义与样例配置。
- **测试目录**
  - 没有 `tests/`。

### 2.5 仓库真实状态判断

综合判断当前仓库为：

- **部分脚手架化（partially scaffolded）**：是。
- **已经有大量内容（populated）**：是，但多数内容位于 `raw_motheds/` 参考区。
- **新架构已实现**：否。
- **可以直接运行的 TE-only CCDS 管线**：否。

## 3. File Inventory by Category

### 3.1 计数概览

基于只读扫描结果：

- 总文件数：`688`
- 总目录数：`204`
- 符号链接：`0`
- Python 文件：`18`
- R 文件：`3`
- Shell 文件：`6`
- Notebook：`1`
- YAML/YML：`11`
- Markdown/README：`10`

注意：

- 这些统计包含 `raw_motheds/` 中参考仓库与运行残留。
- 若只计“当前新项目自身”，真实代码量非常少。

### 3.2 Code

#### 当前项目代码（多为模板）

- `te_analysis/__init__.py`
- `te_analysis/config.py`
- `te_analysis/dataset.py`
- `te_analysis/code_scffold.py`
- `te_analysis/plots.py`
- `te_analysis/modeling/__init__.py`
- `te_analysis/modeling/train.py`
- `te_analysis/modeling/predict.py`

#### 历史 Python 代码

- `raw_motheds/snakescale/scripts/download_reference.py`
- `raw_motheds/snakescale/scripts/generate_yaml.py`
- `raw_motheds/snakescale/scripts/generate_yaml_unitmetadata.py`
- `raw_motheds/snakescale/scripts/guess_adapters.py`
- `raw_motheds/TE_model/src/Fasta.py`
- `raw_motheds/TE_model/src/ribo_counts_to_csv.py`
- `raw_motheds/TE_model/src/ribobase_counts_processing.py`
- `raw_motheds/TE_model/src/transpose_TE.py`
- `raw_motheds/TE_model/src/utils.py`
- `raw_motheds/TE_model/trials/PAX_hela/config.py`

#### 历史 R 代码

- `raw_motheds/TE_model/src/TE.R`
- `raw_motheds/TE_model/other_scr/benchmarking.R`
- `raw_motheds/TE_model/other_scr/prediction.R`

#### Workflow / DSL 代码

- `raw_motheds/snakescale/Snakefile`
- `raw_motheds/snakescale/Snakefile_unitmetadata`
- `raw_motheds/riboflow/RiboFlow.groovy`
- `raw_motheds/riboflow/nextflow.config`

### 3.3 Configs

- `pyproject.toml`
- `pixi.toml`
- `.env`
- `raw_motheds/snakescale/config/config.yaml`
- `raw_motheds/snakescale/schemas/config.schema.yaml`
- `raw_motheds/snakescale/envs/environment.yaml`
- `raw_motheds/snakescale/project.yaml`
- `raw_motheds/snakescale/scripts/references.yaml`
- `raw_motheds/riboflow/environment.yaml`
- `raw_motheds/riboflow/project.yaml`
- `raw_motheds/riboflow/project_umi.yaml`
- `raw_motheds/riboflow/configs/*.config`
- `raw_motheds/TE_model/riboflow_scr/*.yaml`
- `raw_motheds/TE_model/trials/PAX_hela/config.py`（更像 trial 配置脚本）

### 3.4 Docs

- `README.md`
- `raw_motheds/snakescale/README.md`
- `raw_motheds/snakescale/docs/README.md`
- `raw_motheds/snakescale/docs/Snakefile.md`
- `raw_motheds/snakescale/db/README.md`
- `raw_motheds/riboflow/README.md`
- `raw_motheds/riboflow/FAQ.md`
- `raw_motheds/riboflow/CHANGELOG.md`
- `raw_motheds/TE_model/README.md`

### 3.5 Notebooks

- `notebooks/notebook_scaffold.ipynb`

### 3.6 Shell / Workflow

- `Makefile`
- `raw_motheds/TE_model/pipeline.bash`
- `raw_motheds/riboflow/docker/build.sh`
- `raw_motheds/riboflow/docker/deploy.sh`
- `raw_motheds/riboflow/docker/tag.sh`
- `raw_motheds/snakescale/riboflow/docker/build.sh`
- `raw_motheds/snakescale/riboflow/docker/deploy.sh`
- `raw_motheds/snakescale/riboflow/docker/tag.sh`
- `raw_motheds/snakescale/Snakefile`
- `raw_motheds/snakescale/Snakefile_unitmetadata`

### 3.7 Data / Results / Placeholders

#### 当前仓库占位目录

- `data/raw/`
- `data/interim/`
- `data/processed/`
- `data/external/`
- `models/.gitkeep`
- `reports/.gitkeep`
- `reports/figures/.gitkeep`

#### 历史参考数据与产物

- `raw_motheds/snakescale/db/db.sqlite3`
- `raw_motheds/snakescale/reference/*`
- `raw_motheds/TE_model/data/*`
- `raw_motheds/TE_model/trials/PAX_hela/*.csv`
- `raw_motheds/TE_model/trials/PAX_hela/*.rda`

### 3.8 Unknown / Suspicious / Non-project Artifacts

- `raw_motheds/TE_model/.DS_Store`
- `raw_motheds/TE_model/other_scr/.DS_Store`
- `raw_motheds/TE_model/trials/.DS_Store`
- `raw_motheds/TE_model/trials/PAX_hela/__pycache__/*`
- `raw_motheds/snakescale/.snakemake/*`
- 嵌套 git 目录：
  - `raw_motheds/riboflow/.git/`
  - `raw_motheds/snakescale/.git/`
  - `raw_motheds/TE_model/.git/`

## 4. Detailed File-by-File Review

以下聚焦“重要文件”，即会影响迁移判断的代码、配置和关键文档。

### 4.1 根仓库文件

#### `README.md`

- path: `README.md`
- type: Markdown
- role: CCDS 样板说明
- summary:
  - 说明项目目标为多物种 TE 分析。
  - 列出 CCDS 样板结构。
  - 但文档内容与当前仓库真实实现不一致。
- key functions/classes: 无
- inputs: 无
- outputs: 无
- dependencies: 无
- risks:
  - 文档暗示 `dataset.py`、`features.py`、`plots.py` 等是正式实现，但实际是模板。
  - 会误导后续开发者以为新架构已存在。
- recommendation: **split / rewrite later**

#### `pyproject.toml`

- path: `pyproject.toml`
- type: TOML
- role: Python 包元数据与 Ruff 配置
- summary:
  - 定义包名 `te_analysis`。
  - Python 版本约束 `~=3.12.0`。
  - Ruff 目标源码为 `te_analysis`。
- key functions/classes: 无
- inputs: 包构建/静态检查配置
- outputs: 构建与 lint 行为
- dependencies:
  - `flit_core`
  - `ruff`
- risks:
  - 只覆盖当前 `te_analysis`，不涵盖 `raw_motheds`。
  - 包描述很成熟，但实现尚未跟上。
- recommendation: **preserve**

#### `pixi.toml`

- path: `pixi.toml`
- type: TOML
- role: 当前项目环境定义
- summary:
  - 使用 `pixi`，符合你的工具偏好。
  - 仅包含模板级依赖：`loguru`、`ruff`、`tqdm`、`typer`、`python-dotenv`。
  - 不包含 TE 真实依赖，如 `pandas`、`polars`、`snakemake`、`ribopy`、R 依赖等。
- key functions/classes: 无
- inputs: 环境求解
- outputs: 开发环境
- dependencies: pixi/conda-forge
- risks:
  - 当前环境无法支撑真实 TE-only 管线。
- recommendation: **preserve as project base, extend later**

#### `Makefile`

- path: `Makefile`
- type: Makefile
- role: 开发辅助命令
- summary:
  - `requirements` 使用 `pixi install`。
  - `lint` / `format` 针对 Ruff。
  - `data` 目标运行 `te_analysis/dataset.py`。
- key entrypoints:
  - `make requirements`
  - `make lint`
  - `make format`
  - `make data`
- inputs: 项目源码/环境
- outputs: 代码检查、格式化、模板数据命令
- dependencies: `pixi`, `ruff`, `python`
- risks:
  - `make data` 指向模板脚本而非真实数据流程。
- recommendation: **wrap / refactor later**

#### `.env`

- path: `.env`
- type: environment file
- role: 本地环境变量来源
- summary:
  - 被 `te_analysis/config.py` 读取。
  - 本次审计未依赖其具体内容。
- risks:
  - 隐式配置来源，若无文档容易造成行为漂移。
- recommendation: **preserve but document explicitly**

### 4.2 当前 `te_analysis/` 包

#### `te_analysis/config.py`

- type: Python module
- role: 项目路径常量定义
- summary:
  - 读取 `.env`。
  - 计算 `PROJ_ROOT`，定义 `DATA_DIR`、`RAW_DATA_DIR`、`INTERIM_DATA_DIR`、`PROCESSED_DATA_DIR`、`EXTERNAL_DATA_DIR`、`MODELS_DIR`、`REPORTS_DIR`、`FIGURES_DIR`。
  - 配置 `loguru` + `tqdm` 日志兼容。
- key functions/classes:
  - 无函数；核心是模块级路径常量。
- inputs:
  - 当前文件路径
  - `.env`
- outputs:
  - 模块级路径对象
  - 导入时日志输出 `PROJ_ROOT path is ...`
- dependencies:
  - `pathlib`
  - `dotenv.load_dotenv`
  - `loguru`
  - 可选 `tqdm`
- risks:
  - 导入时产生日志副作用。
  - 仅适合作为项目基础设施，不代表 TE 领域逻辑。
- recommendation: **preserve as-is**

#### `te_analysis/dataset.py`

- type: Python CLI template
- role: 样板数据处理入口
- summary:
  - Typer 命令 `main()`。
  - 默认输入 `data/raw/dataset.csv`，输出 `data/processed/dataset.csv`。
  - 仅打印日志与进度条，无真实业务逻辑。
- key functions/classes:
  - `main(input_path, output_path)`
- inputs:
  - `dataset.csv` 模板路径
- outputs:
  - 实际无文件写出
- dependencies:
  - `typer`, `loguru`, `tqdm`
- risks:
  - 容易被误认成真实 ETL 入口。
- classification: **debug/template logic**
- recommendation: **archive or replace**

#### `te_analysis/code_scffold.py`

- type: Python CLI template
- role: 特征生成模板
- summary:
  - 命名拼写有误：`scffold`。
  - 逻辑完全是模板占位。
- key functions/classes:
  - `main(input_path, output_path)`
- risks:
  - 命名错误本身就是维护信号。
  - 不是未来 TE-only 结构中应保留的真实模块。
- classification: **template/dead placeholder**
- recommendation: **discard / replace**

#### `te_analysis/modeling/train.py`

- type: Python CLI template
- role: 建模训练模板
- summary:
  - 针对机器学习训练的样板，而非 TE-only 管线需求。
- key functions/classes:
  - `main(features_path, labels_path, model_path)`
- outputs: 实际无产出
- risks:
  - 误导项目方向，和当前“非性能优化、非建模”为主的目标不一致。
- classification: **template/dead placeholder**
- recommendation: **archive/discard**

#### `te_analysis/modeling/predict.py`

- type: Python CLI template
- role: 推理模板
- summary: 与 TE-only 核心目标无关。
- key functions/classes:
  - `main(features_path, model_path, predictions_path)`
- recommendation: **archive/discard**

#### `te_analysis/plots.py`

- type: Python CLI template
- role: 绘图模板
- summary:
  - 当前任务明确“不做可视化”，此模块不是当前优先级。
- key functions/classes:
  - `main(input_path, output_path)`
- recommendation: **archive/discard for current refactor scope**

#### `te_analysis/__init__.py` 与 `te_analysis/modeling/__init__.py`

- type: package marker
- role: 包初始化
- summary: 无业务逻辑。
- recommendation: **preserve**

### 4.3 Notebook

#### `notebooks/notebook_scaffold.ipynb`

- type: Jupyter notebook scaffold
- role: 通用分析模板
- summary:
  - 包含标题、环境、配置、步骤模板和结果查看单元。
  - 代码中引用的包名是 `spider_silkome_module`，并非当前项目 `te_analysis`。
  - 说明它是从其他项目沿用的脚手架，尚未清理。
- key sections:
  - Environment Setup
  - Configuration
  - Custom Functions
  - Step 1 / Step 2
  - Results
- inputs/outputs:
  - 模板式 `input_dir`、`output_dir`、`step*_output`
- dependencies:
  - `polars`
  - 外部模块 `spider_silkome_module`
- risks:
  - 明显与当前仓库不一致。
  - 若继续存在，应被视为“外来模板残留”。
- recommendation: **archive or fully rewrite**

### 4.4 `raw_motheds/snakescale/`

#### `raw_motheds/snakescale/README.md`

- type: Markdown
- role: SnakeScale 使用说明
- summary:
  - 描述其用途：批量自动化 RiboFlow 运行。
  - 依赖外部 `db-sqlite` 元数据仓库、reference 下载、conda 环境、Snakemake。
  - 假定工作目录名和目录布局固定。
- risks:
  - 强依赖旧工作流与外部人工准备步骤。
  - 文档说明的是独立历史仓库，而不是当前 CCDS 设计。
- recommendation: **reference only / preserve as historical documentation**

#### `raw_motheds/snakescale/docs/Snakefile.md`

- type: Markdown
- role: Snakefile 结构和目录约定说明
- summary:
  - 非常有用，明确写出 SnakeScale 假定的目录结构：`input/project`、`input/fastq`、`modified_project`、`modifications`、`intermediates`、`output`。
  - 能帮助识别历史输入输出契约。
- recommendation: **preserve as reference**

#### `raw_motheds/snakescale/config/config.yaml`

- type: YAML
- role: Snakemake 顶层配置
- summary:
  - 定义 `studies`、`override`、`riboflow_config`、adapter 识别参数、线程数。
- inputs:
  - GEO studies 列表，如 `GSE139910`、`GSE37744_dedup`
- outputs:
  - 驱动 Snakefile 的规则展开
- dependencies:
  - `Snakefile`
  - `schemas/config.schema.yaml`
- risks:
  - 将“研究清单、运行模式、线程参数、adapter 猜测参数”混在一个配置中。
  - `study` 命名通过 `_dedup` 约定编码业务语义。
- recommendation: **wrap then split**

#### `raw_motheds/snakescale/Snakefile`

- type: Snakemake workflow
- role: 历史上游编排器
- summary:
  - 在文件顶层就执行 YAML 生成逻辑。
  - 从 sqlite 元数据生成 study YAML。
  - 下载 fastq、gzip、检查 adapter、检查长度、猜测 adapter、修改 YAML、按可运行性分类 study、最后调用 Nextflow RiboFlow。
- key helper functions:
  - `generate_download_parameters(gsm_dict)`
  - `get_fastq_paths(wildcards)`
  - `get_srr_dict(wildcards)`
  - `get_rnaseq_srr_dict(wildcards)`
  - `get_rnaseq_srr_path(wildcards)`
  - `get_riboseq_srr_dict(wildcards)`
  - `get_riboseq_srr_path(wildcards)`
  - `get_ribo_yaml(wildcards)`
  - `get_cutadapt_summaries(wildcards)`
  - `get_fastq_files(wildcards)`
  - `get_fastq_path(wildcards)`
- key rules:
  - `all`
  - `download_fastq_files`
  - `gzip_fastq`
  - `check_adapter`
  - `check_adapter_stats`
  - `check_lengths`
  - `modify_yaml`
  - `guess_adapter`
  - `classify_studies`
  - `run_riboflow`
- inputs:
  - `config/config.yaml`
  - `project.yaml` 模板
  - `db/db.sqlite3`
  - `scripts/references.yaml`
  - downloaded fastq
- outputs:
  - `input/project/<GSE>/<study>.yaml`
  - `input/modified_project/<study>/<study>_modified.yaml`
  - `modifications/<study>/modification.yaml`
  - `adapter_check_output/*`
  - `log/status.txt`
  - `log/valid_studies.txt`
  - `log/failed/*`
  - `log/success/*`
  - `log/riboflow_status/<study>/riboflow_status.txt`
- side effects:
  - 创建大量目录
  - 调用 `prefetch`, `fasterq-dump`, `gzip`, `cutadapt`, `nextflow`
  - 在顶层运行时即写 `yaml_status.txt`
- dependencies:
  - `snakemake`
  - `pandas`, `yaml`, `Bio.SeqIO`, `gzip`
  - `generate_yaml.py`, `guess_adapters.py`
  - `nextflow`, SRA tools, cutadapt
- risks:
  - **God workflow**：元数据生成、下载、质控、修订配置、分类、执行下游全部混在同一 Snakefile。
  - **大量硬编码相对路径**：`db/db.sqlite3`、`input/project/...`、`input/fastq/...`、`reference/...`。
  - **全局执行副作用**：导入 Snakefile 时就生成 yaml 并写日志。
  - **命名约定即业务逻辑**：study 名中 `_dedup` 表示运行模式。
  - **规则与 Python helper 强耦合**，不利于迁移成清晰模块。
  - `get_fastq_paths()` 的 open 路径疑似缺少 `.yaml` 后缀，是潜在 bug 信号。
  - 文件中混用 Ribo/RNA 逻辑、adapter 逻辑、length 逻辑和最终判定逻辑，职责过宽。
- classification: **production-like historical orchestration, but unmaintainably mixed**
- recommendation: **split and wrap; do not preserve as-is inside new CCDS core**

#### `raw_motheds/snakescale/scripts/generate_yaml.py`

- type: Python CLI / library-like script
- role: 从 RiboBase sqlite 生成 RiboFlow 参数 YAML
- summary:
  - 查询 `metadata_study`、`metadata_experiment`、`metadata_srr`。
  - 基于 template `project.yaml` 生成单个或多个 study 的 RiboFlow YAML。
  - 负责匹配 Ribo-Seq 与 RNA-Seq，组装 fastq 路径，设置 clip 参数、reference 路径、dedup 标志。
- key functions:
  - `generate_clip_sequence(clipping_param_base, experiment_dict, experiment_type)`
  - `generate_yaml(study, template, output, db, download_path, reference_file, reference_folder)`
  - `get_parameters()`
  - `main()`
- inputs:
  - sqlite DB
  - study 或 study list
  - template YAML
  - reference mapping YAML
- outputs:
  - `input/project/<GSE>/<study>.yaml`
- dependencies:
  - `sqlite3`, `pandas`, `yaml`, `numpy`, `os`
- risks:
  - 既做 DB 查询、配对解析、reference 决策，又做文件系统路径拼装和 YAML 输出。
  - 假定 sqlite schema 固定。
  - 假定 study 只能有一个 organism。
  - 用 study 名后缀编码 `dedup/test`。
- classification: **bridge/orchestration helper with reusable core ideas**
- recommendation: **wrap and split into metadata contract + pairing + yaml rendering modules**

#### `raw_motheds/snakescale/scripts/generate_yaml_unitmetadata.py`

- type: Python script
- role: `generate_yaml.py` 的变体
- summary:
  - 结构与 `generate_yaml.py` 高度近似，说明存在重复逻辑分叉。
- risks:
  - 明显 duplication。
- recommendation: **archive after extracting shared logic**

#### `raw_motheds/snakescale/scripts/guess_adapters.py`

- type: Python CLI / utility
- role: 从 fastq 样本中猜测 adapter
- summary:
  - 自定义 `FastqEntry` / `FastqFile`。
  - 读取 reads，计数 kmers，确定 anchor sequence，扩展生成 adapter 猜测。
  - 包含多个 CLI 参数。
- key functions/classes（从审阅到的部分可确认）:
  - `FastqEntry`
  - `FastqFile`
  - `convert_int_to_kmer`
  - `generate_kmers`
  - `get_reads`
  - `count_all_kmers`
  - `determine_anchor_sequence`
  - 以及 `get_parameters()`, `main()`
- inputs:
  - FASTQ / FASTQ.GZ
  - skip/sample/kmer 阈值参数
- outputs:
  - 终端输出/返回 guessed adapter
- dependencies:
  - `gzip`, `numpy`, `subprocess`, `argparse`
- risks:
  - 算法脚本较长，且与 Snakefile 强耦合。
  - 自定义 FASTQ reader，维护成本高。
- classification: **utility logic, potentially wrappable**
- recommendation: **wrap if adapter guessing remains in scope; otherwise archive**

#### `raw_motheds/snakescale/scripts/download_reference.py`

- type: Python CLI utility
- role: 下载并整理 reference tarballs
- summary:
  - 根据 YAML 下载 tar.gz，解压并把 `filter/`、`transcriptome/` 移入目标目录。
- key functions:
  - `_download_references(ref_dict, target_folder)`
  - `download_reference(reference_yaml, target_folder)`
  - `get_parameters()`
  - `main()`
- inputs:
  - references YAML
  - target folder
- outputs:
  - 本地 reference 目录结构
- side effects:
  - 调用 `curl`, `tar`, `shutil.move`, `rmtree`
- dependencies:
  - `subprocess`, `yaml`, `glob`, `shutil`
- risks:
  - 依赖网络和外部命令；不适合直接纳入只读/可复现实验分析核心。
- classification: **environment/bootstrap utility**
- recommendation: **wrap outside core TE pipeline**

### 4.5 `raw_motheds/riboflow/`

#### `raw_motheds/riboflow/README.md`

- type: Markdown
- role: RiboFlow 使用文档
- summary:
  - 描述 Nextflow pipeline，把原始数据处理成 `.ribo` 和 `stats.csv`。
  - 明确 `.ribo` 是关键中间产物。
- value for migration:
  - 定义上游边界很重要：TE-only 新仓库未必需要重写 RiboFlow，只需明确如何接收其输出。
- recommendation: **preserve as upstream reference**

#### `raw_motheds/riboflow/nextflow.config`

- type: Nextflow config
- role: RiboFlow profile 与日志配置
- summary:
  - 定义 `standard`、`stampede_local`、`docker_local`、`singularity_cluster` profiles。
  - 输出 timeline/trace/report 到 `nextflow_logs/`。
- risks:
  - 明显是独立上游项目配置，不应直接塞进新 CCDS 核心包。
- recommendation: **reference only**

#### `raw_motheds/riboflow/project.yaml`

- type: YAML template
- role: RiboFlow 参数样例
- summary:
  - 定义 clip、mapping、reference、input fastq、metadata、rnaseq 等结构。
  - 是理解历史输入契约的关键文件。
- role in new architecture:
  - 应视为**上游接口契约参考**，而非新项目内部业务配置的最终形态。
- risks:
  - 契约过重，包含过多上游运行细节。
- recommendation: **wrap as upstream contract reference**

#### `raw_motheds/riboflow/RiboFlow.groovy`

- type: Nextflow pipeline DSL
- role: 上游原始数据处理器
- summary:
  - 文件很大（约 77 KB），本次未逐段精读其全部 process 实现。
  - 从 README 和配置可确定其职责是把测序与参考文件处理成 `.ribo` 及统计输出。
- judgment:
  - 对当前 TE-only CCDS 项目，应被视为**外部上游依赖/参考实现**。
- recommendation: **do not rewrite inside current repo now; integrate by contract**

### 4.6 `raw_motheds/TE_model/`

#### `raw_motheds/TE_model/README.md`

- type: Markdown
- role: 旧 TE 计算仓库说明
- summary:
  - 明确指出主流程：
    1. `.ribo` flatten 到 raw CSV
    2. `ribobase_counts_processing.py` 做处理
    3. `TE.R` 做 TE
    4. `transpose_TE.py` 做整理
  - 提到 `src/ribo_counts_to_csv.py` 是 winsorization 主入口。
- risks:
  - 流程以 trial 目录驱动，不是模块化生产设计。
- recommendation: **preserve as migration map**

#### `raw_motheds/TE_model/pipeline.bash`

- type: Bash pipeline driver
- role: 旧 TE pipeline 总控脚本
- summary:
  - 通过 `-t` 指定 `trials/<name>`。
  - stage 0: 运行 `python -m trials.<pipeline_dir>.config`
  - stage 1: 运行 `src/ribobase_counts_processing.py`
  - stage 2: 运行 `Rscript src/TE.R`
  - stage 3: 运行 `src/transpose_TE.py`
- inputs:
  - `trials/<name>/config.py`
  - `trials/<name>/ribo_raw.csv`
  - `trials/<name>/rnaseq_raw.csv`
- outputs:
  - 多个 processed CSV 与 TE 结果
- side effects:
  - 直接在 trial 目录写文件
- risks:
  - **God script**：串起所有阶段，但没有稳定契约或错误恢复机制。
  - stage 编号约定式运行；缺少显式 manifest。
- classification: **historical orchestration script**
- recommendation: **split into explicit CCDS stages; archive original**

#### `raw_motheds/TE_model/src/ribo_counts_to_csv.py`

- type: Python module/script
- role: 从 `.ribo` 提取 Ribo/RNA counts；支持 winsorization 回调
- summary:
  - 核心桥接模块之一。
  - 读取 `./data/ribo/<study>[_dedup]/ribo/experiments/<experiment>.ribo`。
  - 用 `ribopy` 获取 CDS count 或 coverage。
  - 若提供 `process_coverage_fn`，则对 coverage 逐基因处理后汇总，支持 winsorization/capping。
  - 同时读取 RNA-seq counts。
  - 聚合所有 experiment 并输出 `ribo_raw.csv` 与 `rnaseq_raw.csv`。
- key functions:
  - `get_coverage_from_experiment(...)`
  - `worker(...)`
  - `main(workdir, sample_filter, ribo_dedup, rna_seq_dedup, process_coverage_fn=None, filter=None, custom_experiment_list=None, rnaseq_fn=None)`
- inputs:
  - `data/paxdb_filtered_sample.csv`
  - `./data/ribo/*/ribo/experiments/*.ribo`
  - trial config 回调函数
- outputs:
  - `<workdir>/rnaseq_raw.csv`
  - `<workdir>/ribo_raw.csv`
- dependencies:
  - `ribopy`, `pandas`, `numpy`, `glob`, `concurrent.futures`
  - `src.utils.intevl`
- side effects:
  - 并发读取 `.ribo`
  - 直接写 CSV
- risks:
  - **路径硬编码严重**：假定 `./data/ribo/...`、`data/paxdb_filtered_sample.csv`。
  - **命名语义隐式**：study 目录名中 `_dedup`。
  - **Ribo 与 RNA 提取强耦合**。
  - **sample_filter/process_coverage_fn/filter/rnaseq_fn** 采用“传函数”的 trial 风格，灵活但缺少显式契约。
  - `NUM_WORKERS = 48` 硬编码。
- classification: **production-relevant bridge logic**
- recommendation: **wrap and split; high-value migration source**

#### `raw_motheds/TE_model/src/utils.py`

- type: Python utility module
- role: `.ribo` 长度窗口推断、CDS 边界查找、outlier capping、bias correction
- summary:
  - `intevl()` 根据 length distribution 选取 usable read length 区间。
  - `get_cds_range_lookup()` 生成 gene -> region boundary 映射。
  - `cap_outliers()` / `cap_outliers_cds_only()` 提供 winsorization/capping 原语。
  - `BiasCorrection` 提供更复杂的 footprint / n-mer 偏差处理。
- key functions/classes:
  - `intevl(ribo_object, experiment_id)`
  - `get_cds_range_lookup(ribo)`
  - `cap_outliers(arr, thresh, filter_zeros=True, cap_min=0)`
  - `cap_outliers_cds_only(arr, gene, boundary_lookup, thresh=99, filter_zeros=False)`
  - `BiasCorrection`
- inputs:
  - ribopy 对象
  - fasta 文件 `data/appris_human_v2_selected.fa.gz`
- outputs:
  - 区间、lookup、capped arrays、footprint dataframe
- dependencies:
  - `ribopy`
  - `pandas`, `numpy`, `itertools`
  - `src.Fasta.FastaFile`
- risks:
  - **隐藏物种假设**：`data/appris_human_v2_selected.fa.gz` 写死为 human。
  - **隐藏参考 build 假设**：使用特定 appris human alias。
  - `BiasCorrection` 将序列文件、alias、experiment 全部捆绑在类中。
- classification: **high-value utility logic, but assumptions-heavy**
- recommendation: **split and preserve selected functions**

#### `raw_motheds/TE_model/src/Fasta.py`

- type: Python utility
- role: FASTA 读取与 `FastaEntry` 表示
- summary:
  - 提供 `FastaEntry` 和 `FastaFile`。
- key functions/classes:
  - `FastaEntry`
  - `FastaFile`
- risks:
  - 通用性尚可，但是自定义 reader，且异常处理有粗糙之处。
- classification: **utility logic**
- recommendation: **wrap if needed; otherwise replace with mature parser later**

#### `raw_motheds/TE_model/src/ribobase_counts_processing.py`

- type: Python script
- role: raw count 表处理、CPM/quantile normalization、dummy gene 聚合、paired/ribo-only 输出
- summary:
  - 用 `OptionParser` 在模块顶层解析 CLI 参数。
  - `data_process()`：读 CSV、按 gene 聚合、计算 CPM 与 quantile normalized 表。
  - `dummy_gene_df()`：按 CPM cutoff + overall cutoff 判定低表达基因。
  - `combine_dummy_gene()`：把被过滤的基因汇总为 `dummy_gene`。
  - paired 模式再读取 `./data/nonpolyA_gene.csv` 去除 non-polyA。
- key functions:
  - `quantile_normalize(df)`
  - `CPM_normalize(df)`
  - `data_process(df)`
  - `dummy_gene_df(df, cpm_cutoff=1, overall_cutoff=70)`
  - `combine_dummy_gene(dummy_gene, df)`
  - `count_ranking_pearson(df)`
- inputs:
  - ribo raw CSV
  - RNA raw CSV（paired 模式）
  - `./data/nonpolyA_gene.csv`
- outputs:
  - `ribo_only_*`
  - `ribo_paired_*`
  - `rna_paired_*`
- dependencies:
  - `bioinfokit`
  - `numpy`, `pandas`
- risks:
  - **脚本即模块**：导入时就解析 CLI。
  - **路径硬编码**：`./data/nonpolyA_gene.csv`。
  - **paired 与 ribo-only 分支混在顶层执行块**。
  - **过滤逻辑与 IO 混杂**。
- classification: **core bridge/winsorization-prep logic with maintainability issues**
- recommendation: **split into pure functions + CLI wrapper**

#### `raw_motheds/TE_model/src/TE.R`

- type: R script
- role: CLR/ILR-based TE 计算
- summary:
  - 读取 `ribo_paired_count_dummy.csv` 与 `rna_paired_count_dummy.csv`。
  - 转置后用 `propr(..., ivar = "clr")` 获得 CLR logratio，再 `clr2ilr`。
  - 对每个 ILR 维度做线性回归，取残差后 `ilr2clr`，构成 TE。
  - 结果保存 `human_TE_sample_level.rda`，并基于 `data/infor_filter.csv` 聚合 cell line 平均，输出 `human_TE_cellline_all.csv`。
- key functions:
  - `TE_clr(RIBO, RNA)`
- inputs:
  - `<workdir>/ribo_paired_count_dummy.csv`
  - `<workdir>/rna_paired_count_dummy.csv`
  - `data/infor_filter.csv`
- outputs:
  - `<workdir>/human_TE_sample_level.rda`
  - `<workdir>/human_TE_cellline_all.csv`
- dependencies:
  - `propr`, `compositions`, `tidyverse`, `foreach`, `doParallel`
- risks:
  - **物种写死为 human**。
  - **依赖外部 infor_filter.csv 隐式元数据**。
  - **输入文件名固定写死**。
  - **并行设置固定 cluster size = 1**，看起来并非真正优化后的实现。
- classification: **core TE calculation logic**
- recommendation: **preserve algorithm, wrap/rewrite interface**

#### `raw_motheds/TE_model/trials/PAX_hela/config.py`

- type: Python trial config script
- role: 具体试验配置，定义 winsorization 策略并直接执行
- summary:
  - 设置 `workdir`、`sample_filter`、`ribo_dedup`、`rna_seq_dedup`。
  - 提供 `process_coverage_fn()`，对 CDS-only coverage 做 `99.5` percentile capping 后求和。
  - 末尾直接调用 `main(...)`。
- key functions:
  - `process_coverage_fn(coverage, gene, ribo)`
- risks:
  - 以 trial 文件承载业务配置和执行入口，难复用、难测试。
- classification: **debug/experimental logic**
- recommendation: **archive after extracting configuration semantics**

## 5. Current Pipeline Responsibility Map

### 5.1 角色映射表

#### metadata / input contract

- `raw_motheds/snakescale/scripts/generate_yaml.py`
  - 从 sqlite 拉 study / experiment / SRR 元数据。
- `raw_motheds/snakescale/db/db.sqlite3`
  - 历史元数据来源。
- `raw_motheds/riboflow/project.yaml`
  - 上游输入结构模板。
- `raw_motheds/snakescale/project.yaml`
  - SnakeScale 用于渲染的模板。

状态：**Present but mixed/unclear**

原因：

- 元数据契约藏在 sqlite schema、模板 YAML、Python 字段名、文件路径拼装逻辑里，没有独立明示层。

#### workflow orchestration

- `raw_motheds/snakescale/Snakefile`
- `raw_motheds/TE_model/pipeline.bash`
- `raw_motheds/riboflow/RiboFlow.groovy`
- `raw_motheds/riboflow/nextflow.config`

状态：**Present but heavily fragmented**

#### SnakeScale / RiboFlow integration

- `raw_motheds/snakescale/Snakefile`
- `raw_motheds/snakescale/scripts/generate_yaml.py`
- `raw_motheds/riboflow/project.yaml`
- `raw_motheds/riboflow/RiboFlow.groovy`

状态：**Present**

#### pairing

- `raw_motheds/snakescale/scripts/generate_yaml.py`
  - 通过 `matched_experiment_id` 将 Ribo-Seq 对到 RNA-Seq。
- `raw_motheds/riboflow/project.yaml`
  - 结构要求 RNA keys 匹配 ribo experiment keys。

状态：**Present but embedded in metadata generation**

#### extraction

- `raw_motheds/TE_model/src/ribo_counts_to_csv.py`

状态：**Present**

#### winsorization

- `raw_motheds/TE_model/src/utils.py`
  - `cap_outliers`, `cap_outliers_cds_only`
- `raw_motheds/TE_model/trials/PAX_hela/config.py`
  - 用 trial-specific `process_coverage_fn()` 激活 winsorization
- `raw_motheds/TE_model/src/ribo_counts_to_csv.py`
  - 接受 `process_coverage_fn`

状态：**Present but mixed/implicit**

#### TE calculation

- `raw_motheds/TE_model/src/TE.R`

状态：**Present**

#### QC

- 上游测序与 adapter/length QC：
  - `raw_motheds/snakescale/Snakefile`
  - `check_adapter`, `check_adapter_stats`, `check_lengths`, `guess_adapter`, `classify_studies`
- 下游表达过滤：
  - `raw_motheds/TE_model/src/ribobase_counts_processing.py`

状态：**Present but split across unrelated layers**

#### output packaging

- `raw_motheds/TE_model/src/transpose_TE.py`（虽未深读，但从 pipeline.bash 可确认其承担结果整理）
- `raw_motheds/TE_model/src/TE.R` 输出 sample-level 和 cell-line-level结果

状态：**Present but incomplete/legacy-specific**

### 5.2 当前缺失层

以下层在当前新 CCDS 仓库中缺失为清晰、可维护实现：

- metadata normalization / explicit schema layer：**Missing**
- sample pairing contract layer：**Missing as standalone module**
- SnakeScale orchestration in CCDS form：**Missing**
- RiboFlow execution wrapper in current package：**Missing**
- count extraction module in current package：**Missing**
- winsorization module in current package：**Missing**
- TE calculation wrapper in current package：**Missing**
- QC report module in current package：**Missing**
- final result packaging module in current package：**Missing**
- project configuration management for TE-only pipeline：**Missing**
- reproducible CLI entrypoints for the actual TE workflow：**Missing**

### 5.3 职责混杂最严重的位置

- `raw_motheds/snakescale/Snakefile`
  - metadata generation
  - download
  - adapter QC
  - length QC
  - adapter guess
  - YAML rewrite
  - study classification
  - RiboFlow execution

- `raw_motheds/snakescale/scripts/generate_yaml.py`
  - DB access
  - experiment pairing
  - adapter inference seed assembly
  - reference selection
  - fastq path rendering
  - YAML output

- `raw_motheds/TE_model/src/ribobase_counts_processing.py`
  - CLI parsing
  - normalization
  - filtering
  - IO writing
  - mode dispatch

- `raw_motheds/TE_model/pipeline.bash`
  - 全流程串联但没有模块边界

## 6. Architectural Smells and Historical Failure Modes

可见的历史维护问题如下。

### 6.1 God scripts / God workflows

- `raw_motheds/snakescale/Snakefile` 是典型 god workflow。
- `raw_motheds/TE_model/pipeline.bash` 是典型 god shell driver。
- `raw_motheds/snakescale/scripts/generate_yaml.py` 承担过多职责。

### 6.2 duplicated logic

- `generate_yaml.py` 与 `generate_yaml_unitmetadata.py` 高度重复。
- `snakescale/` 下嵌有 `riboflow/` 副本，同时 `raw_motheds/riboflow/` 也存在独立副本。
- 模板和 trial 方式导致多个近似分支很容易继续扩散。

### 6.3 hidden assumptions

- study 名后缀 `_dedup` / `_test` 编码运行模式。
- `matched_experiment_id` 假定 sqlite 关系完整。
- `TE.R` 假定 human 数据、`data/infor_filter.csv` 存在且字段匹配。
- `utils.py` 假定 human appris fasta 与 alias。
- `ribo_counts_to_csv.py` 假定 `.ribo` 文件目录结构固定。
- `ribobase_counts_processing.py` 假定 `nonpolyA_gene.csv` 在固定相对路径。

### 6.4 hard-coded paths

明显实例：

- `db/db.sqlite3`
- `input/project/...`
- `input/fastq/...`
- `reference/...`
- `./data/ribo/...`
- `data/paxdb_filtered_sample.csv`
- `./data/nonpolyA_gene.csv`
- `data/appris_human_v2_selected.fa.gz`
- `data/infor_filter.csv`

### 6.5 fragile IO contracts

- 文件命名承载业务状态，例如：
  - `<study>_modified.yaml`
  - `ribo_paired_count_dummy.csv`
  - `rna_paired_quantile_dummy_70.csv`
- 输入输出缺少 schema 校验；大多依赖“这个文件名应该存在”。
- shell/脚本多处直接写当前目录或相对目录，迁移到 CCDS 后极易失效。

### 6.6 undocumented conventions

- trial 命名规则 `PAX_*`
- paired 过滤基因的具体统计口径
- `dummy_gene` 聚合含义
- dedup 与 winsorization 的业务关系
- TE 结果样本级与 cell-line 级输出的应用边界

### 6.7 repository hygiene issues

- 嵌套 `.git/` 仓库
- `.snakemake/` 运行残留
- `.DS_Store` 和 `__pycache__`
- 参考数据与代码混在同一主仓库

## 7. Input/Output Contract Problems

### 7.1 命名问题

- `code_scffold.py` 拼写错误。
- `raw_motheds` 目录名本身拼写异常，容易长期传播错误认知。
- `ribo_dedup` / `rna_seq_dedup` 的布尔含义需要读代码才能理解。
- `dummy_gene` 实际表示“被低表达过滤后合并到 others 的组”，命名不够清晰。

### 7.2 路径问题

- 多数历史逻辑依赖相对路径和固定 cwd。
- 根仓库是 CCDS 结构，但历史代码期望在各自子仓库根目录执行。
- `raw_motheds/snakescale/README.md` 甚至要求工作目录名必须是 `SnakeScale`。

### 7.3 schema ambiguity

- metadata contract 由 sqlite schema + YAML 模板 + Python 代码共同定义，没有单一权威 schema。
- pairing 关系来源于 `matched_experiment_id`，但没有单独的 pairing table contract。
- TE 输入 count table 的行列语义、物种范围、gene alias 规则没有独立规范文档。

### 7.4 hidden assumptions in biological inputs

- organism / genome build / annotation version 没有显式统一声明层。
- `appris_human_v2`、`human`、`apris_human_alias` 等概念散落在不同代码里。
- `nonpolyA_gene.csv`、`infor_filter.csv` 的来源、版本和适用物种未统一记录。
- 对 sample metadata 的完整性缺乏验证。

### 7.5 likely causes of historical maintainability collapse

综合推断，旧流程变得难维护的主要原因是：

- 上游编排、元数据解析、下载、QC、下游统计全部紧耦合。
- 输入契约缺失，靠命名约定和相对路径维持。
- 试验性 trial 配置逐渐演变成事实上的正式接口。
- 代码复用通过“复制脚本改一份”而不是抽象稳定模块实现。
- 参考项目与实际项目边界不清，导致仓库污染与职责模糊。

## 8. Gap Analysis for the New TE-only CCDS Pipeline

以下判断以“新的 TE-only CCDS 仓库应该具备清晰模块和接口”为标准。

### 8.1 metadata layer

状态：**Missing**

缺失内容：

- 输入元数据 schema
- sample table schema
- study / experiment / run / pairing 显式模型
- organism/reference version 显式声明
- metadata validation CLI

### 8.2 orchestration layer

状态：**Missing**

缺失内容：

- 在 CCDS 结构下可复用的 workflow wrapper
- 明确区分 upstream execution 与 downstream TE computation 的阶段化命令
- 当前项目自己的 CLI 入口

### 8.3 bridge layer

状态：**Missing in current package; logic exists only in legacy code**

所需职责：

- `.ribo` / 中间产物读取
- experiment pairing
- count extraction
- sample-level alignment/merge
- raw matrix export

可参考来源：

- `raw_motheds/TE_model/src/ribo_counts_to_csv.py`
- `raw_motheds/snakescale/scripts/generate_yaml.py`

### 8.4 winsorization layer

状态：**Present only implicitly in legacy code**

所需职责：

- coverage capping 策略定义
- 策略参数化
- 基因/区域级 winsorization 函数
- 与 extraction 解耦

可参考来源：

- `raw_motheds/TE_model/src/utils.py`
- `raw_motheds/TE_model/trials/PAX_hela/config.py`

### 8.5 TE computation layer

状态：**Present only as legacy R script**

所需职责：

- 接受标准化输入矩阵
- 调用 CLR/ILR TE 算法
- 输出 sample-level 和 aggregated TE
- 保证输入/输出 schema 明确

可参考来源：

- `raw_motheds/TE_model/src/TE.R`

### 8.6 QC layer

状态：**Missing as dedicated downstream QC module**

已有零散实现：

- 上游 adapter/length 检查：`snakescale`
- expression filtering：`ribobase_counts_processing.py`

缺失内容：

- TE-only 下游 QC 摘要
- 样本配对完整性 QC
- 提取成功率/缺失率 QC
- winsorization 前后摘要统计

### 8.7 output packaging layer

状态：**Present but unclear / legacy-specific**

已有零散实现：

- `TE.R` 输出 `.rda` 与 CSV
- `transpose_TE.py` 做表转置/整理

缺失内容：

- 项目级 canonical outputs 定义
- 统一命名规范
- metadata-linked result manifest

### 8.8 configuration management

状态：**Missing**

缺失内容：

- 新项目自己的配置目录与层级
- TE-only YAML/TOML 配置样例
- 参数默认值与生物学前提说明

### 8.9 reproducible CLI entrypoints

状态：**Missing**

当前 `te_analysis/*.py` 入口都是模板。

## 9. Migration Recommendations

### 9.1 keep as-is

这些内容可直接保留为基础设施或参考文档：

- `pyproject.toml`
- `pixi.toml`
- `te_analysis/config.py`
- `LICENSE`
- `Makefile` 的环境/格式化部分
- `raw_motheds/*/README.md` 作为历史说明资料

### 9.2 wrap without rewriting

这些部分包含高价值逻辑，但不应原样作为新架构核心：

- `raw_motheds/TE_model/src/TE.R`
  - 算法核心值得保留，接口需要重包。
- `raw_motheds/TE_model/src/ribo_counts_to_csv.py`
  - `.ribo` 到 raw matrix 的桥接逻辑值得保留。
- `raw_motheds/TE_model/src/utils.py`
  - `intevl`、`get_cds_range_lookup`、capping 原语值得保留。
- `raw_motheds/snakescale/scripts/generate_yaml.py`
  - metadata 提取和 pairing 逻辑有价值。
- `raw_motheds/snakescale/scripts/guess_adapters.py`
  - 如果未来仍需 adapter guess，可外包保留。

### 9.3 refactor later

这些内容不应先动，但后续需要拆分或改写：

- `raw_motheds/snakescale/Snakefile`
- `raw_motheds/TE_model/src/ribobase_counts_processing.py`
- `Makefile` 中 `data` 目标
- 根 `README.md`

### 9.4 archive / remove from active architecture

这些内容不适合作为当前 TE-only CCDS 主干：

- `te_analysis/dataset.py`
- `te_analysis/code_scffold.py`
- `te_analysis/modeling/train.py`
- `te_analysis/modeling/predict.py`
- `te_analysis/plots.py`
- `notebooks/notebook_scaffold.ipynb`
- `raw_motheds/TE_model/trials/*` 作为 active interface
- `raw_motheds/TE_model/other_scr/*`（与当前目标无关）
- `raw_motheds/snakescale/.snakemake/`
- 嵌套 `.git/` 与 `.DS_Store` 等历史残留

### 9.5 create from scratch now

以下模块是新 CCDS TE-only 管线最先需要建立的：

- metadata contract / schema
- sample pairing contract
- upstream artifact manifest
- `.ribo` extraction module
- winsorization module
- matrix normalization / filtering module
- TE computation wrapper
- QC summary module
- packaging/export module
- project CLI entrypoints

## 10. Minimum Required Module Blueprint

以下是新仓库最小必要模块蓝图。这里描述“应该有的文件/模块”，不代表当前已存在。

### 10.1 Package layout

建议至少包含：

- `te_analysis/config.py`
  - 路径与全局配置基础设施
- `te_analysis/cli.py`
  - 统一 CLI 入口
- `te_analysis/metadata.py`
  - study / sample / run metadata 读取、校验、标准化
- `te_analysis/pairing.py`
  - ribo/rna pairing contract 与验证
- `te_analysis/upstream_contract.py`
  - 上游 `.ribo`、RiboFlow 输出 manifest 定义
- `te_analysis/extract.py`
  - 从 `.ribo` 提取 counts/coverage
- `te_analysis/winsorize.py`
  - capping/winsorization 策略实现
- `te_analysis/filtering.py`
  - CPM/quantile normalization、dummy gene / low-expression 过滤
- `te_analysis/te_compute.py`
  - TE 算法包装层（可能桥接到 R）
- `te_analysis/qc.py`
  - 样本、提取、过滤、winsorization、结果 QC 汇总
- `te_analysis/package_results.py`
  - 输出文件命名、清单与落盘

### 10.2 Config / docs layout

建议新增概念：

- `config/te_pipeline.yaml`
- `config/schemas/*.yaml` 或 `config/*.jsonschema`
- `references/README.md`
- `docs/input_contract.md`
- `docs/upstream_integration.md`
- `docs/output_contract.md`

### 10.3 Data contract layout

建议至少约定：

- `data/raw/metadata/*.csv|tsv`
- `data/external/upstream_manifest/*.csv|json`
- `data/interim/extracted/*.csv|parquet`
- `data/interim/qc/*.json|tsv`
- `data/processed/te/*.csv|parquet`

### 10.4 CLI stage blueprint

建议统一命令层，至少支持：

- `validate-metadata`
- `build-pairing`
- `extract-counts`
- `winsorize-counts`
- `filter-counts`
- `compute-te`
- `summarize-qc`
- `package-results`

## 11. Open Questions / Unknowns

以下问题仅靠当前仓库无法完全确定：

- 当前新仓库最终是否要：
  - 直接调用外部 RiboFlow，还是仅消费既有 `.ribo`。
- 新项目的权威 metadata 来源是否仍为 sqlite/RiboBase，还是会转为 CSV/TSV manifest。
- TE-only 管线是否仍要求支持多物种，还是当前阶段先限定 human。
- winsorization 是否必须保留 trial 风格的可插拔自定义函数，还是收敛为少数标准策略。
- `transpose_TE.py` 的具体输出契约未在本次深读中确认。
- `RiboFlow.groovy` 的内部 process 细节未逐段全面解析；本审计将其视作上游黑盒/参考实现。
- `Snakefile_unitmetadata` 与普通 `Snakefile` 的差异未逐段核对，但可判断其属于重复变体而非新架构主干。

## 12. Appendix

### 12.1 Command outputs summary

- 仓库根目录：`/home/xrx/my_projects/te_analysis`
- 顶层目录数：`10`
- 总文件数：`688`
- 总目录数：`204`
- 符号链接：`0`
- Python 文件：`18`
- R 文件：`3`
- Shell 文件：`6`
- Notebook：`1`
- YAML 文件：`11`

### 12.2 Function inventory summary

#### 当前项目模板入口

- `te_analysis/dataset.py::main`
- `te_analysis/code_scffold.py::main`
- `te_analysis/modeling/train.py::main`
- `te_analysis/modeling/predict.py::main`
- `te_analysis/plots.py::main`

#### SnakeScale 关键函数/规则

- `generate_download_parameters`
- `get_srr_dict`
- `get_rnaseq_srr_dict`
- `get_riboseq_srr_dict`
- `get_ribo_yaml`
- `download_fastq_files`
- `gzip_fastq`
- `check_adapter`
- `check_adapter_stats`
- `check_lengths`
- `guess_adapter`
- `modify_yaml`
- `classify_studies`
- `run_riboflow`

#### TE_model 关键函数

- `ribo_counts_to_csv.py`
  - `get_coverage_from_experiment`
  - `worker`
  - `main`
- `utils.py`
  - `intevl`
  - `get_cds_range_lookup`
  - `cap_outliers`
  - `cap_outliers_cds_only`
  - `BiasCorrection`
- `ribobase_counts_processing.py`
  - `quantile_normalize`
  - `CPM_normalize`
  - `data_process`
  - `dummy_gene_df`
  - `combine_dummy_gene`
  - `count_ranking_pearson`
- `TE.R`
  - `TE_clr`

### 12.3 Path anomalies

- `raw_motheds/` 目录名拼写异常。
- `te_analysis/code_scffold.py` 文件名拼写异常。
- `notebooks/notebook_scaffold.ipynb` 内部仍引用其他项目模块 `spider_silkome_module`。
- `raw_motheds/snakescale/Snakefile` 使用大量固定相对路径，对 cwd 非常敏感。
- `raw_motheds/TE_model` 多个脚本默认从自身仓库根目录执行，不适配当前 CCDS 根目录。

### 12.4 Symlink notes

- 本次扫描未发现符号链接：`0`

### 12.5 Nested repository notes

检测到嵌套 git 仓库：

- `./raw_motheds/riboflow/.git`
- `./raw_motheds/snakescale/.git`
- `./raw_motheds/TE_model/.git`

这表明 `raw_motheds/` 更像“参考仓库集合快照”，而非当前项目的内生模块。

### 12.6 Direct answers to the required audit questions

#### A. Repository reality check

1. 当前存在 CCDS 样板目录、模板 Python 包和 `raw_motheds` 历史参考代码集合。
2. `data/`、`docs/`、`models/`、`notebooks/`、`references/`、`reports/`、`te_analysis/` 已具 CCDS 外观。
3. 缺失清晰的 workflow、metadata contract、bridge、TE compute、QC、CLI 模块。
4. 仓库是**部分 scaffold + 大量历史参考内容**，不是空仓，也不是已完成新架构。

#### B. Code inventory

5. 代码文件已存在，但当前 `te_analysis/` 主要是模板，真实逻辑在 `raw_motheds`。
6. 各代码文件用途见第 4 节逐文件评审。
7. 关键函数/类/入口点见第 12.2 节。
8. 输入、输出、副作用、依赖已在第 4 节逐项总结。
9. 当前仓库同时存在 production-like 历史逻辑、utility 逻辑、debug/trial 逻辑和 dead/template 逻辑。

#### C. Pipeline responsibility mapping

10. 元数据/编排/RiboFlow 集成/配对/提取/winsorization/TE/QC/打包对应关系见第 5 节。
11. 当前新 CCDS 包中，大部分关键层实际上缺失。
12. 最严重职责混杂点是 `Snakefile`、`generate_yaml.py`、`ribobase_counts_processing.py` 和 `pipeline.bash`。

#### D. Historical risk detection

13. 可见 god scripts、重复逻辑、硬编码路径、隐藏 assumptions、fragile IO、约定驱动。
14. 已存在命名不一致、路径敏感、schema 不透明、物种/注释版本隐含问题。
15. 旧管线变得难维护的核心原因是：职责未分层、契约未显式化、试验代码演变成正式接口、仓库边界不清。

#### E. Refactor readiness

16. 可安全保留：`pyproject.toml`、`pixi.toml`、`te_analysis/config.py`、历史 README。
17. 应包装而非重写：`TE.R`、`ribo_counts_to_csv.py`、`utils.py` 部分函数、`generate_yaml.py` 的元数据/配对逻辑。
18. 应拆分/归档/丢弃：模板脚本、trial 入口、god shell/god workflow、重复变体、运行残留。
19. 新 TE-only CCDS 最小模块集见第 10 节。
20. 需要最先创建的缺失文件/模块包括：`cli.py`、`metadata.py`、`pairing.py`、`extract.py`、`winsorize.py`、`filtering.py`、`te_compute.py`、`qc.py`、`package_results.py` 以及相应配置/schema 文档。
