# te_analysis 当前状态交接文件（给 ChatGPT）

日期：2026-04-20  
主仓库分支：`design/v1-minimal`  
vendor/snakescale SHA：`b918e75f877262dca96665d18c3b472675f30a6d`

## 0. 这份文件的用途

这是一份给后续 ChatGPT / Codex / 其他代理继续接手 `te_analysis` 的完整交接文件。  
目标是避免重复摸索 `snakescale` 输入层、避免再走一遍错误路径，并把当前真正的阻断点讲清楚。

当前结论先说在前面：

- `snakescale` 的 sqlite 输入层已经构造成功，`generate_yaml.py --db ...` 已经 smoke 通过。
- 当前真正卡住的不是 sqlite，也还不是 groovy bug，而是 `vendor/snakescale/Snakefile` 的执行契约和我们预期不一致。
- 直接把单 study YAML 当成 `snakemake --configfile ...` 传进去，并不会让主 Snakefile 只跑这个 study；它仍然优先吃 `vendor/snakescale/config/config.yaml` 里的 study 列表。
- 另外，目标 study `GSE109122` 在我们的项目磁盘布局下还没有出现在 `raw_data/Arabidopsis_thaliana/GSE109122/*.fastq.gz`，FASTQ staging 也没有做。

## 1. 仓库与工作区当前状态

### 1.1 主仓库状态

- 当前分支：`design/v1-minimal`
- 当前 `git status --short`：

```text
 ? vendor/TE_model
 m vendor/snakescale
```

说明：

- `vendor/TE_model` 是一个未初始化或未跟踪状态的 vendor 目录。
- `vendor/snakescale` 子模块是 dirty 状态。

### 1.2 vendor/snakescale 子模块状态

`git -C vendor/snakescale status --short` 当前输出：

```text
 M riboflow/RiboFlow.groovy
?? .nextflow.log
?? .nextflow/
?? .snakemake/
?? adapter_check_output/
?? db/create_database.sql
?? db/db.sqlite3
?? input/
?? intermediates/
?? log/
?? modifications/
?? nextflow_logs/
?? output/
?? reference/
?? scripts/__pycache__/
?? staged_fastq/
?? work/
?? yaml_status.txt
```

解释：

- `riboflow/RiboFlow.groovy` 已经被修改，但这不是本轮新改的内容，我没有继续改它。
- 大量未跟踪目录来自之前 `vendor/snakescale` 目录下真实执行或试跑遗留的工作目录，不应直接当成源码变更。
- 后续代理在动 `vendor/snakescale` 之前，必须先区分“真实源码改动”和“运行残留”。

## 2. 这个项目里 snakescale 的真实现状

### 2.1 输入层已经打通

现在已经有可用 sqlite：

- [data/processed/snakescale_input.db](/home/xrx/my_project/te_analysis/data/processed/snakescale_input.db)
- [data/processed/snakescale_etl_drop_log.csv](/home/xrx/my_project/te_analysis/data/processed/snakescale_etl_drop_log.csv)
- [scripts/build_sqlite_db.py](/home/xrx/my_project/te_analysis/scripts/build_sqlite_db.py)

sqlite 当前行数：

```text
metadata_study 120
metadata_experiment 2644
metadata_srr 4157
```

drop log 当前是空的：

- 行数：`0`
- 列：`level, experiment_alias, study_name, corrected_type, drop_reason`

### 2.2 反向工程报告已完成

已有报告：

- [docs/schema_reverse_engineering_report.md](/home/xrx/my_project/te_analysis/docs/schema_reverse_engineering_report.md)

这个报告已经确认了几件关键事实：

- 默认入口真正使用的是 `metadata_study` / `metadata_experiment` / `metadata_srr`
- `unitmetadata_*` 是备用入口，不构造
- 真正必需列远少于历史 SQL 猜出来的全量列
- `matched_experiment_id` 和 `metadata_srr.experiment_id` 在逻辑上应当是整数 FK 域

### 2.3 P1 构造报告已完成

已有报告：

- [docs/sqlite_build_report.md](/home/xrx/my_project/te_analysis/docs/sqlite_build_report.md)

P1 的关键成果：

- 物种覆盖审计已完成
- sqlite ETL 已完成
- `generate_yaml.py` 单 study smoke 已成功

P1 的关键数字：

- study：`120`
- experiment：`2644`
- srr：`4157`
- references 覆盖物种只有 `4` 个：
  - `arabidopsis thaliana`
  - `caenorhabditis elegans`
  - `homo sapiens`
  - `mus musculus`
- 被 references 阻塞的 study 数：`56`

## 3. 已经拍板的关键决策

这些决策已经在之前的 prompt 中明确，不要再回头重问：

- `matched_experiment_id` / `metadata_srr.experiment_id`：统一用整数 FK
- `id`：ETL 预分配稳定整数，不用 `AUTOINCREMENT` 作为业务主策略
- `threep_adapter` 缺失：写空字符串 `''`，不要写 `NULL`
- 不构造 `unitmetadata_*`
- OPTIONAL 列保留列名，值可 `NULL`
- 缺失 matched RNA-Seq 的 Ribo-Seq：理论策略是 drop；但当前数据集 ETL 后实际 `drop=0`
- 物种不在 `references.yaml` 的 study：保留在 sqlite 中，只在审计报告中标注

## 4. 构建 sqlite 的正确方式

之前 P2 失败的直接原因是检查路径错了。  
`scripts/build_sqlite_db.py` 默认输出到 `data/interim/snakescale/db.sqlite3`，但后续流程在找 `data/processed/snakescale_input.db`。

正确构建命令是：

```bash
cd /home/xrx/my_project/te_analysis

mkdir -p data/processed

python scripts/build_sqlite_db.py \
  --output-db data/processed/snakescale_input.db \
  --drop-log data/processed/snakescale_etl_drop_log.csv \
  --summary-json /tmp/snakescale_input_summary.json
```

运行后的预期输出：

```text
[OK] wrote data/processed/snakescale_input.db
     study=120, experiment=2644, srr=4157
     dropped: experiment=0, study=0, skipped_run_rows=11
     smoke_candidate=GSE109122 (arabidopsis thaliana)
```

## 5. ETL 脚本现在做了什么

脚本位置：

- [scripts/build_sqlite_db.py](/home/xrx/my_project/te_analysis/scripts/build_sqlite_db.py)

这个脚本负责：

- 读取 `data/raw/metadata.csv`，且必须 `skiprows=[0]`
- 读取 `vendor/snakescale/scripts/references.yaml`
- 做物种覆盖审计
- 生成 `metadata_study`
- 生成 `metadata_experiment`
- 生成 `metadata_srr`
- 写 sqlite
- 生成 drop log
- 生成 smoke candidate 选择结果

ETL 的几个重要实现细节：

- `study.id`：按 `geo_accession` 字母序稳定分配
- `experiment.id`：按 `(study_id, experiment_alias)` 稳定分配
- `matched_experiment_id`：按 `matched_RNA-seq_experiment_alias -> experiment.id` 翻译
- `threep_adapter`：`fillna('')`
- `organism`：写库时保留原值，不 lower；让 `generate_yaml.py` 自己 lower
- `metadata_srr.sra_accession`：直接来自 `run`
- `metadata_srr.experiment_id`：来自 `experiment_alias -> experiment.id`

## 6. 目标 smoke study 的当前事实

当前最简单、已知可用的 smoke study 是：

- `GSE109122`
- organism：`Arabidopsis thaliana`

从 sqlite 抽出来的真实清单：

```text
geo_accession experiment_alias     type             organism                     threep_adapter sra_accession
    GSE109122       GSM2932477 Ribo-Seq Arabidopsis thaliana AGATCGGAAGAGCACACGTCTGAACTCCAGTCAC    SRR6466829
    GSE109122       GSM2932478 Ribo-Seq Arabidopsis thaliana AGATCGGAAGAGCACACGTCTGAACTCCAGTCAC    SRR6466830
    GSE109122       GSM2932479 Ribo-Seq Arabidopsis thaliana AGATCGGAAGAGCACACGTCTGAACTCCAGTCAC    SRR6466831
    GSE109122       GSM2932480 Ribo-Seq Arabidopsis thaliana AGATCGGAAGAGCACACGTCTGAACTCCAGTCAC    SRR6466832
    GSE109122       GSM2932481  RNA-Seq Arabidopsis thaliana AGATCGGAAGAGCACACGTCTGAACTCCAGTCAC    SRR6466833
    GSE109122       GSM2932482  RNA-Seq Arabidopsis thaliana AGATCGGAAGAGCACACGTCTGAACTCCAGTCAC    SRR6466834
    GSE109122       GSM2932483  RNA-Seq Arabidopsis thaliana AGATCGGAAGAGCACACGTCTGAACTCCAGTCAC    SRR6466835
    GSE109122       GSM2932484  RNA-Seq Arabidopsis thaliana AGATCGGAAGAGCACACGTCTGAACTCCAGTCAC    SRR6466836
```

对应统计：

- Ribo rows：`4`
- RNA rows：`4`
- SRR total：`8`
- Ribo rows with non-null adapter：`4`

## 7. generate_yaml 当前已经 smoke 成功

### 7.1 成功前提

如果从项目根直接调用：

```bash
/home/xrx/miniconda3/envs/snakemake-ribo/bin/python \
  vendor/snakescale/scripts/generate_yaml.py \
  --db data/processed/snakescale_input.db \
  --study GSE109122 \
  --template vendor/snakescale/project.yaml \
  --output data/processed/snakescale_yaml/GSE109122 \
  --download_path input/fastq
```

它会先失败，报：

```text
FileNotFoundError: [Errno 2] No such file or directory: 'scripts/references.yaml'
```

原因：

- `generate_yaml.py` 默认 `reference_file="scripts/references.yaml"`
- 从项目根跑时，这个相对路径不对

### 7.2 正确调用方式

必须显式补：

```bash
/home/xrx/miniconda3/envs/snakemake-ribo/bin/python \
  vendor/snakescale/scripts/generate_yaml.py \
  --db data/processed/snakescale_input.db \
  --study GSE109122 \
  --template vendor/snakescale/project.yaml \
  --output data/processed/snakescale_yaml/GSE109122 \
  --download_path input/fastq \
  --reference_file vendor/snakescale/scripts/references.yaml
```

产物路径：

- [data/processed/snakescale_yaml/GSE109122/GSE109122/GSE109122.yaml](/home/xrx/my_project/te_analysis/data/processed/snakescale_yaml/GSE109122/GSE109122/GSE109122.yaml)

### 7.3 这个 YAML 的重要观察

YAML 已经成功生成，顶层结构包含：

- `alignment_arguments`
- `clip_arguments`
- `deduplicate`
- `do_check_file_existence`
- `do_fastqc`
- `do_metadata`
- `do_rnaseq`
- `input`
- `mapping_quality_cutoff`
- `output`
- `ribo`
- `rnaseq`

最重要的 FASTQ 路径模式是：

```yaml
input:
  fastq:
    GSM2932477:
    - input/fastq/GSE109122/GSM2932477/SRR6466829_1.fastq.gz
rnaseq:
  fastq:
    GSM2932477:
    - input/fastq/GSE109122/GSM2932481/SRR6466833_1.fastq.gz
```

这里有一个非常关键的 vendor 语义：

- `rnaseq.fastq` 的 key 不是 RNA experiment 自己的 `GSM2932481`，而是复用了匹配到的 Ribo experiment key `GSM2932477`
- 这意味着后续 staging 或校验如果假设 RNA 节点的 key 也是 RNA alias，会理解错

## 8. P2 探路目前探到了哪里

### 8.1 预检结果

P2 环境预检通过：

- 分支对
- sqlite 对
- `generate_yaml.py --db` 可用
- `snakemake` 版本可用：`7.24.0`

### 8.2 磁盘 FASTQ 当前并不在目标路径

命令：

```bash
find raw_data/Arabidopsis_thaliana/GSE109122 -name "*.fastq.gz" 2>/dev/null | wc -l
```

结果：

- `0`

这说明：

- 至少在当前项目树下，`raw_data/Arabidopsis_thaliana/GSE109122` 并没有我们想象中的 FASTQ 文件
- 所以即使后面 Snakefile 真正开始要输入文件，也会先撞到缺文件 / staging 问题

### 8.3 第一次 dry-run 的真实报错

第一次在 `vendor/snakescale` 下直接 dry-run，碰到的不是业务错误，而是环境错误：

```text
OSError: [Errno 30] Read-only file system:
'/home/xrx/.cache/snakemake/snakemake/source-cache/runtime-cache/...'
```

原因：

- 当前环境里 `~/.cache/snakemake` 对这个 snakemake 进程不可写

临时绕法：

```bash
XDG_CACHE_HOME=/tmp/snakemake-cache ...
```

### 8.4 第二次 dry-run 的关键事实

把 cache 指到 `/tmp` 后，dry-run 不再报环境错，但它并没有真正对 `GSE109122` 展开 DAG。

日志核心内容：

```text
Config file config/config.yaml is extended by additional config specified via the command line.
Currently working on GSE139910
Currently working on GSE37744_dedup
Currently Generating YAML File for: GSE37744_dedup
Building DAG of jobs...
localrule all:
```

这说明：

- 直接 `snakemake --configfile ../../data/processed/snakescale_yaml/.../GSE109122.yaml`
- 并不会让主 `Snakefile` 只针对 `GSE109122`
- 主 Snakefile 仍然优先依赖它自己顶部声明的：

```python
configfile: "config/config.yaml"
STUDIES = config['studies']
```

对应源码证据：

- [vendor/snakescale/Snakefile](/home/xrx/my_project/te_analysis/vendor/snakescale/Snakefile)
- `configfile: "config/config.yaml"` 在第 14 行
- `STUDIES = config['studies']` 在第 21 行

对应默认配置文件内容：

- [vendor/snakescale/config/config.yaml](/home/xrx/my_project/te_analysis/vendor/snakescale/config/config.yaml)

里面当前写的是：

```yaml
studies:
  - GSE139910
  - GSE37744_dedup
```

所以，P2 当前探明的第一业务阻断点是：

- **Snakefile 配置契约不匹配**
- 不是 sqlite 问题
- 也还没走到 `download_fastq_files`
- 更还没走到 `RiboFlow.groovy`

## 9. 当前最真实的阻断排序

按已经拿到的证据，当前阻断优先级应该这样排：

### 阻断 1：Snakefile 的 config 契约不匹配

现象：

- `--configfile <single-study-yaml>` 不会把 `Snakefile` 锁到 `GSE109122`
- 它仍然吃 `vendor/snakescale/config/config.yaml`

这一步不解决，后面所有“只跑一个 study”的探路都不可信。

### 阻断 2：FASTQ 真实文件不在 YAML 期望路径

现象：

- `GSE109122` 在 DB / YAML 都有 8 个 SRR
- 但 `raw_data/Arabidopsis_thaliana/GSE109122/*.fastq.gz` 当前是 0
- YAML 期望的是 `input/fastq/GSE109122/<GSM>/<SRR>_1.fastq.gz`

这说明即使阻断 1 解决，下一步高概率就是 staging / MissingInput 问题。

### 阻断 3：groovy bug 暂时没有被触发

现象：

- 目前没有拿到任何 `RiboFlow.groovy` / `task.cpus` 的真实运行时报错
- 还不能认定它是当前第一阻断点

结论：

- 先别急着修 groovy
- 先让主 Snakefile 真正指向目标 study 并展开真实 DAG

## 10. 你现在可以相信的文件

这些文件已经存在且可直接引用：

- [docs/schema_reverse_engineering_report.md](/home/xrx/my_project/te_analysis/docs/schema_reverse_engineering_report.md)
- [docs/sqlite_build_report.md](/home/xrx/my_project/te_analysis/docs/sqlite_build_report.md)
- [scripts/build_sqlite_db.py](/home/xrx/my_project/te_analysis/scripts/build_sqlite_db.py)
- [data/processed/snakescale_input.db](/home/xrx/my_project/te_analysis/data/processed/snakescale_input.db)
- [data/processed/snakescale_etl_drop_log.csv](/home/xrx/my_project/te_analysis/data/processed/snakescale_etl_drop_log.csv)
- [data/processed/snakescale_yaml/GSE109122/GSE109122/GSE109122.yaml](/home/xrx/my_project/te_analysis/data/processed/snakescale_yaml/GSE109122/GSE109122/GSE109122.yaml)

## 11. 你现在不能默认相信的东西

- `vendor/snakescale/db/db.sqlite3`
  - 这是历史样例，不是权威输入库
- `vendor/snakescale/db/create_database.sql`
  - 这是历史逆向产物，不是源码真值
- `vendor/snakescale/config/config.yaml`
  - 这是 vendor 默认 config，不代表我们项目真正要跑的 study
- `vendor/snakescale` 下大量 `input/`, `output/`, `.snakemake/`, `work/`
  - 这些大概率是历史运行残留，不应直接当成当前项目的正式产物

## 12. 如果你是下一个 ChatGPT，建议怎么接

建议按这个顺序继续：

1. 先不要动 sqlite，输入层已经通了。
2. 先研究 `vendor/snakescale/Snakefile` 如何在不改 vendor 源码的前提下，只对 `GSE109122` 生效。
3. 在解决单 study config 契约之后，再做一次真正针对 `GSE109122` 的 dry-run。
4. 只有那一步成功后，再看 DAG 里是否出现 `download_fastq_files`、是否需要 staging。
5. 只有真正跑到 `RiboFlow.groovy` / nextflow 相关步骤之后，才有资格判断 groovy bug 是否是现实阻断。

## 13. 强提醒

- 当前最容易误判的地方，是以为“YAML 生成成功 == Snakefile 可以拿这个 YAML 直接跑单 study”。事实不是。
- 当前第二个最容易误判的地方，是以为“主要问题一定是下载规则”。现在证据还没走到那一步。
- 当前第三个最容易误判的地方，是把 `vendor/snakescale` 子模块的脏状态都当成源码变更；其中绝大多数更像运行残留。

## 14. 一句话交接结论

**输入层已完成，真正的下一步不是重建 sqlite，也不是立刻修 groovy，而是先搞清楚如何让 `vendor/snakescale/Snakefile` 真正只针对 `GSE109122` 展开 DAG；在那之前，任何 pipeline 层结论都不稳。**
