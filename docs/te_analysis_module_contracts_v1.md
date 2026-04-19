# te_analysis 模块职责合同（顶层设计的功能尺度补充）

**适用文档**：本文件是 `te_analysis_top_level_design_v1.md` 的**功能边界细则**
**尺度**：按模块/文件/目录，**不按时间**
**核心约束**：MVP 原则 —— 复用 > 封装 > 自写。任何"自写"都必须通过本文件的合同约束
**使用方式**：开工前把本文件打印贴在工位旁；写任何代码前先确认其不违反此合同；Codex 生成任何文件前先引用对应小节

---

## 0. 三条不可协商的全局约束

### GC-1：代码所有权比例（Code Ownership Ratio）
| 类别 | 来源 | 规模目标 |
|---|---|---|
| vendor 代码（snakescale + TE_model） | git submodule | **100% 复用，0 修改** |
| 本项目自写 Python | `src/te_analysis/` | **≤ 500 行总** |
| 本项目自写 shell/make | `Makefile` + `scripts/` | **≤ 100 行总** |
| 本项目自写测试 | `tests/` | **≤ 300 行总** |
| 自写总上限 | 全部合计 | **≤ 900 行** |

**违反处置**：任一类超限 20% 触发停工审查，确认是否在造轮子。

### GC-2：功能来源优先级（Feature Source Priority）
需要某个功能时的决策树（**必须自上而下穷尽**）：

1. vendor 里已有 → 直接调用
2. vendor 里没有但属于其职责范围 → 提上游 issue，本项目等
3. vendor 里没有且不属于其职责范围，但 Python 标准库能做 → 用标准库，≤ 20 行
4. 标准库做不到但有成熟 PyPI 包 → 加进 `environment.yml`，薄封装
5. 以上都不适用 → **默认放弃该功能**，写进 `docs/backlog.md`

**违反处置**：跳过任一层级直接自写，PR 不允许合并。

### GC-3：单一事实源（Single Source of Truth）
| 事实域 | 唯一源 | 禁止事项 |
|---|---|---|
| snakescale 合同 | `vendor/snakescale` 的 README/example | 禁止在本项目内重新定义 `project.yaml` schema |
| TE_model 合同 | `vendor/TE_model` 的 README/源码 | 禁止在本项目内重写 `TE.R` 逻辑 |
| 实验清单 | `data/raw/metadata.csv` | 禁止出现第二个"样本登记表" |
| 路径常量 | `src/te_analysis/config.py` | 禁止在其他模块硬编码路径 |
| 版本锁定 | `.gitmodules` + submodule commit SHA | 禁止 `environment.yml` 内再写 vendor 版本 |

---

## 1. 模块全景总表

| # | 模块 | 类型 | 所有权 | 行数上限 | 关键词 |
|---|---|---|---|---|---|
| M1 | `src/te_analysis/stage_inputs.py` | 自写 Python | 本项目 | **250** | metadata → project.yaml + symlinks |
| M2 | `src/te_analysis/run_upstream.py` | 自写 Python | 本项目 | **80** | 薄壳调 snakescale |
| M3 | `src/te_analysis/run_downstream.py` | 自写 Python | 本项目 | **80** | 薄壳调 TE_model |
| M4 | `src/te_analysis/config.py` | 自写 Python | 本项目 | **60** | 路径/环境常量 |
| M5 | `Makefile` | 自写 shell | 本项目 | **80** | 统一入口 |
| M6 | `environment.yml` / `environment-r.yml` | 配置 | 本项目 | **60** | 依赖声明 |
| M7 | `data/raw/metadata.csv` | 手工数据 | 用户维护 | N/A | 实验清单 |
| M8 | `vendor/snakescale/` | git submodule | 原作者 | **0 自写** | 上游执行核 |
| M9 | `vendor/TE_model/` | git submodule | 原作者 | **0 自写** | 下游执行核 |
| M10 | `tests/test_stage_inputs.py` | 自写 Python | 本项目 | **150** | 单测 |
| M11 | `tests/test_smoke_downstream.py` | 自写 Python | 本项目 | **100** | 端到端冒烟 |
| M12 | `docs/` | 文档 | 本项目 | N/A | 仅 4 篇 |
| M13 | `references/vendor_contracts.md` | 文档 | 本项目 | N/A | vendor 合同速查 |
| M14 | `data/` 目录布局 | 约定 | N/A | N/A | CCDS 对齐 |

**所有"自写"模块合计 ≤ 900 行**（呼应 GC-1）。

---

## 2. M1 — `stage_inputs.py`（全项目唯一需要认真写代码的模块）

### 2.1 唯一职责
将 `data/raw/metadata.csv` 转换为 snakescale 原生可吃的目录结构：**一个 `project.yaml` + 一组符号链接化的 FASTQ**。

### 2.2 必须做（MUST）
- M1.MUST.1：解析 CLI 参数 `--metadata`、`--study`、`--out`，三个全部必填
- M1.MUST.2：按 `--study` 过滤 `metadata.csv`，拿到该 study 的所有行
- M1.MUST.3：按 `references/vendor_contracts.md` 中记录的 schema 构造 `project.yaml` 字典
- M1.MUST.4：把 `project.yaml` 写到 `<out>/project.yaml`
- M1.MUST.5：为每条 run 在 `<out>/staged_fastq/` 下创建符号链接，命名严格遵守 snakescale 规约
- M1.MUST.6：任何异常立即 `raise`，退出码非零
- M1.MUST.7：幂等 —— 同输入重复运行，产出 byte-identical

### 2.3 禁止做（MUST NOT）
- M1.MUSTNOT.1：**禁止**下载任何文件（不联网）
- M1.MUSTNOT.2：**禁止**做 FASTQ 完整性校验（gzip/md5/行数）—— 坏文件让 snakescale 自己报
- M1.MUSTNOT.3：**禁止**做 adapter 预检测、pre-trimmed 预判
- M1.MUSTNOT.4：**禁止**生成任何 `_manifest.tsv / _conflict.tsv / _ingest_report.md / unresolved.tsv`
- M1.MUSTNOT.5：**禁止**做 SRX↔SRR 自动展开 —— 用户应在 `metadata.csv` 里一行一 run 写好
- M1.MUSTNOT.6：**禁止**自己"猜"`project.yaml` 字段 —— schema 不清的字段直接报错退出
- M1.MUSTNOT.7：**禁止**写"兼容多个 metadata 格式"的 fallback —— 只认一种 schema
- M1.MUSTNOT.8：**禁止**做 fallback、retry、"智能恢复"

### 2.4 接口契约

```text
CLI:
    python -m te_analysis.stage_inputs \
        --metadata PATH \
        --study    STR \
        --out      PATH

输入:
    PATH --metadata: 指向 data/raw/metadata.csv
    STR  --study:    必须与 metadata.csv 中某个 study 值完全一致
    PATH --out:      目标目录；不存在会创建；存在会清空重建

输出:
    <out>/project.yaml           合法 snakescale 配置
    <out>/staged_fastq/<run>.fastq.gz -> <绝对路径>  符号链接

退出码:
    0   成功
    非0 失败（stderr 给出清晰原因）

副作用:
    仅 <out>/ 目录；不动 data/raw/；不写 log 文件
```

### 2.5 失败模式（全部必须 raise，不做 fallback）
| 情形 | 期望行为 |
|---|---|
| `metadata.csv` 不存在 | `FileNotFoundError` |
| `--study` 在 metadata 中找不到 | `ValueError` + 列出可用 study |
| 某条 run 的 `fastq_path` 指向不存在的文件 | `FileNotFoundError` |
| `project.yaml` 某个必填字段无法从 metadata 填出 | `KeyError` + 指出缺失字段 |
| `<out>` 无写权限 | `PermissionError`（让 OS 抛） |

### 2.6 Definition of Done（DoD）
- [ ] 行数 ≤ 250
- [ ] 单文件，无子模块
- [ ] 所有 `MUST` 项覆盖
- [ ] 所有 `MUST NOT` 项经过代码审查确认
- [ ] `tests/test_stage_inputs.py` 全绿
- [ ] 用 GSE132441 跑出的 `project.yaml` 能被 snakescale dry-run 识别

---

## 3. M2 — `run_upstream.py`（薄壳）

### 3.1 唯一职责
调用 `vendor/snakescale` 的原生入口命令，把 stage_inputs 产物喂进去，等退出码。

### 3.2 必须做
- M2.MUST.1：解析 CLI `--study-dir`
- M2.MUST.2：按 `references/vendor_contracts.md` 拼出 snakescale 启动命令
- M2.MUST.3：`subprocess.run(..., check=False)`
- M2.MUST.4：透传退出码到 shell

### 3.3 禁止做
- M2.MUSTNOT.1：**禁止**解析 snakescale 的日志做决策
- M2.MUSTNOT.2：**禁止**做重试、断点续跑、部分重跑
- M2.MUSTNOT.3：**禁止**在 Python 侧做并发/多 study 调度 —— 一次只跑一个 study
- M2.MUSTNOT.4：**禁止**在此文件里做 `project.yaml` 的二次校验（那是 M1 或 snakescale 自己的事）
- M2.MUSTNOT.5：**禁止**用 Python 修改 snakescale 的任何配置

### 3.4 接口契约
```text
CLI:
    python -m te_analysis.run_upstream --study-dir PATH

输入:
    PATH --study-dir: 期待 <path>/project.yaml 与 <path>/staged_fastq/ 存在

输出:
    snakescale 原生输出（默认落在 snakescale 自己决定的位置，
    由 M1 生成的 project.yaml 控制去向）

退出码:
    透传 snakescale 的退出码
```

### 3.5 DoD
- [ ] 行数 ≤ 80
- [ ] 无状态（不维护自己的 cache / db / log）
- [ ] 完整命令能在文件头注释里一行写出

---

## 4. M3 — `run_downstream.py`（薄壳）

### 4.1 唯一职责
调用 `vendor/TE_model/TE.R` 和 `vendor/TE_model/transpose_TE.py`，把 `.ribo` 转成最终 TE CSV。

### 4.2 必须做
- M3.MUST.1：解析 CLI `--study-dir`、`--out-dir`
- M3.MUST.2：按 `references/vendor_contracts.md` 拼 `Rscript TE.R ...` 命令
- M3.MUST.3：按 `references/vendor_contracts.md` 拼 `python transpose_TE.py ...` 命令
- M3.MUST.4：将 TE_model 产物复制或移动到 `--out-dir`
- M3.MUST.5：任一子进程失败立即退出

### 4.3 禁止做
- M3.MUSTNOT.1：**禁止**重实现 `TE.R` 的任何数学
- M3.MUSTNOT.2：**禁止**在 Python 侧做 TE 后处理（归一化、CLR、winsorization 等）
- M3.MUSTNOT.3：**禁止**修改 `transpose_TE.py` 的输入格式
- M3.MUSTNOT.4：**禁止**做下游图表生成（那是 notebook 的事）

### 4.4 DoD
- [ ] 行数 ≤ 80
- [ ] 与 `verify_gse105082_hela_triplet_stage2` 的旧产出数值一致（浮点精度内）

---

## 5. M4 — `config.py`（路径常量）

### 5.1 唯一职责
把项目内所有路径、环境变量、vendor 相对位置**写成常量**，供 M1/M2/M3 引用。

### 5.2 必须做
- M4.MUST.1：定义 `PROJECT_ROOT` = 本文件父目录逐级上溯到 git 根
- M4.MUST.2：定义 `DATA_RAW`、`DATA_INTERIM`、`DATA_PROCESSED` 三个路径常量
- M4.MUST.3：定义 `VENDOR_SNAKESCALE`、`VENDOR_TE_MODEL` 两个路径常量
- M4.MUST.4：可通过环境变量覆盖（`TE_ANALYSIS_ROOT` 等），便于测试

### 5.3 禁止做
- M4.MUSTNOT.1：**禁止**包含业务逻辑（解析 metadata、调 snakescale 等）
- M4.MUSTNOT.2：**禁止**定义 class —— 用模块级 `Path` 常量即可
- M4.MUSTNOT.3：**禁止**在此文件做 I/O（不读 yaml、不写 log）

### 5.4 DoD
- [ ] 行数 ≤ 60
- [ ] 其他模块的路径硬编码全部替换为 `from .config import ...`

---

## 6. M5 — `Makefile`（统一入口）

### 6.1 唯一职责
把分散的命令凝聚成**不超过 7 个 target**，让新人 `make help` 就能开动。

### 6.2 必须提供的 target
| target | 行为 |
|---|---|
| `help` | 打印其他 target 的一行说明 |
| `env` | `conda env create -f environment.yml` |
| `submodules` | `git submodule update --init --recursive` |
| `stage` | 调 M1，参数 `STUDY=<GSE>` |
| `upstream` | 依赖 `stage`，调 M2 |
| `downstream` | 依赖 `upstream`，调 M3 |
| `all` | 等价 `downstream` |

可选：`clean`（删 `data/interim/<STUDY>/` 和 `data/processed/te/<STUDY>/`）

### 6.3 禁止做
- M5.MUSTNOT.1：**禁止**添加 `dashboard`、`report`、`all-studies`、`parallel` 等 target
- M5.MUSTNOT.2：**禁止**在 Makefile 里写复杂 shell 逻辑（超过 3 行就该进 Python）
- M5.MUSTNOT.3：**禁止**用 Makefile 做配置拼接（配置住在 `metadata.csv`）

### 6.4 DoD
- [ ] 行数 ≤ 80
- [ ] `make help` 输出 ≤ 10 行
- [ ] 一个新 clone 的人走完 `make env && make submodules && make all STUDY=<known-good>` 能看到 TE CSV

---

## 7. M6 — `environment.yml`（依赖声明）

### 7.1 唯一职责
声明本项目自写代码所需的 Python + R 依赖。**vendor 的依赖由 vendor 自己管**。

### 7.2 必须包含
- Python 3.11+
- pandas（读 metadata.csv）
- PyYAML（写 project.yaml）
- snakemake 或 nextflow（按 vendor_contracts.md 结论二选一）
- R base + TE_model 的 DESCRIPTION 列出的包

### 7.3 禁止包含
- M6.MUSTNOT.1：**禁止**包含 vendor 仓库里已声明的重复依赖
- M6.MUSTNOT.2：**禁止**包含"将来可能用到"的包（Jupyter 额外 kernel、可视化库等）
- M6.MUSTNOT.3：**禁止**在 `pip` 段里 pin 自己的 git 仓库

### 7.4 DoD
- [ ] 行数 ≤ 60（含注释）
- [ ] 在干净 VM 上 `conda env create` 能成功
- [ ] 所有包都有明确 major 版本（`pandas>=2.0`，不需要精确 hash）

---

## 8. M7 — `data/raw/metadata.csv`（用户数据，项目最关键的静态约定）

### 8.1 唯一职责
把"本项目处理哪些实验、每个实验对应哪些本地 FASTQ"这一事实**记录为一张表**。用户手工维护。

### 8.2 Schema（MVP 最小字段）

| 列 | 类型 | 必填 | 含义 | 例子 |
|---|---|---|---|---|
| `study` | str | ✓ | GSE ID | `GSE132441` |
| `experiment` | str | ✓ | experiment 级唯一 ID | `GSM3861100` |
| `assay` | enum | ✓ | `ribo` 或 `rna` | `ribo` |
| `run` | str | ✓ | SRR 级 ID，多 run 一行一个 | `SRR9215960` |
| `fastq_path` | str | ✓ | 相对 `data/raw/` 的 FASTQ 路径 | `fastq/SRR9215960.fastq.gz` |
| `organism` | str | ✓ | 下划线二项式 | `Arabidopsis_thaliana` |
| `pair_id` | str | ✓ | Ribo/RNA 配对键；同一 experiment 下 Ribo 和 RNA 共享 | `GSE132441_pair01` |

### 8.3 强约束
- M7.C.1：一行 = 一个 run
- M7.C.2：Ribo 和对应 RNA 必须共享 `pair_id`
- M7.C.3：`fastq_path` 必须是本地已存在的文件，**不接受 URL**
- M7.C.4：若同一 experiment 有多个技术重复 run，用多行表达，所有行 `experiment` 值相同

### 8.4 禁止扩展
- M7.MUSTNOT.1：**禁止**加"质量分"、"是否 pre-trimmed"、"adapter 序列"等衍生列 —— 这些由 snakescale 决定
- M7.MUSTNOT.2：**禁止**用 JSON / SQLite / Excel 替代 CSV —— git diff 友好性优先
- M7.MUSTNOT.3：**禁止**把 metadata 拆成多个文件（`experiments.csv` + `runs.csv` 等）—— 一张表，扁平

### 8.5 Schema 文档
所有字段定义必须同步到 `docs/metadata_schema.md`，该文档是唯一权威。

---

## 9. M8 / M9 — vendor 子模块（snakescale + TE_model）

### 9.1 所有权声明
- **代码所有者**：原作者（RiboBase / CenikLab）
- **本项目的责任**：只锁版本、只调用、不修改

### 9.2 必须做
- M8/9.MUST.1：用 `git submodule` 引入，锁定到某个**已在 GSE132441 / GSE105082 上验证过的** commit SHA
- M8/9.MUST.2：`.gitmodules` 记录上游 URL
- M8/9.MUST.3：任何 vendor bug 优先走上游 issue；等不起就 fork，在 fork 里修，submodule 指向 fork

### 9.3 禁止做
- M8/9.MUSTNOT.1：**禁止**在 `vendor/*` 下直接 edit 文件
- M8/9.MUSTNOT.2：**禁止**把 vendor 代码 copy 到 `src/` 下
- M8/9.MUSTNOT.3：**禁止**把 vendor 作为 "例子" 抄进文档 —— 文档应引用行号

### 9.4 Fork 触发条件
仅在以下**全部**满足时允许 fork：
1. 某 bug 阻塞冲刺主路径
2. 上游 issue 提交超过 7 天无响应
3. 修复涉及 ≤ 20 行代码
否则走 "绕开 / 换 study / 放入 backlog" 路线。

---

## 10. M10 — `tests/test_stage_inputs.py`（M1 的单测）

### 10.1 覆盖范围
| 场景 | 期望 |
|---|---|
| 正常：metadata + 完整 FASTQ | 退出 0，产物完备 |
| metadata 不存在 | `FileNotFoundError` |
| study 不在 metadata 中 | `ValueError` |
| FASTQ 缺失 | `FileNotFoundError` |
| 多 run 的 experiment | 每个 run 对应一条 symlink |
| Ribo/RNA 配对完整性 | pair_id 一一对应 |
| 幂等性 | 连续两次运行产物 byte-identical |

### 10.2 禁止做
- M10.MUSTNOT.1：**禁止**真调 snakescale（那是 M11 的职责）
- M10.MUSTNOT.2：**禁止**依赖真实 FASTQ 数据 —— 用 `tmp_path` + 空 `.fastq.gz` stub

### 10.3 DoD
- 行数 ≤ 150
- 用 `pytest` + `pytest-mock` 即可运行
- CI 里 <10 秒跑完

---

## 11. M11 — `tests/test_smoke_downstream.py`（端到端冒烟）

### 11.1 唯一职责
用已知 positive baseline（`verify_gse105082_hela_triplet_stage2`）验证 `make downstream` 产出与旧值一致。

### 11.2 必须做
- M11.MUST.1：冻结旧 baseline 为 fixture（固定 md5 或固定数值）
- M11.MUST.2：在新骨架上跑 `make downstream STUDY=GSE105082`
- M11.MUST.3：比较产物 CSV 与 baseline

### 11.3 禁止做
- M11.MUSTNOT.1：**禁止**在此测试里跑 snakescale（太慢；snakescale 的冒烟另立）
- M11.MUSTNOT.2：**禁止**用随机数据

### 11.4 DoD
- 行数 ≤ 100
- 在开发机跑 ≤ 5 分钟

---

## 12. M12 — `docs/` 目录

### 12.1 仅允许以下 4 篇文档

| 文件 | 内容 | 规模 |
|---|---|---|
| `docs/architecture.md` | 链接到 `te_analysis_top_level_design_v1.md` | <20 行 |
| `docs/metadata_schema.md` | M7 的 schema 权威定义 | ~100 行 |
| `docs/reproducibility.md` | 新人从零复现的步骤（5 条 make 命令） | ~50 行 |
| `docs/backlog.md` | 所有被拒绝的功能请求 + 拒绝理由 | 持续累积 |

### 12.2 禁止
- M12.MUSTNOT.1：**禁止**新增 ADR、RFC、设计讨论等文档 —— 讨论走 PR
- M12.MUSTNOT.2：**禁止**在 docs 下放实验日记
- M12.MUSTNOT.3：**禁止**重复 vendor 的 README

---

## 13. M13 — `references/vendor_contracts.md`（vendor 合同速查）

### 13.1 地位
**本项目内所有自写代码访问 vendor 功能时的唯一权威摘要。** 任何代码用到 snakescale 或 TE_model 的某条合同，都必须在此文档有对应条目，并带 `vendor/<repo>/<file>:<lineno>` 引用。

### 13.2 必须包含
- snakescale 启动命令（完整）
- snakescale `project.yaml` 字段表
- snakescale FASTQ 目录/命名规约
- TE_model `TE.R` 输入目录结构
- TE_model `transpose_TE.py` 调用方式

### 13.3 禁止
- M13.MUSTNOT.1：**禁止**在此文档做"推测"或"估计" —— 查不到就写 `UNKNOWN — 需要人工确认`
- M13.MUSTNOT.2：**禁止**抄整段 vendor 源码 —— 用行号引用代替

---

## 14. M14 — `data/` 目录布局（CCDS 对齐）

| 路径 | 用途 | git | 写入者 |
|---|---|---|---|
| `data/raw/metadata.csv` | 用户维护的实验清单 | ✓ 纳管 | 用户 |
| `data/raw/fastq/` | 本地 FASTQ 物理文件 | ✗ ignore | 用户 |
| `data/external/` | 外部只读备份（镜像等） | ✗ ignore | 用户 |
| `data/interim/snakescale/<STUDY>/` | snakescale 中间产物 | ✗ ignore | M2 |
| `data/processed/te/<STUDY>/` | 最终 TE 输出 | ✗ ignore | M3 |

### 14.1 禁止
- M14.MUSTNOT.1：**禁止**创建 `data/upstream/`、`data/pilot/`、`data/staging/` 等自造层级
- M14.MUSTNOT.2：**禁止**在 `data/raw/` 下生成任何带下划线前缀的审计文件
- M14.MUSTNOT.3：**禁止**把 `snakescale_runtime/` 镜像到 `data/` 下

---

## 15. MVP 功能矩阵（有 / 无 / 延迟）

| 功能域 | MVP 状态 | 理由 |
|---|---|---|
| 单 study 端到端执行 | **有** | 项目存在理由 |
| 多 study 指定执行 | **有**（手动循环） | `make all STUDY=A && make all STUDY=B` 已够 |
| `metadata.csv` 手工维护 | **有** | 用户负责 |
| Ribo/RNA 1:1 配对 | **有**（通过 `pair_id`） | snakescale 的最小契约 |
| pre-trimmed 数据处理 | **无** | 原作者拒绝的场景，我们也拒绝 |
| adapter 自动检测 | **无（由 snakescale 做）** | 我们不碰 |
| FASTQ 完整性校验 | **无** | 坏文件让 snakescale 报 |
| SRX → SRR 自动展开 | **无** | 用户自行在 metadata 写 |
| 双源 FASTQ 冲突解析 | **无** | 用户一开始就只放一份 |
| 断点续跑 | **无**（依赖 snakemake/nextflow 自带） | 不自实现 |
| 多 study 并行 | **延迟**（backlog） | 先做对，再做快 |
| 下游可视化 | **延迟** | notebook 里做，不入主流程 |
| CLI 美化（rich/click） | **无** | argparse 够用 |
| 日志聚合仪表盘 | **无** | vendor 日志足矣 |
| Docker 化 | **延迟** | conda 先行 |
| CI/CD | **延迟** | 本地 pytest 先行 |
| 检查点/缓存管理 | **无**（交给 snakemake） | 不重复造轮子 |
| 远程 FASTQ 支持 | **无** | 项目初心是本地 FASTQ |
| 下载模块 | **无** | 项目存在的理由就是绕开它 |

---

## 16. 禁止实现功能清单（反向清单，贴墙上）

以下所有功能，**在 MVP 阶段明确禁止实现**。如果 Codex 或任何 agent 建议实现它们，拒绝。

| # | 禁止功能 | 潜在诱惑场景 | 正确应对 |
|---|---|---|---|
| F1 | 自动从 SRA 下载 FASTQ | "用户不想手动下载" | 指向 sra-toolkit 官方文档 |
| F2 | FASTQ gzip/md5 校验 | "怕坏文件" | 让 snakescale 自己报 |
| F3 | adapter 猜测器 | "CenikLab 有这个" | snakescale 内置，不碰 |
| F4 | pre-trimmed 数据支持 | "某 study 很想用" | 从 metadata 剔除该 study |
| F5 | SRX → SRR 展开工具 | "metadata.csv 写起来累" | 用户用 Excel 展开 |
| F6 | 双源 FASTQ 去重 | "Box 和 SRA 都有一份" | 用户只在 metadata 放一个 |
| F7 | 元数据 audit report | "想知道整体健康度" | 写 notebook，不入主代码 |
| F8 | 进度条 / rich TUI | "美观" | 终端原生输出 |
| F9 | 多 study 并行调度 | "服务器有 208 核" | 写 shell 循环 |
| F10 | 下游图表自动生成 | "提升用户体验" | notebook 做 |
| F11 | REST API / 服务化 | "团队协作" | 不是本项目范围 |
| F12 | `metadata.csv` validator CLI | "提前发现错误" | 让 M1 报错就够了 |
| F13 | 自定义 snakescale 规则 | "改几个规则就通了" | 走 fork，不在外壳做 |
| F14 | 断点续跑/部分重跑 | "失败后重试快" | snakemake 自带 |
| F15 | 测试数据自动生成器 | "单测方便" | 手工准备小 fixture |

每次 Codex 建议以上任一功能，回答固定模板：

> "该功能违反 `te_analysis_module_contracts_v1.md` §16 F?。改写到 `docs/backlog.md` 并继续原任务。"

---

## 17. 决策日志（可追溯的架构选择）

### D-01 为什么用 submodule 而不是 fork？
- 选项：submodule / fork / pip / copy-paste
- 决定：submodule
- 理由：版本锁定 + 可追上游 + 零维护负担
- 撤销条件：上游超过 6 个月不维护

### D-02 为什么 `metadata.csv` 不是 SQLite？
- 决定：CSV
- 理由：git diff 友好；不需要 ORM；列数 ≤ 10
- 撤销条件：行数 > 10000 且需要复杂 join 查询

### D-03 为什么 `run_upstream.py` 不解析 snakescale 日志？
- 决定：只看退出码
- 理由：日志解析 = 紧耦合；vendor 日志格式可能变
- 撤销条件：退出码不足以判断成功（极少见）

### D-04 为什么不自写 FASTQ 校验？
- 决定：完全不校验
- 理由：snakescale 内部会校验；双校验 = 双维护
- 撤销条件：snakescale 被证明跳过某类坏文件

### D-05 为什么禁止多 study 并行？
- 决定：MVP 禁止
- 理由：snakemake 已有调度；双重并行 = 死锁风险
- 撤销条件：单 study 稳定后 benchmarks 表明需要

### D-06 为什么禁止下游可视化入主流程？
- 决定：可视化只在 notebook
- 理由：可视化需求高频变化；入主流程等于频繁改 `run_downstream.py`
- 撤销条件：发表论文时某张图被冻结为标准输出

### D-07 为什么禁止 Docker 化入 MVP？
- 决定：conda 先行
- 理由：vendor 本身依赖复杂；Docker image 可能被上游变更拖累
- 撤销条件：上游提供官方 Docker image

### D-08 为什么 `stage_inputs.py` 不做 `project.yaml` 字段兜底？
- 决定：schema 不清即报错
- 理由：兜底 = 掩盖上游合同误读
- 撤销条件：无（永久有效）

---

## 18. Backlog 管理（扩展延迟槽）

### 18.1 触发场景
任何时候冒出"不如加个 X 功能"的念头，按以下流程：

1. **停手**，不写代码
2. 打开 `docs/backlog.md`
3. 追加条目，格式：
   ```markdown
   ## <YYYY-MM-DD> <功能名>
   - 场景：<什么情况下想加>
   - 影响面：<涉及哪些模块>
   - 禁止依据：<本合同 §哪一条>
   - 回顾时机：<冲刺结束 / 第 N 个 study 后 / 永不>
   ```
4. 回到原任务

### 18.2 回顾机制
冲刺结束后，逐条评估 backlog 是否晋升为正式 issue。**默认选择是"继续留在 backlog"**。

---

## 19. 合同违反示例（反面教材）

### 反面 1：在 `stage_inputs.py` 里加 FASTQ 校验
```python
# ❌ 违反 M1.MUSTNOT.2
def validate_fastq(path):
    with gzip.open(path) as f:
        f.read(1024)  # 检测 gzip 完整性
```
**为什么错**：把 snakescale 的职责搬到外壳层，一旦 snakescale 内部校验升级，这里就成了冗余或冲突源。

### 反面 2：Makefile 里加 all-studies target
```makefile
# ❌ 违反 M5.MUSTNOT.1
all-studies:
    for s in $$(cut -f1 -d, data/raw/metadata.csv | tail -n +2 | sort -u); do \
        $(MAKE) all STUDY=$$s || true; \
    done
```
**为什么错**：这是 F9（多 study 并行调度）的变体；一旦加了，下一步必然是"失败重试"、"跳过已完成"、"日志汇总"，滑坡开始。

### 反面 3：在 `run_upstream.py` 解析日志
```python
# ❌ 违反 M2.MUSTNOT.1
if "classify_studies discard" in log_text:
    raise RuntimeError("Study rejected by gate")
```
**为什么错**：把 snakescale 的内部消息作为契约使用。vendor 下次改字符串就崩。退出码才是合同。

### 反面 4：`metadata.csv` 加衍生列
```csv
# ❌ 违反 M7.MUSTNOT.1
study,experiment,assay,run,fastq_path,organism,pair_id,quality_score,is_pretrimmed
```
**为什么错**：`quality_score` 是谁算的？什么时候更新？一旦有这列，下一步就是写"质量评分工具"，又开始造轮子。

### 反面 5：`src/te_analysis/upstream/pilot_package.py` 保留
```text
# ❌ 违反本合同根本原则
src/te_analysis/
├── stage_inputs.py
├── run_upstream.py
├── run_downstream.py
└── upstream/           # ← 旧包袱
    └── pilot_package.py
```
**为什么错**：保留"以防万一"的旧模块 = 心理上允许自己回头用它 = 下次偷懒就复用 = 设计重置。

---

## 20. 合同自检清单（每次 PR 前对照）

- [ ] 自写 Python 总行数 ≤ 500？
- [ ] `vendor/` 下是否有任何文件 edit？（必须零）
- [ ] 是否新增 `docs/` 文档超过 4 篇？（不允许）
- [ ] 是否新增 Makefile target 超过 7 个？（不允许）
- [ ] `metadata.csv` 是否新增列？（触发设计讨论）
- [ ] 是否引入 §16 禁止清单中的功能？（必须拒绝）
- [ ] 新增代码是否都能追溯到本合同某条 MUST？（不能追溯 = 不该存在）
- [ ] 是否有"以防万一"的 fallback / try-except 吞异常？（禁止）

---

## 21. 合同终局判断

本合同的最终目的不是"写多漂亮的代码"，而是保证一件事：

> **本项目自身永远是一张皮，原作者的 snakescale 和 TE_model 永远是肉。皮不长过肉，项目就不会失败。**

判定项目是否偏离的**单一可验证指标**：

```text
total_lines(src/ + Makefile + scripts/ + tests/) 
    / total_lines(vendor/**)
    < 0.05
```

**即：自写代码必须 < vendor 代码量的 5%**。

高于这个比例，说明开始在外壳里重建 vendor 功能，应立即审查。

置信度：**高**。这是 MVP 成败的单点指标。

---

## 结束语

此合同与 `te_analysis_top_level_design_v1.md`（架构）、`te_analysis_sprint_plan_v1.md`（时间）组成三角：

- **架构**回答"项目长什么样"
- **时间**回答"按什么节奏做"
- **合同**（本文件）回答"每部分能/不能做什么"

冲刺中如果三者发生冲突，**合同优先于时间，架构优先于合同**。架构不变，合同是对架构的细化，时间是对合同的排程。

**写代码前先问**：本模块想做的事，在合同里能找到哪条 MUST 背书？找不到 —— 不做。
