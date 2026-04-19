# Prompt: Commit F 收尾清扫 + T0 Vendor Recon（合并版）

> **代理目标**：Opus 4.7 on Windsurf
> **前置假设**：分支 `design/v1-minimal`，HEAD = `5db070d`（Commit E3），工作树干净，Commit E 执行报告中未解决清单 1–6 已全部被代理知晓。
> **全局硬约束**：本 prompt 期间 **不得** `git push`，不得触碰 `vendor/ / references/ / tests/fixtures/ / data/raw/metadata.csv / .env / .codex / .gitmodules / Makefile / environment.yml / environment-r.yml / pyproject.toml / README.md / .gitignore`，不得修改 T1 的 5 个 stub 文件 (`src/te_analysis/{__init__,config,run_downstream,run_upstream,stage_inputs}.py`)，不得新增任何自造业务代码。

---

## 0. 执行模型

四个原子 commit **串行** 推进，每个 commit 独立通过自己的 DoD 才能进入下一个。Commit 内出现任何 **停工触发条件**（见各节），立即 `git reset --hard HEAD~1` 并停下来报告，不得创造性修复。

| Commit | 核心职责 | 性质 |
|---|---|---|
| **F1** | 清理 E 阶段后仍 broken / 逻辑悬空的测试 | 删除 |
| **F2** | 清理 `docs/` 下与 v1-minimal 不兼容的历史审计文档 | 删除 |
| **F3** | 清理根级碎屑（如有） | 删除（可能为空 commit → 跳过） |
| **F4** | 产出 T0 Vendor Recon 文档 × 3 | 新增 |

---

## 1. Commit F1 — tests 最终对齐

### 1.1 Pre-flight：逐个测试实读

对以下 **6 份在 Commit E 后保留的遗留测试** 执行 `head -40` 读取前 40 行，并报告每份的：
1. 实际 import 清单（stdlib / 第三方 / 本仓库模块路径）
2. 文件目标（测什么）
3. **裁决**：`KEEP` / `DELETE` / `RENAME`（若保留但语义需重命名）

待盘点清单：
- `tests/test_upstream_dryrun.py`
- `tests/test_ingest_raw_symlinks.py`
- `tests/test_config_loading.py`
- `tests/test_fixture_integrity.py`
- `tests/test_legacy_te_stage2_positive_baseline.py`
- `tests/test_legacy_te_stage3_final_output_contract.py`

### 1.2 裁决规则（强制）

| 条件 | 裁决 |
|---|---|
| import 路径指向 Commit E 已删除的模块（`te_analysis.adapters/pipeline/handoff/raw/upstream/downstream/utils/cli/settings` 或根级 `te_analysis.*`） | `DELETE` |
| import 路径指向 **已删除目录但内容**（如 `data/audits/` / `configs/`） | `DELETE` |
| 只 import stdlib / pytest / pandas / numpy / pyyaml，且逻辑围绕 **被 T1 `preserve` 保留下来** 的 `verify_gse105082/baseline.json` / `data/raw/metadata.csv` / `tests/fixtures/` | `KEEP` |
| 只 import stdlib / pytest / pandas，但测试目标是 "ingestion layer / CLI / handoff manifest / stage contracts" 等已废弃概念 | `DELETE` |
| 其他无法判定 | `KEEP` + 在报告中标红 |

### 1.3 停工触发

- 若某份测试同时 import 了"已删除模块"**和**"T1 新 stub"：停工，报告交错依赖。
- 若 `test_legacy_te_stage2_positive_baseline.py` 或 `test_legacy_te_stage3_final_output_contract.py` 的主体逻辑不依赖 `verify_gse105082/baseline.json` 或 `tests/fixtures/`：停工，报告意外结构，**不得** 自行删除。

### 1.4 执行

```bash
git rm <DELETE 集合>
git add -A
git status
git diff --cached --stat
git commit -m "purge: retire broken / orphaned legacy tests (Commit F1)

- tests/test_upstream_dryrun.py: imports deleted te_analysis.upstream.dryrun
- <其余 DELETE 条目逐行列出，各一句原因>

Remaining tests: <KEEP 集合逐行列出>

Refs: te_analysis_commit_e_purge_legacy_prompt.md unresolved item #1,#2"
```

### 1.5 DoD

- `git status --porcelain` 为空
- 保留的测试集里 **没有任何一份** import 了 Commit E 已删除的模块
- `python -c "import ast, pathlib; [ast.parse(p.read_text()) for p in pathlib.Path('tests').glob('test_*.py')]"` 不抛 SyntaxError
- commit message 按上述模板

---

## 2. Commit F2 — docs/ 历史审计清理

### 2.1 Pre-flight：白名单 vs 候选删除集

**白名单（绝对保留）**：
```
docs/te_analysis_top_level_design_v1.md
docs/te_analysis_module_contracts_v1.md
docs/te_analysis_sprint_plan_v1.md
docs/architecture.md
docs/metadata_schema.md
docs/reproducibility.md
docs/backlog.md
docs/.gitkeep
```

**候选删除集（逐个审视）**：
```
docs/legacy_repo_forensic_audit.md
docs/migration_blueprint_final.md
docs/module_boundaries_phase1.md
docs/repo_census_and_migration_audit.md
docs/upstream_input_contract.md
docs/architecture/   (子目录)
docs/image/          (子目录)
```

### 2.2 审视规则（必须逐项执行）

对每个候选，先 **读 前 80 行 + tail 20 行**，然后作出如下裁决：

| 情况 | 裁决 |
|---|---|
| 内容为"旧代码库考古 / 已废弃 migration blueprint / 已被三份权威合同取代" | `DELETE` |
| 内容是 **snakescale / TE_model 输入契约的逆向分析**（任何形式，哪怕不完整） | `MOVE → docs/vendor_recon_prior/` 且保留；本 commit 不删，用于 F4 输入 |
| 子目录（`architecture/`、`image/`）只含图片/截图/zip/xls | 若无任何 md 在 `docs/architecture.md` 或白名单内引用 → `DELETE`；若被引用 → `KEEP` |
| 无法判定 | `KEEP`，在报告中明确标出"需下一轮独立决策" |

**重点警告**：`docs/upstream_input_contract.md` 极可能是 T0 的前置素材，**优先 `MOVE` 而不是 `DELETE`**。除非内容明显无关或仅 2–3 行占位。

### 2.3 引用检查

在执行 `git rm` 之前，对每个 `DELETE` 候选执行：
```bash
grep -r "<basename_without_ext>" docs/ README.md --include='*.md'
```
任何白名单文档中出现引用 → **停工**，报告交叉引用，不得删。

### 2.4 执行

```bash
# 若有 MOVE 项
mkdir -p docs/vendor_recon_prior
git mv docs/upstream_input_contract.md docs/vendor_recon_prior/
# DELETE 项
git rm <DELETE 集合>
git status
git commit -m "purge: remove superseded legacy docs (Commit F2)

Deleted (superseded by te_analysis_top_level_design_v1 + module_contracts_v1 + sprint_plan_v1):
- <逐行>

Moved to docs/vendor_recon_prior/ (input for T0 Vendor Recon):
- <逐行>

Retained authoritative set:
- docs/te_analysis_top_level_design_v1.md
- docs/te_analysis_module_contracts_v1.md
- docs/te_analysis_sprint_plan_v1.md
- docs/architecture.md / metadata_schema.md / reproducibility.md / backlog.md"
```

### 2.5 DoD

- 白名单中的 8 份文件 md5 **未变**
- `docs/` 顶层只剩白名单 + `vendor_recon_prior/`（若触发 MOVE）+ 未决子目录
- 报告中明确列出每个候选的裁决依据（前几行摘要）

---

## 3. Commit F3 — 根级碎屑（条件性）

### 3.1 扫描清单

执行后报告：
```bash
ls -la
git ls-files | grep -E '^\.(pytest_cache|mypy_cache|ruff_cache|coverage)' | head
git ls-files | grep -E '\.(pyc|pyo|egg-info|DS_Store)$' | head
git ls-files 'notebooks/'
git ls-files 'logs/'
```

### 3.2 删除规则

| 项 | 动作 |
|---|---|
| `.pytest_cache/` / `.mypy_cache/` / `.coverage` 被 git 跟踪 | `git rm -r --cached` + 确认 `.gitignore` 已覆盖（已在 pre-flight 看过则跳过）|
| `notebooks/` 含已追踪的遗留 `.ipynb` 且这些 notebook import 已删除模块 | `git rm`；否则 `KEEP` |
| `logs/` 若被追踪 | `git rm -r --cached` |
| `.vscode/` `.windsurf/` | **KEEP**（IDE 个人配置） |
| `LICENSE` | **KEEP** |
| 其他 | `KEEP` |

### 3.3 执行

如有删除项：
```bash
git rm -r <...>
git commit -m "purge: clean root-level stragglers (Commit F3)

- <逐行列出并说明>"
```

如扫描结果 **无任何需删项**：
- **跳过 Commit F3**，在报告中明确 "F3 skipped — no eligible stragglers"
- 不要创造性地找东西删

### 3.4 DoD

- 根级无被追踪的 cache / 已删除模块依赖的 notebook
- `.vscode/`、`.windsurf/`、`LICENSE` 未动

---

## 4. Commit F4 — T0 Vendor Recon 输出

**目标**：产出三份文档，全部新增在 `docs/` 下，**纯读不改** vendor/，不修改任何 submodule 内文件。

### 4.1 任务边界（硬合同）

| MUST | MUST NOT |
|---|---|
| 只读 `vendor/snakescale/`、`vendor/TE_model/` 已 clone 的内容 | ❌ 写入 vendor/ 任何文件 |
| 只读 `vendor/snakescale` 的 Snakefile / rules / config schemas / README / example configs | ❌ `cd vendor/snakescale && git checkout` 或 `git fetch` |
| 输出文档使用 "作者契约" 措辞而非 "我们的实现" | ❌ 推断任何未在 vendor 文件中显式写出的字段 |
| 任何"我们的 metadata.csv ↔ 作者字段"对应关系必须基于 vendor 源码直接引用（给出行号） | ❌ 杜撰字段名；如果某字段作者未要求，明确标注 "作者未暴露" |
| 区分"作者已有实验证据要求的字段" vs "作者 README 写了但代码未校验的字段" | ❌ 用"大概率/应该"等模糊措辞 |

### 4.2 产出文档 1：`docs/snakescale_contract.md`

必须包含以下章节：

```markdown
## 0. 溯源
- Vendor path: vendor/snakescale
- Commit SHA locked at recon: <git -C vendor/snakescale rev-parse HEAD>
- 上游仓库: <origin URL>

## 1. 入口文件契约
### 1.1 project.yaml / config.yaml 必需字段
| 字段路径 | 类型 | 作者出处（文件:行） | 我方 metadata.csv 对应列 / 推导方式 | 置信度 |

### 1.2 manifest / sample table 必需列
| 列名 | 类型 | 空值规则 | 作者出处（文件:行） | 我方字段 | 置信度 |

### 1.3 数据布局要求
（FASTQ 放在哪、命名规则、index 文件 / adapter / genome reference 由谁提供）

## 2. db 文件契约（如适用）
（若 snakescale 有 sqlite/yaml/csv 形式的 reference db，逐字段列出；如没有，写明 "作者未使用 db 文件"）

## 3. classify_studies gate
（作者的 gate 规则实际检查了什么；给出 rule 名 + 具体逻辑摘要 + 文件:行）

## 4. 输出契约（.ribo 路径、子文件、命名）

## 5. 我方 stage_inputs.py 落地映射表
| 我方 metadata.csv 列 | → snakescale 字段 | 需要的最小转换 | 置信度 |

## 6. 已知开放问题
- 字段 X：作者 README 要求但代码未校验 → 自由度
- 字段 Y：我方缺失，可能需要补采集 → 阻断项
```

### 4.3 产出文档 2：`docs/te_model_contract.md`

```markdown
## 0. 溯源
## 1. TE.R 输入文件契约
（.ribo 路径、RNA.ribo 路径、哪些 meta 字段）
## 2. transpose_TE.py 输入/输出
## 3. 我方 run_downstream.py 落地映射
## 4. 已知开放问题
```

### 4.4 产出文档 3：`docs/vendor_sha_recommendation.md`

```markdown
## 推荐 pin SHA
| Submodule | 当前 (unlocked) | 推荐 pin | 理由 |
| snakescale | b918e75 | <SHA or "keep current"> | <... tag / 最近稳定 commit / 有 release note 支持> |
| TE_model | 0b42e3f | <SHA or "keep current"> | <...> |

## 升级风险（对我方 stage_inputs.py 的潜在影响）
## 下一次升级触发条件
```

### 4.5 执行

```bash
# 编写三份文档到 docs/
git add docs/snakescale_contract.md docs/te_model_contract.md docs/vendor_sha_recommendation.md
git status
git commit -m "docs(t0): vendor recon — snakescale + TE_model input contracts + SHA recommendation (Commit F4)

Reverse-engineered contracts from read-only inspection of vendor submodules.
No code changes, no vendor modifications.

- docs/snakescale_contract.md: N fields mapped, K open issues
- docs/te_model_contract.md: M fields mapped, J open issues
- docs/vendor_sha_recommendation.md: recommend pin @ <SHA/SHA>

Task: T0 (Vendor Recon) per te_analysis_sprint_plan_v1.md"
```

### 4.6 DoD

- 三份文档全部存在，每份 ≥ 50 行
- 所有 "作者出处" 引用都给出 `filename:linenum` 格式，可验证
- 对每个字段显式给出 **置信度** 标签（`高` / `中` / `低` / `空白`），高置信度必须有代码层面证据（不只是 README）
- "作者未暴露 / 自由度" 的字段明确列出，不隐瞒
- vendor/ 目录 `git status` 无变化
- 三份文档之间 **无重复** 字段定义

### 4.7 T0 停工触发

- vendor 里找不到 project.yaml 或类似 schema 文件 → 停工，报告 "vendor 契约不在我假设的位置，需用户指引"
- 某核心字段作者既无代码也无 README 描述 → 停工，不要杜撰
- 发现我方 metadata.csv 缺少作者要求的**硬字段** → 不要 patch 自己，在文档里明确列为阻断项

---

## 5. 最终执行报告模板

```markdown
# Commit F + T0 执行报告

## Pre-flight 摘要
- F1 测试裁决表：<markdown 表格，KEEP/DELETE 逐行>
- F2 docs 候选裁决表：<markdown 表格>
- F3 根级扫描：<yes/no 列举>
- F4 vendor 两 submodule 当前 HEAD SHA：<...>

## 新增 Commits
| # | Hash | Message 首行 | 文件变动统计 |
| F1 | ... | purge: retire broken / orphaned legacy tests (Commit F1) | +0/-N |
| F2 | ... | purge: remove superseded legacy docs (Commit F2) | +0/-N |
| F3 | ... OR `SKIPPED` | ... | ... |
| F4 | ... | docs(t0): vendor recon — ... | +N/-0 |

## 终态快照
- `src/te_analysis/` 文件数 / 总行数（应仍为 5 / 42）
- `tests/*.py` 顶层保留清单
- `docs/` 顶层保留清单 + 新增三份 T0 文档
- SELF/VENDOR 行数比（`find src/ -name '*.py' | xargs wc -l | tail -1` vs `find vendor/*/ -name '*.py' -o -name '*.smk' -o -name '*.R' | xargs wc -l | tail -1`）

## T0 核心结论（给用户看的 TL;DR，≤ 15 行）
- snakescale 入口文件：<project.yaml 或 ...>
- 我方 metadata.csv 与作者 schema 的字段匹配度：<N/M 硬字段命中 / 软字段命中 / 缺失字段 K 个>
- 缺失硬字段清单（阻断项）：<...>
- 推荐 pin SHA：snakescale → ...，TE_model → ...
- 下一任务推荐：T1 SHA lock / T2 config.py / T3 metadata schema validator，按哪个优先？

## DoD 自检（逐条勾选）
- [ ] 分支仍为 design/v1-minimal
- [ ] HEAD 以上新增 3 或 4 个 commit
- [ ] git status --porcelain 为空
- [ ] 黑名单项 md5 全部未变
- [ ] src/te_analysis/ 仍为 5 stub（行数 ≤ 50）
- [ ] vendor/ 目录无任何写入
- [ ] 三份 T0 文档全部有 ≥ 50 行，字段引用有行号

## 未解决 / 偏差清单
<如无 → 写 "无"；有 → 逐条列出并提供继续决策所需的信息>
```

---

## 6. 失败处置

- **F1/F2/F3 任意停工**：`git reset --hard HEAD~1` 回退当前 commit，**不继续后续 commit**，报告并等待用户指令
- **F4 写到一半发现 vendor 契约不在假设位置**：已写的 docs 保留在工作区 **但不 commit**，报告观察到的真实结构，等待用户决定 T0 方向
- **任意时刻若 `git status` 出现对黑名单项的改动**：`git restore <path>`，在报告中标红

---

## 7. 黑名单快照（绝对不动）

```
vendor/snakescale/**    vendor/TE_model/**    .gitmodules
references/**           tests/fixtures/**     data/raw/metadata.csv
.env                    .codex                LICENSE
Makefile                environment.yml       environment-r.yml
pyproject.toml          README.md             .gitignore
src/te_analysis/__init__.py
src/te_analysis/config.py
src/te_analysis/run_downstream.py
src/te_analysis/run_upstream.py
src/te_analysis/stage_inputs.py
docs/te_analysis_top_level_design_v1.md
docs/te_analysis_module_contracts_v1.md
docs/te_analysis_sprint_plan_v1.md
docs/architecture.md    docs/metadata_schema.md
docs/reproducibility.md docs/backlog.md
```

**结束。开始 Commit F1 Pre-flight。**
