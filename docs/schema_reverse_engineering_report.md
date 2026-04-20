# snakescale sqlite schema 逆向推导报告

日期：2026-04-20  
vendor SHA：b918e75f877262dca96665d18c3b472675f30a6d  
扫描代理：Codex

## 1. 扫描摘要

- 扫描 Python 文件数：4
- 扫描 Snakefile/groovy/nf 文件数：3
- 额外检视的 yaml/config/sh 旁证文件数：15
- 定位的 sqlite 访问点数：12
- 发现的表名（源码真实字符串）：`metadata_study`、`metadata_experiment`、`metadata_srr`、`unitmetadata_study`、`unitmetadata_experiment`、`unitmetadata_srr`
- 驱动类型：`raw sqlite3` + `pandas.read_sql_query`
- ORM 迹象：未发现 Django ORM / SQLAlchemy / Peewee model
- shell 层 `sqlite3` CLI：未发现
- runtime 写库语义：未发现 `INSERT` / `UPDATE` / `DELETE`；默认与备用入口均为只读查询
- 默认流程入口：`vendor/snakescale/Snakefile:11` 导入 `generate_yaml`
- 备用流程入口：`vendor/snakescale/Snakefile_unitmetadata:11` 导入 `generate_yaml_unitmetadata`
- 默认流程的 db 路径来源：`vendor/snakescale/Snakefile:38`
- 备用流程的 db 路径来源：`vendor/snakescale/Snakefile_unitmetadata:38`
- 参考文件仅作对比，不作真值：`vendor/snakescale/db/create_database.sql`、`vendor/snakescale/db/db.sqlite3`

### 1.1 Phase A 命中统计

| Phase A 输出 | 行数 | 结论 |
|---|---:|---|
| `/tmp/schema_recon/A1_connections.txt` | 14 | 命中仅集中在 `generate_yaml*.py` |
| `/tmp/schema_recon/A2_raw_sql.txt` | 50 | raw SQL 基本都来自两份 yaml 生成脚本 |
| `/tmp/schema_recon/A3_orm_models.txt` | 0 | 无 ORM model |
| `/tmp/schema_recon/A4_table_name_refs.txt` | 69 | `metadata_*` 主要来自默认入口，`unitmetadata_*` 来自备用入口 |
| `/tmp/schema_recon/A5_pipeline_refs.txt` | 2 | pipeline 层只传递 db 路径，不直接写 SQL |
| `/tmp/schema_recon/A6_suspect_files.txt` | 2 | 可疑 schema 文件只有 `db/create_database.sql` 与 `schemas/config.schema.yaml` |

### 1.2 分析边界

- 代码归属边界按 `git -C vendor/snakescale ls-files` 确认，仅分析被 vendor 跟踪的源文件。
- `vendor/snakescale/work/`、`.snakemake/`、`.nextflow/` 等生成物未作为 schema 真值来源。
- `vendor/snakescale/db/create_database.sql` 与 `vendor/snakescale/db/db.sqlite3` 仅用于 §5 历史差异参考。
- 本报告的 REQUIRED / OPTIONAL / UNSURE 判定以“默认源码不改动时，对列名存在性与列值语义的需求强度”为准。
- 对于“只在 SELECT 投影中出现、后续逻辑不消费”的列，本报告归入 OPTIONAL，但要注意：当前 raw SQL 仍显式点名这些列，若真正从 schema 中删列，则必须同步改源码查询。

### 1.3 sqlite 访问点清单

| # | 访问点 | 类型 | 证据 |
|---|---|---|---|
| 1 | `db/db.sqlite3` 作为默认 db 参数传入 | workflow call site | `vendor/snakescale/Snakefile:38` |
| 2 | `sqlite3.connect(db)` | connection | `vendor/snakescale/scripts/generate_yaml.py:74` |
| 3 | `SELECT ... FROM "metadata_study" WHERE geo_accession = ...` | read | `vendor/snakescale/scripts/generate_yaml.py:97-105` |
| 4 | `SELECT ... FROM "metadata_experiment" WHERE study_id = ...` | read | `vendor/snakescale/scripts/generate_yaml.py:114-125` |
| 5 | `SELECT ... FROM "metadata_srr" WHERE experiment_id = ...`（Ribo-Seq） | read | `vendor/snakescale/scripts/generate_yaml.py:231-236` |
| 6 | `SELECT ... FROM "metadata_srr" WHERE experiment_id = ...`（RNA-Seq） | read | `vendor/snakescale/scripts/generate_yaml.py:249-253` |
| 7 | `db/db.sqlite3` 作为备用 db 参数传入 | workflow call site | `vendor/snakescale/Snakefile_unitmetadata:38` |
| 8 | `sqlite3.connect(db)` | connection | `vendor/snakescale/scripts/generate_yaml_unitmetadata.py:74` |
| 9 | `SELECT ... FROM "unitmetadata_study" WHERE geo_accession = ...` | read | `vendor/snakescale/scripts/generate_yaml_unitmetadata.py:97-105` |
| 10 | `SELECT ... FROM "unitmetadata_experiment" WHERE study_id = ...` | read | `vendor/snakescale/scripts/generate_yaml_unitmetadata.py:114-125` |
| 11 | `SELECT ... FROM "unitmetadata_srr" WHERE experiment_id = ...`（Ribo-Seq） | read | `vendor/snakescale/scripts/generate_yaml_unitmetadata.py:231-236` |
| 12 | `SELECT ... FROM "unitmetadata_srr" WHERE experiment_id = ...`（RNA-Seq） | read | `vendor/snakescale/scripts/generate_yaml_unitmetadata.py:249-253` |

## 2. 必需表与列清单（REQUIRED）

### 表 `metadata_study`

| 列名 | 推断类型 | 必需性 | 用途 / 证据（文件:行） |
|---|---|---|---|
| `geo_accession` | TEXT | REQUIRED | 研究入口查找键；`WHERE "metadata_study"."geo_accession" = "{study_gse}"`，命中失败直接抛错；`vendor/snakescale/scripts/generate_yaml.py:102,107-108` |
| `id` | INTEGER | REQUIRED | 作为后续 `metadata_experiment.study_id` 查询键；`study_id = study_df['id'].values[0]`；`vendor/snakescale/scripts/generate_yaml.py:97,110,122-123` |

**主键/业务主键**：  
`id` 是内部主键；`geo_accession` 是实际业务主键，默认流程以它承接 `--study GSE...` 入口。

**JOIN 关系**（若有）：  
`metadata_study.id` ↔ `metadata_experiment.study_id`；证据在 `vendor/snakescale/scripts/generate_yaml.py:110,122-123`。

**空值约定**：  
未见 `IS NULL` / `COALESCE`。`geo_accession` 若为 NULL 或无法匹配 study 字符串，会触发 `study_df.empty` 并报 “Study was not found in the database.”；证据在 `vendor/snakescale/scripts/generate_yaml.py:105-108`。

**INSERT 必填列**：  
runtime 源码未见对 sqlite 的 `INSERT`。若仅按运行时需要，写入必填列不可由源码直接证明。

**列级事实摘录**：  
- `study` 参数允许 `_dedup` / `_test` 后缀，但最终 lookup 仍回到 `gse_only`；`vendor/snakescale/scripts/generate_yaml.py:87-95`。  
- 因此 `geo_accession` 的值域必须是 `GSE\d+` 这一 study 层 accession，而不是 GSM / SRR；`vendor/snakescale/scripts/generate_yaml.py:90,102`。

### 表 `metadata_experiment`

| 列名 | 推断类型 | 必需性 | 用途 / 证据（文件:行） |
|---|---|---|---|
| `id` | INTEGER | REQUIRED | 作为 experiment 内部标识；既用于 `matched_experiment_id` 自连接比较，也用于后续查询 `metadata_srr.experiment_id`；`vendor/snakescale/scripts/generate_yaml.py:114,149-150,228,248-253` |
| `study_id` | INTEGER | REQUIRED | 默认按 `WHERE "metadata_experiment"."study_id" = {id}` 拉取 study 下全部实验；`vendor/snakescale/scripts/generate_yaml.py:122-123` |
| `matched_experiment_id` | INTEGER-like / 与 `id` 同域 | REQUIRED | Ribo-Seq 行通过它匹配 RNA-Seq 行；比较方式是 `rnaseq_df['id'] == matched_rnaseq_id`，明显期待与 `id` 同域；`vendor/snakescale/scripts/generate_yaml.py:115,149-156` |
| `experiment_alias` | TEXT | REQUIRED | 作为 GSM 级业务键，用于 `ribo_dict` / `rna_dict` / YAML key / FASTQ 子目录名；`vendor/snakescale/scripts/generate_yaml.py:115,146-147,153,247,272-279` |
| `type` | TEXT | REQUIRED | 取值至少要支持 `'RNA-Seq'` 与 `'Ribo-Seq'`；用于将同一表拆成两类实验；`vendor/snakescale/scripts/generate_yaml.py:116,126-127` |
| `organism` | TEXT | REQUIRED | 用于决定参考文件；代码会 `lower()` 后去 `references.yaml` 查键；`vendor/snakescale/scripts/generate_yaml.py:120,164-181` 和 `vendor/snakescale/scripts/references.yaml:6-15` |
| `threep_adapter` | TEXT | REQUIRED | 用于拼接 `clip_arguments`；空字符串表示“无 adapter”，但列必须存在且值应可被 `len()` 处理；`vendor/snakescale/scripts/generate_yaml.py:120,32-67,159-162` |

**主键/业务主键**：  
`id` 是内部主键；`experiment_alias` 实际承担跨 YAML / FASTQ 路径的业务键角色。

**JOIN 关系**（若有）：  
`metadata_experiment.study_id` ↔ `metadata_study.id`；`vendor/snakescale/scripts/generate_yaml.py:110,122-123`。  
`metadata_experiment.matched_experiment_id` ↔ `metadata_experiment.id`；代码中是 DataFrame 级自连接，而非 SQL JOIN；`vendor/snakescale/scripts/generate_yaml.py:149-156`。  
`metadata_experiment.id` ↔ `metadata_srr.experiment_id`；`vendor/snakescale/scripts/generate_yaml.py:228-236,248-253`。

**空值约定**：  
`matched_experiment_id` 可以为空，空时该 Ribo-Seq 不会挂上 `rnaseq` 子节点；证据是 `matched_df` 允许为空，且 `if cur_gsm in ribo_rna_dict` 才处理 RNA-Seq；`vendor/snakescale/scripts/generate_yaml.py:149-156,244-259`。  
`threep_adapter` 可为空字符串；`len(candidate_adapter) == 0` 时不会追加 `-a` 参数；`vendor/snakescale/scripts/generate_yaml.py:47-66`。  
`organism` 实际上不应为空；若值是 `None` 会在 `.lower()` 处崩溃；`vendor/snakescale/scripts/generate_yaml.py:169-181`。

**INSERT 必填列**：  
runtime 源码未见 `INSERT`。若以运行语义反推，至少 `study_id`、`experiment_alias`、`type`、`organism`、`id` 需要有值；`matched_experiment_id` 可空；`threep_adapter` 可为空字符串但不建议为 `NULL`。

**列级事实摘录**：  
- `type` 不是展示字段，而是分表逻辑；若不是这两个字面值，实验会被静默排除在 `rnaseq_df` / `riboseq_df` 之外；`vendor/snakescale/scripts/generate_yaml.py:126-127`。  
- `experiment_alias` 直接进入输出 YAML 的一级 key；一旦重复，会导致后写覆盖前写；`vendor/snakescale/scripts/generate_yaml.py:145-147,155-156,297,300`。  
- `matched_experiment_id` 若存 GSM 文本而不是 `id` 域值，则 `rnaseq_df[rnaseq_df['id'] == matched_rnaseq_id]` 恒为空；`vendor/snakescale/scripts/generate_yaml.py:149-150`。  
- `organism` 必须与 `references.yaml` 的 lower-case key 对齐，例如 `homo sapiens`；`vendor/snakescale/scripts/generate_yaml.py:169-181` 和 `vendor/snakescale/scripts/references.yaml:8-15`。  
- `threep_adapter` 是唯一真正参与 adapter 参数生成的数据库列；`fivep_adapter` 在 helper 中被读取但没有下游分支消费；`vendor/snakescale/scripts/generate_yaml.py:34-35,62-65`。

### 表 `metadata_srr`

| 列名 | 推断类型 | 必需性 | 用途 / 证据（文件:行） |
|---|---|---|---|
| `experiment_id` | INTEGER-like / 与 `metadata_experiment.id` 同域 | REQUIRED | 通过 `WHERE "metadata_srr"."experiment_id" = {id}` 取某实验下的全部 SRR；`vendor/snakescale/scripts/generate_yaml.py:231-236,249-253` |
| `sra_accession` | TEXT | REQUIRED | 生成 FASTQ 路径与最终下载 accession；`vendor/snakescale/scripts/generate_yaml.py:239-240,255-257,273,279` |

**主键/业务主键**：  
runtime 逻辑不消费 `metadata_srr.id`；真正承担业务键的是 `sra_accession`，并通过 `experiment_id` 挂到 experiment。

**JOIN 关系**（若有）：  
`metadata_srr.experiment_id` ↔ `metadata_experiment.id`；证据在 `vendor/snakescale/scripts/generate_yaml.py:228-236,248-253`。

**空值约定**：  
未见 `IS NULL` / `COALESCE`。Ribo-Seq experiment 若查不到任何 SRR，会落入 `empty_experiments` 并报错；`vendor/snakescale/scripts/generate_yaml.py:281-295`。RNA-Seq experiment 查不到 SRR 则仅删除对应 `rnaseq.fastq` entry；`vendor/snakescale/scripts/generate_yaml.py:299-312`。

**INSERT 必填列**：  
runtime 源码未见 `INSERT`。若以运行语义反推，`experiment_id` 与 `sra_accession` 必须有值。

**列级事实摘录**：  
- `sra_accession` 直接拼成 `{SRR}_1.fastq.gz`；`vendor/snakescale/scripts/generate_yaml.py:273,279`。  
- 同一 `experiment_id` 可对应多个 `sra_accession`；代码默认聚合成列表；`vendor/snakescale/scripts/generate_yaml.py:224-242,244-259`。  
- Ribo-Seq 与 RNA-Seq 共用同一 `metadata_srr` 表，区分来自上游 `metadata_experiment.type` 与字典分支，而不是来自 `metadata_srr` 自身列；`vendor/snakescale/scripts/generate_yaml.py:126-127,224-259`。

## 3. 可选列清单（OPTIONAL）

> 说明：本节的 OPTIONAL 指“当前源码会在 SELECT 投影里显式点名这些列，但默认 pipeline 后续逻辑并不消费其值”。  
> 因此它们在**值语义**上可缺省 / 可留空；但若完全删除列名，当前 SQL 仍会报错，除非同步修改源码查询。

### 表 `metadata_study`

| 列名 | 推断类型 | 必需性 | 用途 / 证据（文件:行） |
|---|---|---|---|
| `creation_date` | TEXT | OPTIONAL | 仅 SELECT 投影；`vendor/snakescale/scripts/generate_yaml.py:97` |
| `notes` | TEXT | OPTIONAL | 仅 SELECT 投影；`vendor/snakescale/scripts/generate_yaml.py:98` |
| `metadata_checked` | TEXT | OPTIONAL | 仅 SELECT 投影；`vendor/snakescale/scripts/generate_yaml.py:98` |
| `modifier` | TEXT | OPTIONAL | 仅 SELECT 投影；`vendor/snakescale/scripts/generate_yaml.py:98` |
| `study_accession` | TEXT | OPTIONAL | 仅 SELECT 投影；`vendor/snakescale/scripts/generate_yaml.py:99` |
| `study_title` | TEXT | OPTIONAL | 仅 SELECT 投影；`vendor/snakescale/scripts/generate_yaml.py:99` |
| `study_type` | TEXT | OPTIONAL | 仅 SELECT 投影；`vendor/snakescale/scripts/generate_yaml.py:100` |
| `study_abstract` | TEXT | OPTIONAL | 仅 SELECT 投影；`vendor/snakescale/scripts/generate_yaml.py:100` |
| `study_description` | TEXT | OPTIONAL | 仅 SELECT 投影；`vendor/snakescale/scripts/generate_yaml.py:100` |
| `xref_link` | TEXT | OPTIONAL | 仅 SELECT 投影；`vendor/snakescale/scripts/generate_yaml.py:101` |
| `submission_accession` | TEXT | OPTIONAL | 仅 SELECT 投影；`vendor/snakescale/scripts/generate_yaml.py:101` |
| `sradb_updated` | TEXT | OPTIONAL | 仅 SELECT 投影；`vendor/snakescale/scripts/generate_yaml.py:101` |
| `soft_deleted` | TEXT | OPTIONAL | 仅 SELECT 投影；未见软删除过滤逻辑；`vendor/snakescale/scripts/generate_yaml.py:102` |

**主键/业务主键**：  
与 REQUIRED 节相同；OPTIONAL 列不改变该表主键判断。

**JOIN 关系**（若有）：  
OPTIONAL 列未参与 JOIN。

**空值约定**：  
源码未读取这些值，因此未见任何 `NULL` / 空字符串分支。

**INSERT 必填列**：  
runtime 源码未见 `INSERT`。

### 表 `metadata_experiment`

| 列名 | 推断类型 | 必需性 | 用途 / 证据（文件:行） |
|---|---|---|---|
| `creation_date` | TEXT | OPTIONAL | 仅 SELECT 投影；`vendor/snakescale/scripts/generate_yaml.py:114` |
| `notes` | TEXT | OPTIONAL | 仅 SELECT 投影；`vendor/snakescale/scripts/generate_yaml.py:114` |
| `metadata_checked` | TEXT | OPTIONAL | 仅 SELECT 投影；`vendor/snakescale/scripts/generate_yaml.py:114` |
| `modifier` | TEXT | OPTIONAL | 仅 SELECT 投影；`vendor/snakescale/scripts/generate_yaml.py:115` |
| `experiment_accession` | TEXT | OPTIONAL | 仅 SELECT 投影；`vendor/snakescale/scripts/generate_yaml.py:116` |
| `title` | TEXT | OPTIONAL | 仅 SELECT 投影；`vendor/snakescale/scripts/generate_yaml.py:116` |
| `study_name` | TEXT | OPTIONAL | 仅 SELECT 投影；`vendor/snakescale/scripts/generate_yaml.py:116` |
| `design_description` | TEXT | OPTIONAL | 仅 SELECT 投影；`vendor/snakescale/scripts/generate_yaml.py:117` |
| `sample_accession` | TEXT | OPTIONAL | 仅 SELECT 投影；`vendor/snakescale/scripts/generate_yaml.py:117` |
| `sample_attribute` | TEXT | OPTIONAL | 仅 SELECT 投影；`vendor/snakescale/scripts/generate_yaml.py:117` |
| `library_strategy` | TEXT | OPTIONAL | 仅 SELECT 投影；`vendor/snakescale/scripts/generate_yaml.py:117` |
| `library_layout` | TEXT | OPTIONAL | 仅 SELECT 投影；`vendor/snakescale/scripts/generate_yaml.py:118` |
| `library_construction_protocol` | TEXT | OPTIONAL | 仅 SELECT 投影；`vendor/snakescale/scripts/generate_yaml.py:118` |
| `platform` | TEXT | OPTIONAL | 仅 SELECT 投影；`vendor/snakescale/scripts/generate_yaml.py:118` |
| `platform_parameters` | TEXT | OPTIONAL | 仅 SELECT 投影；`vendor/snakescale/scripts/generate_yaml.py:118` |
| `xref_link` | TEXT | OPTIONAL | 仅 SELECT 投影；`vendor/snakescale/scripts/generate_yaml.py:119` |
| `experiment_attribute` | TEXT | OPTIONAL | 仅 SELECT 投影；`vendor/snakescale/scripts/generate_yaml.py:119` |
| `submission_accession` | TEXT | OPTIONAL | 仅 SELECT 投影；`vendor/snakescale/scripts/generate_yaml.py:119` |
| `sradb_updated` | TEXT | OPTIONAL | 仅 SELECT 投影；`vendor/snakescale/scripts/generate_yaml.py:119` |
| `cell_line` | TEXT | OPTIONAL | 仅 SELECT 投影；`vendor/snakescale/scripts/generate_yaml.py:120` |
| `group` | TEXT | OPTIONAL | 仅 SELECT 投影；`vendor/snakescale/scripts/generate_yaml.py:120` |
| `fivep_adapter` | TEXT / NULL | OPTIONAL | helper 会构造 `cur_fivep_set`，但下游无分支消费；`vendor/snakescale/scripts/generate_yaml.py:35,120` |
| `threep_umi_length` | INTEGER | OPTIONAL | 仅 SELECT 投影；`vendor/snakescale/scripts/generate_yaml.py:121` |
| `fivep_umi_length` | INTEGER | OPTIONAL | 仅 SELECT 投影；`vendor/snakescale/scripts/generate_yaml.py:121` |
| `read_length` | TEXT | OPTIONAL | 仅 SELECT 投影；源码真实长度检查改从 FASTQ 读，不读该列；`vendor/snakescale/scripts/generate_yaml.py:121` 与 `vendor/snakescale/Snakefile:438-465` |
| `is_paired_end` | TEXT | OPTIONAL | 仅 SELECT 投影；路径生成始终写 `_1.fastq.gz`，未依据该列分支；`vendor/snakescale/scripts/generate_yaml.py:121,273,279` |
| `experiment_file` | TEXT | OPTIONAL | 仅 SELECT 投影；`vendor/snakescale/scripts/generate_yaml.py:121` |

**主键/业务主键**：  
与 REQUIRED 节相同；OPTIONAL 列不改变该表的主键与业务键判定。

**JOIN 关系**（若有）：  
OPTIONAL 列未参与 JOIN。

**空值约定**：  
`fivep_adapter` 即便为 `NULL`，当前代码也不会用它改变 `clip_arguments`；但 helper 中仍会构建集合，值域最好保持为 `NULL` 或空字符串之一，不要混合复杂对象；`vendor/snakescale/scripts/generate_yaml.py:34-35`。  
其余列未见任何判空逻辑。

**INSERT 必填列**：  
runtime 源码未见 `INSERT`。

### 表 `metadata_srr`

| 列名 | 推断类型 | 必需性 | 用途 / 证据（文件:行） |
|---|---|---|---|
| `id` | INTEGER | OPTIONAL | 仅 SELECT 投影；后续未读；`vendor/snakescale/scripts/generate_yaml.py:231,249` |
| `creation_date` | TEXT | OPTIONAL | 仅 SELECT 投影；后续未读；`vendor/snakescale/scripts/generate_yaml.py:232,250` |

**主键/业务主键**：  
与 REQUIRED 节相同；`id` 未被 runtime 消费。

**JOIN 关系**（若有）：  
OPTIONAL 列未参与 JOIN。

**空值约定**：  
源码未读取这些值，因此无运行时判空语义。

**INSERT 必填列**：  
runtime 源码未见 `INSERT`。

## 4. 存疑列（UNSURE）—— 需要用户拍板

### 表 `metadata_experiment`

| 列名 | 推断类型 | 必需性 | 用途 / 证据（文件:行） |
|---|---|---|---|
| `matched_experiment_id` | `INTEGER` FK-like 或 TEXT 自然键 | UNSURE | 默认代码将其与 `rnaseq_df['id']` 比较，语义上更像 `metadata_experiment.id` 域；但历史样例库把它存成 `TEXT`；`vendor/snakescale/scripts/generate_yaml.py:149-156`，`vendor/snakescale/db/create_database.sql:43,71-72` |
| `fivep_adapter` | TEXT / NULL | UNSURE | 当前 helper 读取但不消费；若要严格最小 schema，可考虑后续改源码后删除；若要零改动兼容，则应保留；`vendor/snakescale/scripts/generate_yaml.py:34-35,120` |
| `id` | INTEGER | UNSURE | runtime 只要求它可比较、可作为 join key；未见插入路径，因此是否需要 `AUTOINCREMENT` 无法由源码直接证明；`vendor/snakescale/scripts/generate_yaml.py:110,149-150,228,248-253` 与 `vendor/snakescale/db/create_database.sql:37` |

**主键/业务主键**：  
`id` 的“必须存在”没有疑问；疑问只在于是否要强制 `PRIMARY KEY AUTOINCREMENT`。  
`matched_experiment_id` 的“必须有该列”没有疑问；疑问在于它究竟存 `id` 域还是存别的自然键。

**JOIN 关系**（若有）：  
源码实际 join 语义是 `matched_experiment_id -> id`，不是 `matched_experiment_id -> experiment_alias`；`vendor/snakescale/scripts/generate_yaml.py:149-156`。

**空值约定**：  
`matched_experiment_id` 允许缺失，缺失表示该 Ribo-Seq 没有匹配 RNA-Seq；`vendor/snakescale/scripts/generate_yaml.py:149-156,244-259`。  
`fivep_adapter` 未见真实空值语义，只能说“值不被消费”；`vendor/snakescale/scripts/generate_yaml.py:34-35`。

**INSERT 必填列**：  
runtime 源码未见 `INSERT`。

**问用户**：  
- 我们是否统一把 `matched_experiment_id` 定义为指向 `metadata_experiment.id` 的整数型外键，而不是 GSM 文本？  
- `fivep_adapter` 是不是只为了历史兼容保留？  
- `id` 是否需要数据库层自增约束，还是 ETL 预分配稳定整数即可？

### 表 `metadata_srr`

| 列名 | 推断类型 | 必需性 | 用途 / 证据（文件:行） |
|---|---|---|---|
| `experiment_id` | `INTEGER` FK-like 或 TEXT 自然键 | UNSURE | 查询语句用 `{id}` 直接过滤，来源是 `metadata_experiment.id`；语义更像整数 FK，但历史样例库中此列是 `TEXT`；`vendor/snakescale/scripts/generate_yaml.py:228-236,248-253`，`vendor/snakescale/db/create_database.sql:87-89` |
| `id` | INTEGER | UNSURE | runtime 完全不读取此列，是否保留数据库 surrogate key 只能从历史 SQL 猜，不是源码硬需求；`vendor/snakescale/scripts/generate_yaml.py:231,249`，`vendor/snakescale/db/create_database.sql:85` |

**主键/业务主键**：  
`sra_accession` 显然是业务键；`id` 是否存在纯属数据库设计选择，源码未依赖。  
`experiment_id` 则必须与 experiment 域可关联，但存储类型待定。

**JOIN 关系**（若有）：  
源码 join 语义是 `metadata_srr.experiment_id -> metadata_experiment.id`；`vendor/snakescale/scripts/generate_yaml.py:228-236,248-253`。

**空值约定**：  
`experiment_id` 不应为空；为空则查不到 SRR。  
`id` 未被消费，无判空语义。

**INSERT 必填列**：  
runtime 源码未见 `INSERT`。

**问用户**：  
- 我们是否统一把 `metadata_srr.experiment_id` 定义为整数型外键到 `metadata_experiment.id`？  
- `metadata_srr.id` 是否要保留，还是直接以 `(experiment_id, sra_accession)` 作为业务唯一键？

### 表 `unitmetadata_study`

| 列名 | 推断类型 | 必需性 | 用途 / 证据（文件:行） |
|---|---|---|---|
| `geo_accession` | TEXT | UNSURE | 备用入口 `generate_yaml_unitmetadata.py` 用它做 study lookup；`vendor/snakescale/scripts/generate_yaml_unitmetadata.py:102,107-108` |
| `id` | INTEGER | UNSURE | 备用入口用它驱动 `unitmetadata_experiment.study_id` 查询；`vendor/snakescale/scripts/generate_yaml_unitmetadata.py:110,122-123` |

**主键/业务主键**：  
若保留 `Snakefile_unitmetadata` 路径，则与 `metadata_study` 完全同构。  
若不保留，该整张表都可从最小默认 schema 中移除。

**JOIN 关系**（若有）：  
`unitmetadata_study.id` ↔ `unitmetadata_experiment.study_id`；`vendor/snakescale/scripts/generate_yaml_unitmetadata.py:110,122-123`。

**空值约定**：  
与 `metadata_study` 同构。

**INSERT 必填列**：  
runtime 源码未见 `INSERT`。

**问用户**：  
- 默认分支并不调用 `Snakefile_unitmetadata`，我们是否还要为这个备用入口维护一整套 `unitmetadata_*` 表族？

### 表 `unitmetadata_experiment`

| 列名 | 推断类型 | 必需性 | 用途 / 证据（文件:行） |
|---|---|---|---|
| `id` | INTEGER | UNSURE | 备用入口中的 experiment 主键；`vendor/snakescale/scripts/generate_yaml_unitmetadata.py:114,149-150,228,248-253` |
| `study_id` | INTEGER | UNSURE | 备用入口按此列筛 study；`vendor/snakescale/scripts/generate_yaml_unitmetadata.py:122-123` |
| `matched_experiment_id` | INTEGER-like / 与 `id` 同域 | UNSURE | 与默认 schema 同样存在“类型域”问题；`vendor/snakescale/scripts/generate_yaml_unitmetadata.py:115,149-156` |
| `experiment_alias` | TEXT | UNSURE | 备用入口的 GSM 业务键；`vendor/snakescale/scripts/generate_yaml_unitmetadata.py:115,146-147,153,247,272-279` |
| `type` | TEXT | UNSURE | 备用入口按 `'RNA-Seq'` / `'Ribo-Seq'` 分流；`vendor/snakescale/scripts/generate_yaml_unitmetadata.py:116,126-127` |
| `organism` | TEXT | UNSURE | 备用入口用它匹配 `references.yaml`；`vendor/snakescale/scripts/generate_yaml_unitmetadata.py:120,164-181` |
| `threep_adapter` | TEXT | UNSURE | 备用入口生成 `clip_arguments`；`vendor/snakescale/scripts/generate_yaml_unitmetadata.py:120,32-67,159-162` |

**主键/业务主键**：  
若保留这套表族，则判定与 `metadata_experiment` 完全同构。

**JOIN 关系**（若有）：  
`unitmetadata_experiment.study_id` ↔ `unitmetadata_study.id`；`vendor/snakescale/scripts/generate_yaml_unitmetadata.py:110,122-123`。  
`unitmetadata_experiment.matched_experiment_id` ↔ `unitmetadata_experiment.id`；`vendor/snakescale/scripts/generate_yaml_unitmetadata.py:149-156`。  
`unitmetadata_experiment.id` ↔ `unitmetadata_srr.experiment_id`；`vendor/snakescale/scripts/generate_yaml_unitmetadata.py:228-253`。

**空值约定**：  
与 `metadata_experiment` 同构。

**INSERT 必填列**：  
runtime 源码未见 `INSERT`。

**问用户**：  
- 若要支持 `Snakefile_unitmetadata`，是否接受维护一套与 `metadata_experiment` 平行、几乎完全镜像的表？  
- 这套备用入口是否已经废弃，只是历史遗留脚本？

### 表 `unitmetadata_srr`

| 列名 | 推断类型 | 必需性 | 用途 / 证据（文件:行） |
|---|---|---|---|
| `experiment_id` | INTEGER-like / 与 `unitmetadata_experiment.id` 同域 | UNSURE | 备用入口按 experiment_id 取 SRR；`vendor/snakescale/scripts/generate_yaml_unitmetadata.py:231-236,249-253` |
| `sra_accession` | TEXT | UNSURE | 备用入口生成 FASTQ 路径；`vendor/snakescale/scripts/generate_yaml_unitmetadata.py:239-240,255-257,273,279` |

**主键/业务主键**：  
若保留这套表族，则与 `metadata_srr` 同构。

**JOIN 关系**（若有）：  
`unitmetadata_srr.experiment_id` ↔ `unitmetadata_experiment.id`；`vendor/snakescale/scripts/generate_yaml_unitmetadata.py:231-236,249-253`。

**空值约定**：  
与 `metadata_srr` 同构。

**INSERT 必填列**：  
runtime 源码未见 `INSERT`。

**问用户**：  
- `unitmetadata_*` 是否需要和默认 `metadata_*` 同时存在，还是可以整体移除备用入口？

## 5. 与历史倒推产物的差异（参考性对比）

**仅为参考**，本节不影响 §2-§4 的 REQUIRED 判定。

### 5.1 历史 `create_database.sql` 声明但源码未语义使用的列（可降级为兼容列）

- `metadata_study`：`creation_date`、`notes`、`metadata_checked`、`modifier`、`study_accession`、`study_title`、`study_type`、`study_abstract`、`study_description`、`xref_link`、`submission_accession`、`sradb_updated`、`soft_deleted`；声明见 `vendor/snakescale/db/create_database.sql:14-27`，源码仅投影不消费见 `vendor/snakescale/scripts/generate_yaml.py:97-102`
- `metadata_experiment`：`creation_date`、`notes`、`metadata_checked`、`modifier`、`experiment_accession`、`title`、`study_name`、`design_description`、`sample_accession`、`sample_attribute`、`library_strategy`、`library_layout`、`library_construction_protocol`、`platform`、`platform_parameters`、`xref_link`、`experiment_attribute`、`submission_accession`、`sradb_updated`、`cell_line`、`group`、`fivep_adapter`、`threep_umi_length`、`fivep_umi_length`、`read_length`、`is_paired_end`、`experiment_file`；声明见 `vendor/snakescale/db/create_database.sql:38-70`，源码仅投影或旁路读取见 `vendor/snakescale/scripts/generate_yaml.py:114-121,34-35`
- `metadata_srr`：`id`、`creation_date`；声明见 `vendor/snakescale/db/create_database.sql:85-88`，源码不消费见 `vendor/snakescale/scripts/generate_yaml.py:231-233,249-251`

### 5.2 源码使用但历史 SQL 未声明的表 / 列（旧 schema 漏项）

- 整个 `unitmetadata_*` 表族未出现在 `vendor/snakescale/db/create_database.sql`
- `unitmetadata_study` 被 `vendor/snakescale/scripts/generate_yaml_unitmetadata.py:97-105` 使用
- `unitmetadata_experiment` 被 `vendor/snakescale/scripts/generate_yaml_unitmetadata.py:114-125` 使用
- `unitmetadata_srr` 被 `vendor/snakescale/scripts/generate_yaml_unitmetadata.py:231-253` 使用
- `Snakefile_unitmetadata` 明确把 `generate_yaml_unitmetadata` 作为 workflow 入口；`vendor/snakescale/Snakefile_unitmetadata:11,38`

### 5.3 类型声明冲突（历史 SQL vs 源码推断 vs 本地样例库）

| 对象 | 历史 `create_database.sql` | 本地样例 `db.sqlite3` | 源码推断 | 证据 |
|---|---|---|---|---|
| `metadata_experiment.matched_experiment_id` | `INTEGER`；`vendor/snakescale/db/create_database.sql:43,72` | `TEXT`；`vendor/snakescale/db/db.sqlite3` 的 `.schema metadata_experiment` | 应与 `metadata_experiment.id` 同域；至少要能和 `rnaseq_df['id']` 比较 | `vendor/snakescale/scripts/generate_yaml.py:149-150` |
| `metadata_srr.experiment_id` | `INTEGER`；`vendor/snakescale/db/create_database.sql:87-89` | `TEXT`；`vendor/snakescale/db/db.sqlite3` 的 `.schema metadata_srr` | 应与 `metadata_experiment.id` 同域；至少要能被 `WHERE experiment_id = {id}` 命中 | `vendor/snakescale/scripts/generate_yaml.py:231-236,249-253` |
| `metadata_study.geo_accession` | `TEXT NOT NULL UNIQUE`；`vendor/snakescale/db/create_database.sql:18,31` | `TEXT`，未见唯一约束；`vendor/snakescale/db/db.sqlite3` 的 `.schema metadata_study` | 业务上必须唯一，否则 `study_df['id'].values[0]` 含糊 | `vendor/snakescale/scripts/generate_yaml.py:102,110` |
| `metadata_experiment.type` | `TEXT NOT NULL CHECK(...)`；`vendor/snakescale/db/create_database.sql:46` | `TEXT`，未见 CHECK；`vendor/snakescale/db/db.sqlite3` 的 `.schema metadata_experiment` | 运行时依赖字面值 `'RNA-Seq'` / `'Ribo-Seq'` | `vendor/snakescale/scripts/generate_yaml.py:126-127` |

### 5.4 历史样例库还暴露出的结构漂移

- 本地样例库只含 `metadata_*` 三张表，不含 `unitmetadata_*`；这意味着备用入口目前没有随库一并交付
- 本地样例库未显式保留 `PRIMARY KEY` / `FOREIGN KEY` / `UNIQUE` 约束文本，说明它更像“为脚本凑列名”的历史产物，而不是权威 DDL
- 但本地样例库把 `matched_experiment_id`、`experiment_id` 都做成了 `TEXT`，这与默认代码的比较方式直接张力最大

## 6. 下一步建议（给用户）

- 先拍板 `matched_experiment_id`：建议统一为指向 `metadata_experiment.id` 的整数型外键语义；否则默认代码永远无法把 Ribo-Seq 挂到匹配的 RNA-Seq
- 再拍板 `metadata_srr.experiment_id`：建议统一为指向 `metadata_experiment.id` 的整数型外键语义
- 决定是否保留 `unitmetadata_*` 全家桶：默认 `Snakefile` 不需要它，但 repo 里确实保留了完整备用入口
- 在 REQUIRED 列中，`metadata.csv` 大概率没有直接字段可对上的项包括：`metadata_study.id`、`metadata_experiment.id`、`metadata_experiment.study_id`、`metadata_experiment.matched_experiment_id`、`metadata_srr.experiment_id`
- 在 REQUIRED 列中，源码默认值不明的字段包括：三个 `id` 域的生成策略、`matched_experiment_id` 的空值策略、`threep_adapter` 应用空字符串还是 `NULL`
- pipeline 层已经暗示 RNA-Seq 与 Ribo-Seq 共享同一库：二者共用 `metadata_experiment`，靠 `type` 分流；若某个 Ribo-Seq 没有匹配 RNA-Seq，`generate_yaml.py` 会删除对应 `rnaseq` 节点，而不是失败；`vendor/snakescale/scripts/generate_yaml.py:126-127,244-259,299-312`
- 结构性问题 1：`Snakefile_unitmetadata` 依赖 `config/config_unitmetadata.yaml`，但该文件未见于 tracked files，提示备用入口可能不完整或已半废弃；证据在 `vendor/snakescale/Snakefile_unitmetadata:14`
- 结构性问题 2：默认 `project.yaml` 模板预置了 `rnaseq:` 节点；`generate_yaml.py` 先写入 `ribo_yaml['rnaseq']['clip_arguments']`，后续再按是否有 SRR 决定删除整个 `rnaseq` 节点；证据在 `vendor/snakescale/project.yaml:147-159` 与 `vendor/snakescale/scripts/generate_yaml.py:162,299-312`
- 结构性问题 3：`fivep_adapter` 虽被读取却不参与任何 adapter 决策，像是历史残留列；若未来要做真正最小 schema，优先考虑和原作者确认这列是否可删

## 附录 A. 默认入口 `metadata_*` 列级证据矩阵

### A.1 `metadata_study`

| 列名 | 出现位置 | 被后续逻辑消费？ | 当前判定 |
|---|---|---|---|
| `id` | `vendor/snakescale/scripts/generate_yaml.py:97` | 是，生成 `study_id` | REQUIRED |
| `creation_date` | `vendor/snakescale/scripts/generate_yaml.py:97` | 否 | OPTIONAL |
| `notes` | `vendor/snakescale/scripts/generate_yaml.py:98` | 否 | OPTIONAL |
| `metadata_checked` | `vendor/snakescale/scripts/generate_yaml.py:98` | 否 | OPTIONAL |
| `modifier` | `vendor/snakescale/scripts/generate_yaml.py:98` | 否 | OPTIONAL |
| `geo_accession` | `vendor/snakescale/scripts/generate_yaml.py:99,102` | 是，study lookup | REQUIRED |
| `study_accession` | `vendor/snakescale/scripts/generate_yaml.py:99` | 否 | OPTIONAL |
| `study_title` | `vendor/snakescale/scripts/generate_yaml.py:99` | 否 | OPTIONAL |
| `study_type` | `vendor/snakescale/scripts/generate_yaml.py:100` | 否 | OPTIONAL |
| `study_abstract` | `vendor/snakescale/scripts/generate_yaml.py:100` | 否 | OPTIONAL |
| `study_description` | `vendor/snakescale/scripts/generate_yaml.py:100` | 否 | OPTIONAL |
| `xref_link` | `vendor/snakescale/scripts/generate_yaml.py:101` | 否 | OPTIONAL |
| `submission_accession` | `vendor/snakescale/scripts/generate_yaml.py:101` | 否 | OPTIONAL |
| `sradb_updated` | `vendor/snakescale/scripts/generate_yaml.py:101` | 否 | OPTIONAL |
| `soft_deleted` | `vendor/snakescale/scripts/generate_yaml.py:102` | 否 | OPTIONAL |

### A.2 `metadata_experiment`

| 列名 | 出现位置 | 被后续逻辑消费？ | 当前判定 |
|---|---|---|---|
| `id` | `vendor/snakescale/scripts/generate_yaml.py:114` | 是，自连接与 SRR lookup | REQUIRED |
| `creation_date` | `vendor/snakescale/scripts/generate_yaml.py:114` | 否 | OPTIONAL |
| `notes` | `vendor/snakescale/scripts/generate_yaml.py:114` | 否 | OPTIONAL |
| `metadata_checked` | `vendor/snakescale/scripts/generate_yaml.py:114` | 否 | OPTIONAL |
| `modifier` | `vendor/snakescale/scripts/generate_yaml.py:115` | 否 | OPTIONAL |
| `study_id` | `vendor/snakescale/scripts/generate_yaml.py:115,122` | 是，WHERE | REQUIRED |
| `matched_experiment_id` | `vendor/snakescale/scripts/generate_yaml.py:115,149-156` | 是，但类型域待定 | REQUIRED / UNSURE |
| `experiment_alias` | `vendor/snakescale/scripts/generate_yaml.py:115,146-147,153` | 是，GSM 业务键 | REQUIRED |
| `experiment_accession` | `vendor/snakescale/scripts/generate_yaml.py:116` | 否 | OPTIONAL |
| `type` | `vendor/snakescale/scripts/generate_yaml.py:116,126-127` | 是，Ribo/RNA 分流 | REQUIRED |
| `title` | `vendor/snakescale/scripts/generate_yaml.py:116` | 否 | OPTIONAL |
| `study_name` | `vendor/snakescale/scripts/generate_yaml.py:116` | 否 | OPTIONAL |
| `design_description` | `vendor/snakescale/scripts/generate_yaml.py:117` | 否 | OPTIONAL |
| `sample_accession` | `vendor/snakescale/scripts/generate_yaml.py:117` | 否 | OPTIONAL |
| `sample_attribute` | `vendor/snakescale/scripts/generate_yaml.py:117` | 否 | OPTIONAL |
| `library_strategy` | `vendor/snakescale/scripts/generate_yaml.py:117` | 否 | OPTIONAL |
| `library_layout` | `vendor/snakescale/scripts/generate_yaml.py:118` | 否 | OPTIONAL |
| `library_construction_protocol` | `vendor/snakescale/scripts/generate_yaml.py:118` | 否 | OPTIONAL |
| `platform` | `vendor/snakescale/scripts/generate_yaml.py:118` | 否 | OPTIONAL |
| `platform_parameters` | `vendor/snakescale/scripts/generate_yaml.py:118` | 否 | OPTIONAL |
| `xref_link` | `vendor/snakescale/scripts/generate_yaml.py:119` | 否 | OPTIONAL |
| `experiment_attribute` | `vendor/snakescale/scripts/generate_yaml.py:119` | 否 | OPTIONAL |
| `submission_accession` | `vendor/snakescale/scripts/generate_yaml.py:119` | 否 | OPTIONAL |
| `sradb_updated` | `vendor/snakescale/scripts/generate_yaml.py:119` | 否 | OPTIONAL |
| `organism` | `vendor/snakescale/scripts/generate_yaml.py:120,164-181` | 是，reference lookup | REQUIRED |
| `cell_line` | `vendor/snakescale/scripts/generate_yaml.py:120` | 否 | OPTIONAL |
| `group` | `vendor/snakescale/scripts/generate_yaml.py:120` | 否 | OPTIONAL |
| `threep_adapter` | `vendor/snakescale/scripts/generate_yaml.py:120,34,47,62` | 是，cutadapt 参数 | REQUIRED |
| `fivep_adapter` | `vendor/snakescale/scripts/generate_yaml.py:120,35` | 只被旁路读取 | OPTIONAL / UNSURE |
| `threep_umi_length` | `vendor/snakescale/scripts/generate_yaml.py:121` | 否 | OPTIONAL |
| `fivep_umi_length` | `vendor/snakescale/scripts/generate_yaml.py:121` | 否 | OPTIONAL |
| `read_length` | `vendor/snakescale/scripts/generate_yaml.py:121` | 否，真实长度从 FASTQ 读 | OPTIONAL |
| `is_paired_end` | `vendor/snakescale/scripts/generate_yaml.py:121` | 否 | OPTIONAL |
| `experiment_file` | `vendor/snakescale/scripts/generate_yaml.py:121` | 否 | OPTIONAL |

### A.3 `metadata_srr`

| 列名 | 出现位置 | 被后续逻辑消费？ | 当前判定 |
|---|---|---|---|
| `id` | `vendor/snakescale/scripts/generate_yaml.py:231,249` | 否 | OPTIONAL |
| `experiment_id` | `vendor/snakescale/scripts/generate_yaml.py:231,233,249,251` | 是，WHERE / join | REQUIRED / UNSURE |
| `sra_accession` | `vendor/snakescale/scripts/generate_yaml.py:232,239,250,256` | 是，路径生成 | REQUIRED |
| `creation_date` | `vendor/snakescale/scripts/generate_yaml.py:232,250` | 否 | OPTIONAL |

## 附录 B. 备用入口 `unitmetadata_*` 列级证据矩阵

### B.1 `unitmetadata_study`

| 列名 | 出现位置 | 被后续逻辑消费？ | 当前判定 |
|---|---|---|---|
| `id` | `vendor/snakescale/scripts/generate_yaml_unitmetadata.py:97` | 是，生成 `study_id` | UNSURE |
| `creation_date` | `vendor/snakescale/scripts/generate_yaml_unitmetadata.py:97` | 否 | UNSURE |
| `notes` | `vendor/snakescale/scripts/generate_yaml_unitmetadata.py:98` | 否 | UNSURE |
| `metadata_checked` | `vendor/snakescale/scripts/generate_yaml_unitmetadata.py:98` | 否 | UNSURE |
| `modifier` | `vendor/snakescale/scripts/generate_yaml_unitmetadata.py:98` | 否 | UNSURE |
| `geo_accession` | `vendor/snakescale/scripts/generate_yaml_unitmetadata.py:99,102` | 是，study lookup | UNSURE |
| `study_accession` | `vendor/snakescale/scripts/generate_yaml_unitmetadata.py:99` | 否 | UNSURE |
| `study_title` | `vendor/snakescale/scripts/generate_yaml_unitmetadata.py:99` | 否 | UNSURE |
| `study_type` | `vendor/snakescale/scripts/generate_yaml_unitmetadata.py:100` | 否 | UNSURE |
| `study_abstract` | `vendor/snakescale/scripts/generate_yaml_unitmetadata.py:100` | 否 | UNSURE |
| `study_description` | `vendor/snakescale/scripts/generate_yaml_unitmetadata.py:100` | 否 | UNSURE |
| `xref_link` | `vendor/snakescale/scripts/generate_yaml_unitmetadata.py:101` | 否 | UNSURE |
| `submission_accession` | `vendor/snakescale/scripts/generate_yaml_unitmetadata.py:101` | 否 | UNSURE |
| `sradb_updated` | `vendor/snakescale/scripts/generate_yaml_unitmetadata.py:101` | 否 | UNSURE |
| `soft_deleted` | `vendor/snakescale/scripts/generate_yaml_unitmetadata.py:102` | 否 | UNSURE |

### B.2 `unitmetadata_experiment`

| 列名 | 出现位置 | 被后续逻辑消费？ | 当前判定 |
|---|---|---|---|
| `id` | `vendor/snakescale/scripts/generate_yaml_unitmetadata.py:114` | 是，自连接与 SRR lookup | UNSURE |
| `creation_date` | `vendor/snakescale/scripts/generate_yaml_unitmetadata.py:114` | 否 | UNSURE |
| `notes` | `vendor/snakescale/scripts/generate_yaml_unitmetadata.py:114` | 否 | UNSURE |
| `metadata_checked` | `vendor/snakescale/scripts/generate_yaml_unitmetadata.py:114` | 否 | UNSURE |
| `modifier` | `vendor/snakescale/scripts/generate_yaml_unitmetadata.py:115` | 否 | UNSURE |
| `study_id` | `vendor/snakescale/scripts/generate_yaml_unitmetadata.py:115,122` | 是，WHERE | UNSURE |
| `matched_experiment_id` | `vendor/snakescale/scripts/generate_yaml_unitmetadata.py:115,149-156` | 是，但类型域待定 | UNSURE |
| `experiment_alias` | `vendor/snakescale/scripts/generate_yaml_unitmetadata.py:115,146-147,153` | 是，GSM 业务键 | UNSURE |
| `experiment_accession` | `vendor/snakescale/scripts/generate_yaml_unitmetadata.py:116` | 否 | UNSURE |
| `type` | `vendor/snakescale/scripts/generate_yaml_unitmetadata.py:116,126-127` | 是，Ribo/RNA 分流 | UNSURE |
| `title` | `vendor/snakescale/scripts/generate_yaml_unitmetadata.py:116` | 否 | UNSURE |
| `study_name` | `vendor/snakescale/scripts/generate_yaml_unitmetadata.py:116` | 否 | UNSURE |
| `design_description` | `vendor/snakescale/scripts/generate_yaml_unitmetadata.py:117` | 否 | UNSURE |
| `sample_accession` | `vendor/snakescale/scripts/generate_yaml_unitmetadata.py:117` | 否 | UNSURE |
| `sample_attribute` | `vendor/snakescale/scripts/generate_yaml_unitmetadata.py:117` | 否 | UNSURE |
| `library_strategy` | `vendor/snakescale/scripts/generate_yaml_unitmetadata.py:117` | 否 | UNSURE |
| `library_layout` | `vendor/snakescale/scripts/generate_yaml_unitmetadata.py:118` | 否 | UNSURE |
| `library_construction_protocol` | `vendor/snakescale/scripts/generate_yaml_unitmetadata.py:118` | 否 | UNSURE |
| `platform` | `vendor/snakescale/scripts/generate_yaml_unitmetadata.py:118` | 否 | UNSURE |
| `platform_parameters` | `vendor/snakescale/scripts/generate_yaml_unitmetadata.py:118` | 否 | UNSURE |
| `xref_link` | `vendor/snakescale/scripts/generate_yaml_unitmetadata.py:119` | 否 | UNSURE |
| `experiment_attribute` | `vendor/snakescale/scripts/generate_yaml_unitmetadata.py:119` | 否 | UNSURE |
| `submission_accession` | `vendor/snakescale/scripts/generate_yaml_unitmetadata.py:119` | 否 | UNSURE |
| `sradb_updated` | `vendor/snakescale/scripts/generate_yaml_unitmetadata.py:119` | 否 | UNSURE |
| `organism` | `vendor/snakescale/scripts/generate_yaml_unitmetadata.py:120,164-181` | 是，reference lookup | UNSURE |
| `cell_line` | `vendor/snakescale/scripts/generate_yaml_unitmetadata.py:120` | 否 | UNSURE |
| `group` | `vendor/snakescale/scripts/generate_yaml_unitmetadata.py:120` | 否 | UNSURE |
| `threep_adapter` | `vendor/snakescale/scripts/generate_yaml_unitmetadata.py:120,34,47,62` | 是，cutadapt 参数 | UNSURE |
| `fivep_adapter` | `vendor/snakescale/scripts/generate_yaml_unitmetadata.py:120,35` | 只被旁路读取 | UNSURE |
| `threep_umi_length` | `vendor/snakescale/scripts/generate_yaml_unitmetadata.py:121` | 否 | UNSURE |
| `fivep_umi_length` | `vendor/snakescale/scripts/generate_yaml_unitmetadata.py:121` | 否 | UNSURE |
| `read_length` | `vendor/snakescale/scripts/generate_yaml_unitmetadata.py:121` | 否 | UNSURE |
| `is_paired_end` | `vendor/snakescale/scripts/generate_yaml_unitmetadata.py:121` | 否 | UNSURE |
| `experiment_file` | `vendor/snakescale/scripts/generate_yaml_unitmetadata.py:121` | 否 | UNSURE |

### B.3 `unitmetadata_srr`

| 列名 | 出现位置 | 被后续逻辑消费？ | 当前判定 |
|---|---|---|---|
| `id` | `vendor/snakescale/scripts/generate_yaml_unitmetadata.py:231,249` | 否 | UNSURE |
| `experiment_id` | `vendor/snakescale/scripts/generate_yaml_unitmetadata.py:231,233,249,251` | 是，WHERE / join | UNSURE |
| `sra_accession` | `vendor/snakescale/scripts/generate_yaml_unitmetadata.py:232,239,250,256` | 是，路径生成 | UNSURE |
| `creation_date` | `vendor/snakescale/scripts/generate_yaml_unitmetadata.py:232,250` | 否 | UNSURE |

## 附录 C. workflow 层对 schema 的外部约束

| 约束 | 结论 | 证据 |
|---|---|---|
| study 参数格式 | 允许 `GSE...`、`GSE..._dedup`、`GSE..._test`，数据库 lookup 统一回退到 `GSE...` | `vendor/snakescale/scripts/generate_yaml.py:87-95` |
| RNA-Seq 是否必须存在 | 不必须；若匹配不到 SRR，则删掉 `rnaseq` 节点继续 | `vendor/snakescale/scripts/generate_yaml.py:244-259,299-312` |
| Ribo-Seq 是否必须存在 | 必须；没有 Ribo-Seq experiment 或没有 SRR 都会失败 | `vendor/snakescale/scripts/generate_yaml.py:145-147,281-295` |
| organism 值域 | 至少应覆盖 `references.yaml` 中的 lower-case keys | `vendor/snakescale/scripts/generate_yaml.py:169-181`，`vendor/snakescale/scripts/references.yaml:8-42` |
| SRR 文件命名约定 | 始终拼 `_1.fastq.gz`，未见 paired-end 分支 | `vendor/snakescale/scripts/generate_yaml.py:273,279`，`vendor/snakescale/Snakefile:171,202,213,217` |
| RNA-Seq 是否与 Ribo-Seq 同表 | 是；`metadata_experiment.type` 决定分流 | `vendor/snakescale/scripts/generate_yaml.py:126-127` |
| 默认 pipeline 是否直接碰 sqlite | 只在 yaml 生成入口读取；后续规则全基于 YAML / FASTQ | `vendor/snakescale/Snakefile:38-42,86-217,769-959` |
| classify_studies 是否增加新的数据库列需求 | 否；它只消费 YAML 和 FASTQ 统计，不新增 sqlite schema 需求 | `vendor/snakescale/Snakefile:769-927` |

## 附录 D. 历史参考文件快照结论

| 参考文件 | 观察 | 结论 |
|---|---|---|
| `vendor/snakescale/db/README.md` | 只写了“运行前必须把 `db.sqlite3` 放在该目录” | 不提供 schema 权威信息 |
| `vendor/snakescale/db/create_database.sql` | 提供了 `metadata_*` 三张表与示例插入 | 可作为历史 DDL 参考，但缺失 `unitmetadata_*` |
| `vendor/snakescale/db/db.sqlite3` | 只有 `metadata_*` 三张表，且两个关键 join 列被做成 `TEXT` | 是历史样例，不应覆盖源码语义 |

## 附录 E. 最小默认 schema 建议稿（非实施，仅供用户拍板）

> 本附录不是实施方案，只是把 §2 的 REQUIRED 结果压缩成一份“如果只保默认 pipeline，源码语义至少要求什么”。

| 表 | 最低必备列 | 备注 |
|---|---|---|
| `metadata_study` | `id`, `geo_accession` | `geo_accession` 建议唯一 |
| `metadata_experiment` | `id`, `study_id`, `matched_experiment_id`, `experiment_alias`, `type`, `organism`, `threep_adapter` | `matched_experiment_id` 建议与 `id` 同域；可空 |
| `metadata_srr` | `experiment_id`, `sra_accession` | `experiment_id` 建议与 `metadata_experiment.id` 同域 |

### E.1 这份“最小默认 schema”刻意没有直接写进 DDL 的东西

- 没有把 `AUTOINCREMENT` 写死，因为源码本身只要求稳定可比较的 id
- 没有把 `fivep_adapter` 放进最低必备列，因为它不影响当前默认逻辑结果
- 没有把 `unitmetadata_*` 放进最低必备列，因为默认 `Snakefile` 不调用它
- 没有把所有 SELECT-only 列列进最低必备列，因为本报告区分了“语义必需”和“零改动兼容列”
- 如果用户要实现“完全不改 vendor 源码也不改 raw SQL”，则仍应把 OPTIONAL 列一并保留为兼容列

### E.2 用户拍板后最可能进入下一轮的问题

- id 如何分配：顺序整数、稳定哈希还是沿用历史样例
- `matched_experiment_id` 如何从 metadata 推导：靠样本配对规则还是外部映射
- `threep_adapter` 缺失时统一填 `''` 还是 `NULL`
- 是否保留 `unitmetadata_*` 与其对应入口
- 是否保留所有 SELECT-only 兼容列，还是在后续最小化 vendor query 后进一步瘦身
