# SRR 粒度决议设计

## 1. 问题陈述

作者 `vendor/snakescale/scripts/generate_yaml.py:231-257` 通过 db.sqlite3 的 `metadata_srr` 表把 GSM → SRR 列表展开为 FASTQ 路径 `{download_path}/{GSE}/{GSM}/{SRR}_1.fastq.gz`（见 `docs/snakescale_contract.md §1.3`）。我方 `data/raw/metadata.csv` 是 experiment (SRX / GSM) 级的 27 列表（见 `memory: project_metadata_schema_reality.md`），**缺失 run (SRR) 粒度字段**；并且 1 个 SRX 可对应 ≥ 1 个 SRR（单 SRX 可能有多个 run / technical replicate），无法直接 1:1 映射。

这是 T4 `stage_inputs.py` 的硬阻断项：`stage_inputs` 必须把我方 metadata 转成作者 project.yaml L2 中 `input.fastq[GSM] = [SRR_fastq_paths]` 的结构，缺 SRR → 无法构造列表。

**本 commit 的产出是决策文档，不是代码**；不修改 `data/raw/metadata.csv`，不创建 `data/raw/metadata_srr.csv`，不触达 `paxdb_filtered_sample.csv`（后者是 T6 的冲突）。

## 2. 文件系统真相

Pre-flight 阶段实测（Commit G2 时刻）：

| 维度 | 值 | 来源命令 |
|---|---|---|
| `data/raw/fastq/` 目录 | **不存在** | `ls data/raw/fastq` → `No such file or directory` |
| GSE 目录数 | 0 | `find data/raw/fastq -maxdepth 1 -mindepth 1 -type d \| wc -l` |
| GSM 目录数 | 0 | `find data/raw/fastq -maxdepth 2 -mindepth 2 -type d \| wc -l` |
| SRR 目录数 | 0 | `find data/raw/fastq -maxdepth 3 -mindepth 3 -type d \| wc -l` |
| `*.fastq.gz` 文件数 | 0 | `find data/raw/fastq -name '*.fastq.gz' \| wc -l` |
| metadata.csv 行数 | 2646（含 1 行 tag + 1 行 header → 2644 数据行） | `wc -l data/raw/metadata.csv` |
| metadata.csv 列数 | 27 | 第 2 行（真实表头）分词 |
| 与 SRR/run 相关列 | **零个**（仅有 SRX 级 `experiment_accession`, 样本级 `sample_accession`, 提交级 `submission_accession`；均非 run 级）| 正则 `srr\|sra\|accession\|run` 过滤 |
| 现存 SRR 映射文件 | **未找到** | `find . ... -name '*srr*' -o -name 'SraRunTable*' -o -name '*runinfo*'` 返回空 |

### 2.1 关键推论

- **FASTQ 尚未 stage** → 任何"从文件系统反推 SRR"的方案**当前不可验证**（方案 C 的核心假设被证伪）。
- metadata.csv 的最细粒度是 SRX (`experiment_accession`，形如 `SRX5512335`) + GSM (`experiment_alias`，形如 `GSM3667333`)，**不具备 SRR 列**。
- 仓库内无任何 `SraRunTable.csv` / `runinfo.csv` 等外部导出，说明 SRR 尚未被采集过。
- SRX → SRR 扇出分布 **当前未知**（FASTQ 未 stage、无映射文件），只能从 SRA 侧估计典型 1:1~1:4，但本项目 scope 不含 SRA 爬取。

### 2.2 SRX→SRR 扇出分布

**不可得**（FASTQ 未 stage + 无 SraRunTable 导出）。该维度将在 FASTQ stage 完成或 SraRunTable 导入后补测。

## 3. 候选方案

### 方案 A：直接扩展 metadata.csv（新增 `sra_accession` 列，一行一 SRR）

- **变更内容**：metadata.csv 从 2644 数据行 × 27 列 → N' × 28 列（N' ≥ 2644；若典型扇出 1:1.3 则 N' ≈ 3400，若 1:2 则 N' ≈ 5300）。同一 SRX 的 26 个 experiment 级字段在每个 SRR 行**原样重复**。
- **实现路径**：
  1. 用 SRA efetch / ENA API 对 2644 个 `experiment_accession` 查询 run 列表（数据层任务，不在本 scope）
  2. 新增 `sra_accession` 列；把每个 SRX 的 N 个 SRR 展开为 N 行
  3. 重算所有依赖 metadata.csv 的 md5（`tests/fixtures/gse105082/baseline.json` 等）
- **优势**：单一 SSOT；stage_inputs.py 实现最简（一次 `groupby('experiment_alias').agg(list)` 即可）
- **劣势 / 风险**：
  - 破坏 "metadata.csv = experiment 级" 的现有语义 → 同一 SRX 的实验级字段在多行重复，打破唯一性约束（如 `experiment_alias` 不再是主键）
  - baseline.json / 既有 md5 快照全部失效 → 需同步重算；T14 基线冻结成本抬升
  - 未来要对 experiment 级字段做 update 时，必须全行广播（SSOT 表面化为强、内部一致性隐式保障失效）
- **对下游契约的影响**：`stage_inputs.py` 无需做 SRX→SRR 展开，只需按 `experiment_alias` 聚合 run；`docs/metadata_schema.md` 需新增 "SRR 多行表示" 章节
- **数据层工作量**：**中**（量化：需要对 2644 SRX 发起 SRA 查询、落盘约 +1000~2700 新行；需要 ~1 处代码改动点：`docs/metadata_schema.md` 章节重写 + baseline 重算 + 潜在 ~5 处 csv 读取处增加去重逻辑）

### 方案 B：新增 sidecar `data/raw/metadata_srr.csv`（experiment-run 映射表）

- **文件契约**：2 列 `experiment_alias, sra_accession`（多对一；按行为 SRR 级，约 3000~5300 行）
- **实现路径**：
  1. 用 SRA efetch / ENA API 查 2644 SRX 的 run 列表（数据层任务，同 A）
  2. 写 `data/raw/metadata_srr.csv`
  3. 在 `docs/metadata_schema.md` 新增 §"SRR sidecar" 章节描述此文件的契约与 join 键
  4. 在 T3 schema validator 增一条：`metadata_srr.experiment_alias ⊆ metadata.experiment_alias` 的引用完整性检查
- **优势**：
  - metadata.csv 语义不变，27 列 2644 行保持；baseline.json md5 不受影响
  - 对作者 `generate_yaml.py:231-257` 查询的 `metadata_srr` 表形成**天然 1:1 语义对应**（列名 `experiment_alias`, `sra_accession` 与作者 SQL 字段同名）
  - 将来若要把此 sidecar 补回 metadata.csv（方案 A），只需一次 left-join；反之 A→B 拆分代价更高
- **劣势 / 风险**：
  - 引入两个 SSOT → 必须额外维护"两表一致性"校验（新增样本时两边同步）
  - `stage_inputs.py` 多一次 merge 逻辑
- **对下游契约的影响**：`stage_inputs.py` 需要 `metadata ⋈ metadata_srr on experiment_alias` 后再 groupby；T3 schema validator 新增跨表引用检查函数
- **数据层工作量**：**中**（量化：新建 1 个 csv，约 3000~5300 行；需要 ~3 处代码改动点：T3 schema validator 加 1 函数、T4 stage_inputs 加 1 次 merge、`docs/metadata_schema.md` 加 1 章节）

### 方案 C：文件系统反向推导（扫描 `data/raw/fastq/{GSE}/{GSM}/{SRR}*.fastq.gz`）

- **实现路径**：stage_inputs.py 内对每条 metadata 行调用 `Path.glob("data/raw/fastq/{GSE}/{GSM}/*_1.fastq.gz")`，从文件名解析 SRR 号
- **优势**：零新增 schema；FASTQ = ground truth（存在即可用）
- **劣势 / 风险**：
  - **当前 FASTQ 完全未 stage**（见 §2），stage_inputs.py 现在**无法工作**（鸡生蛋）
  - 反向推导隐式，出错时**静默丢样本**（如 GSM 目录为空 → pandas 产出空 list，默默从 project.yaml 的 `input.fastq` 缺失该 GSM）
  - 不可幂等：metadata 未变但 FASTQ 增删 → stage_inputs 产物变化，难以追踪
  - 与作者 `generate_yaml.py` 的显式表驱动范式不一致
- **对下游契约的影响**：`stage_inputs.py` 强耦合文件系统；CI / smoke test 必须伴随 FASTQ fixture 存在
- **数据层工作量**：**低**（量化：~0 行新数据 + ~20 行 stage_inputs 内的 glob/regex 代码）— 但代价在运行期鲁棒性而非一次性工作量

## 4. 方案矩阵（一眼对比）

| 维度 | A: 扩展 metadata | B: sidecar | C: 文件系统反推 |
|---|---|---|---|
| SSOT 数 | 1 (metadata) | 2 (metadata + sidecar) | 0 (文件系统) |
| metadata 语义破坏 | 是（experiment 级 → run 级） | 否 | 否 |
| `experiment_alias` 主键唯一性 | 被破坏（多行重复） | 保持 | 保持 |
| 对 baseline.json 影响 | 必须重算 | 无 | 无 |
| stage_inputs.py 复杂度 | 低（1 次 groupby） | 中（1 次 merge + 1 次 groupby） | 高（glob + 异常处理 + 静默丢失保护） |
| FASTQ 未 stage 时可用 | 可用 | 可用 | **不可用** |
| 增量 stage FASTQ 时的表现 | 无感 | 无感 | 部分样本静默失败 |
| 人工维护成本 | 低（一次展开） | 中（每次新样本补两表） | 极低（无维护） |
| 与作者 `generate_yaml.py` 对齐度 | 中（SSOT 合一但列结构偏离原表） | **高**（两表结构与作者 `metadata_experiment` + `metadata_srr` 1:1 对应） | 低（不走表驱动） |
| 新样本落盘数据量（假设 2644 SRX、扇出 1.3）| +~790 行 × 28 列 | +~3400 行 × 2 列 | 0 |

## 5. 推荐

### 5.1 推荐方案：**B（sidecar `data/raw/metadata_srr.csv`）**

### 5.2 置信度：**中**

### 5.3 推荐理由

1. **运行时可行性**：方案 C 当前**不可用**（§2 实测 FASTQ 未 stage），排除。
2. **语义保持**：方案 A 破坏 `experiment_alias` 主键唯一性；方案 B 保持现有 metadata.csv 所有语义不变（27 列 / 2644 行 / md5 不变 / baseline.json 不失效）。
3. **契约对齐**：作者原 schema 就是 `metadata_experiment` + `metadata_srr` 两张表分离（`generate_yaml.py:114-123` vs `:231-235`）；方案 B 与此 1:1 语义对应度最高，T4 实现时 code path 接近作者逻辑的直译。
4. **回滚代价**：B → A 只需 left-join 一次即可合并；A → B 要拆分 + 回填 md5，代价非对称。
5. 置信度只能给 "中"：§2 缺少 SRX→SRR 扇出实证数据；若后续 SRA 导出显示绝大多数为 1:1（扇出退化），则方案 A 的"多行重复"劣势会大幅减弱，届时可重新评估。未升为"高"是因无运行时证据支撑；未降为"低"是因架构论据充分且三方案中唯一满足"当前可用 + 不破坏现有语义"的只有 B。

### 5.4 若用户选择其他方案，T3/T4 的合同调整点

**若选 A**：
- `docs/metadata_schema.md`：新增"run 级展开"章节；将 `experiment_alias` 从 primary key 降级为非唯一外键语义
- `tests/fixtures/gse105082/baseline.json`：需重算所有 metadata md5
- T3 validator：移除 `experiment_alias unique` 校验
- T4 stage_inputs：直接 `df.groupby('experiment_alias')['sra_accession'].agg(list)` 即可
- 数据层：需一次 SRA efetch 批量查询 + 落盘展开 metadata.csv
- 黑名单冲突：本轮 prompt §6 明确禁止动 `data/raw/metadata.csv` → A 方案下一轮实现

**若选 C**：
- T3 validator：需新增"FASTQ 存在性"前置检查，否则 stage_inputs 无法运行
- T4 stage_inputs：glob 逻辑 + 每条 metadata 行的文件存在校验 + 静默失败保护（未匹配必须抛异常而非跳过）
- CI/smoke：`tests/fixtures/` 必须伴随 FASTQ 样本（或 mock 文件）
- 建议只作为 B 的 validator 内部**一致性比对**（FASTQ 实际存在的 SRR 应等于 sidecar 中声明的 SRR），不作为主 source

## 6. 落地 DoD（交给下一轮 prompt 实施）

### 6.1 新建 / 修改文件清单

- **新建** `data/raw/metadata_srr.csv`（2 列：`experiment_alias`, `sra_accession`）— 由数据层任务填充；本项目 scope 不含 SRA 采集
- **修改** `docs/metadata_schema.md`：新增 §"SRR sidecar (metadata_srr.csv)" 章节，含列定义、主键、引用完整性约束
- **修改** `src/te_analysis/stage_inputs.py`（T4）：在 SRX→SRR 展开处调用 `pd.read_csv(paths['data']['raw'] / 'metadata_srr.csv').merge(...)`

### 6.2 校验函数签名（仅声明，不实现）

```python
# T3 metadata validator 新增函数（非本轮落地）
def validate_srr_sidecar(metadata: pd.DataFrame, srr_sidecar: pd.DataFrame) -> None:
    """Validate metadata_srr.csv:
    - srr_sidecar 两列且均非空
    - srr_sidecar['experiment_alias'] ⊆ metadata['experiment_alias']
    - srr_sidecar['sra_accession'] 无重复
    - 所有 Ribo-Seq / RNA-Seq 类型的 metadata row 在 sidecar 中至少 1 条
    Raises ValueError on any violation.
    """
```

### 6.3 与 T3 metadata schema validator 的接口

- T3 主 validator 增加可选参数 `srr_sidecar_path: Path | None`；若非 None，join 后再校验
- sidecar 文件 **可选**：若未提供，T3 warn；若提供则强校验
- T4 stage_inputs 对 sidecar 缺失必须**硬失败**，不退化到方案 C

## 7. 不做的事（反边界）

- 本文档**不决定**如何**采集** SRR 值（SRA efetch / SraRunTable / ENA REST 都是数据层手段，不在本仓库 scope）
- 本文档**不修改** `data/raw/metadata.csv`
- 本文档**不创建** `data/raw/metadata_srr.csv`（等用户确认方案 B 后，作为独立数据层任务交付）
- 本文档**不处理** `paxdb_filtered_sample.csv` 就地修改 vs 零改 vendor 的冲突（T6 专属）
- 本文档**不决定** SRR 缺失样本的回退策略（如 dry-run 跳过 vs 硬失败；留给 T4 实施者）
