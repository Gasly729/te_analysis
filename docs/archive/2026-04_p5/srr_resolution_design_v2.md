# SRR 粒度决议设计 v2

## 0. 上一版 G2（方案 B）为什么错 — 废止声明

前版 `docs/srr_resolution_design.md`（Commit G2 = `2433a9d`，已在 Commit H1 = 上一 commit 被 `git revert`）**推荐方案 B**（sidecar `metadata_srr.csv`）。此推荐**违反**本项目三处刚性约束：

1. **`docs/te_analysis_top_level_design_v1.md §5.2`** — metadata.csv 必列含 `run | str | SRR/run-level ID（多 run 时每行一个）`。顶层设计从来就是要求 run-level 扁平表。
2. **`docs/te_analysis_top_level_design_v1.md §9` 砍掉清单** — `data/raw/metadata_runs.tsv / metadata_runs_unresolved.tsv` 被明文砍掉，砍掉理由原文："SRX↔SRR 展开应内联在 `metadata.csv` 里（每行 one run）"。方案 B 的 `metadata_srr.csv` 就是此被砍模式的同形替代。
3. **`docs/te_analysis_module_contracts_v1.md §M7.MUSTNOT.3`** — "**禁止**把 metadata 拆成多个文件（`experiments.csv` + `runs.csv` 等）—— 一张表，扁平"。方案 B 直接违反。

**根因**：G2 分析未交叉引用顶层设计和 module_contracts，被 snakescale 作者的两表（`metadata_experiment` + `metadata_srr`）schema 误导，又把"metadata.csv md5 不能变"当成伪约束，导致推导路径系统性错位。

**本 v2 推荐方案 A**（就地 enrich `metadata.csv` 为 run-level 扁平表），并已在 Commit H2 中**真实落盘执行**。

## 1. 问题陈述

作者 `vendor/snakescale/scripts/generate_yaml.py:231-257` 通过 db.sqlite3 的 `metadata_srr` 表把 GSM → SRR 展开为 FASTQ 路径 `{download_path}/{GSE}/{GSM}/{SRR}_1.fastq.gz`。我方必须向 snakescale 提供等效的 run-level 映射。

本项目选择**在本地 `metadata.csv` 内联展开**（方案 A），数据来源为 NCBI SRA（通过 `pysradb.SRAweb().srx_to_srr()` 查询）。

## 2. 文件系统真相（H2 执行前）

| 维度 | 值 |
|---|---|
| `data/raw/fastq/` 目录 | 不存在（FASTQ 尚未 stage） |
| metadata.csv（pre-H2） | 2646 行 × 27 列（数据行 2644；独立 SRX 2635） |
| metadata.csv 中 SRR 列 | 零个 |
| 现存 SRR 映射文件 | 无 |

（证据原始输出见 Commit G2 被 revert 文档 §2；数据未变）

## 3. 现行方案：A — 就地 enrich metadata.csv

### 3.1 字段扩展

在 metadata.csv 末尾新增两列：

| 列名 | 类型 | 含义 | 来源 |
|---|---|---|---|
| `run` | str | SRA run accession (SRR.../ERR...) | `pysradb.SRAweb().srx_to_srr()` 查询 NCBI |
| `fastq_path` | str | 相对 `data/raw/` 的 FASTQ 声明路径 | 规则拼装：`fastq/{study_name}/{experiment_alias}/{run}_1.fastq.gz` |

### 3.2 展开规则（run-level flattening）

- 同一 SRX 对应 N 个 SRR → 在输出表中复制该 SRX 所在行 N 次，每行填入一个 SRR；所有其他 27 列字段原样复制
- 复合主键从 (`experiment_alias`) 升级为 (`experiment_alias`, `run`)
- unresolved SRX（pysradb 查不到 SRR）**保留原行**，`run` 和 `fastq_path` 置空 — T3 validator 将来对此报警，不静默丢弃

### 3.3 数据量实测（H2 真实运行结果）

- Input: 2644 experiment-level 行，2635 unique SRX
- pysradb 返回: 4159 SRX→SRR 映射
- Output: **4168 run-level 行**（含 3 个 unresolved SRX 保留）
- **Unresolved SRX: 3 / 2635 = 0.11%**（远低于 5% 停工阈值）

### 3.4 扇出分布实测

| fanout (SRR per SRX) | # SRX |
|---|---|
| 1 | 2295（87.1%）|
| 2 | 149 |
| 3 | 41 |
| 4 | 19 |
| 5 | 11 |
| 6 | 3 |
| 7 | 12 |
| 8 | 55 |
| 9 | 4 |
| 10 | 4 |
| 12 | 19 |
| 14 | 2 |
| 16 | 13 |
| 17 | 1 |
| 19 | 1 |
| 21 | 1 |
| 28 | 1 |
| 59 | 1 |
| 84 | 1 |

绝大多数（87.1%）SRX 是 1:1 单 run；长尾存在最高 1:84 的 SRX（少数 high-replicate 实验）。

## 4. NCBI 查询管线（pysradb 实现）

### 4.1 工具与依赖

- 工具：`pysradb>=2.0`（纯 Python，pip/conda 可装）
- 核心 API：`pysradb.sraweb.SRAweb().srx_to_srr(list[str]) -> DataFrame`
- 返回字段：`experiment_accession, run_accession, study_accession, ...`（共 24 列，本项目仅取前两列）
- 注入点：`environment.yml` 的 pip 段 +1 行 `pysradb>=2.0`

### 4.2 批处理与鲁棒性

- **Batch size = 50**（实测 NCBI eutils 对 500-SRX query 会 SSL EOF；50 稳定）
- **Retry**: 每 chunk 最多 3 次，sleep 5/10/15s
- **Rate limit**: pysradb 自带 NCBI 3 req/s 遵守，不需额外节流

### 4.3 落盘一致性

- 写 output 前 `shutil.copy2(input, backup)` 生成 `data/raw/metadata.csv.preH2.bak`
- 写 output 时保留 row-0 "Curated Data,..." tag 行（填逗号对齐新列数）
- 写失败不破坏 input（先 backup 再 overwrite；原子性由 fs 保障）

### 4.4 实际执行记录（本 H2 commit 内）

```text
[enrich] input rows=2644 unique SRX=2635
[enrich]   chunk 1..53 (0-2635/2635)
[enrich] pysradb returned 4159 SRX->SRR mappings
[enrich] wrote report -> data/raw/_srr_enrichment_report.md
[enrich] backup -> data/raw/metadata.csv.preH2.bak
[enrich] wrote enriched metadata -> data/raw/metadata.csv (4168 rows)
```

总耗时约 4 分钟（chunk 间 NCBI 响应主导）。

## 5. `fastq_path` 填充策略

- 格式：`fastq/{study_name}/{experiment_alias}/{run}_1.fastq.gz`（贴合 snakescale `generate_yaml.py:262,273,279` 的 `{download_path}/{GSE}/{GSM}/{SRR}_1.fastq.gz` 路径）
- **声明性语义**：本字段是 metadata 承诺的未来路径；FASTQ 未 stage 时**不校验**文件存在性。校验由 T3 validator（可选模式）或 T4 `stage_inputs.py`（硬模式）负责
- paired-end 支持：目前仅声明 `_1.fastq.gz`；若 `library_layout == PAIRED`，T4 实施时需同步声明 `_2.fastq.gz`（下轮扩展点）

## 6. 反面参考：为什么不选 B / C（历史文档，不执行）

### 方案 B（sidecar `metadata_srr.csv`）

- 违反顶层 §5.2 / §9 砍掉清单 / M7.MUSTNOT.3（见 §0）
- 引入双 SSOT 一致性维护负担
- 与 top-level 设计意图对立

### 方案 C（文件系统反推）

- FASTQ 当前完全未 stage → 当下即不可用
- 隐式推导 + 静默失样本风险
- 与显式表驱动范式冲突

## 7. 落地 DoD 与下游影响

### 7.1 已完成（本 H2 commit）

- [x] `data/raw/metadata.csv`: 2644 → 4168 行，+ 2 列（`run`, `fastq_path`）
- [x] `data/raw/metadata.csv.preH2.bak`: 原文件备份
- [x] `data/raw/_srr_enrichment_report.md`: unresolved / fanout 报告
- [x] `scripts/enrich_metadata_srr.py`: 一次性 pysradb 查询脚本（≤ 80 行）
- [x] `environment.yml`: pip 段 + `pysradb>=2.0`

### 7.2 对下游契约的影响

- **T3 metadata schema validator**（未实现）：需按本文档更新 run-level 主键规则；新增"unresolved run 警告"；引用 `run` + `fastq_path` 列定义
- **T4 `stage_inputs.py`**（未实现）：简化为 `df.groupby('experiment_alias')['run'].agg(list)`，不需 merge；按 `fastq_path` 直接构造 `project.yaml` 的 `input.fastq[GSM] = [fastq_path...]`
- **`tests/fixtures/gse105082/baseline.json`**：需重算（metadata.csv md5 已变）；列入 **T14** baseline 刷新任务，**本轮不处理**
- **T6 `paxdb_filtered_sample.csv`**：不受影响，继续由 T6 处理

### 7.3 对 `src/te_analysis/config.py` 的影响

**零影响**。config.py / paths.toml 只负责路径 SSOT；不接触 metadata schema。

## 8. 不做的事（反边界）

- 本文档不决定 FASTQ 如何下载（数据层任务）
- 本文档不实现 T3 validator
- 本文档不实现 T4 stage_inputs
- 本文档不重算 baseline.json（T14）
- 本文档不处理 paxdb 就地改 vs 零改 vendor 冲突（T6）
