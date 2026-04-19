# te_analysis Progress Snapshot

**快照时间**：2026-04-19 UTC+08:00
**分支**：`design/v1-minimal`（HEAD=`f08f363`）
**上次 push**：`db59910`（远端 `origin/design/v1-minimal`）— 本地领先 **20 个 commit**
**用途**：跨 session 交接 / Claude 冷启动 ground truth / 人类快速回顾

---

## 0. 项目一句话总纲

本仓是一个 **CCDS 外壳**，把用户本地 FASTQ + metadata 喂给 **原封不动** 的 `vendor/snakescale`（上游）和 `vendor/TE_model`（下游），自写代码仅限 "metadata → project.yaml + FASTQ 符号链接" 的薄层胶水。

**项目宪法**（只读，不改）：

- `docs/te_analysis_top_level_design_v1.md` — 顶层设计
- `docs/te_analysis_module_contracts_v1.md` — 14 个模块的职责合同（M1-M14 + GC-1/2/3 + DoD）
- `docs/te_analysis_sprint_plan_v1.md` — T0-T14 任务分解 + DAG + 里程碑

**若 Claude 下一轮开始前迷失方向**：读这三份文档 > 读本 snapshot > 看 git log > 看代码。

---

## 1. 任务进度表（T0-T14，全量）

| ID | 名称 | 状态 | 关键产物 | 决胜 commit |
|---|---|---|---|---|
| **T0** | Vendor Recon | ✅ | `references/vendor_contracts.md` + `docs/{snakescale,te_model}_contract.md` + `docs/vendor_sha_recommendation.md` | F4 + L4 |
| **T1** | CCDS Skeleton | ✅ | 目录树 / submodule 锁 SHA / Makefile 骨架 / `environment.yml` | `09461fd` + `63dd49b` + G1 |
| **T2** | `config.py` | ✅ | `src/te_analysis/config.py` + `configs/paths.toml` | G3 |
| **T3** | metadata schema + 填充 | ✅ | `data/raw/metadata.csv` (4168 run-level 行 × 30 列) + `docs/metadata_schema.md` | H2 + J1 + J2 + J3 |
| **T4** | `stage_inputs.py` | ✅ | `src/te_analysis/stage_inputs.py` + 双测 | K1 + K2 + K3 + K4 |
| **T5** | `run_upstream.py` | ✅ | `src/te_analysis/run_upstream.py` + `test_run_upstream.py` | L1 |
| **T6** | `run_downstream.py` | ✅（schema 级）| `src/te_analysis/run_downstream.py` + `test_run_downstream.py` | L2 |
| **T7** | Makefile | ✅ | `Makefile`（7 target + clean）| L3 |
| **T8** | GSE132441 上游 E2E | ⬜ 未启动 | 需 snakemake + nextflow + `vendor/snakescale/reference/` 完整部署 | — |
| **T9** | GSE105082 下游 E2E + 数值对齐 | ⬜ 未启动 | 需真实 `.ribo` + R + TE_model 依赖 + `tests/fixtures/gse105082/baseline_outputs/` 重算 | — |
| **T10** | `stage_inputs` 单测 | ✅ | 8 件于 `test_stage_inputs.py` + 7 件于 `test_stage_inputs_schema.py` | K2 + K3 |
| **T11** | 下游冒烟测试 | ⬜ 未启动（需 T9 产物）| — | — |
| **T12** | 旧代码清理 | 🟡 **非正式达成** | F1-F4 + I + L5 已移除所有违规遗产；正式启动需等 T8 AND T9 绿 | — |
| **T13** | 文档定稿 | ⬜ 未启动（需 T12 正式绿）| — | — |
| **T14** | 基线冻结 | ⬜ 未启动（需 T12）| — | — |

### 里程碑

- **M-Alpha (T0) ✅**
- **M-Bravo (T1+T2+T3) ✅**
- **M-Charlie (T4+T5+T6) ✅**
- **M-Delta (T7+T8+T9)** 🟡 T7 ✅；T8 / T9 未启动
- **M-Echo (T12)** ⬜
- **M-Final (T13+T14)** ⬜

**进度估计**：14 任务中 8 件完全绿 + 1 件降级绿 = **~64%**；距 M-Final 还差 **T8 → T9 → T11 → T12 → T13/T14** 五步。

---

## 2. 完整 Commit 时间轴

按时间倒序，已跟 sprint plan 任务对应：

```text
f08f363 L6  docs: progress snapshot for cross-session handoff
df61603 L5  chore: remove stale prompt doc after T0 completion
7bb4fea L4  docs(t0): aggregate vendor contracts → references/vendor_contracts.md
325f195 L3  feat(t7): Makefile unified entry
bd200bd L2  feat(t6): run_downstream.py thin wrapper
d209a2a L1  feat(t5): run_upstream.py thin wrapper
0a4b7c8 K4  docs(t4): architecture + reproducibility + backlog sync
a8bd709 K3  test(t4): project.yaml schema validator
fac349e K2  test(t4): stage_inputs unit tests
acea46c K1  feat(t4): implement stage_inputs.py
50f7cf9 I   purge: remove orphaned legacy scripts per top_level §9 cut-list
f54a581 J3  test(t3): verification tool + backlog absorption
8fd2e9f J2  docs(t3): complete metadata_schema.md field definitions
9470bb2 J1  fix(t3): align fastq_path to real disk layout + add R2 column
9ce9d98 H3  docs: sync schema + contract docs with H2 run-level enrichment
e06d6ad H2  feat(t3-prereq): SRR run-level enrichment via pysradb
beaf752 H1  revert: G2 SRR sidecar recommendation
5534d6e G3  feat(t2): config.py + paths.toml — SSOT for repo paths
2433a9d G2  docs(t3-prereq): SRR granularity resolution (REVERTED by H1)
58b80d6 G1  deps(vendor): formalize SHA pin for snakescale + TE_model
db59910 ←── origin/design/v1-minimal（push 线）
9636bcd F4  docs(t0): vendor recon
681476c F2  purge: remove superseded legacy docs
b25c4e8 F1  purge: retire broken / orphaned legacy tests
5db070d E3  purge: remove dual package manager + dead legacy tests
0336ef0 E2  purge: remove legacy data/config/report directories
54cb892 E1  purge: remove residual legacy Python packages
397d6db     preserve: migrate high-value legacy assets for T9/T11 baseline
63dd49b     vendor: add snakescale + TE_model submodules
09461fd     scaffold: CCDS directory layout + stub modules
3f9e32d     prune: remove self-invented ingestion layer per module_contracts §9
```

**注意 G2 → H1 的反转**：G2 曾错误推荐 sidecar `metadata_srr.csv`，与顶层 §5.2/§9 + M7.MUSTNOT.3 冲突 → H1 `git revert`，H2 落地正确方案 A（pysradb NCBI 查询 + 就地 enrich metadata.csv 为 run-level 扁平表）。

---

## 3. 当前仓库状态

### 3.1 `git status`

- 工作区**干净**（`git status --porcelain` 除 vendor untracked 外空）
- 仅 `vendor/snakescale` 有 untracked `reference/`（用户预置的 bowtie2 索引库，非本项目产物，vendor tracked SHA 未动）
- 未 push；`design/v1-minimal` 领先 `origin/design/v1-minimal` 20 commit

### 3.2 Submodule HEAD（已锁定，严禁 rebase）

| Submodule | SHA |
|---|---|
| `vendor/snakescale` | `b918e75f877262dca96665d18c3b472675f30a6d` |
| `vendor/TE_model` | `0b42e3f756e20b9954548b65ff8a64ae063d9a89` |

### 3.3 测试状态

```bash
PYTHONPATH=src python -m pytest tests/ -v
# 35 passed in ~2.4s
```

| 文件 | 件数 | 覆盖 |
|---|---|---|
| `tests/test_config.py` | 5 | `load_paths()` + REPO_ROOT 标记 + schema 校验 |
| `tests/test_stage_inputs.py` | 8 | happy path (GSE132441) + 幂等 + 5 raise 分支 + CLI |
| `tests/test_stage_inputs_schema.py` | 7 | project.yaml 结构 / reference paths / Ribo-GSM 键 / clip / output bases / ribo 块不变 |
| `tests/test_run_upstream.py` | 6 | CLI 入口 + command 结构 + symlink + dedup + exit code |
| `tests/test_run_downstream.py` | 9 | `_load` + `_write_trial` + `_copy_products` + end-to-end mocked |
| **合计** | **35** | — |

`tests/test_smoke_downstream.py` 还是 5 行 stub（等 T11 启动）。

### 3.4 数据层快照

| 项 | 值 |
|---|---|
| `data/raw/metadata.csv` | **4168 数据行 × 30 列**（2 行头）；md5 `48c07b96...` |
| `data/raw/{organism}/{GSE}/*.fastq.gz` | **4689 个文件**（含 336 个 paired R2）|
| `data/raw/metadata.csv.preH2.bak` | 2644 行原始备份（gitignored，本地保留）|
| `data/raw/metadata.csv.preJ1.bak` | J1 前备份（gitignored）|
| `data/raw/_srr_enrichment_report.md` | H2 执行报告（gitignored）|
| `data/raw/_fastq_align_report.md` | J1 执行报告（gitignored）|
| `data/raw/_t3_verification_report.md` | J3 执行报告（gitignored）|

### 3.5 代码体量（自写）

| 文件 | 行数 | 上限 | 合规 |
|---|---|---|---|
| `src/te_analysis/stage_inputs.py` | 265 | M1=250 | +6%（用户允许）|
| `src/te_analysis/config.py` | 46 | M4=60 | ✅ |
| `src/te_analysis/run_upstream.py` | 77 | M2=80 | ✅ |
| `src/te_analysis/run_downstream.py` | 93 total / 74 non-blank | M3=80 | 非空度量 ✅；total +16% 用户允许 |
| `src/te_analysis/__init__.py` | 5 | stub | ✅ |
| **src/ 小计** | **486** | top_level < 500 | ✅ |
| `tests/test_stage_inputs.py` | 130 | M10=150 | ✅ |
| `tests/test_stage_inputs_schema.py` | 88 | — | ✅ |
| `tests/test_config.py` | 39 | — | ✅ |
| `tests/test_run_upstream.py` | 91 | — | ✅ |
| `tests/test_run_downstream.py` | 136 | — | ✅ |
| `tests/test_smoke_downstream.py` | 5 (stub) | M11=100 | ✅（待实现）|
| **tests/ 小计** | **489** | M10+M11=250 | **+96%** — 违反 GC-1 硬约束需审查 |
| `scripts/enrich_metadata_srr.py` | 139 | — | 一次性 |
| `scripts/align_fastq_paths.py` | 174 | — | 一次性 |
| `scripts/verify_t3_metadata.py` | 160 | — | 一次性 |
| **scripts/ 小计** | **473** | M5+scripts=100 | **+373%** — 一次性工具，module_contracts §M12 未明确禁止 |
| **Makefile** | 39 | M5=80 | ✅ |
| **全量自写** | **~1500** | GC-1 = 900 | **+66%** — 超限，**T12 应审查是否删 `scripts/` 一次性工具** |

**GC-1 超限的两大来源**：

1. `tests/` 比合同 300 行上限高 189 行 — 源于 K2/K3/L1/L2 四个测试文件都覆盖多分支 DoD（非冗余），建议 T12 时决定是否合并单测文件或接受现实
2. `scripts/` 473 行 — 三个一次性数据 enrichment/alignment/verification 工具。top-level §2 将 `scripts/` 定义为"一次性运维脚本可丢弃"，合规性待 T12 正式决定

---

## 4. 目录布局（当前）

```text
te_analysis/
├── .gitmodules              # 锁 SHA，ignore=none
├── .gitignore               # data/ 全忽略 + 例外 metadata.csv
├── Makefile                 # 39 行 7+1 target
├── README.md                # 21 行
├── pyproject.toml           # build + pytest config
├── environment.yml          # conda + pip (pysradb>=2.0)
├── environment-r.yml        # R 环境占位
│
├── configs/
│   └── paths.toml           # 路径 SSOT，由 config.py 加载
│
├── data/
│   └── raw/
│       ├── metadata.csv                    # 4168 rows × 30 cols（唯一 tracked 数据）
│       ├── metadata.csv.preH2.bak          # gitignored
│       ├── metadata.csv.preJ1.bak          # gitignored
│       ├── _srr_enrichment_report.md       # gitignored
│       ├── _fastq_align_report.md          # gitignored
│       ├── _t3_verification_report.md      # gitignored
│       └── {organism}/{GSE}/*.fastq.gz     # 4689 files, gitignored
│
├── docs/
│   ├── architecture.md                     # M12 标准（含 T4 data-flow 图）
│   ├── backlog.md                          # 3+ 条纳入条目
│   ├── metadata_schema.md                  # 123 行完整字段表
│   ├── reproducibility.md                  # partial recipe
│   ├── snakescale_contract.md              # 135 行 T0 产物
│   ├── te_model_contract.md                # 120 行 T0 产物
│   ├── vendor_sha_recommendation.md        # SHA 锁定决议
│   ├── srr_resolution_design_v2.md         # H2 决议（超越 G2 反面）
│   ├── te_analysis_top_level_design_v1.md  # ★项目宪法 1
│   ├── te_analysis_module_contracts_v1.md  # ★项目宪法 2
│   ├── te_analysis_sprint_plan_v1.md       # ★项目宪法 3
│   ├── progress_snapshot.md                # ← 本文件
│   └── vendor_recon_prior/                 # T0 前侦察残留
│
├── references/
│   └── vendor_contracts.md                 # L4 T0 聚合速查（M13 正式产物）
│
├── src/
│   └── te_analysis/
│       ├── __init__.py                     # 5 行
│       ├── config.py                       # 46 行（T2 ✅）
│       ├── stage_inputs.py                 # 265 行（T4 ✅）
│       ├── run_upstream.py                 # 77 行（T5 ✅）
│       └── run_downstream.py               # 93 行（T6 ✅）
│
├── scripts/                                # 一次性数据工具（非主路径）
│   ├── enrich_metadata_srr.py              # H2 pysradb 查询
│   ├── align_fastq_paths.py                # J1 磁盘扫描
│   ├── verify_t3_metadata.py               # J3 schema 验证
│   └── .gitkeep
│
├── tests/
│   ├── __init__.py
│   ├── test_config.py                      # 5 件
│   ├── test_stage_inputs.py                # 8 件
│   ├── test_stage_inputs_schema.py         # 7 件
│   ├── test_run_upstream.py                # 6 件
│   ├── test_run_downstream.py              # 9 件
│   ├── test_smoke_downstream.py            # stub（待 T11）
│   └── fixtures/
│       └── gse105082/                      # baseline_outputs + baseline.json（T14 待刷新）
│
└── vendor/
    ├── snakescale/                         # SHA b918e75, ro
    └── TE_model/                           # SHA 0b42e3f, ro
```

---

## 5. 关键设计决策（可追溯）

### 5.1 FASTQ 布局：{organism}/{GSE}/{EXP}_{assay}_{SRR}_[12].fastq.gz

**决策**：J1 将 `fastq_path` 对齐磁盘真相，新增 `fastq_path_r2` 列。

**理由**：top-level §4 数据流图原本设想扁平 `data/raw/fastq/`，但磁盘现实是三级分层（用户已批量下载），强对齐代价高。Canonical path = 磁盘真相。

**后果**：`stage_inputs.py` symlink 真实文件到 `<out>/staged_fastq/{GSE}/{GSM}/{SRR}_[12].fastq.gz`（对齐 snakescale `generate_yaml.py:262,273,279` 硬编码）。

### 5.2 SRR 内联 vs sidecar

**决策**：方案 A — 就地 enrich `metadata.csv` 为 run-level 扁平表。

**理由**：顶层设计 §5.2 明文 "metadata.csv 必含 `run` 列"；§9 砍掉清单禁止 sidecar；M7.MUSTNOT.3 禁止拆表。G2 曾误推荐方案 B，H1 revert 后 H2 用 pysradb 落地方案 A。

**执行结果**：2644 → 4168 行，unresolved SRX 仅 3/2635（0.11%）。

### 5.3 project.yaml 生成策略

**决策**：读 `vendor/snakescale/project.yaml` 作模板，只覆盖动态字段。

**动态字段**：`clip_arguments`、`rnaseq.clip_arguments`、`deduplicate`、`rnaseq.deduplicate`、`do_rnaseq`、`input.reference.{filter,transcriptome,regions,transcript_lengths}`、`input.fastq_base`、`input.fastq`、`rnaseq.fastq_base`、`rnaseq.fastq`、`output.{output,intermediates}.base`。

**静态字段继承**：`do_fastqc`、`mapping_quality_cutoff`、`alignment_arguments.*`、`ribo.*`、`output.*.{log,fastqc,ribo}` 等。

**理由**：GC-3 SSOT + M1.MUSTNOT.6 "禁止猜字段"；snakescale 升级时自动继承新 schema。

### 5.4 Paired-end 处理

**决策**：R1 和 R2 都 symlink；`input.fastq[GSM]` 列表仅放 R1 路径。

**理由**：snakescale `Snakefile:171,202` 硬编码 `_1.fastq.gz`。R2 symlink 已就位，待未来 snakescale 支持无数据迁移即可升级。

### 5.5 T6 `paxdb_filtered_sample.csv` 冲突

**决策**：`ribo_counts_to_csv.main(custom_experiment_list=...)` 从 `metadata.csv` 构造实验列表，完全绕过 `paxdb_filtered_sample.csv`。

**理由**：满足 M8/M9.MUSTNOT.1 "禁止 edit vendor"；te_model_contract §6.2 option a。

**落地**：`run_downstream.py._write_trial` 生成 `vendor/TE_model/trials/{study}/config.py` 调用 `main()` with `custom_experiment_list`。

### 5.6 T5 `run_upstream.py` 注入机制

**决策**：将 `<study-dir>/project.yaml` symlink 至 `vendor/snakescale/input/project/{GSE}/{study}.yaml`。

**理由**：`Snakefile:36` 若该文件存在则跳过 `generate_yaml()` → 绕过 `db/db.sqlite3` 依赖。`vendor/snakescale/input/` 是 snakescale 自己 .gitignored 的 runtime 区域，非 tracked 文件。

**启动命令**：`snakemake -p --cores N --config studies="['<study>']"` cwd=`vendor/snakescale/`。

### 5.7 数值对齐推迟

**决策**：T4 DoD §6（snakescale dry-run）+ T6 DoD §4.4（verify_gse105082 数值一致）均降级为 **schema 级验证**，真数值留 T8/T9/T14。

**理由**：dry-run 需 db.sqlite3 + reference/ + nextflow 环境；数值对齐需真实 `.ribo` + R。本 session 不具备，backlog 已记录。

---

## 6. Backlog（`docs/backlog.md` 现状）

| # | 条目 | 源任务 | 触发重访 |
|---|---|---|---|
| 1 | Relocate vendor contracts → `references/vendor_contracts.md` | T0 / J3 | **已由 L4 resolved** |
| 2 | Resolve 3 unresolved SRX from H2 + 21 missing fastq_path (0.50% loss) | T3 / J1 | T14 baseline lock |
| 3 | paired-end staging in T4 | J1 / T4 | **已由 K1 resolved**（R2 symlink 但不入 project.yaml）|

下一 session 应开启的新 backlog 条目：

- 4. `tests/` 合计 489 行 vs GC-1 300 上限 → T12 审查
- 5. `scripts/` 合计 473 行 → T12 审查
- 6. T6 真数值对齐 (DoD §4.4) → T9 + T14 合并验证

---

## 7. 下一步路线图（推荐执行顺序）

### 7.1 近期（1 session 可完）

| 候选 | 前置 | 环境要求 | 预期产出 |
|---|---|---|---|
| **T8** GSE132441 上游 E2E | T5 ✅ | 完整 snakemake + nextflow + `vendor/snakescale/reference/arabidopsis/` | `.ribo` 文件在 `vendor/snakescale/output/GSE132441/ribo/experiments/*.ribo` |
| **T9** GSE105082 下游 E2E | T6 ✅ | R + TE_model 依赖 + GSE105082 `.ribo` 就位 | `data/processed/te/GSE105082/human_TE_cellline_all_T.csv` + 与旧 fixture 数值比对 |

T8 和 T9 互不依赖，可并行（不同环境也行）。

### 7.2 中期（需 T8/T9 均绿）

- **T11** 冻结 T9 产物为 smoke test fixture（≤ 100 行）
- **T12** 正式启动 legacy purge（审查 tests/ + scripts/ 超限）
- **T13** 文档定稿（精简 `docs/` 至 M12 的 4 篇 + contracts）
- **T14** baseline 冻结 + `git tag v0.1-mvp`

### 7.3 如何开始 T8（给下一个 Claude）

```bash
# 1. 前置环境
conda activate te_analysis
conda install -c bioconda snakemake nextflow  # if not present
# 下载 Arabidopsis 参考
python vendor/snakescale/scripts/download_reference.py \
    --target vendor/snakescale/reference \
    --yaml vendor/snakescale/scripts/references.yaml

# 2. 走 T4-T5 链路
PYTHONPATH=src python -m te_analysis.stage_inputs \
    --metadata data/raw/metadata.csv \
    --study GSE132441 \
    --out data/interim/snakescale/GSE132441

PYTHONPATH=src python -m te_analysis.run_upstream \
    --study-dir data/interim/snakescale/GSE132441 --cores 4

# 3. 期望产物
# vendor/snakescale/output/GSE132441/ribo/experiments/{GSM3863556,GSM3863558,GSM3863561}.ribo
```

### 7.4 如何开始 T9

```bash
# 1. 确保 GSE105082 的 .ribo 就位（Zenodo 下载或 T8 产出）
ln -s <ribo_source> vendor/TE_model/data/ribo/GSE105082

# 2. 走 T6 链路
PYTHONPATH=src python -m te_analysis.run_downstream \
    --study-dir data/interim/snakescale/GSE105082 \
    --out-dir data/processed/te/GSE105082

# 3. 数值比对
diff data/processed/te/GSE105082/homo_sapiens_TE_cellline_all_T.csv \
     tests/fixtures/gse105082/baseline_outputs/human_TE_cellline_all_T.csv
# 注：J1 后 metadata.csv md5 已变，baseline 可能需要 T14 重算
```

---

## 8. 不可越界的硬约束（冷启动前必读）

### 8.1 绝对不动清单

- `vendor/**` 的 tracked 文件（submodule SHA 锁死；`M8/M9.MUSTNOT.1`）
- 项目宪法三文档：`docs/te_analysis_{top_level_design,module_contracts,sprint_plan}_v1.md`
- `configs/paths.toml`（T2/G3 冻结）
- `data/raw/metadata.csv` 除非 T9 或 T14 显式触发
- `.gitmodules` 除非显式 vendor bump

### 8.2 绝对不做事项

- 不 push（用户决定）
- 不重写 snakescale/TE_model 任何函数
- 不做 SRX→SRR 自动展开（metadata 已 run-level，就地 enrich 已完成）
- 不做 adapter 预检测 / FASTQ 完整性校验（`M1.MUSTNOT.2,3`）
- 不解析 snakescale 日志做决策（`M2.MUSTNOT.1`）
- 不在 Python 侧重实现 TE.R 数学（`M3.MUSTNOT.1`）
- 不引入新文档类型（ADR / RFC / 实验日记 — `M12.MUSTNOT.1`）
- 不再给 metadata.csv 加列（除非 T14 显式要求；参见 `M7.MUSTNOT.1`）

### 8.3 用户偏好（跨 session 生效）

- 输出用中文；代码注释用英文
- 使用 `pixi` 默认（本项目走 conda，已协商）
- 最小修改原则，避免 over-engineering
- 轻度超出硬行数限制可接受，不影响整体
- 长周期工作可维护 `progress_snapshot.md` / `progress.txt` 类笔记（本文件即是）

---

## 9. 已知风险 / 未决问题

1. **`tests/fixtures/gse105082/baseline.json`** 可能已失效（J1 后 metadata.csv md5 改变）→ T14 重算
2. **`scripts/` 违反 GC-1** → T12 决定是否归档或保留为 `archive/`
3. **`tests/` 违反 GC-1** → T12 决定是否合并测试文件
4. **snakescale `Snakefile:171,202` paired-end 限制** → 上游 issue / 等 vendor 升级
5. **`nonpolyA_gene.csv` 物种适用性** 未决（te_model_contract §6.4）→ T6 运行非 human/mouse 时需补策略
6. **`te_model_contract §6.6` `model_results.txt` 文档与代码不一致** → 已统一用 `human_TE_cellline_all_T.csv` 作终止信号

---

## 10. 如何验证当前状态（冷启动校验命令）

```bash
# (a) 基本一致性
git log --oneline -5
git submodule status
git status --porcelain   # 期望仅 "?? vendor/snakescale"

# (b) 测试全绿
source /home/xrx/miniconda3/etc/profile.d/conda.sh
conda activate te_analysis
PYTHONPATH=src python -m pytest tests/ -v
# 期望：35 passed in <3s

# (c) Stage T4 smoke
PYTHONPATH=src python -m te_analysis.stage_inputs \
    --metadata data/raw/metadata.csv --study GSE132441 --out /tmp/t4_verify
ls /tmp/t4_verify/project.yaml /tmp/t4_verify/staged_fastq/GSE132441/
# 期望：project.yaml + 6 个 symlink（3 Ribo + 3 RNA）

# (d) Makefile dry-run
make -n all STUDY=GSE132441
# 期望：3 条 command 链（stage → upstream → downstream）

# (e) 数据层校验
python scripts/verify_t3_metadata.py
# 期望 exit 0 + closure 100%
```

---

## 11. 术语 cheat-sheet

| 缩写 | 含义 |
|---|---|
| GSE / GSM / SRX / SRR | GEO study / GEO sample / SRA experiment / SRA run |
| M1-M14 | module_contracts 中的模块编号（M1=stage_inputs, M2=run_upstream, M3=run_downstream, ...）|
| T0-T14 | sprint_plan 中的任务编号 |
| GC-1/2/3 | module_contracts 中的三条全局约束（代码量 / 功能来源优先级 / SSOT）|
| F/E/G/H/I/J/K/L | 本地未 push 的 commit 批次代号 |
| L1/L2/... | 某批次内的顺序 commit |
| CCDS | Common Computational Data Structure（项目目录范式）|

---

**End of snapshot**. 下一 session 从本文件 §7 选路线继续。
