# Contract Testing Gap v1

## 1. 现状诊断

当前 42 个测试覆盖了三类合同：

| 维度 | 现有测试 | 覆盖情况 |
|---|---:|---|
| 配置与路径常量 | 5 | `config.py` 的 repo-root 与路径加载 |
| T4 staging 产物 | 15 | study 过滤、报错分支、`project.yaml` schema、FASTQ symlink |
| T5/T6 薄壳行为 | 15 | 命令拼接、symlink、subprocess 返回码、下游 mocked E2E |
| T9 冻结产物 smoke | 7 | fixture 文件存在、schema、hash 冻结 |

缺失的合同层：

- vendor `cwd` 相对路径可见性
- Snakemake “输入槽位”与 T4 产物命名是否对齐
- `download_fastq_files -> gzip_fastq` 的 mtime 语义
- `classify_studies` 与 `override=True` 的真正分界
- Nextflow `RiboFlow.groovy` 的 shell/groovy 插值有效性

结论：当前测试更像“我方薄壳单测 + 下游 fixture smoke”，并没有覆盖“我方产物进入 vendor runtime 后是否仍满足合同”。

## 2. 三次 T8 挂点归类

| 挂点 | 根因 | 缺的测试层 |
|---|---|---|
| Session-M `_1.fastq` vs `_1.fastq.gz` | T4 产物命名符合 post-gzip，而 `Snakefile:download_fastq_files` 读 pre-gzip 槽位 | vendor 输入槽位 contract test |
| Session-N staged_fastq 不可见 | `project.yaml` 中相对路径从 `vendor/snakescale/` 解析，`data/interim/...` 不在其 cwd 下 | vendor cwd visibility test |
| Session-N `RiboFlow.groovy` 15 处 typo | vendor 自身 bug，当前测试没有任何“最小上游执行核”探针 | mini vendor E2E / vendor contract smoke |

结论：42 tests 全绿不代表 T8 可绿，因为它们几乎都停在 vendor 入口之外。

## 3. 建议新增层

建议新增 **mini-mock vendor E2E**，目标：

- 输入：10KB 假 FASTQ、最小 `project.yaml`
- 运行物：stub `Snakefile` / stub `RiboFlow.groovy`
- 目标：在 `<5s` 内覆盖“命名、相对路径、mtime、gate、命令拼接”五个合同点

推荐范围：

1. 用临时目录模拟 `vendor/snakescale/`
2. 放一个只保留 `download_fastq_files`、`gzip_fastq`、`classify_studies`、`run_riboflow` 的 stub Snakefile
3. `run_riboflow` 不跑 Nextflow，只记录收到的 study / yaml / override
4. 用空 FASTQ 和 touch 改 mtime，验证 Method F 是否真的让 DAG 停在预期位置

## 4. 测试桩清单

建议新增 5 件：

- `test_vendor_stub_accepts_stage_inputs_layout`
- `test_vendor_stub_requires_vendor_visible_staged_fastq`
- `test_vendor_stub_download_rule_short_circuits_with_method_f`
- `test_vendor_stub_override_true_bypasses_invalid_gate_only`
- `test_vendor_stub_rejects_multiple_adapters_without_override`

预计代码量：

- `tests/test_vendor_contract_smoke.py`：120-160 行
- `tests/fixtures/vendor_stub/`：40-60 行

预计覆盖增益：

- 补足 T8 三次失败都缺失的“边界层”测试
- 不引入真实 snakescale / nextflow / bowtie2 依赖

## 5. T12 纳入方式

建议把它作为 **T12 的首个子任务**，而不是独立 `T12.5`。置信度：中。

理由：

1. 它本质是“合同补测”，不是新功能。
2. 它直接服务于 T12 对 tests/ 结构与必要性的审查。
3. 若单独拆成 `T12.5`，只会制造新的流程节点，不会降低复杂度。

补充判断：

- 若 #8 先以 upstream PR 解决，则这层测试应在 revendor 之前落地。
- 若 #8 长时间阻塞，这份设计稿即可先作为 T12 审查输入，不需要提前启动编码。
