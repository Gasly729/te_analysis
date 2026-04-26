# snakescale Input Contract (reverse-engineered)

## 0. 溯源

- Vendor path: `vendor/snakescale`
- Commit SHA locked at recon: `b918e75f877262dca96665d18c3b472675f30a6d`
- Upstream: <https://github.com/RiboBase/snakescale>
- Entry point: `Snakefile` (declared via `configfile: "config/config.yaml"` at `vendor/snakescale/Snakefile:14`)
- Schema validator: `schemas/config.schema.yaml` is called at `vendor/snakescale/Snakefile:17`
- Downstream runner: Nextflow RiboFlow is invoked by `rule run_riboflow` via `shell("nextflow riboflow/RiboFlow.groovy -params-file {input.study_yaml} -profile {params.profile}")` at `vendor/snakescale/Snakefile:950`

snakescale is therefore **a Snakemake orchestrator** that (1) takes a list of studies, (2) generates **per-study** RiboFlow `.yaml` files, (3) runs adapter/length QC, and (4) shells out to Nextflow `RiboFlow.groovy`.

## 1. 入口文件契约

snakescale has **two layers** of YAML:

- **L1 — orchestrator config** (`config/config.yaml`, validated by `schemas/config.schema.yaml`): lists which studies to run and run-wide knobs.
- **L2 — per-study RiboFlow project file** (`input/project/{gse_only}/{study}.yaml`): describes one study's adapters, FASTQ paths, references. This is derived from the template `project.yaml` by `scripts/generate_yaml.py`.

### 1.1 L1 orchestrator config — required fields

| 字段路径 | 类型 | 作者出处（文件:行） | 我方 metadata.csv 对应列 / 推导方式 | 置信度 |
|---|---|---|---|---|
| `studies` | `array[string]` | `schemas/config.schema.yaml:15-19,75-77`；消费于 `Snakefile:21` | 从 `metadata.csv.study_name` 列唯一化（形如 `GSE128216`）；`_dedup` / `_test` 后缀由上层决策附加（`generate_yaml.py:87-95`） | 高 |
| `riboflow_config` | `string` | `schemas/config.schema.yaml:12-14,77`；消费于 `Snakefile:938` (`params.profile`) | **作者未暴露到 metadata 层** — 是 Nextflow profile 名（如 `stampede_local`，见 `config/config.yaml:13`），需在我方 config.py 中常量化 | 中 |
| `threads.*` | `object{string→int}` | `schemas/config.schema.yaml:21-40`；required set 包含 `threads` (`schemas/config.schema.yaml:78`) | 运行时资源参数，与 metadata 无关；由 T2 `config.py` 暴露环境变量 | 高 |
| `override` | `boolean` (default `false`) | `schemas/config.schema.yaml:5-8`；消费于 `Snakefile:949` | 运行开关，非 metadata 字段 | 高 |
| `adapter_threshold` | `integer` (default `50`) | `schemas/config.schema.yaml:9-11`；消费于 `Snakefile:363` | 运行阈值，非 metadata 字段 | 高 |
| `check_adapter.skipped_reads` / `check_adapter.sample_size` | `integer` | `schemas/config.schema.yaml:41-49`；消费于 `Snakefile:287-288` | 运行参数 | 高 |
| `guess_adapter.{skipped_reads, sample_size, min_length, max_length, skipped_nucleotides, seed_length, match_ratio}` | `integer/number` | `schemas/config.schema.yaml:50-73`；消费于 `Snakefile:682-688` | 运行参数 | 高 |

**required set**（`config.schema.yaml:75-78`）：`studies`, `riboflow_config`, `threads`。其余默认值已由 schema 规定。

### 1.2 L2 per-study project.yaml — required fields

作者的 `project.yaml` 模板（`vendor/snakescale/project.yaml`）定义了 **RiboFlow** 消费的字段。`scripts/generate_yaml.py` 使用 **db.sqlite3** 中 `metadata_study` / `metadata_experiment` / `metadata_srr` 三张表 **填充** 此模板并写入 `input/project/{GSE}/{study}.yaml`（`generate_yaml.py:319-324`）。

| 字段路径 | 类型 | 作者出处（文件:行） | 我方字段 | 置信度 |
|---|---|---|---|---|
| `do_fastqc` | `boolean` | `project.yaml:4` | 非 metadata，默认 `true` 保持 | 高 |
| `do_check_file_existence` | `boolean` | `project.yaml:7` | 非 metadata，保持 `true` | 高 |
| `deduplicate` | `boolean` | `project.yaml:11`；被 `generate_yaml.py:317` 根据 study 名尾缀 `_dedup` 覆写 | 由 study 名后缀派生 | 高 |
| `do_rnaseq` | `boolean` | `project.yaml:19`；被 `generate_yaml.py:314` 置为 `'rnaseq' in ribo_yaml` | 由 `metadata.csv.matched_RNA-seq_experiment_alias` 是否非空派生 | 高 |
| `do_metadata` | `boolean` | `project.yaml:24` | 非 metadata，默认 `false` | 高 |
| `clip_arguments` | `string` (cutadapt CLI) | `project.yaml:28`；被 `generate_yaml.py:159-160` 重新拼装（基于所有 riboseq 实验的 `threep_adapter`） | 由 `metadata.csv.threep_adapter` 合并推导（`generate_clip_sequence` 在 `generate_yaml.py:39-67`） | 高 |
| `mapping_quality_cutoff` | `integer` | `project.yaml:37` | 非 metadata，默认 20 | 高 |
| `alignment_arguments.{filter,transcriptome,genome}` | `string` | `project.yaml:42-52` | 非 metadata | 高 |
| `ribo.{ref_name, metagene_radius, left_span, right_span, read_length.min/max, coverage}` | mixed | `project.yaml:56-64` | 非 metadata，RiboPy 参数 | 高 |
| `output.output.base`, `output.intermediates.base` | `string` | `project.yaml:72-94`；被 `generate_yaml.py:315-316` 覆写为 `output/{study}` / `intermediates/{study}` | 由我方运行目录布局派生 | 高 |
| `input.reference.filter` | `string` (bowtie2 idx glob) | `project.yaml:108-111`；填充于 `generate_yaml.py:186-187`；来源 `scripts/references.yaml` | 由 `metadata.csv.organism` 映射 → `scripts/references.yaml[organism].filter` | 高 |
| `input.reference.transcriptome` | `string` (glob) | `project.yaml:114-115`；同上 | 同上 | 高 |
| `input.reference.regions` | `string` (.bed) | `project.yaml:118-119`；同上 | 同上 | 高 |
| `input.reference.transcript_lengths` | `string` (.tsv) | `project.yaml:121-122`；同上 | 同上 | 高 |
| `input.fastq_base` | `string` (路径前缀) | `project.yaml:126` | 我方固定为 `""`（直接给绝对/相对完整路径） | 高 |
| `input.fastq` | `object{GSM → list[str]}` | `project.yaml:127`；填充于 `generate_yaml.py:297`；消费于 `Snakefile:100-108` | `metadata.csv.experiment_alias`（GSM）→ `[{download_path}/{GSE}/{GSM}/{SRR}_1.fastq.gz, ...]` | 中（SRR 解析见 §6）|
| `input.root_meta` | `string` (yaml 路径) | `project.yaml:131-134` | 非 metadata，默认 `""` | 高 |
| `input.metadata.base` / `input.metadata.files` | `string / object` | `project.yaml:137-143` | 非 metadata，默认空 | 高 |
| `rnaseq.clip_arguments` | `string` | `project.yaml:148`；被 `generate_yaml.py:162` 重新拼装 | 由 matched RNA-Seq 实验的 adapter 派生 | 高 |
| `rnaseq.fastq_base` | `string` | `project.yaml:152` | 同 ribo | 高 |
| `rnaseq.deduplicate` | `boolean` | `project.yaml:154`；被 `generate_yaml.py:307` 覆写 | 由 study 后缀派生 | 高 |
| `rnaseq.filter_arguments` | `string` | `project.yaml:155` | 非 metadata | 高 |
| `rnaseq.bt2_argumments` | `string` (注意作者拼写 `argumments`) | `project.yaml:156` | 非 metadata | 高 |
| `rnaseq.fastq` | `object{GSM → list[str]}` | `project.yaml:159`；填充于 `generate_yaml.py:300` | `metadata.csv.matched_RNA-seq_experiment_alias` 关联到对应 RNA GSM → SRR fastq.gz 列表 | 中（SRR 解析见 §6）|

### 1.3 数据布局要求

`generate_yaml.py:262,273,279` 明确 FASTQ 路径构造：

```
{download_path}/{GSE}/{GSM}/{SRR}_1.fastq.gz
```

- `download_path` 是 `generate_yaml.py` 的 `--download_path` 参数（`generate_yaml.py:42` Snakefile 中硬编码为 `"input/fastq/"`）。
- `Snakefile:243-248` 中 `rule download_fastq_files` 运行 `prefetch {accession} && fasterq-dump -O {dir} {accession}` → 作者**默认会下载**。
- 但 `rule download_fastq_files:242` 先执行 `if not os.path.isfile(cur_file) and not os.path.isfile(output[0])`，**文件已存在则跳过下载** → 我方 pre-stage FASTQ 到上述路径即可 no-op 该规则。
- 参考索引由 `vendor/snakescale/scripts/download_reference.py` + `scripts/references.yaml` 提供（README:55-60）；不由我方 metadata 管。
- adapter 由 metadata 提供（`threep_adapter` 列）或作者 `guess_adapters.py` 动态猜测（`Snakefile:631-766`）。

## 2. db 文件契约

作者**使用** sqlite 文件（`vendor/snakescale/db/db.sqlite3` — **不在 submodule 内，来自 db-sqlite 仓**，见 `README.md:21-30`）。`generate_yaml.py:97-123` 查询三张表：

- `metadata_study`（按 `geo_accession` 过滤）：`id, creation_date, notes, metadata_checked, modifier, geo_accession, study_accession, study_title, study_type, study_abstract, study_description, xref_link, submission_accession, sradb_updated, soft_deleted`
- `metadata_experiment`（按 `study_id` 过滤）：`id, creation_date, notes, metadata_checked, modifier, study_id, matched_experiment_id, experiment_alias, experiment_accession, type, title, study_name, design_description, sample_accession, sample_attribute, library_strategy, library_layout, library_construction_protocol, platform, platform_parameters, xref_link, experiment_attribute, submission_accession, sradb_updated, organism, cell_line, group, threep_adapter, fivep_adapter, threep_umi_length, fivep_umi_length, read_length, is_paired_end, experiment_file`
- `metadata_srr`（按 `experiment_id` 过滤）：`id, experiment_id, sra_accession, creation_date`

**我方替代**：不使用 db.sqlite3；将上述三表"展平"合并为**单张** `data/raw/metadata.csv`（run-level 扁平表，H2 起含 `run` + `fastq_path` 两列）。见 `docs/srr_resolution_design_v2.md`。

## 3. classify_studies gate

作者在 `Snakefile:769-926` 实现 `rule classify_studies`，基于 `check_adapter` / `check_lengths` / `guess_adapter` 三个中间 yaml 判定 study 是否进入 `run_riboflow`：

- **adapter gate**（`Snakefile:829-841`）：若 `adapter_yaml.low_adapter_files` 非空且 `length_yaml.has_all_uneven_lengths` 为 `false` 且 `guess_yaml.consensus_adapter` 为 `None` → study 判 invalid。
- **length gate**（`Snakefile:845-856`）：若 `length_yaml.uneven_files` 非空且 `has_all_uneven_lengths` 为 `false` 且无 consensus guessed adapter → invalid。
- **multiple adapters gate**（`Snakefile:865-870`）：`guess_yaml.detected_adapters` 长度 >1 → invalid。
- RNA-Seq 侧并行检查（`Snakefile:873-897`）。
- 输出：`log/success/{study}/modifications.log` 或 `log/failed/{study}/modifications.log`（`Snakefile:902-908`）；`log/valid_studies.txt`（`Snakefile:924-926`）。

**我方 `run_upstream.py` MUST NOT 重新实现 gate 逻辑**（module_contracts §M2）。

## 4. 输出契约

- RiboFlow 最终写出 `.ribo` 文件，由 snakescale `rule run_riboflow` 触发（`Snakefile:929-959`）。
- snakescale **自身**只产出：`log/status.txt`, `log/valid_studies.txt`, `log/failed/**`, `log/success/**`, `log/riboflow_status/{study}/riboflow_status.txt`。
- `.ribo` 路径由 RiboFlow.groovy 决定，**不在** snakescale 源码中显式构造；TE_model README 假设位于 `data/ribo/{study}/ribo/experiments/{GSM}.ribo`（见 `vendor/TE_model/src/ribo_counts_to_csv.py:20`）。

## 5. 我方 stage_inputs.py 落地映射表

| 我方 `metadata.csv` 列 | → snakescale 字段（L1 或 L2） | 最小转换 | 置信度 |
|---|---|---|---|
| `study_name` (e.g. `GSE128216`) | L1 `config.yaml.studies[]`（去重）；L2 用作 `{gse_only}` 路径键 | 唯一化 + 可选附加 `_dedup` / `_test` 尾缀 | 高 |
| `experiment_alias` (GSM) | L2 `input.fastq` 的 key（或 `rnaseq.fastq` key，取决于 `corrected_type`） | 直接 | 高 |
| `corrected_type` (`Ribo-Seq` / `RNA-Seq`) | 决定放入 `input.fastq` 还是 `rnaseq.fastq` | 分流 | 高 |
| `matched_RNA-seq_experiment_alias` | 决定 RNA GSM 是否进入 `rnaseq.fastq`（仅该实验关联的 RNA GSM）| 1-to-1 配对 | 高 |
| `organism` | L2 `input.reference.{filter,regions,transcript_lengths,transcriptome}` | 小写化后查 `vendor/snakescale/scripts/references.yaml` | 高 |
| `threep_adapter` | L2 `clip_arguments` （Ribo）或 `rnaseq.clip_arguments` | 走 `generate_clip_sequence` 等价算法；MVP 可直接传实验级 adapter | 高 |
| `threep_umi_length` / `fivep_umi_length` | L2 `clip_arguments` 中的 `-u` 参数前缀 | `-u {fivep_umi_length}` / UMI 裁剪规则 | 中（作者基线 base 为 `-u 1`，行 `generate_yaml.py:159`）|
| `study_name` 后缀解析（外部决策） | `deduplicate` / `_dedup` 尾缀 | study 名附加 `_dedup` → `deduplicate: true` | 高 |
| `run` / `fastq_path`（H2 新增） | `rnaseq.fastq[GSM]` / `input.fastq[GSM]` 的 SRR fastq 路径列表 | `df.groupby('experiment_alias')['fastq_path'].agg(list)` | 高 |

## 6. 已知开放问题

1. **SRR 解析缺失（阻断项）— 已于 Commit H2 解决**：作者通过 `metadata_srr` 表（SRR ↔ GSM）解析每个 GSM 对应的 SRR 列表（`generate_yaml.py:231-257`），用以构造 `{download_path}/{GSE}/{GSM}/{SRR}_1.fastq.gz`。
   - **解决方案**：采用 **方案 A**（`docs/srr_resolution_design_v2.md`）— 就地 enrich `data/raw/metadata.csv` 为 run-level 扁平表，通过 `pysradb` 查询 NCBI SRA 补齐 `run` + `fastq_path` 两列。与顶层设计 §5.2 / §9 / module_contracts §M7.MUSTNOT.3 对齐。
   - **现状**：metadata.csv 从 2644 → 4168 run-level 行（2635 unique SRX，3 unresolved，0.11%）。
   - T4 `stage_inputs.py` 可直接 `df.groupby('experiment_alias')['run'].agg(list)` 构造 `input.fastq[GSM]`，无需 sidecar 或 merge。
   - （历史参考）前版本曾在 Commit G2 中推荐 sidecar `metadata_srr.csv` 方案，违反顶层设计，已在 Commit H1 `git revert` 作废。
2. **`read_length` / `is_paired_end` 缺失（软阻断）**：作者 `metadata_experiment.is_paired_end` 为 `0`/`1`；我方 metadata 无对应列。作者代码中仅 RNA-Seq `library_layout` 用于匹配配对，snakescale 的 `Snakefile:171,202` 均硬编码 `{accession}_1.fastq.gz` → **假设全部按 single-end 文件名布局处理**（paired 会额外有 `_2.fastq.gz`，但作者代码未显式出现该路径）。T4 实施前需用户确认。
3. **`riboflow_config` profile 名**：作者 `config/config.yaml:13` 是 `stampede_local`（TACC 私有集群 profile）。我方本地必须换成自定义 profile；值非 metadata 字段，应在 T2 `config.py` 中作为常量暴露。
4. **`scripts/references.yaml`** 是作者预先枚举的 `organism → 参考文件相对路径` 字典（`generate_yaml.py:178-187`）。**作者未在代码中校验 organism 是否 **已** 下载到 `reference/` 目录**，只校验 key 在 yaml 中。T4 落地需与 T0 `download_reference.py` 协同检查文件就位。
5. **`generate_yaml.py` 的 `_test` 后缀**（`generate_yaml.py:94`）行为未在 README 暴露 — 作者未暴露用途，MVP 不支持。
6. **`input.metadata.files` 机制**（`project.yaml:137-143`）支持把 **per-experiment YAML 元数据**注入 .ribo 文件根。`generate_yaml.py` **未填充**此字段。作者未要求 → 我方默认 `do_metadata: false`、不提供。若后续需要 meta 嵌入 .ribo，再打开。
7. **DB 路径硬编码**：`Snakefile:38` 内嵌 `db="db/db.sqlite3"` — 我方不使用 db.sqlite3，因此**必须 fork 或 monkey-patch 绕过 `generate_yaml()` 调用**，或 **直接生成 `input/project/{GSE}/{study}.yaml`** 跳过 `generate_yaml` 路径（`Snakefile:36` 的 `if not os.path.isfile(study_yaml_path)` 检查允许我方预置 yaml）。推荐：stage_inputs.py **直接写** `input/project/{GSE}/{study}.yaml`，使 `generate_yaml()` 分支不触发。此策略在 T4 实施前需 sprint_plan 确认。
