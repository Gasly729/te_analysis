# Codex Window Handoff

## 1. Current project state

- 新仓库已确认采用方法两阶段：upstream `FASTQ -> .ribo`，downstream `.ribo -> TE`。
- 新仓库已确认采用工程三层：`upstream/`、`handoff/`、`downstream/`。
- `raw_motheds/` 仍是只读参考后端区，未被迁移进新主架构。
- `src/te_analysis/` 下已建立新的本地 wrapper 骨架、stage registry、I/O contracts 和配置骨架。
- `handoff/` 层已可构建 machine-readable manifest、做严格校验、并稳定序列化为 JSON。
- handoff 仍以 study-scoped experiment-level `.ribo` collection 为主对象，`all.ribo` 仅是可选聚合物。
- sidecar 已显式建模为 study-scoped 与 shared 两类，required sidecar 缺失会 fail closed。
- winsorization 已被架构上提升为 explicit downstream stage，但仍未迁移实现。
- 轻量无依赖检查已通过：`compileall` 成功，手动加载并执行 handoff/stage/config 测试函数成功。

## 2. Confirmed architecture decisions

- 方法边界不可改：
  - upstream method owner = `SnakeScale / RiboFlow`
  - downstream method owner = `TE_model`
- 工程边界不可改：
  - `upstream/`
  - `handoff/`
  - `downstream/`
- handoff truth 不可改：
  - 主下游输入 = study-scoped experiment-level `.ribo` collection
  - `all.ribo` = optional aggregate artifact only
  - sidecar tables/config references 是真实 contract 的组成部分
- downstream 顺序不可改：
  - extraction
  - winsorization
  - filtering
  - TE compute
  - result packaging
- winsorization 语义不可改：
  - 原始实现属于 downstream extraction-time semantics
  - 新架构中显式记录为单独 stage
  - 但尚未迁移实现
- `raw_motheds/` 不得被当作新主架构、主 import surface 或主 config surface。

## 3. What has been implemented

- `docs/architecture/pipeline_blueprint.md`
  - 固定了“方法两阶段 + 工程三层”的总蓝图。
- `docs/architecture/stage_contracts.md`
  - 固定了各 stage 的输入/输出边界和 config ownership。
- `docs/architecture/handoff_spec.md`
  - 固定了 handoff validity rules、sidecar scope、manifest minimum schema。
- `docs/architecture/migration_plan.md`
  - 固定了迁移顺序和明确延后项。
- `src/te_analysis/pipeline/models.py`
  - 保证 stage identity、layer、contract metadata 有 typed 定义。
- `src/te_analysis/pipeline/stage_registry.py`
  - 保证 stage 顺序、handoff 层独立性、winsorization/compute/packaging 语义分离已固定。
- `src/te_analysis/pipeline/io_contracts.py`
  - 现在仅作为 handoff contract 的兼容导出层，不再自己承载 contract 真相。
- `src/te_analysis/handoff/ribo_manifest.py`
  - 保证 manifest、artifact、sidecar、validation summary 的 typed schema 已存在。
- `src/te_analysis/handoff/handoff_builder.py`
  - 保证可只读扫描 `.ribo`、收集 sidecar、构建 manifest、稳定序列化 JSON。
- `src/te_analysis/handoff/validators.py`
  - 保证支持 strict validation、fail-closed sidecar 检查、`all.ribo` alone invalid。
- `configs/pipeline/*.yaml`
  - 保证 local staged FASTQ、download disabled、handoff/main object 等方向已锁定。
- `configs/downstream/te_model.yaml` 与 `configs/downstream/winsorization.yaml`
  - 保证 downstream 仍围绕 `TE_model` wrapper，winsorization 语义已显式收紧。
- `tests/test_handoff_manifest.py`
  - 保证 manifest construction、serialization、missing sidecar failure、scope distinction 已被覆盖。
- `tests/test_stage_contracts.py`
  - 保证 stage order 与 handoff/winsorization contract 兼容性已被覆盖。
- `tests/test_config_loading.py`
  - 保证关键 config 文本约束仍被检查。

## 4. What is intentionally not implemented yet

- SnakeScale wrapper 实际执行逻辑
- RiboFlow wrapper 实际执行逻辑
- study config materialization 逻辑
- handoff manifest 写回磁盘/CLI
- `.ribo` 解析与 extraction 逻辑
- winsorization 实现
- filtering 实现
- `TE.R` wiring 与 downstream compute 逻辑
- backend execution、scheduler、subprocess runtime

## 5. Current highest-priority next step

实现最小可运行的本地 handoff CLI / file-emission 层：基于现有 `handoff_builder` 和 `validators`，从显式 study 输入生成并落盘 handoff manifest，同时提供 build/validate 两个只读命令入口，不执行任何 backend。

## 6. Boundaries that must not be violated

- 不得修改 `raw_motheds/`。
- 不得开始迁移 extraction / winsorization / filtering / TE compute 生物学逻辑。
- 不得把 `all.ribo` 重新设计成唯一 downstream API。
- 不得把 missing required sidecars 降级成 warning。
- 不得让 active code import `raw_motheds/`、`archive/`、历史 `workflow/` 或 runtime residue。
- 不得重新引入 downloader fallback 或隐式路径猜测。
- 不得让 packaging 改变 TE numerical semantics。

## 7. Files a new window must read first

- `/home/xrx/my_project/te_analysis/docs/architecture/pipeline_blueprint.md`
- `/home/xrx/my_project/te_analysis/docs/architecture/handoff_spec.md`
- `/home/xrx/my_project/te_analysis/src/te_analysis/pipeline/stage_registry.py`
- `/home/xrx/my_project/te_analysis/src/te_analysis/handoff/ribo_manifest.py`
- `/home/xrx/my_project/te_analysis/src/te_analysis/handoff/handoff_builder.py`
- `/home/xrx/my_project/te_analysis/src/te_analysis/handoff/validators.py`
- `/home/xrx/my_project/te_analysis/configs/downstream/winsorization.yaml`

## 8. Recommended next task prompt

在 `/home/xrx/my_project/te_analysis` 中实现最小可运行的 handoff CLI / manifest emission 层。只在 `src/te_analysis/cli.py` 和必要的 handoff 相关模块内做最小改动，新增只读命令以构建和校验 handoff manifest，并将 manifest 以稳定 JSON 写入显式输出路径。不要执行 SnakeScale、RiboFlow 或 TE_model；不要实现 `.ribo` 内容解析、winsorization、filtering 或 TE compute；不要修改 `raw_motheds/`；保持 handoff 仍以 experiment-level `.ribo` collection 为主对象，`all.ribo` 仅作为 optional aggregate artifact。
