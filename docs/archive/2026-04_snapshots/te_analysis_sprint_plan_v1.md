# te_analysis 任务分解与依赖合同

**版本**：v1（模块尺度重写版，取代时间尺度草案）
**尺度**：任务 / 依赖 / DoD，**不含任何时间单位**
**配套文档**：
- 架构：`te_analysis_top_level_design_v1.md`
- 模块合同：`te_analysis_module_contracts_v1.md`
- 任务分解（本文件）

**使用方式**：任一任务满足"前置 DoD 全部绿灯"即可启动；无依赖关系的任务可并行推进；不按日历推进，按依赖满足推进。

---

## 0. 文档定位

本文件回答一个问题：**"把顶层设计落地成一个可跑管线，需要哪些离散任务？每个任务的边界在哪里？怎么算完？"**

不回答：何时开始、何时结束、每天做什么。

任务状态机：

```text
[未启动]  ──前置全绿──>  [进行中]  ──DoD全绿──>  [已完成]
                                  │
                                  └──DoD未达──>  [需返工]
```

---

## 1. 任务依赖 DAG

```text
                      [ T0 Vendor-Recon ]
                              │
          ┌───────────────────┼──────────────────────────────┐
          │                   │                              │
     [ T1 Skeleton ]          │                              │
          │                   │                              │
   ┌──────┼──────┐            │                              │
   │      │      │            │                              │
 [T2]   [T3]   [T6]           │                              │
Config Meta  Downstream       │                              │
   │      │      │            │                              │
   └──┬───┴──────┤            │                              │
      │          │            │                              │
    [ T4 stage_inputs ] ◄─────┘                              │
           │                                                 │
    [ T5 run_upstream ] ◄───────────────────────────────────┘
           │                                 │
           └─────► [T7 Makefile] ◄──T6───────┘
           │                                 │
    [ T8 Upstream-E2E ]              [ T9 Downstream-E2E ]
           │                                 │
    [T10 Unit Tests]                 [T11 Smoke Test]
           │                                 │
           └──────────┬──────────────────────┘
                      │
               [ T12 Legacy Purge ]
                      │
          ┌───────────┴────────────┐
          │                        │
   [T13 Docs Finalize]      [T14 Baseline Lock]
```

**依赖类型**：实线 = 硬前置（DoD 必须全绿才能开工）

---

## 2. 任务总览表

| ID | 名称 | 前置 | 关联合同条款 | 本任务行数上限 |
|---|---|---|---|---|
| T0 | Vendor 合同侦察 | ∅ | §13 M13 | N/A（纯文档） |
| T1 | CCDS 骨架 + Submodule | ∅ | §2, §9 M8/M9 | N/A（结构） |
| T2 | `config.py` 路径常量 | T1 | §5 M4 | ≤ 60 |
| T3 | `metadata.csv` schema + 首批填充 | T0, T1 | §8 M7 | N/A（数据） |
| T4 | `stage_inputs.py` 实现 | T0, T1, T2, T3 | §2 M1 | ≤ 250 |
| T5 | `run_upstream.py` 实现 | T0, T2, T4 | §3 M2 | ≤ 80 |
| T6 | `run_downstream.py` 实现 | T0, T2 | §4 M3 | ≤ 80 |
| T7 | Makefile 统一入口 | T4, T5, T6 接口稳定 | §6 M5 | ≤ 80 |
| T8 | 上游端到端（GSE132441） | T5, T7 | 架构 §11 C | N/A（验证） |
| T9 | 下游端到端（GSE105082） | T6, T7 | 架构 §11 C | N/A（验证） |
| T10 | `stage_inputs` 单测 | T4 | §10 M10 | ≤ 150 |
| T11 | 下游冒烟测试 | T9 | §11 M11 | ≤ 100 |
| T12 | 旧模块清理 | T8 绿 AND T9 绿 | 架构 §11 D | N/A（删除） |
| T13 | 文档定稿 | T12 | §12 M12 | N/A（文档） |
| T14 | 基线冻结 | T12 | §11 M11 扩展 | ≤ 50 行测试 fixture |

---

## 3. 并行性矩阵

| 任务组 | 启动条件 | 可同时推进 | 理由 |
|---|---|---|---|
| {T0, T1} | 立即 | ✓ | 互不依赖：T0 读 vendor 源码，T1 搭目录 |
| {T2, T3, T6} | T1 绿后 | ✓ | 互不读写同一产物 |
| {T10} | T4 绿后 | ✓ | 独立于 T5/T6/T7 |
| {T5, T6} | 各自前置满足后 | ✓ | 互不读写对方产物 |
| {T8, T9} | 各自前置满足后 | ✓ | 不同 study，不同链路 |
| {T13, T14} | T12 绿后 | ✓ | 独立产出 |

**反并行清单**（不要试图并行）：
- T4 与 T3 并行 → metadata schema 还没定就写 stage_inputs，保证翻车
- T5 与 T0 并行 → snakescale 启动命令还没侦察清楚就写壳
- T12 与 T8/T9 并行 → 删旧代码时主路径还没证明能走

---

## 4. 任务详细合同

### T0 — Vendor 合同侦察

| 属性 | 内容 |
|---|---|
| 核心职责 | 从 `vendor/snakescale` 与 `vendor/TE_model` 源码中提取本项目自写代码所需的全部契约，落地为 `references/vendor_contracts.md` |
| 前置依赖 | ∅（只需两个仓库的 URL） |
| 输入 | 两个 submodule 的源码；README / example / Snakefile / Groovy |
| 输出 | `references/vendor_contracts.md`（结构见 module_contracts §13） |
| 边界 MUST | 每条事实附带 `vendor/<repo>/<file>:<lineno>` 引用 |
| 边界 MUST NOT | 猜；估计；"大概是"；抄整段源码 |
| 失败处置 | 查不到的字段明确写 `UNKNOWN — 需要人工确认`，列入"未解决问题清单"，**禁止**据此推进下游任务 |
| DoD | ① `project.yaml` 字段表完整 ② snakescale 启动命令完整 ③ FASTQ 目录/命名规约明确 ④ `TE.R` 输入目录结构明确 ⑤ `transpose_TE.py` 调用方式明确 ⑥ 未解决问题清单为空**或**清单内问题已标明 fallback 方案 |

---

### T1 — CCDS 骨架 + Submodule

| 属性 | 内容 |
|---|---|
| 核心职责 | 按顶层设计 §2 建立空骨架目录；用 `git submodule` 引入 snakescale 和 TE_model 并锁 SHA |
| 前置依赖 | ∅ |
| 输入 | 顶层设计 §2 的目录结构定义 |
| 输出 | ① 完整目录树 ② `.gitmodules` 有两条记录 ③ `.gitignore` 正确忽略 data 子目录 ④ `environment.yml` / `environment-r.yml` 空架 ⑤ Makefile 骨架（所有 target 为 `@echo "TODO"`） |
| 边界 MUST | submodule 锁定到"已在已知 study 上验证过"的 commit SHA |
| 边界 MUST NOT | 提交任何真实代码逻辑；修改 vendor 内文件；从旧项目复制 `src/te_analysis/upstream/` 任何内容 |
| 失败处置 | submodule 拉取失败 → 检查网络/SSH；**禁止**用 copy-paste 代替 submodule |
| DoD | ① `git submodule status` clean ② `make help` 输出正确 ③ 目录树与设计 §2 100% 对齐 ④ `.gitignore` 审查通过 |

---

### T2 — `config.py` 路径常量

| 属性 | 内容 |
|---|---|
| 核心职责 | 集中定义所有路径常量与环境变量覆盖点 |
| 前置依赖 | T1 |
| 输入 | T1 产出的目录结构 |
| 输出 | `src/te_analysis/config.py` |
| 边界 MUST | 仅 module-level `Path` 常量；支持 `TE_ANALYSIS_ROOT` 环境变量覆盖 |
| 边界 MUST NOT | 写 class；做 I/O；含业务逻辑；重复 vendor 内部路径 |
| 失败处置 | 路径解析失败直接 raise，不做 fallback |
| DoD | ① 行数 ≤ 60 ② `from te_analysis.config import DATA_RAW` 可用 ③ 单测覆盖"环境变量覆盖"场景 |

---

### T3 — `metadata.csv` Schema 定义 + 首批填充

| 属性 | 内容 |
|---|---|
| 核心职责 | 固化 metadata 字段合同；产出 GSE132441 + GSE105082 两个 study 的真实 metadata 行 |
| 前置依赖 | T0（需要知道 snakescale 的 pairing 期望）、T1（需要 `docs/` 目录） |
| 输入 | T0 产物、旧项目已有的 GSE132441 / GSE105082 信息、本地 FASTQ 清单 |
| 输出 | ① `docs/metadata_schema.md` ② `data/raw/metadata.csv`（含两个 study 的所有 run） |
| 边界 MUST | 严格按模块合同 §8 M7 字段表 |
| 边界 MUST NOT | 新增合同外列；把 SRX↔SRR 做成自动展开工具（手工展开即可） |
| 失败处置 | 某条 run 本地 FASTQ 缺失 → 不填进 metadata，列入"待补采"清单 |
| DoD | ① schema 文档齐 ② 两个 study 的 metadata 行齐 ③ 所有 `fastq_path` 指向真实存在文件 ④ Ribo/RNA `pair_id` 100% 一一对应 |

---

### T4 — `stage_inputs.py` 实现

| 属性 | 内容 |
|---|---|
| 核心职责 | metadata → snakescale 原生 `project.yaml` + FASTQ 符号链接 |
| 前置依赖 | T0（schema 权威）、T1、T2（路径常量）、T3（有真实 metadata 可试） |
| 输入 | `data/raw/metadata.csv` + `--study` + `--out` |
| 输出 | `<out>/project.yaml` + `<out>/staged_fastq/*` |
| 边界 MUST | 模块合同 §2.2 全部 MUST 条款 |
| 边界 MUST NOT | 模块合同 §2.3 全部 MUST NOT 条款（尤其 FASTQ 校验、审计文件） |
| 失败处置 | 模块合同 §2.5 失败模式表，全部 raise，无 fallback |
| DoD | ① 行数 ≤ 250 ② 对 GSE132441 产出的 `project.yaml` 被 snakescale dry-run 认可 ③ 幂等性验证通过 ④ 与 T10 一起绿 |

---

### T5 — `run_upstream.py` 实现

| 属性 | 内容 |
|---|---|
| 核心职责 | 拼接并 `subprocess.run` snakescale 原生启动命令 |
| 前置依赖 | T0（启动命令权威）、T2、T4（有合法产物可喂） |
| 输入 | `--study-dir`（T4 输出目录） |
| 输出 | 透传 snakescale 退出码；snakescale 自身产物 |
| 边界 MUST | 模块合同 §3.2 |
| 边界 MUST NOT | 模块合同 §3.3（解析日志、重试、并发、配置修改） |
| 失败处置 | 退出码非零即任务失败；**禁止**内部重试 |
| DoD | ① 行数 ≤ 80 ② 完整 snakescale 命令可在文件头注释一行写出 ③ 无状态（不写 log / db） |

---

### T6 — `run_downstream.py` 实现

| 属性 | 内容 |
|---|---|
| 核心职责 | 调 `TE.R` + `transpose_TE.py`，产物归位到 `data/processed/te/<STUDY>/` |
| 前置依赖 | T0（TE_model 调用契约）、T2 |
| 输入 | `--study-dir`、`--out-dir` |
| 输出 | `data/processed/te/<STUDY>/` 下的 `.rda` + `.csv` |
| 边界 MUST | 模块合同 §4.2 |
| 边界 MUST NOT | 模块合同 §4.3（重实现数学、后处理、图表） |
| 失败处置 | 任一子进程失败立即退出 |
| DoD | ① 行数 ≤ 80 ② 与 `verify_gse105082_hela_triplet_stage2` 旧产出数值一致（浮点精度内） |

---

### T7 — Makefile 统一入口

| 属性 | 内容 |
|---|---|
| 核心职责 | 把 T4/T5/T6 的 CLI 凝聚为 ≤ 7 个 make target |
| 前置依赖 | T4/T5/T6 的 CLI 契约稳定（代码不必全部完成，但签名已冻结） |
| 输入 | 三个模块的 CLI 参数列表 |
| 输出 | `Makefile` |
| 边界 MUST | 模块合同 §6.2 的 target 清单 |
| 边界 MUST NOT | 模块合同 §6.3（`all-studies`、dashboard、并行调度） |
| 失败处置 | target 之间的依赖失败自动中断（make 原生行为） |
| DoD | ① 行数 ≤ 80 ② `make help` ≤ 10 行 ③ `make env && make submodules && make all STUDY=<known-good>` 可一路通到 TE CSV |

---

### T8 — 上游端到端验证（GSE132441）

| 属性 | 内容 |
|---|---|
| 核心职责 | 在已知 positive baseline 上跑通 `make upstream`，产出 `.ribo` |
| 前置依赖 | T5、T7，且 GSE132441 的 FASTQ 已完整落地在 `data/raw/fastq/` |
| 输入 | T4 产出的 `project.yaml` + staged FASTQ |
| 输出 | `data/interim/snakescale/GSE132441/` 下的 `.ribo` + `all.ribo` |
| 边界 MUST | 直接跑 `make upstream STUDY=GSE132441`；不定制参数 |
| 边界 MUST NOT | 为了通过而临时修改 vendor；为了通过而在外壳打 patch |
| 失败处置 | 失败根因落入"合同误读 / 环境不全 / 数据损坏"三类之一，分别回溯到 T0 / T1 / T3 修复，**禁止**在 T5 内部 hack |
| DoD | ① `make upstream` 退出码 0 ② `.ribo` 文件存在且 size > 0 ③ 与旧项目同 study 产出做字节/结构对照，差异可解释 |

---

### T9 — 下游端到端验证（GSE105082）

| 属性 | 内容 |
|---|---|
| 核心职责 | 在已知 positive baseline 上跑通 `make downstream`，产出 TE CSV |
| 前置依赖 | T6、T7；GSE105082 的 `.ribo` 已就位（复用旧产物或重跑 T8 风格通路） |
| 输入 | 已有 `.ribo` 文件 |
| 输出 | `data/processed/te/GSE105082/` 下的 `.rda` + CSV 系列 |
| 边界 MUST | 与 `verify_gse105082_hela_triplet_stage2` 数值严格一致 |
| 边界 MUST NOT | 允许"大致一致"——必须数值级对齐 |
| 失败处置 | 数值不一致 → 回溯 T0 下游合同条款 → 回溯 T6 实现 |
| DoD | ① 产物齐 ② 与旧 baseline 数值比对通过 ③ 产出路径符合 CCDS `data/processed/` 约定 |

---

### T10 — `stage_inputs` 单元测试

| 属性 | 内容 |
|---|---|
| 核心职责 | 以 mock + fixture 验证 T4 的边界条件与幂等性 |
| 前置依赖 | T4 |
| 输入 | pytest `tmp_path` + stub FASTQ 文件 |
| 输出 | `tests/test_stage_inputs.py` |
| 边界 MUST | 覆盖模块合同 §10.1 场景表 |
| 边界 MUST NOT | 真调 snakescale；依赖真实 GSE 数据 |
| 失败处置 | 任一场景失败阻止 T4 进入 done |
| DoD | ① 行数 ≤ 150 ② CI 跑完 ≤ 10 秒 ③ 覆盖所有 `raise` 分支 |

---

### T11 — 下游冒烟测试

| 属性 | 内容 |
|---|---|
| 核心职责 | 把 T9 的验证固化为可自动运行的测试 |
| 前置依赖 | T9 |
| 输入 | 冻结的 baseline fixture（md5 或数值） |
| 输出 | `tests/test_smoke_downstream.py` |
| 边界 MUST | 模块合同 §11.2 |
| 边界 MUST NOT | 模块合同 §11.3（随机数据、真调 snakescale） |
| 失败处置 | 失败即阻断 T12 |
| DoD | ① 行数 ≤ 100 ② 开发机跑完 ≤ 5 分钟 ③ 数值差异检测包含容差定义 |

---

### T12 — 旧模块清理

| 属性 | 内容 |
|---|---|
| 核心职责 | 物理删除当前 repo 中所有"本合同禁止"的自造模块与产物 |
| 前置依赖 | T8 AND T9 同时绿（不允许只有一个绿就动手） |
| 输入 | 顶层设计 §11 D 清理清单 + 模块合同 §9 砍掉清单 |
| 输出 | 一个 PR，内容全是 `git rm` |
| 边界 MUST | 按顺序删：代码 → scripts → 审计 TSV → 自造目录 → 相关文档段落 |
| 边界 MUST NOT | 保留"以防万一"的旧模块；保留 commented-out 代码块；在同一 PR 里引入新功能 |
| 失败处置 | 删后 T8 / T9 / T10 / T11 任一红 → 回滚并定位依赖 |
| DoD | ① `src/te_analysis/upstream/` 不存在 ② `data/upstream/pilot/` 不存在 ③ 所有 `_*.tsv` 审计文件不存在 ④ `cloc src/` 对比清理前 -60% 以上 ⑤ T8/T9/T10/T11 仍全绿 |

---

### T13 — 文档定稿

| 属性 | 内容 |
|---|---|
| 核心职责 | 按模块合同 §12 清单确保 docs 有且仅有 4 篇 |
| 前置依赖 | T12 |
| 输入 | 最终代码 + 顶层设计 + 本文件 |
| 输出 | `docs/architecture.md` / `docs/metadata_schema.md` / `docs/reproducibility.md` / `docs/backlog.md` |
| 边界 MUST | 每篇 ≤ 合同 §12.1 规定的规模 |
| 边界 MUST NOT | 新增 ADR / RFC / 实验日记 |
| 失败处置 | 文档与代码不一致 → 以代码为准改文档 |
| DoD | ① 四篇齐 ② 新手按 `reproducibility.md` 从零 clone 能走到 TE CSV ③ `backlog.md` 已承接冲刺期间所有被拒的功能请求 |

---

### T14 — 基线冻结

| 属性 | 内容 |
|---|---|
| 核心职责 | 把 T8 / T9 的产物 md5 或数值写成 regression fixture |
| 前置依赖 | T12 |
| 输入 | 已清理后的 repo + T8/T9 稳定产物 |
| 输出 | `tests/fixtures/` 下的 baseline 记录；`git tag v0.1-mvp` |
| 边界 MUST | fixture 是数值/hash，不是完整产物文件 |
| 边界 MUST NOT | 把整个 `.ribo` 二进制塞进 git |
| 失败处置 | 冻结后某日 baseline 漂移 → 先怀疑 vendor submodule SHA 是否被改 |
| DoD | ① fixture 文件 ≤ 50 行 ② 打 tag ③ `pytest tests/` 从 clean state 全绿 |

---

## 5. 里程碑（以 DoD 绿灯计，不以日期计）

| 里程碑 | 判定 | 含义 |
|---|---|---|
| **M-Alpha** | T0 绿 | 已把 vendor 合同吃透，可以开始写外壳 |
| **M-Bravo** | T1/T2/T3 全绿 | 骨架齐备，核心模块可开工 |
| **M-Charlie** | T4/T5/T6 全绿 | 三个薄壳写完，等待端到端 |
| **M-Delta** | T7/T8/T9 全绿 | 端到端通路证明成立，新骨架可替代旧项目 |
| **M-Echo** | T12 绿 | 旧包袱彻底清除 |
| **M-Final** | T13/T14 绿 | 可复现 MVP 完成，`v0.1-mvp` 打 tag |

---

## 6. 任务状态推进规则

### 6.1 启动条件
- 所有前置任务的 **全部 DoD 条款** 绿灯
- 前置的部分绿灯**不构成**启动资格

### 6.2 暂停条件
- 任一 MUST NOT 被触发 → 立即暂停，审计代码
- 发现依赖的 vendor 合同有误 → 回到 T0 补正

### 6.3 完成条件
- 任务的 **全部 DoD 条款** 绿灯
- 代码行数在上限内
- 相关单测/冒烟测试全绿

### 6.4 返工条件
- 下游任务发现前置任务 DoD 实际未达 → 前置任务回到"进行中"
- 下游验证暴露合同误读 → T0 回到"进行中"

---

## 7. 反模式识别（触发即停工）

| 反模式 | 识别信号 | 应对 |
|---|---|---|
| 跳过 T0 直接写 T4/T5 | `stage_inputs.py` 里出现"我猜 project.yaml 的字段是..." | 停工；回 T0 |
| T4 未绿就开 T5/T6 | 两个任务同时 in_progress | 暂停后发者 |
| T12 在 T8/T9 都绿前启动 | 旧代码已删，主路径证明尚不成立 | 回滚清理 PR |
| T13 在 T12 前启动 | 文档先行，代码后变 | 暂停 T13，等 T12 |
| 任务内部长出不在合同里的功能 | 行数超限；新增未声明文件 | 功能写进 backlog，代码回滚 |
| 用"这个其实挺快的"绕开前置 | 任务状态跳跃 | 合同无 "快" 选项 |

---

## 8. Backlog 吸收机制

任何任务执行过程中冒出的"不如顺便也做 X"，**不得**并入当前任务，统一按以下格式落入 `docs/backlog.md`：

```markdown
## <条目标题>
- 来源任务：T?
- 触发场景：<具体情况>
- 涉及模块：<M? / vendor / docs>
- 本合同依据：<哪条 MUST NOT 阻止了立即实施>
- 回顾触发条件：<M-Final 绿后 / 第 N 个 study 后 / 永不>
```

---

## 9. 自检清单（每次声明任务完成前对照）

- [ ] 任务的全部 DoD 条款都有可验证证据？
- [ ] 关联的模块合同条款全部遵守？
- [ ] 代码行数在 §2 上限内？
- [ ] 没有悄悄修改 `vendor/`？
- [ ] 没有生成合同外的 artifact 文件？
- [ ] 没有向 `metadata.csv` 新增列？
- [ ] 没有在任务里顺便做了另一个任务的工作？
- [ ] 执行中冒出的扩展想法都已入 backlog，未写进代码？

---

## 10. 最高约束

> **本文件的每一条 DoD 都是硬约束。不允许"差不多算绿了"**。
> **任何"我觉得可以开工了"的直觉，都必须能翻译成"T? 的哪几条 DoD 已绿"；翻译不出来，就没到启动条件。**

---

## 11. 与其他文档的映射

| 问题 | 去哪儿看 |
|---|---|
| 项目长什么样？ | `te_analysis_top_level_design_v1.md` |
| 每个模块能/不能做什么？ | `te_analysis_module_contracts_v1.md` |
| 要做哪些离散任务？按什么顺序？ | 本文件 |
| vendor 的原生契约是什么？ | `references/vendor_contracts.md`（T0 产出） |

冲突时优先级：**架构 > 模块合同 > 任务分解**。任务分解调整不触发合同变更；合同变更必须反向推动架构审查。
