# Codex Handoff · te_analysis · Session O（2026-04-20）

> 给接手 Codex 的对齐文件 + 可直接粘贴的任务 prompt。Windsurf 限额切换至 Codex。
> 本文件**第一部分是背景对齐**（你需要读完才能理解现状），**第二部分是本轮任务 prompt**（直接粘贴进 IDE Codex 插件执行）。

---

# 第一部分 · 项目对齐

## 0. 元信息

| 项 | 值 |
|---|---|
| 仓库 | `/home/xrx/my_project/te_analysis` |
| 分支 | `design/v1-minimal` |
| HEAD | `505663d`（本地领先 `origin/design/v1-minimal`=`bbcfaae` 1 个 commit；可 push）|
| 宪法三件套 | `docs/te_analysis_{top_level_design,module_contracts,sprint_plan}_v1.md` 只读 |
| 权威 ground truth | `docs/progress_snapshot.md` |
| 上游 GitHub | https://github.com/Gasly729/ccds-translation-efficiency |
| 执行代理 | 本轮 = Codex（IDE 插件）；Windsurf 本周限额耗尽 |

## 1. 当前状态 TL;DR

- **T0-T7 + T9(schema) + T11 全绿**；进度 ~85%
- **T8 三次重试挂在三层不同问题**：
  1. Session-M：`_1.fastq` vs `.fastq.gz` 格式错位（backlog #7）
  2. Session-N：上轮 Windsurf 发现**第二层病因** —— stage_inputs 的 staged_fastq 放在 `data/interim/...`，而 snakemake cwd=`vendor/snakescale/` 看不见
  3. Session-N：真阻断 = **vendor `RiboFlow.groovy` 15 处拼写错误**（backlog #8）
- **方案 F 已验证可行**：mtime 序法 + staged_fastq symlink 到 `vendor/snakescale/staged_fastq/{GSE}` → B3 `--until check_adapter` 6/6 成功
- **方案 F 未码化到 src/**（backlog #9）—— 下次 T8 重试仍需手动 2 个 symlink + 空 fastq + mtime

## 2. 本轮 Windsurf 产出的关键事实

### 2.1 snakemake 9.19 CLI 语义（已核实）

| 旗标 | 语义 | 用途 |
|---|---|---|
| `--omit-from`, `-O` | 跳该 rule + **下游**（不是上游！）| ❌ 死路 |
| `--until`, `-U` | 只跑到指定 rule 为止 | ✅ probe 阶段 |
| `--touch`, `-t` | 标记已存在 output 为 up-to-date；**file 不存在会 fail** | 🟡 需先手造 |
| `--consider-ancient RULE=INPUTITEMS` | 强制视 input 为 ancient，不因 mtime 新而 rerun | 🟢 方案 F 的保险杠 |
| `--allowed-rules` | 手册明文"仅供内部使用，生产不推荐" | ❌ |

### 2.2 方案 F 完整成分（2 步）

**必要前提**（每次 T8 重试前执行）：
```bash
# (a) 把 staged_fastq 链到 snakemake cwd 可见处
ln -s ../../data/interim/snakescale/GSE132441/staged_fastq/GSE132441 \
      vendor/snakescale/staged_fastq/GSE132441

# (b) 给每个 SRR 建空 _1.fastq（老 mtime） + 刷新 .gz（新 mtime）
find data/interim/snakescale/GSE132441/staged_fastq -name '*_1.fastq.gz' | while read gz; do
  fastq="${gz%.gz}"
  touch -d '1 hour ago' "$fastq"
  touch -h "$gz"
done
```

### 2.3 真 vendor bug（backlog #8）

`vendor/snakescale/riboflow/RiboFlow.groovy` 15 处 `samtools -@ {task.cpus}` 少写 `$`（groovy 不做插值 → bash 把字面量 `{task.cpus}` 当文件路径 → samtools 报 `failed to open "-@"`）。

行号：**260, 261, 321, 322, 358, 359, 553, 1172, 1173, 1528, 1529, 1585, 1586, 1624, 1625**

这是 **vendor 自身的字面 bug**，与我方方案 F 无关；按 GC-0 禁改 vendor，T8 在当前 SHA 下无法绿。

### 2.4 额外发现：`override=False` classify_studies 判定

`run_riboflow` 对"无法猜 adapter"的 study 会写 "failed" 跳过 nextflow；需 `--config override=True` 强跑。背后逻辑：Ribo-seq FASTQ 若已 pre-clip，snakescale 内置 adapter 猜测会失败 → 判 study invalid。

**memory 记录 72% 样本缺 3' adapter** —— 这意味大规模运行时会有一批 study 被判 invalid。**必须量化**。

## 3. 当前 backlog 清单

| # | 状态 | 内容 |
|---|---|---|
| #6 | OPEN（挂 T14） | baseline.json J1-drift：行数 -0.18%、基因集移 195、mean `\|Δ\|`=0.120 |
| #7 | ✅ RESOLVED in N via method F | `_1.fastq` vs `.gz` 格式错位 + 路径可见性 |
| #8 | 🔴 NEW / 阻塞 T8 | vendor `RiboFlow.groovy` 15 处 `{task.cpus}` 少 `$` |
| #9 | OPEN / 待 #8 解后启 | method F 码化进 `stage_inputs.py` 或新 helper 模块 |

## 4. Claude 视角的风险判断（供 Codex 知情）

- **#8 真阻断**，优先级最高；但解法是**调研类任务**（看 upstream 是否已修），不是代码任务
- **classify_studies 72% 风险**：调研类 + 数据量化；不解 T14 会炸
- **方案 F 码化**：延到 #8 解之后，避免白写（若 SHA 升级后 vendor 接口变了就要返工）
- **contract testing 缺口**：项目级建议，T12 正式启时补一层 mini-mock E2E 测试

## 5. 硬约束（重申）

- `vendor/**` tracked + submodule SHA（**包括 `.groovy`**）—— 禁动
- 宪法三件套 + `configs/paths.toml` + `data/raw/metadata.csv` —— 禁动（除非 T14 触发）
- `.gitmodules` —— 禁动
- **不 push** —— 用户明示批准前本地积压（当前本地领先 1）
- **禁启** T12/T13/T14（未到前置条件）
- 任务拆解**禁用** Day/Week/Sprint 等时间单位 —— 用 DAG + DoD + 断点判据
- 输出**中文**；代码注释英文；严格区分**已验证事实** vs **推断**；不确定给**置信度（高/中/低）**

## 6. Codex 工作风格约束（继承自 `feedback_codex_workflow.md`）

- 优先窄任务：一次一个边界清晰的小改动
- 每次说明："这一步会不会动 runtime / fixtures / frozen tree"
- 报错日志回复顺序：① 错误定位 → ② 修复方案；不做原理科普
- 缺关键状态信息（是否 commit / stash / reset）→ 主动指出并要求验证，不默认最好情况

## 7. 已弃旧叙事（不要再引用）

- 旧 PR -1b/-1c/0 序列 → 改走 T0-T14 DAG
- G2 sidecar 方案（已 H1 revert）
- 旧 `src/te_analysis/{adapters, downstream, handoff, cli.py, ...}` 已 E1 清除

---

# 第二部分 · 本轮任务 prompt（直接粘贴到 Codex）

> 以下内容是 Codex 本轮的工作合同。任务包含 **调研 + 数据量化 + 设计稿 + 决策树 + snapshot 维护**，一次闭合多个问题。**不写任何代码**（除了 snapshot / backlog / 设计文档的 markdown 更新）。

## §1 冷启动强制校验（失败即 abort）

```bash
# (a) 基本一致性
git log --oneline -5
git submodule status
git status --porcelain   # 期望仅 "?? vendor/snakescale"

# (b) snapshot self-reference 检查
grep -oE 'HEAD=`[a-f0-9]+' docs/progress_snapshot.md | head -1
git rev-parse HEAD | cut -c1-7
git rev-list --count origin/design/v1-minimal..HEAD
# 若不一致 → 先 bump snapshot 再进主任务

# (c) 测试全绿
conda activate te_analysis
PYTHONPATH=src python -m pytest tests/ -v   # 期望 42 passed

# (d) T4 smoke
PYTHONPATH=src python -m te_analysis.stage_inputs \
  --metadata data/raw/metadata.csv --study GSE132441 --out /tmp/t4_verify

# (e) metadata closure
python scripts/verify_t3_metadata.py
```

**任一失败 → 立即停止并报告**，不擅自修代码。

## §2 主任务 DAG（5 条并行 / 2 条串行）

```
冷启动✅
  ↓
┌──────────────────────────────────────────────────────┐
│ [O1 · 并行] #8 upstream 调研（最高优先级，决定 §3 分支）│
│ [O2 · 并行] classify_studies 72% 风险量化             │
│ [O3 · 并行] vendor_patches/ 目录合规性 audit          │
│ [O4 · 并行] method F 码化设计稿（不写代码，只出 MD）  │
│ [O5 · 并行] contract testing 缺口分析                 │
└──────────────────────────────────────────────────────┘
  ↓
[O6 · 串行] 综合决策：#8 走 a/b/c 哪条
  ↓
[O7 · 串行] snapshot + backlog bump（单独 commit）
```

## §3 各子任务 DoD

### O1 · #8 upstream 调研（优先级：最高）

**目标**：判断 snakescale/TE_model 的 upstream 是否已修 groovy typo，决定 #8 走 a/b/c 哪条。

**动作**：
```bash
# 查 snakescale submodule URL
git -C vendor/snakescale config --get remote.origin.url

# 克隆 upstream main 到 /tmp（只读调研，不污染工作树）
cd /tmp
git clone --depth 50 <snakescale_url> snakescale_upstream
cd snakescale_upstream

# 查 RiboFlow.groovy 的关键行
grep -n 'task.cpus' riboflow/RiboFlow.groovy | head -20
grep -nE '-@ \$\{task\.cpus\}|-@ \{task\.cpus\}' riboflow/RiboFlow.groovy

# 若已修 → 找到修复 commit
git log --oneline --all -- riboflow/RiboFlow.groovy | head -20
git log -S 'task.cpus' --oneline riboflow/RiboFlow.groovy | head -10

# 若未修 → 搜 issues/PRs
# （只读抓 README / CONTRIBUTING，不尝试 web 访问）
```

**DoD**：回答以下 4 个问题，每题附证据（commit hash / file:line / grep 输出）：
1. upstream main 分支当前 HEAD 的 `RiboFlow.groovy` 是否已修 15 处 typo？
2. 如已修，是哪个 commit 修的？diff 规模多大（几行 / 涉及几个文件）？
3. 从我们锁定的 SHA `b918e75` 到 upstream main，中间累计多少个 commit？涉及哪些"非 typo 相关"的变更？（只列 commit title，不做深度分析）
4. upstream 的 issue tracker 里有没有关于 `task.cpus` / `samtools -@` / `groovy interpolation` 的公开讨论？

**不做**：
- 不动 `vendor/snakescale/` 的 submodule pointer
- 不写代码
- 不尝试 apply patch

---

### O2 · classify_studies 72% 风险量化

**目标**：在大规模运行前搞清楚"override=False 会让多少 study 被判 invalid"。

**动作**：
```bash
# (a) 读 snakescale classify_studies rule 的判定逻辑
grep -n 'classify_studies\|override' vendor/snakescale/Snakefile | head -20
# 找到 rule body 后读完整逻辑，判断"invalid" 的触发条件是什么（全部 Ribo 样本无 adapter？任一无？）
```

```python
# (b) 量化我方 metadata.csv
import pandas as pd
m = pd.read_csv('data/raw/metadata.csv', skiprows=[0])
ribo = m[m['corrected_type'] == 'Ribo-Seq']

# 按 study 分组统计 threep_adapter 非空率
by_study = ribo.groupby('study_name').agg(
    total=('threep_adapter', 'size'),
    has_adapter=('threep_adapter', lambda s: s.notna().sum()),
    pct=('threep_adapter', lambda s: s.notna().mean()),
).sort_values('pct')

# 按 Snakefile 判定规则分类（假设"任一样本无 adapter → invalid"，若 rule 要求全有则改 == 1）
invalid_studies = by_study[by_study['pct'] < 1.0]  # 保守估计
strict_invalid = by_study[by_study['pct'] == 0]    # 严格估计

print(f"Total Ribo studies: {len(by_study)}")
print(f"Strict invalid (0% have adapter): {len(strict_invalid)}")
print(f"Partial invalid (<100% have adapter): {len(invalid_studies)}")
print(f"Full valid (100% have adapter): {len(by_study) - len(invalid_studies)}")

# 保存详细清单
invalid_studies.to_csv('/tmp/t8_invalid_studies_audit.csv')
```

**DoD**：
1. 读懂 classify_studies 的判定逻辑后，用自己的话复述（引 Snakefile:行号）—— 置信度标注
2. 按判定逻辑量化：全量 Ribo studies 有多少 / `override=False` 下多少会被判 invalid / 占比
3. 评估 `override=True` 的代价：会跳过哪些 QC？产出是否仍可用于 TE 计算？（引 te_model_contract）
4. 产出 `/tmp/t8_invalid_studies_audit.csv` 清单

**不做**：不跑 snakescale；只做静态分析 + pandas 统计。

---

### O3 · `vendor_patches/` 目录合规性 audit

**目标**：如果 #8 走路径 b（本地 patch），需要先确认 `vendor_patches/` 不违反宪法。

**动作**：
```bash
# 查宪法三件套有没有明文提到 vendor_patches / 补丁 / override
grep -nE 'vendor_patches|patch|override|apply_patch' \
  docs/te_analysis_top_level_design_v1.md \
  docs/te_analysis_module_contracts_v1.md \
  docs/te_analysis_sprint_plan_v1.md

# 看 module_contracts 的 M8/M9 MUSTNOT 原文
grep -nA5 'M8\.\|M9\.' docs/te_analysis_module_contracts_v1.md
```

**DoD**：
1. 引用宪法原文判断：`vendor_patches/*.patch` + `run_upstream.py` apply 的模式**是否违反** M8/M9.MUSTNOT.1 "禁改 vendor"？
2. 如果合规：给出 `vendor_patches/` 的目录契约草案（文件命名 / apply 顺序 / 版本锁定策略），100 行以内
3. 如果不合规：说明为何，建议走路径 a（upstream PR）或 c（SHA 升级）

**不做**：不创建 `vendor_patches/` 目录；不写 patch。

---

### O4 · Method F 码化设计稿（设计文档，不写代码）

**目标**：为 backlog #9 出一个 PR-ready 的设计稿（等 #8 解后直接实现）。

**动作**：

写一份 `docs/design/method_f_codification_v1.md`，结构：

1. **现状**：方案 F 两步骤（staged_fastq symlink + mtime 序）目前手动执行
2. **三个候选方案**：
   - **A. 扩 `stage_inputs.py`**：评估行数增量（当前 265 / M1=250，预计 +40 → 305）
   - **B. 新建 `src/te_analysis/stage_snakescale_injection.py`**（M1a helper）独立模块
   - **C. 扩 `run_upstream.py`**：把 injection 放在 upstream run 的前置 hook
3. **每个方案**：
   - 函数签名（签名级，不写函数体）
   - 测试桩命名（`test_snakescale_injection.py` 的测试件名清单）
   - M 合同影响（M1 / M2 / M5 各超几行）
   - 回滚难度
4. **推荐**：给出明确倾向 + 置信度
5. **实现顺序**：等 #8 解后，按什么 DAG 上手

**DoD**：`docs/design/method_f_codification_v1.md` 存在且涵盖上述 5 节；**不改任何 `src/` 代码**；不做任何 commit 触发 tests。

**不做**：不实现任何函数。

---

### O5 · Contract testing 缺口分析

**目标**：为什么 42 tests 全绿还是在 T8 挂了三次？T12 正式启时需要补什么测试层？

**动作**：

写一份 `docs/design/contract_testing_gap_v1.md`：

1. **现状诊断**：列出现有 42 个测试覆盖的合同维度（schema / mtime / cwd / ... 各几个）
2. **三次 T8 挂的根因归类**：每次挂是哪层合同缺测试？
3. **建议新增层**：**mini-mock vendor E2E** —— 用 10KB 假 FASTQ + 空 rule body / stub Snakefile 走完 DAG，目标 <5 秒完成
4. **测试桩清单**：预计新增多少测试件、覆盖哪些维度、预计代码量
5. **T12 纳入优先级**：这是 T12 审查的子任务，还是独立 T12.5？

**DoD**：`docs/design/contract_testing_gap_v1.md` 存在且 200 行以内。

**不做**：不写任何 test 代码。

---

### O6 · 综合决策：#8 路径选择

**前置**：O1 完成

**动作**：基于 O1 的 4 个答案 + O3 的合规 audit，产出一份 `docs/design/backlog_8_resolution_plan_v1.md`：

1. 三路径 a/b/c 的**最终评估表**（代价 / 风险 / 复位难度 / 时间预算【用"一次 session" / "跨多次 session" 而非 Day/Week】）
2. **推荐路径** + 置信度
3. 选定路径的**实施 DAG**（仅骨架，不实施）：前置 → 执行 → 验证 → 回滚预案
4. 若选 c（SHA 升级）：列出"升级后需重跑的校验"清单（test/T4 smoke/T9 重算 / ...）

**DoD**：设计文档存在；**不执行任何路径**；不改 submodule pointer。

---

### O7 · snapshot + backlog bump（串行，最后一步）

**动作**：

1. `docs/progress_snapshot.md`：
   - §1 任务表：T8 行 status 标注"⏸ 阻塞于 #8（vendor typo），调研完成"
   - §2 commit 时间轴追加本轮所有 commit
   - §6 backlog 现状：#7 → ✅ RESOLVED；#8/#9 条目 refresh；新增本轮 4 份设计稿引用
   - §9 已知风险：加入 classify_studies 72% 量化结果
   - §10 冷启动校验：tests 数字若因本轮调研未变保持 42
2. `docs/backlog.md`：同步补充 O1-O6 的产出引用

**DoD**：单独 commit `docs(o): session-O research + design docs + backlog refresh`。

## §4 硬约束（违反即回滚）

- 不动 `vendor/**`（**含 `.groovy`**）、submodule SHA、宪法、metadata.csv、paths.toml、.gitmodules
- **不 push**（本地领先 1 状态允许新增，但保持不 push）
- **本轮不写任何 src/ 代码、不写任何 tests/ 代码** —— 纯调研 + 设计文档 + snapshot
- 禁启 T12/T13/T14
- 禁用时间单位（Day/Week/Sprint）—— 用 DAG / DoD / "一次 session" / "一轮尝试"

## §5 断点协议（防死磕）

| 情况 | 动作 |
|---|---|
| §1 冷启动任一不绿 | abort |
| O1 upstream clone 失败（网络 / 权限）| 记 blocker，跳 O1，先做 O2-O5 |
| O2 rule body 读不懂 / 逻辑不显式 | 不推断，标"需 snakescale 文档或 upstream 咨询"，量化部分仍做 |
| O3 宪法无明文 | **保守判定为"需用户裁定"**，O6 路径 b 标"待用户 sign-off"；不擅自定性 |
| O4/O5 写不下去 | 单子任务 abort，其他继续；汇报哪个卡住及为何 |
| 任一 pytest 退化 < 42 | 立即 `git reset --hard`，abort 全轮 |

## §6 交付清单

结束时必须同时满足：
- [ ] O1 answers 报告（可嵌在 O6 设计稿里）
- [ ] `/tmp/t8_invalid_studies_audit.csv` 存在
- [ ] `docs/design/method_f_codification_v1.md` 存在
- [ ] `docs/design/contract_testing_gap_v1.md` 存在
- [ ] `docs/design/backlog_8_resolution_plan_v1.md` 存在
- [ ] snapshot + backlog.md 已 bump（O7 commit 落地）
- [ ] 本轮不写 src/ 代码、不写 tests/ 代码、不动 vendor
- [ ] 最终汇报：中文；区分已验证事实 / 推断；每个判断附置信度

## §7 反馈汇报要求

汇报按以下结构（中文，markdown）：

1. §1 冷启动校验结果（snapshot drift 若有必须报告）
2. O1-O6 每个子任务的 DoD 完成情况（✅ / 部分 / ❌ + 原因）
3. **关键决策建议**（#8 路径 a/b/c 推荐 + 置信度）
4. **classify_studies 风险量化结果**（具体数字）
5. **本轮新增 commit 清单**（本地，未 push）
6. 下一轮（Session-P）建议入口

---

**End of handoff**. Codex 从第二部分 §1 起手即可。
