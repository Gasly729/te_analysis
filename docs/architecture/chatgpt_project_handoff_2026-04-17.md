# ChatGPT 项目交接文档（2026-04-17）

## 1. 文档目的

这份文档用于把 `te_analysis` 项目当前的真实进度、已完成里程碑、未完成项、风险边界和后续建议，完整交接给下一个 ChatGPT / Codex 窗口继续工作。

这不是设计草案，而是基于当前仓库、真实 runtime、真实测试和真实数据接入结果整理的状态快照。

---

## 2. 项目基本信息

- 仓库路径：`/home/xrx/my_project/te_analysis`
- 当前开发仓库：只有这个仓库是 active repo
- 当前最新提交（HEAD）：
  - `6bab8f1 feat: add raw FASTQ ingestion engine with dual-batch conflict resolution, metadata cross-validation, and symlink materialization contract for data/raw handoff layer`
- 近期关键提交：
  - `55da000 feat: split Stage 3 output contract into baseline-specific regression lock and general cross-runtime validation layer`
  - `10e84f2 feat: extend Stage 2 positive baseline to Stage 3 final output contract`
  - `86abc7a feat: add Stage 2 positive baseline specification`
- 当前工作树状态：
  - `M scripts/ingest_raw_symlinks.py`
  - `M tests/test_ingest_raw_symlinks.py`
- 当前 `.gitignore` 没有挂起改动

---

## 3. 项目固定边界

这些边界已经基本拍板，后续不要随意重构：

1. 项目 scope 是 **TE-only**，不是 TEC。
2. 架构固定为：
   - `upstream / handoff / downstream`
3. downstream 的主 handoff object 是：
   - `experiment-level .ribo`
4. legacy downstream 复用策略固定：
   - 复用 `raw_motheds/TE_model`
   - 通过 `legacy-compatible sandbox`
   - 不拆 `TE_model / winsorization`
5. frozen legacy tree 不允许改。
6. 已经有一条 human / HeLa 的正路径 baseline 成功打通并被冻结，不能轻易动合同语义。

---

## 4. 已完成的大里程碑

### 4.1 downstream Stage 0 → 3 已打通

已确认成功的正基线：

- `run_id = verify_gse105082_hela_triplet_stage2`
- cohort：
  - `GSM2817679`
  - `GSM2817680`
  - `GSM2817681`
- grouping：`HeLa`

真实成功路径：

1. readiness 成功
2. Stage 0 成功
3. Stage 1 成功
4. Stage 2 成功
5. Stage 3 成功

真实入口：

- Stage 2：
  - `Rscript src/TE.R "trials/<run_id>"`
- Stage 3：
  - `python src/transpose_TE.py -o "trials/<run_id>"`

Stage 2 关键输出：

- `human_TE_sample_level.rda`
- `human_TE_cellline_all.csv`

Stage 3 关键输出：

- `human_TE_cellline_all_T.csv`

### 4.2 baseline / contract / regression lock 已冻结

已存在的关键文件：

- `configs/downstream/legacy_te_stage2_positive_baseline.json`
- `docs/architecture/legacy_te_stage2_positive_baseline.md`
- `tests/test_legacy_te_stage2_positive_baseline.py`
- `tests/test_legacy_te_stage3_final_output_contract.py`
- `tests/test_fixture_integrity.py`

当前合同语义：

1. `verify_gse105082_hela_triplet_stage2` 是 baseline-specific 的成功样本。
2. Stage 3 的 `10862 x 1` 和列名 `HeLa` 只作为这条 baseline 的回归常量，不是跨物种通用规则。
3. 通用 Stage-3 contract 只锁：
   - 文件存在
   - 非空
   - 路径在受控 runtime root 下
   - 可解析
   - 列无重复
   - 行索引非空
   - 与 Stage 2 → Stage 3 的真实转置 / 后缀剥离语义一致

### 4.3 Stage 2 最小样本 fail-fast 已实现

现有规则：

1. 单样本 runtime 允许用于 Stage 0 / Stage 1 smoke。
2. 当 `target_stage >= 2` 时，要求至少 2 个 matched samples。
3. 这条限制是 legacy `TE.R` 的方法学边界，不是 wrapper bug。
4. 不应通过 patch `TE.R` 去支持 single-sample Stage 2。

### 4.4 fixture 漂移问题已处理

`tests/test_data/` 之前出现过意外 drift：

- 多个 `*_all.ribo` symlink 丢失
- `GSE106448.ribo`
- `all.ribo`

这些都已经审计并恢复，另外加了：

- `tests/test_fixture_integrity.py`

---

## 5. raw 数据接入层（PR -1 / PR -1b / PR -1b.1）现状

### 5.1 PR -1：最初版 raw symlink ingest

已做过第一版：

- 从 organized 数据树接入
- 生成 `data/raw/_manifest.tsv`
- 生成 `data/raw/_ingest_report.md`
- 做过 dry-run / apply / 测试

但这个版本后来被 PR -1b 的“双源融合”版本替代。

### 5.2 PR -1b：双源 raw FASTQ 重组接入

已实现并实跑的双源输入：

- `batch1 = /home/xrx/raw_data/TE_ribo-seq/sradownloader_output`
- `batch2 = /home/xrx/raw_data/output2`

当前脚本：

- `scripts/ingest_raw_symlinks.py`

当前 alias 表：

- `scripts/organism_alias_min.yaml`

当前测试：

- `tests/test_ingest_raw_symlinks.py`

当前真实输出：

- `data/raw/_manifest.tsv`
- `data/raw/_ingest_report.md`
- `data/raw/_source_conflict.tsv`

真实 source probe 结果：

- batch1：
  - `4696` 个 FASTQ
  - 约 `5.4TB`
  - 目录深度分布：`{2: 4696}`
- batch2：
  - `203` 个 FASTQ
  - 约 `346.2GB`
  - 目录深度分布：`{1: 203}`

### 5.3 PR -1b 的真实 metadata 事实

当前仓库内真实 metadata 文件：

- `data/raw/metadata.csv`

它和最初想象的不完全一致，已经通过实证确认：

1. 正确读法是：
   - `pd.read_csv(path, header=0, skiprows=[0])`
2. 它 **没有** `run_alias` 列。
3. 它有这些关键列：
   - `experiment_alias`
   - `organism`
   - `corrected_type`
   - `experiment_accession`
   - `study_name`
   - `library_strategy`
   - `library_layout`
4. 因为没有 `run_alias`，PR -1b 脚本实际采用了 fallback：
   - 优先 `run_alias`（若将来有）
   - 否则回退到文件名中的 `GSM/SRX/ERX/DRX`
   - 再用 metadata 的 `experiment_alias / experiment_accession` 做匹配

### 5.4 PR -1b 初次 apply 后的状态

初次 PR -1b 实跑后，manifest 关键统计是：

- `matched = 4434`
- `skipped = 510`
- `srr_not_in_metadata = 504`
- `size_mismatch_between_batches = 6`

之后又做了一次只读调查，确认：

1. `srr_not_in_metadata = 504` 实际混了两类东西：
   - 真正的 “物理文件存在但 metadata 查不到”
   - “metadata 有记录但没落到 matched” 的 orphan_metadata
2. `size_mismatch` 其实只有 3 个冲突 key，对应 6 条 manifest 行（batch1 + batch2 各 1）

### 5.5 PR -1b.1：对 PR -1b 的后续修复

这部分目前**代码已经改好并实跑成功，但还没有 commit**。

当前挂起文件：

- `M scripts/ingest_raw_symlinks.py`
- `M tests/test_ingest_raw_symlinks.py`

本轮修复做了 4 件事：

#### 修复 1：拆分 orphan_metadata

现在：

- `orphan_metadata` 单独作为 skip_reason
- `srr_not_in_metadata` 只保留“物理文件存在但 metadata 查不到”

#### 修复 2：扩展 hybrid 检测

除了 `_x_`，现在还识别：

- `" x "`
- `"*"`（星号）

用于命中这类 metadata：

- `Saccharomyces cerevisiae* Saccharomyces paradoxus`

#### 修复 3：新增 `--force-prefer-batch2`

新增 CLI 参数：

- `--force-prefer-batch2 SRR6255540,SRR6255541,SRR6255542`

作用：

- 对指定 SRR，即使 batch1 / batch2 size 不一致，也允许选 batch2
- 同时在 manifest 的 `warning` 字段写入：
  - `forced_prefer_batch2_size_mismatch`

这 3 个 SRR 已人工确认：

- `SRR6255540`
- `SRR6255541`
- `SRR6255542`

它们属于：

- `Mus_musculus`
- `GSE106528`

判断为：

- batch1 = 部分下载
- batch2 = 完整重下载

#### 修复 4：实跑后的 manifest 统计已变化

最新真实 manifest：

- 路径：`data/raw/_manifest.tsv`
- MD5：`8b9a40b18a748a1fc386996356195faf`

最新统计：

- `manifest_rows = 4938`
- `matched = 4437`
- `skipped = 501`
- `srr_not_in_metadata = 256`
- `orphan_metadata = 245`
- `size_mismatch_between_batches = 0`

warning 分布：

- `single_but_mate_1_only = 3786`
- `single_but_mate_1_only;forced_prefer_batch2_size_mismatch = 3`

注意：

1. `245` 不是 bug。
2. 初步估算的 `248` orphan_metadata 之所以少了 3，是因为：
   - 被 force promote 的 3 个 SRR 已落成 matched
   - 它们对应的 metadata 不再算 orphan

### 5.6 当前 raw ingest 测试状态

当前 ingest 测试数：

- `18 passed`

回归锁状态：

- `6 passed`

本轮新增的 3 条测试是：

- `test_orphan_metadata_has_distinct_skip_reason`
- `test_hybrid_detected_by_star_separator`
- `test_force_prefer_batch2_promotes_size_mismatch_to_matched`

---

## 6. 现在最重要的“当前状态判断”

### 6.1 什么已经稳定

以下内容已经稳定，后续模型不要重复质疑：

1. downstream Stage 0 → 3 的 human / HeLa triplet baseline 已经成功。
2. baseline / contract / regression lock 已经落地。
3. raw FASTQ 双源接入层已经能在真实数据上工作。
4. metadata 的真实 schema 已经实证，不要再假设有 `run_alias`。

### 6.2 什么还没收尾

当前最重要的未收尾项只有一个：

#### PR -1b.1 的代码改动尚未 commit

当前工作树仍然有：

- `scripts/ingest_raw_symlinks.py`
- `tests/test_ingest_raw_symlinks.py`

这意味着：

1. 现在**不适合直接切 PR -1c 分支**。
2. 否则会把 PR -1b.1 的改动一起带进下个分支，污染 PR 边界。

### 6.3 `.gitignore` 当前状态

根据当前仓库状态：

- `.gitignore` 现在不是 modified
- 之前“PR -1b.1 要单独给 `.gitignore` 做 commit”这个计划，在当前工作树里已经没有对象
- 当前最近日志里没有你要求的那条 `.gitignore` 独立 commit

所以：

1. 不能伪造 empty commit
2. 不能为了满足旧 prompt 去硬做一个空的 `.gitignore` 提交

---

## 7. 对 PR -1c 的正确理解

不要把 PR -1c 狭义理解成：

- “只处理 256 条 `srr_not_in_metadata`”

这不够。

PR -1c 真正更核心的任务应该是：

1. 做 **SRX → SRR 展开**
2. 产出可靠的 `metadata_runs.tsv` 或等价物
3. 把 experiment-level metadata 和 run-level FASTQ join key 彻底理顺

`256` 条 `srr_not_in_metadata` 只是目前最显眼的对冲症状，不是 PR -1c 的全部。

---

## 8. 当前关键数字总表

### 8.1 downstream baseline

- Stage 2 baseline runtime：
  - `verify_gse105082_hela_triplet_stage2`
- 成功输出：
  - `human_TE_sample_level.rda`
  - `human_TE_cellline_all.csv`
  - `human_TE_cellline_all_T.csv`

### 8.2 raw ingest 当前真实统计

- source FASTQ 总数：`4899`
- matched：`4437`
- skipped：`501`
- `srr_not_in_metadata`：`256`
- `orphan_metadata`：`245`
- `size_mismatch_between_batches`：`0`
- promoted SRR：
  - `SRR6255540`
  - `SRR6255541`
  - `SRR6255542`

### 8.3 metadata 当前真实状态

- 行数：`2644`
- 关键列存在：
  - `experiment_alias`
  - `organism`
  - `corrected_type`
  - `experiment_accession`
  - `study_name`
  - `library_strategy`
  - `library_layout`
- `run_alias`：**不存在**

### 8.4 orphan_metadata 分布（只读调查结果）

当前 orphan_metadata 数量：

- `245`

分布较多的 organism：

- `Mus musculus`
- `Zea mays`
- `D. melanogaster`
- `Rattus norvegicus`
- `Rat`
- `Homo sapiens`
- `Saccharomyces paradoxus`
- `Saccharomyces uvarum`
- `Leishmania donovani`

### 8.5 当前未提交状态

- `M scripts/ingest_raw_symlinks.py`
- `M tests/test_ingest_raw_symlinks.py`

---

## 9. 下一个模型必须遵守的工作边界

### 9.1 进入 PR -1c 之前

必须先做：

1. 审计 `.gitignore` 当前真实状态是否还有需要提交的内容
2. 把以下两处已完成但未提交的改动落 commit：
   - `scripts/ingest_raw_symlinks.py`
   - `tests/test_ingest_raw_symlinks.py`
3. 确保 `git status --short` 干净后，再切 PR -1c

### 9.2 明确禁止

1. 不伪造 empty commit
2. 不 stash / reset / amend
3. 不 rebase / 不 force-push
4. 不改 frozen legacy tree
5. 不把 PR -1b.1 和 PR -1c 混在一个分支里

---

## 10. 建议给下一个模型的任务顺序

### Step 1：收尾 PR -1b.1

只做：

1. 审计 `.gitignore` 去向
2. commit `scripts/ingest_raw_symlinks.py`
3. commit `tests/test_ingest_raw_symlinks.py`
4. 跑：
   - `tests/test_ingest_raw_symlinks.py`
   - `tests/test_fixture_integrity.py`
   - `tests/test_legacy_te_stage2_positive_baseline.py`
   - `tests/test_legacy_te_stage3_final_output_contract.py`

### Step 2：在 clean main 上开始 PR -1c

PR -1c 重点：

1. SRX → SRR 展开
2. 生成 metadata 级 run mapping
3. 解释并吸收现在剩余的 `srr_not_in_metadata`

---

## 11. 三条“AI 生成提示词”原文归档

下面三条 prompt **不要求现在执行**。它们只是归档在这里，供下一个 ChatGPT / Codex 参考。可以直接复制，也可以只参考其中的结构。

### 11.1 Prompt 1：PR -1b.1 followup — `.gitignore` 审计 + commit 挂起改动

```text
PR -1b.1 followup — .gitignore 审计 + commit 挂起改动

执行方式：IDE Codex 插件（非 CLI）。
性质：收尾，非新增 feature。
严格禁止：

不伪造 empty commit
不 stash / reset 任何工作树改动
不 amend 6bab8f1（不改 main 已 push 的历史）
不 rebase / 不 force-push
本 prompt 作用域仅限 .gitignore + scripts/ingest_raw_symlinks.py + tests/test_ingest_raw_symlinks.py，任何其他改动一律拒绝并停机

1. 核心任务
两件事，顺序先 1.A 后 1.B：
1.A（审计 .gitignore 去向）
验证 memory 和 PR -1b 报告里记录的 "仍悬挂 M .gitignore" 当前去向是 A / B / C 中的哪一个：

A：6bab8f1（PR -1b commit）已经把 .gitignore 修正吃进去了 → 本 PR 无需再做任何 .gitignore commit
B：HEAD 的 .gitignore 仍然保留 bd5fe5e 引入的过宽 /tests/ 规则、且缺 /raw_motheds/ → 本 PR 需要独立 commit 修正
C：中间态（部分修正部分没修） → 按实际 diff 决定是否补 commit，精确列明

1.B（落 commit PR -1b.1 的代码改动）
把工作树中两处挂起改动：
M scripts/ingest_raw_symlinks.py
M tests/test_ingest_raw_symlinks.py
落成一个独立 commit（不合并 .gitignore）。

2. 输入（全部只读 git 命令，先不改任何文件）
请先跑以下命令并把 stdout 落到 /tmp/pr_1b1_followup_audit.txt：
bashgit status --porcelain
git log --oneline -n 10
git stash list
git log --oneline --follow -n 10 -- .gitignore
echo "--- bd5fe5e diff on .gitignore ---"
git show bd5fe5e -- .gitignore
echo "--- 6bab8f1 diff on .gitignore ---"
git show 6bab8f1 -- .gitignore
echo "--- HEAD .gitignore content ---"
cat .gitignore
echo "--- working tree diff on M files ---"
git diff --stat scripts/ingest_raw_symlinks.py tests/test_ingest_raw_symlinks.py
把 /tmp/pr_1b1_followup_audit.txt 的完整内容原样贴回给用户，作为后续判断依据。

3. 处理逻辑
3.1 判定 .gitignore 去向
基于 2 节的 audit 输出，必须明确说出 A / B / C，并给出证据：

6bab8f1 的 .gitignore diff 是否包含 /raw_motheds/？
6bab8f1 的 .gitignore diff 是否移除 /tests/（或窄化为 /tests/test_data/...）？
HEAD .gitignore 里是否还有裸 /tests/ 这条过宽规则？

3.2 落 PR -1b.1 代码 commit
bashgit add scripts/ingest_raw_symlinks.py tests/test_ingest_raw_symlinks.py
git status --porcelain     # 确认 staged 的只有这两个文件
git commit -m "feat(ingest): split orphan_metadata label, extend hybrid regex, add --force-prefer-batch2

- orphan_metadata now carries its own skip_reason instead of being folded into srr_not_in_metadata
- hybrid detection now recognises '_x_', ' x ', and '*' separators on raw organism strings
- new CLI flag --force-prefer-batch2 promotes listed SRRs from size_mismatch to matched (batch2 wins)
- real apply: SRR6255540,SRR6255541,SRR6255542 (Mus_musculus GSE106528) → promoted
- 18 ingest tests green + 3 regression locks green
- manifest md5: 8b9a40b18a748a1fc386996356195faf"
3.3 仅在判定为 B 或 C 时，追加 .gitignore commit
bash# 按 audit 结论编辑 .gitignore，使其最终满足：
#   - 含 /raw_motheds/
#   - 仅屏蔽 /tests/test_data/GSE105082/（或 PR -1b 实际落地的精确路径），不含裸 /tests/
#   - 含 /data/scratch/ （如果尚未有）
#   - 保留其他已有规则，不误删
git diff .gitignore      # 人眼过一遍再 add
git add .gitignore
git commit -m "chore(gitignore): narrow /tests/ to /tests/test_data/GSE105082/ and add /raw_motheds/"
判定为 A 时：跳过 3.3，不创造任何 .gitignore commit。
3.4 事后验证
bashgit status --porcelain       # 必须为空
git log --oneline -n 5
python -m pytest -q tests/test_fixture_integrity.py tests/test_legacy_te_stage2_positive_baseline.py tests/test_legacy_te_stage3_final_output_contract.py
python -m pytest -q tests/test_ingest_raw_symlinks.py
三条 regression lock 必须 6/6 passed。ingest 测试必须 18/18 passed。任一红就停机报告、不 push。
3.5 Push
bashgit log origin/main..HEAD --oneline     # 列出将要 push 的 commit
git push origin main

4. 预期输出
请 Codex 显式以下面格式贴回（不留字段空缺）：
== PR -1b.1 followup ==
audit_log: /tmp/pr_1b1_followup_audit.txt (内容见下)
------
<粘贴 /tmp/pr_1b1_followup_audit.txt 完整内容>
------

gitignore_resolution: A | B | C
gitignore_evidence:
  6bab8f1_touched_gitignore: yes | no
  HEAD_has_broad_/tests/_rule: yes | no
  HEAD_has_/raw_motheds/: yes | no
  HEAD_gitignore_content: |
    <完整内容>

commits_created:
  - <hash> <subject>          # PR -1b.1 代码 (必有)
  - <hash> <subject>          # 仅 B/C 情况有

pytest_after:
  regression_locks: 6/6 passed
  ingest_tests: 18/18 passed

git_status_after: clean | DIRTY
stash_list: empty | <content>
pushed_to_origin: yes (via git push origin main) | no (reason)
skipped_or_blocked:
  - <items or "none">
```

### 11.2 Prompt 2：先核对数字，再标出进入 PR -1c 前必须收尾的悬挂项

```text
先做 3 件事：核对 Codex 的数字 / 标出必须在进入 PR -1c 之前收尾的 2 个悬挂项 / 写一条收尾 prompt。不接受 Codex 的 "直接进入 PR -1c" 建议 —— 有未 commit 的改动分支切换会污染。
PR -1b.1 结果判定
核心逻辑通过（置信度：高），4 处修复都能在 manifest 数字上对上账。但有两个收尾项不能跳过。
数字对账（自洽性检查）
项旧新Δ解释
total49444938-63 条 size_mismatch 的 batch1 侧物理行 被丢弃（batch2 晋位保留）
matched44344437+33 条 force-promote 落到 matched
skipped510501-9-6（size_mismatch 清零）+ -3（orphan 对应的 SRR 落地成 matched）
srr_not_in_metadata504（混 256+248）256label 分离真实孤儿文件，未变
orphan_metadata0245标签独立248 → 245 因为 3 条 GSE106528 SRR 已 promote 到 matched，其 metadata 不再孤儿
245 vs 248 的解释可信（置信度：高）。promoted 的 3 条 SRR6255540/41/42 都是 Mus musculus GSE106528，metadata 里本就对得上这 3 个 SRR 背后的 SRX → 248 - 3 = 245 自洽。
Codex 关于 warning 统计的提醒是对的：single_but_mate_1_only;forced_prefer_batch2_size_mismatch 是组合 token，未来按 ; 拆了统计，不要当复合字符串 key。
❌ 两个必须先收尾的悬挂项
悬挂项 1：PR -1b.1 的代码改动还没 commit
 M scripts/ingest_raw_symlinks.py
 M tests/test_ingest_raw_symlinks.py
这两个文件是 PR -1b.1 的全部修复产物，测试通过 + 实跑通过但没 commit。如果切 pr/-1c-expand-sra-runs 分支就会把这两个改动带过去，PR 边界立刻模糊。必须先 commit 到 main（或 pr/-1b.1 分支再 merge）。
悬挂项 2：.gitignore 状态与 memory 不一致，需证据
memory 里（project_te_analysis_status.md L109）和 PR -1b 完成报告里都明确写了 M .gitignore 悬挂、PR -1b.1 要独立 commit。现在 Codex 报告说"工作树里 .gitignore 已经不是 modified"——没说去哪了。
按 feedback_codex_workflow.md 的规则，这种关键状态缺失不能默认最好情况。三种可能性：

A（最可能）：PR -1b 的 6bab8f1 commit 把 .gitignore 修正一起吃进去了 → 无需再做任何事，只需证据
B：bd5fe5e 的过宽 /tests/ 规则还在 HEAD 上 → 需要独立 commit 修正（这是 memory 原本预期要做的）
C：改动被 stash / reset 丢了 → 需要重做

Codex 没给 git log 6bab8f1 -- .gitignore 或 git stash list 的输出，不能凭空判断。
对 Codex "直接进 PR -1c" 建议的判断
不采纳（原因 2 点）：

分支干净性问题（悬挂项 1）。PR -1c 应该从 clean 的 main HEAD 拉分支。
Codex 把 PR -1c 窄化为 "对 256 条真实 srr_not_in_metadata 做 metadata 补查"，这是口径错位。PR -1c 的真实任务是所有 2644 个 experiment-level 记录的 SRX→SRR 展开，256 只是其中一个对冲项。按 Codex 这个口径做会漏掉 PR -1c 最核心的产出 metadata_runs.tsv（未来全体 per-sample runtime 的 join key 源）。
```

### 11.3 Prompt 3：PR -1c / PR 0 的设计选择说明

```text
两条 prompt 的关键设计选择（你跑之前可能想改）
PR -1c

离线缓存强制，首轮只写不洗（避免失败重跑爆 API）
Manifest 对冲被我升格为本 PR 必达项 —— 这是验证"256/248 错位 = SRX/SRR 展开两端"这个假设的唯一闭环路径
cell_line 只做正则级补全（ENA sample_title），BioSample / GEO HTML 推到 PR 2
默认 concurrency=5，首轮建议 --limit 200 先 smoke

PR 0

snakescale 部署出仓库到 /home/xrx/tools/，符合"外部调用、不 fork"的拍板
不自动下载样本 B 的 FASTQ —— 如果物理文件在 data/raw/ 找不到就停机询问，避免无预算网络操作
样本 B 的 guess_adapters.py 决策被我显式分成 a/b/c/d 四分支，Codex 必须明确落哪一支；落 d 分支（与原文逻辑不一致）是 P0 信号

两个我在写的时候犹豫过的点（你可以一票否决）

PR -1c 要不要顺便做 organism 归一化？我选了不做，因为 PR 2 已经占着这事。若你想一步到位合并，告诉我，我把 PR -1c 扩到约 2-3 天工期。
PR 0 要不要跑 PAIRED 样本？我选了只跑 SINGLE。PAIRED 在 metadata 里 Ribo 只有 38 条，推到 PR 4 里和 yeast 一起压测更有性价比。

等 PR -1b.1 manifest 贴回来，如果 orphan_metadata 数量级和 PR -1b 估计偏离较大（>±20%），PR -1c §4.3 的 metadata_runs.tsv 预期规模我会调一下。其余结构不受影响。
```

---

## 12. 给下一个 ChatGPT 的一句话总结

当前项目已经把 **human/HeLa downstream 正路径** 和 **双源 raw FASTQ 接入层** 跑通了；眼下真正需要先收尾的是 **PR -1b.1 的两个未提交文件**，然后再干净地进入 **PR -1c 的 SRX→SRR 展开与 metadata_runs.tsv 建设**。

