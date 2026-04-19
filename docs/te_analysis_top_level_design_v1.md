# te_analysis 顶层设计方案 v1

**生成日期**：2026-04-19
**设计者视角**：项目架构师 / CCDS 规范 / 最小封装优先
**核心原则**：不重复造轮子；原作者有什么就用什么；CCDS 是目录约束，不是实现约束
**适用范围**：推翻当前 upstream 过度工程，回到"封装而非重建"的初心

---

## 0. 一句话设计总纲

> **本项目是一个 CCDS 外壳**，负责把用户本地已下载的 FASTQ/metadata 喂给**原封不动的上游 snakescale 和下游 TE_model**，仅此而已。除目录规范和最小胶水脚本外，不做任何元数据治理、身份层、沙箱化、运行时镜像等工作。

---

## 1. 第一性原理：这个项目存在的最小理由

### 1.1 真实需求链条
1. 原作者的 `snakescale` + `TE_model` 已经是可跑的完整管线
2. 本地网络慢，不适合用 snakescale 内置下载模块
3. **需要的唯一本质能力**：用本地 FASTQ 替换 snakescale 的下载产物
4. **附加需求**：整个流程用 CCDS 布局包起来，保证可复现

### 1.2 推论
- 不需要重写 snakescale 的任何部分
- 不需要重写 TE_model 的任何部分
- 不需要自己做 metadata 治理（原作者已经定义好 `project.yaml`）
- 不需要自己做 QC 门禁（`classify_studies` 是原作者的选择，服从即可）
- **唯一需要自写的代码**：一层薄到不能再薄的"metadata → project.yaml + FASTQ 布局"转换

**置信度：高**。任何与上述推论冲突的工作都是 scope creep。

---

## 2. 目录结构（CCDS 合规，最小偏离）

```text
ccds-translation-efficiency/
├── README.md
├── LICENSE
├── Makefile                        # 顶层统一入口
├── environment.yml                 # conda 环境（主 Python 环境）
├── environment-r.yml               # R 环境（TE_model 专用，可选分离）
├── pyproject.toml                  # 项目包元数据
├── .gitignore
├── .gitmodules                     # 声明 vendor/ 下的 submodule
│
├── data/                           # CCDS 数据层（git-ignored，数据不入库）
│   ├── external/                   # 外部来源备份（只读）
│   ├── raw/                        # 用户本地下载的 FASTQ + metadata.csv
│   │   ├── metadata.csv            # 用户手工维护的 experiment-level 清单
│   │   └── fastq/                  # 本地 FASTQ 真实物理存储
│   ├── interim/                    # 上游中间产物
│   │   └── snakescale/<STUDY>/     # snakescale 原生输出（.ribo/all.ribo/logs）
│   └── processed/                  # 最终产物
│       └── te/<STUDY>/             # TE_model 输出（.rda/.csv）
│
├── references/                     # CCDS 参考层（静态参考资料）
│   ├── snakescale-docs/             # 原作者文档的本地快照（可选）
│   └── te_model-docs/
│
├── docs/                           # 项目文档
│   ├── architecture.md             # 本文档
│   ├── reproducibility.md          # 如何复现整个实验
│   └── metadata_schema.md          # metadata.csv 字段定义
│
├── notebooks/                      # 探索性分析（不进主流程）
│
├── src/
│   └── te_analysis/
│       ├── __init__.py
│       ├── stage_inputs.py         # 【核心】metadata.csv → project.yaml + 符号链接
│       ├── run_upstream.py         # 薄壳：调用 vendor/snakescale
│       ├── run_downstream.py       # 薄壳：调用 vendor/TE_model
│       └── config.py               # 路径常量与环境解析
│
├── vendor/                         # 原作者代码（git submodule，版本锁定）
│   ├── snakescale/                 # https://github.com/RiboBase/snakescale
│   └── TE_model/                   # https://github.com/CenikLab/TE_model
│
├── scripts/                        # 一次性运维脚本（可丢弃）
│   └── bootstrap.sh                # 首次克隆后的初始化脚本
│
└── tests/
    ├── test_stage_inputs.py        # stage_inputs 转换逻辑单测
    └── test_smoke_downstream.py    # 针对 verify_gse105082 的端到端冒烟
```

**关键特征**：
- `src/te_analysis/` 下**只有 4 个 .py 文件**，目标总行数 < 500 行
- `vendor/` 内代码**零修改**（如需修复 bug 走 fork + 锁 commit）
- `data/` 全部 git-ignore，仅 `metadata.csv` 例外

---

## 3. 依赖管理策略：Git Submodule

| 选项 | 优点 | 缺点 | 决策 |
|---|---|---|---|
| **Git submodule + 锁 commit** | 版本明确；可复现；上游更新可追踪；零维护负担 | 需 `git submodule update --init` | **采用** |
| Fork 到自己的组织 | 完全可控 | 维护负担；与上游分叉后难合并 | **拒绝**（除非原作者不再维护） |
| pip / conda 安装 | 干净 | 原作者未发布包 | **不适用** |
| copy-paste 代码 | 简单 | 失去可复现性与升级路径 | **拒绝** |

**具体实施**：
```bash
git submodule add https://github.com/RiboBase/snakescale     vendor/snakescale
git submodule add https://github.com/CenikLab/TE_model        vendor/TE_model
git submodule update --init --recursive
# 锁定到某个已验证的 commit：
cd vendor/snakescale && git checkout <KNOWN_GOOD_SHA> && cd -
cd vendor/TE_model   && git checkout <KNOWN_GOOD_SHA> && cd -
git add vendor/ && git commit -m "pin vendor commits"
```

**置信度：高**。这是科研可复现性领域的标准做法。

---

## 4. 数据流（最简形态）

```text
用户手工维护:
    data/raw/metadata.csv       (experiment-level, 一行一个 experiment)
    data/raw/fastq/*.fastq.gz   (本地已下载好的文件)
                │
                │  [ src/te_analysis/stage_inputs.py ]
                │  读 metadata.csv → 按 snakescale 规约产出：
                │    · project.yaml
                │    · 符号链接到 snakescale 期望的 staged 目录
                ▼
    data/interim/snakescale/<STUDY>/
        ├── project.yaml
        └── staged_fastq/ -> data/raw/fastq/*
                │
                │  [ src/te_analysis/run_upstream.py ]
                │  cd vendor/snakescale && snakemake/nextflow 运行
                │  参数: --config 指向上面 project.yaml
                ▼
    data/interim/snakescale/<STUDY>/
        ├── ribo/<exp>.ribo      (experiment-level)
        └── all.ribo
                │
                │  [ src/te_analysis/run_downstream.py ]
                │  Rscript vendor/TE_model/TE.R <输入目录>
                │  python  vendor/TE_model/transpose_TE.py ...
                ▼
    data/processed/te/<STUDY>/
        ├── TE_sample_level.rda
        ├── TE_cellline_all.csv
        └── TE_cellline_all_T.csv
```

**关键决策：所有中间/最终产物都严格落在 CCDS 约定的层级**（interim / processed），不再有 `data/upstream/pilot/...`、`snakescale_runtime/` 这类自造目录。

---

## 5. 唯一核心模块：`stage_inputs.py` 的契约

### 5.1 责任边界（只做这些）

| 做 | 不做 |
|---|---|
| 读 `metadata.csv` | 不做 SRA 检索/下载 |
| 生成 snakescale 原生 `project.yaml` | 不维护 `_manifest.tsv / _source_conflict.tsv / metadata_runs_unresolved.tsv` |
| 根据 metadata 把本地 FASTQ 符号链接到 snakescale 期望的路径 | 不反向校验原始 FASTQ 完整性（坏文件让 snakescale 自己报） |
| 基础 sanity：文件存在、命名规约符合 | 不做 pre-trimmed / adapter autodetect 预审计 |
| 返回非零退出码 + 清晰错误信息 | 不写复杂的"为什么这个 study 不适合"分析报告 |

**目标行数**：< 250 行，单文件。

### 5.2 输入数据结构：`metadata.csv` 的精简 schema

建议列（仅保留必要字段，其余靠 `project.yaml` 外挂）：

| 列名 | 类型 | 含义 | 必填 |
|---|---|---|---|
| `study` | str | GSE ID | ✓ |
| `experiment` | str | experiment-level 唯一 ID（对应 `.ribo` 文件名） | ✓ |
| `assay` | enum | `ribo` / `rna` | ✓ |
| `run` | str | SRR/run-level ID（多 run 时每行一个） | ✓ |
| `fastq_path` | str | 本地 FASTQ 相对 `data/raw/` 的路径 | ✓ |
| `organism` | str | 下划线二项式（如 `Homo_sapiens`） | ✓ |
| `pair_id` | str | Ribo/RNA 配对键（同 experiment 下 Ribo 和 RNA 共享 pair_id） | ✓ |

**注意**：如果原作者 snakescale 已有自己的 `project.yaml` 示例 schema，**以其为准**，这里的列只是翻译源。

**置信度：中**。`project.yaml` 真实字段需要读 `vendor/snakescale` 的 README 或 example 确认，不要凭空猜测。

### 5.3 CLI 契约

```bash
python -m te_analysis.stage_inputs \
    --metadata data/raw/metadata.csv \
    --study GSE119681 \
    --out    data/interim/snakescale/GSE119681
```

- 幂等：重复运行产出一致
- 显式 study 选择，**不要默认"选最字母靠前的 study"**
- 输出一个 `project.yaml` + 一个 `staged_fastq/` 目录

---

## 6. 上游/下游薄壳模块

### 6.1 `run_upstream.py`
```python
# 伪代码
def run_upstream(study_dir: Path) -> int:
    # study_dir = data/interim/snakescale/<STUDY>/
    cmd = [
        <snakemake 或 nextflow 入口>,
        "--configfile", study_dir / "project.yaml",
        "--directory",  VENDOR_SNAKESCALE,
        # ...其他原作者约定的参数
    ]
    return subprocess.run(cmd, check=False).returncode
```
- **不解析 snakescale 内部日志**
- **不在 Python 侧重试**
- 成功判据：退出码 0 + 目标 `.ribo` 文件存在

### 6.2 `run_downstream.py`
```python
def run_downstream(study_dir: Path, out_dir: Path) -> int:
    # 1. 调 TE.R
    subprocess.run(["Rscript", VENDOR_TE_MODEL / "TE.R", str(study_dir)], check=True)
    # 2. 调 transpose_TE.py
    subprocess.run(["python", VENDOR_TE_MODEL / "transpose_TE.py", "-o", str(study_dir)], check=True)
    # 3. 把产物 copy/move 到 out_dir (data/processed/te/<STUDY>/)
```
- 复用当前已验证过的 `verify_gse105082_hela_triplet_stage2` 合同
- 这一侧**无需大改**（报告 §4.1 已证明通路成立）

---

## 7. Makefile：统一入口

```makefile
STUDY ?= GSE119681

.PHONY: help env submodules stage upstream downstream all clean

help:
	@echo "make env          # 创建 conda 环境"
	@echo "make submodules   # 拉取 vendor/"
	@echo "make stage STUDY=<GSE>   # 准备 snakescale 输入"
	@echo "make upstream STUDY=<GSE>  # 跑 snakescale"
	@echo "make downstream STUDY=<GSE># 跑 TE_model"
	@echo "make all STUDY=<GSE>       # stage + upstream + downstream"

env:
	conda env create -f environment.yml

submodules:
	git submodule update --init --recursive

stage:
	python -m te_analysis.stage_inputs --metadata data/raw/metadata.csv \
		--study $(STUDY) --out data/interim/snakescale/$(STUDY)

upstream: stage
	python -m te_analysis.run_upstream --study-dir data/interim/snakescale/$(STUDY)

downstream: upstream
	python -m te_analysis.run_downstream \
		--study-dir data/interim/snakescale/$(STUDY) \
		--out-dir   data/processed/te/$(STUDY)

all: downstream

clean:
	rm -rf data/interim/snakescale/$(STUDY) data/processed/te/$(STUDY)
```

**优点**：新人 clone 下来，一条 `make all STUDY=GSE132441` 就能重跑。这就是 CCDS 想要的可复现性。

---

## 8. 可复现性策略（CCDS 核心价值所在）

| 维度 | 措施 | 置信度 |
|---|---|---|
| 代码版本 | git submodule 锁 commit SHA | 高 |
| 环境 | `environment.yml` 固定主要包版本（非精确 hash） | 高 |
| 数据契约 | `metadata.csv` + `data/raw/fastq/` 由用户保证；文档给出下载清单 | 中 |
| 参考基因组 | 由 `vendor/snakescale/scripts/references.yaml` 控制；本项目不复制 | 高 |
| 运行入口 | Makefile 单一入口，无隐藏选项 | 高 |
| 日志 | snakescale/nextflow 原生日志直接落在 `data/interim/...`，不转存 | 高 |

**禁止**的"伪复现"手段：
- 不把中间产物 commit 进 git
- 不写"我手动改过的脚本片段"注释
- 不在主分支存放实验性修改

---

## 9. 被显式砍掉的东西清单（重要）

以下当前存在或计划中的模块，**在本设计中明确不纳入**：

| 被砍对象 | 当前位置 | 砍掉理由 |
|---|---|---|
| `src/te_analysis/upstream/pilot_package.py` | 当前 repo | 与 snakescale 原生 `project.yaml` 功能重叠 |
| `scripts/build_upstream_pilot_package.py` | 当前 repo | 同上；默认选 alphabetically-first study 的行为本身就是反模式 |
| `data/raw/_manifest.tsv` | 当前 repo | snakescale 不需要 |
| `data/raw/_source_conflict.tsv` | 当前 repo | snakescale 不需要；双源冲突应由用户在 metadata.csv 里决策 |
| `data/raw/_ingest_report.md` | 当前 repo | 自造审计层 |
| `data/raw/metadata_runs.tsv` / `metadata_runs_unresolved.tsv` | 当前 repo | SRX↔SRR 展开应内联在 `metadata.csv` 里（每行 one run）|
| `snakescale_runtime/` 镜像结构 | 当前 repo | snakescale 本身就是运行时，不需要在外面再镜像一份 |
| classify_studies 审计 / proven-negative 证据体系 | 当前 repo | 原作者的 QC gate 就是权威；服从或剔除，不要外部审计 |

**预估删代码量：60-80%**（基于报告 §9.1 的模块清单）。

---

## 10. 多视角交叉验证

### 10.1 软件工程师视角
最小依赖图 + 最小状态空间。仅 4 个 Python 文件的主流程，故障面清晰。**批准**。

### 10.2 生信流水线工程师视角
关键风险是"snakescale 原生 `project.yaml` schema 我们是否完全掌握"。如果掌握不全，`stage_inputs.py` 产出会被 snakescale 拒绝。**需要在动工前读 `vendor/snakescale` 的 example 配置**。**有条件批准**。

### 10.3 科研项目管理视角
CCDS 合规 + Makefile 入口 + submodule 锁版本 = 论文发表时可以直接引用的可复现实验。符合"未来项目可复现"的初心。**批准**。

**三视角共识**：设计成立，但落地前需读原作者仓库的 example，确认 `project.yaml` schema。

---

## 11. 迁移路径：从当前状态到本设计

**尺度说明**：本节按任务依赖推进，不按时间推进。详细任务合同见 `te_analysis_sprint_plan_v1.md`。

### 11.1 任务里程碑（按 DoD 绿灯推进）

| 里程碑 | 判定条件 | 对应任务 |
|---|---|---|
| **M-Alpha** | vendor 合同全部提取完成 | T0 |
| **M-Bravo** | CCDS 骨架 + 路径常量 + metadata schema 就位 | T1 / T2 / T3 |
| **M-Charlie** | 三个薄壳（stage_inputs / run_upstream / run_downstream）全部到 DoD | T4 / T5 / T6 |
| **M-Delta** | 端到端通路在两个 positive baseline 上绿 | T7 / T8 / T9 |
| **M-Echo** | 旧模块全部 `git rm`，主路径仍绿 | T12 |
| **M-Final** | 文档齐、基线冻结、`v0.1-mvp` tag | T13 / T14 |

### 11.2 启动条件（不允许跳级）

- T0 / T1：无前置，立即可启动
- T2 / T3 / T6：T1 全绿后启动
- T4：T0 + T1 + T2 + T3 全绿后启动
- T5：T0 + T2 + T4 全绿后启动
- T7：T4 / T5 / T6 的 CLI 接口冻结后启动
- T8：T5 + T7 全绿 + GSE132441 本地 FASTQ 就位
- T9：T6 + T7 全绿 + GSE105082 `.ribo` 可访问
- T12：T8 AND T9 同时绿（不允许只一个绿就动手）
- T13 / T14：T12 全绿

### 11.3 并行性
- `{T0, T1}`：全并行
- `{T2, T3, T6}`：T1 绿后全并行
- `{T5, T6}`：各自前置满足后并行
- `{T8, T9}`：各自前置满足后并行
- `{T13, T14}`：T12 绿后并行

### 11.4 反模式
- **禁止**：T0 未完即凭猜测启动 T4 / T5
- **禁止**：T12 在 T8 / T9 未同时绿时启动
- **禁止**：以"差不多了"代替 DoD 绿灯

**置信度：中**。里程碑可达成，具体多少任务/多少次返工取决于 T0 能还原出多完整的 vendor 合同。

---

## 12. 风险与 Open Questions

### 12.1 主要风险

| 风险 | 概率 | 影响 | 对策 |
|---|---|---|---|
| snakescale 的 `project.yaml` schema 比想象中复杂 | 中 | 中 | 阶段 A 先读 example，不行就 fork snakescale 加注释 |
| 原作者 `TE.R` 的输入目录契约与现有 verify 路径不完全一致 | 低 | 中 | 已有 positive baseline，参照即可 |
| 某些 study 的 FASTQ 命名规约与 snakescale 期望冲突 | 中 | 低 | `stage_inputs.py` 的符号链接步骤就是做命名标准化 |
| pre-trimmed 类数据无法通过 `classify_studies` | 高 | 低 | 不追，直接从 `metadata.csv` 剔除；如必须收，fork snakescale 改 gate |
| 原作者仓库更新后 submodule 追不上 | 低 | 低 | 锁 commit；每季度评估一次是否 bump |

### 12.2 必须解答后再动工的问题

1. `vendor/snakescale/project.yaml.example` 或类似文件是否存在？字段列表是什么？
2. snakescale 入口到底是 `snakemake ...` 还是 `nextflow run ...`？参数形式？
3. `TE.R` 期望的输入目录里，`.ribo` 文件应该怎么命名、怎么组织？
4. CCDS 的 `data/interim/` 在多 study 情况下怎么组织最干净？（本设计提议 `data/interim/snakescale/<STUDY>/`）

**这些问题 1 小时内可以读原作者 README 解决，不要再靠推测往前走。**

---

## 13. 设计的自我审核

| 审核项 | 结果 |
|---|---|
| 是否偏离用户初心（"跑通原作者流程 + CCDS 可复现"）？ | 否，完全对齐 |
| 是否包含事实性错误？ | `project.yaml` schema 为推测，已在 §5.2 与 §12 标注需验证 |
| 逻辑链条是否闭环？ | 闭环：原始输入 → stage → upstream → downstream → 最终产物 |
| 是否"重复造轮子"？ | 已在 §9 明确砍掉所有与原作者功能重叠的自造模块 |
| 是否遵循 CCDS？ | 目录结构 §2 严格对齐 |

---

## 14. 最终交付承诺（如果采纳本设计）

- **代码规模**：自写 Python 代码 **< 500 行总**（不含 vendor/submodule/测试）
- **可复现性**：新人 clone + `make env && make submodules && make all STUDY=<GSE>` 即可复现
- **故障面**：只会在三处失败 —— 环境、`metadata.csv`、原作者管线本身
- **维护成本**：原作者管线的 bug 走上游 issue，不在本项目内部 patch

---

## 附录 A：与当前项目的 diff 摘要

| 区域 | 当前 | 本设计 | 动作 |
|---|---|---|---|
| snakescale 接缝 | 自造 pilot_package + runtime 镜像 | submodule + 原生 project.yaml | 删除自造层 |
| 元数据层 | manifest / conflict / unresolved 三件套 | 单一 metadata.csv | 合并归一 |
| 目录布局 | `data/upstream/pilot/...` 自造 | `data/interim/snakescale/<STUDY>/` CCDS 标准 | 迁移 |
| 调用入口 | 零散脚本 | Makefile 单入口 | 收口 |
| 下游 | 已通（verify_gse105082） | 保持 | 不动 |
| QC 审计 | 外部 classify_studies 审计 | 直接服从原作者 gate | 删除 |

## 附录 B：最大敬畏清单（不要再犯的错）

1. 不要再写"身份层"
2. 不要再做"双源 FASTQ 冲突解析"
3. 不要再生成任何以 `_` 开头的审计 TSV
4. 不要再做"pilot/runtime materialization"
5. 不要在本项目内改 vendor 代码（要改就 fork）
6. 不要试图让 snakescale 适配你 —— 让你适配它
