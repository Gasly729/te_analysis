# Vendor SHA Lock Recommendation

## 0. 溯源

Recon 时间：T0 (Commit F4)；当前 vendor submodule HEAD 由 Commit C (`63dd49b`) 拉取自 upstream default branch。

## 1. 推荐 pin SHA

| Submodule | 当前 (unlocked HEAD) | 推荐 pin | 理由 |
|---|---|---|---|
| `vendor/snakescale` | `b918e75f877262dca96665d18c3b472675f30a6d` | **`b918e75` — keep current** | 契约逆向分析基于此 SHA；`Snakefile`, `schemas/config.schema.yaml`, `project.yaml`, `scripts/generate_yaml.py` 的所有行号引用均绑定于此 SHA；upstream 无明确 release tag（`git -C vendor/snakescale tag -l` 空），无其他稳定锚点 |
| `vendor/TE_model` | `0b42e3f756e20b9954548b65ff8a64ae063d9a89` | **`0b42e3f` — keep current** | 同上：`pipeline.bash:1-44`、`src/TE.R:1-69`、`src/transpose_TE.py:1-13`、`src/ribobase_counts_processing.py:1-137` 均绑定于此 SHA；upstream 无 release tag |

## 2. 落锁动作（SHA lock 专有 commit — 不在 F4 范围）

SHA 锁定是 sprint_plan 中**独立 commit**（推荐命名 `vendor: lock submodule SHAs per T0 vendor_contracts`），执行步骤：

```text
cd vendor/snakescale && git checkout b918e75 && cd ../..
cd vendor/TE_model  && git checkout 0b42e3f && cd ../..
git add vendor/snakescale vendor/TE_model
git commit -m "vendor: lock snakescale @ b918e75, TE_model @ 0b42e3f per T0 recon"
```

当前 F4 **不执行**此动作（prompt §5 已排除 "SHA 锁定"）。

## 3. 升级风险（对我方 stage_inputs.py 的潜在影响）

### 3.1 snakescale 升级敏感面

| 作者路径 | 我方 stage_inputs 依赖 | 升级影响 |
|---|---|---|
| `project.yaml` 模板字段 | 全部 L2 字段生成逻辑 | 任何字段新增/删除/重命名 → stage_inputs 构造 yaml 失效 |
| `schemas/config.schema.yaml` required set | L1 `config.yaml` 构造 | required 变更 → schema validation 抛异常 |
| `scripts/generate_yaml.py:97-123` 的 SQL 查询列表 | （仅作字段参考，我方不走 db 分支）| 作者新增列可能意味着新增**硬需求**字段 — 需人工审阅 |
| `Snakefile:100-108` 中 `riboseq_dict = ribo_yaml['input']['fastq']` 的结构假设 | stage_inputs 的 fastq dict 构造 | 结构变更 → 下游规则 KeyError |
| `Snakefile:229-231` 的 `wildcard_constraints` 正则（study 名）| stage_inputs 的 study 命名 | 作者收紧正则可能拒绝我方命名 |

### 3.2 TE_model 升级敏感面

| 作者路径 | 我方 run_downstream 依赖 | 升级影响 |
|---|---|---|
| `src/TE.R:16-17` 硬编码输入文件名（`ribo_paired_count_dummy.csv`, `rna_paired_count_dummy.csv`） | Stage 2 产物名 | 文件名变更 → R 读取失败 |
| `src/TE.R:59` 硬编码 `data/infor_filter.csv` | 我方 infor_filter 供给路径 | 作者重命名 → R 读取失败 |
| `src/TE.R:67` 输出 `human_TE_cellline_all.csv` | Stage 3 `transpose_TE.py` 输入 | 输出名变更 → Stage 3 链式失败 |
| `src/ribobase_counts_processing.py:122` `./data/nonpolyA_gene.csv` | 物种过滤依赖 | 作者加入 organism 分支 → 可能需新增 sidecar |
| `pipeline.bash:24` `python -m trials.{pipeline_dir}.config` | Stage 0 入口 | 作者改成其他 import path → 我方生成的 trial config.py 布局失效 |
| `src/ribo_counts_to_csv.py:main(...)` 签名 | 我方 Stage 0 Python 直连调用方案 | 签名变更 → 直连调用失效 |

## 4. 下一次升级触发条件

### 4.1 必须升级的触发器

- upstream 修复 **我方当前阻断项**（见各 contract 的 §6）：
  - snakescale：若作者将 db.sqlite3 依赖从 `generate_yaml.py` 抽离为可选（当前 `Snakefile:38` 硬调用）→ 可简化我方绕过逻辑。
  - snakescale：若作者暴露 `local_staged_fastq` 模式（免 `prefetch`/`fasterq-dump`）→ 可对齐 `upstream_input_contract.md` 语义。
  - TE_model：若作者移除 `./data/infor_filter.csv` 的硬编码相对路径（改为 CLI 参数）→ 可移除 `cwd=vendor/TE_model/` 约束。
  - TE_model：若作者修复 `human_TE_*` 命名的跨物种问题 → 可移除我方 wrapping 层重命名逻辑。

### 4.2 可选升级的触发器

- upstream 发布 tag（当前无）→ 从 SHA 切换到 tag 更稳。
- upstream CI 绿灯 + changelog 明确 "no input contract change" → 可激进跟随 main。
- 我方下游新增支持的 organism，而 snakescale 的 `references.yaml` 未覆盖 → 被迫升级或 fork 补充。

### 4.3 必须**冻结**的触发器（不升级）

- 在 T4 stage_inputs 完成 + T9 契约测试全绿之前，**不得**升级任何一端 SHA — 否则会使 contract 文档与实际代码不一致。

## 5. 升级测试清单（建议绑定 T9 / T14）

- `tests/fixtures/gse105082/` 基线 MD5 回归（T14 冻结）
- stage_inputs 产出的 `project.yaml` 与手工基线 diff 为空
- run_downstream 产出的 `human_TE_cellline_all_T.csv` 与 `tests/fixtures/gse105082/baseline_outputs/human_TE_cellline_all_T.csv` md5 一致

以上任一失败 → 升级回滚。
