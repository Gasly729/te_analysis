# Method F Codification v1

## 1. 现状

Method F 目前依赖两步手工注入：

1. 把 `data/interim/snakescale/{GSE}/staged_fastq/{GSE}` 暴露到 `vendor/snakescale/staged_fastq/{GSE}`，解决 snakescale 在 `cwd=vendor/snakescale/` 下看不到相对路径的问题。
2. 为每个 `_1.fastq.gz` 额外制造一个更老的空 `_1.fastq`，再刷新 `.gz` 的 mtime，绕过 `download_fastq_files` 和 `gzip_fastq`。

该方案已在 T8 Phase B 验证可行，但仍是 session 级 shell 操作，不属于 `src/` 合同。

## 2. 三个候选方案

### A. 扩 `stage_inputs.py`

签名草案：

```python
def _create_snakescale_placeholders(out: Path, study: str) -> int: ...
def _touch_plain_fastq_placeholder(gz_path: Path, age_seconds: int = 3600) -> Path: ...
```

测试桩命名：

- `test_create_snakescale_placeholders_creates_plain_fastq`
- `test_create_snakescale_placeholders_preserves_gz_symlink`
- `test_create_snakescale_placeholders_orders_mtime_correctly`
- `test_stage_inputs_cli_writes_method_f_scaffold`

合同影响：

- M1：`265 -> ~305`，相对上限 `250` 变为 `+55`
- M2：无直接变化
- M5：无变化

回滚难度：低。单文件回退即可，但会把运行时注入逻辑永久塞进 T4。

判断：

- 优点：一次写完，T4 直接产出 snakescale-ready 目录。
- 缺点：把“vendor cwd 注入”与“metadata -> project.yaml”混在同一模块，职责边界变差。

### B. 新建 `src/te_analysis/stage_snakescale_injection.py`

签名草案：

```python
def inject_staged_fastq(study_dir: Path, vendor_root: Path, study: str) -> Path: ...
def prepare_download_bypass(staged_root: Path, age_seconds: int = 3600) -> int: ...
```

测试桩命名：

- `test_inject_staged_fastq_links_vendor_visible_tree`
- `test_prepare_download_bypass_creates_plain_fastq_placeholders`
- `test_prepare_download_bypass_preserves_existing_gz_links`
- `test_prepare_download_bypass_sets_placeholder_older_than_gz`
- `test_run_upstream_calls_snakescale_injection_once`

合同影响：

- M1：保持现状，最多只补一行文档引用
- M2：预计 `77 -> ~85`，相对上限 `80` 约 `+5`
- M5：无变化

回滚难度：低。删除 helper 并回退 `run_upstream.py` 的一处调用即可。

判断：

- 优点：把 Method F 作为“运行前注入层”独立建模，最贴近真实职责。
- 优点：测试边界清晰，可单独做 contract test。
- 缺点：多一个 helper 模块，需要在 M1/M2 文档里补一条引用。

### C. 扩 `run_upstream.py`

签名草案：

```python
def _inject_staged_fastq(study_dir: Path, study: str) -> Path: ...
def _prepare_fastq_placeholders(study_dir: Path, age_seconds: int = 3600) -> int: ...
```

测试桩命名：

- `test_inject_staged_fastq_relinks_vendor_target`
- `test_prepare_fastq_placeholders_creates_plain_fastq`
- `test_prepare_fastq_placeholders_is_idempotent`
- `test_main_prepares_method_f_before_subprocess`

合同影响：

- M1：无变化
- M2：`77 -> ~125`，相对上限 `80` 变为 `+45`
- M5：无变化

回滚难度：中。逻辑集中在一个文件里，方便撤回，但会继续抬高 M2 的复杂度。

判断：

- 优点：调用点最直接。
- 缺点：`run_upstream.py` 会从“薄壳命令拼接”膨胀成“命令拼接 + 运行时修补”，违背 M2 初衷。

## 3. 推荐

推荐 **B. 新建 `stage_snakescale_injection.py` helper**。置信度：高。

理由：

1. Method F 的核心不是 metadata staging，而是“把已有 staged 产物适配到 vendor runtime 语义”。
2. 它比 A 更少污染 M1，比 C 更少挤压 M2。
3. 它天然适合承接后续 mini-mock vendor E2E 测试。

不推荐 A 的原因：把 T4 从“声明式 staging”推向“带 vendor 语义的 staging”。

不推荐 C 的原因：会让 M2 明显超出其“薄壳”定位。

## 4. 实现顺序

前置：先解决 backlog #8，确认最终走 upstream PR / fork-SHA，而不是本地 patch。

实施 DAG：

1. 新建 `src/te_analysis/stage_snakescale_injection.py`
2. 先写 helper 单测，不碰真实 vendor
3. 在 `run_upstream.py` 中增加一处调用
4. 补 `test_run_upstream.py` 的集成断言
5. 以 `snakemake --until check_adapter` 复验 GSE132441

## 5. 备注

本稿只定义实现落点，不主张在 #8 未解前先写代码；否则 helper 细节可能随着最终 vendor 解决路径变化而返工。
