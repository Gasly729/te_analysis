| 主链路 | 当前能跑到 | 最大阻塞 |
|---|---|---|
| te_analysis | **✅ 已验证：GSE125086 有 `.ribo`；GSE105082 已出 TE 表，但两者还不像同一条端到端样板** | **GSE132441 默认例子没出 `.ribo`** |
| snakescaleTE 缝合版 | **✅ 已验证：GSE48603 旧结果可读；Homo sapiens 物种 TE 已出表，靠 serial-fallback 绕过并行问题** | **shared TE_model 的 R 并行开 socket 失败** |

## 能跑通什么

| 事项 | 结论 |
|---|---|
| A 线上游 | **✅ 已验证：`vendor/snakescale/output/GSE125086/ribo/` 有 6 个实验 `.ribo` 和 `all.ribo`。GSE132441 只有分期、0 字节占位和一个剪切文件，状态是 failed；这不是小缺口，而是默认入口没落到目标结果。🔍 推断：A 包装能接上 snakescale，但默认例子还没闭环。** |
| A 线下游 | **✅ 已验证：`run_downstream` 对 GSE105082 产出 3 个 TE 文件。❓ 未知：GSE125086 是否已用同一受控入口接到 TE；当前看不到对应产物。** |
| B 线 | **✅ 已验证：GSE48603 的 `all.ribo` 是旧工作区软链，当前机器能读，但不是可迁移仓库产物；Homo sapiens species 选 4 个研究、55 个实验，用 serial-fallback 产出 `human_TE_cellline_all.csv`。** |
| 只在纸面/半路 | **✅ 已验证：GSE132441 `make all` 没有当前 `.ribo`；Arabidopsis species 只有 prepare/smoke，没有最终 TE 表，所以不能算第二物种闭环。** |

## 哪里在流血

| 严重度 | 问题是什么 | 为什么是问题 | 力气 |
|---|---|---|---|
| 高 | **✅ GSE132441 上游失败。** | 默认研究不能证明 A 线可生产，也挡住后续示范。 | 约 1 天 |
| 高 | **✅ shared TE_model Stage 2 socket 失败。** | B 线不用 serial-fallback 就卡住。 | 数小时到 1 天 |
| 中 | **✅ 测试不是绿色。** | `PYTHONPATH=src pytest tests` 为 58 过 1 失败；裸跑还扫归档测试。这会挡住后续放心改代码。 | 数小时 |

## 潜在的坑（还没炸但会炸）

| 坑 | 置信度 | 判断 |
|---|---|---|
| vendor | 高 | **✅ 顶层 git 显示两个 vendor 被删，`.gitmodules` 改成 ignore all；vendor 内还有未提交补丁和产物。重新 clone 或换机器时最容易失真。** |
| 存储 | 高 | **✅ 仓库 661G，磁盘 93% 已用，`vendor/snakescale/intermediates` 633G；再开大批量前要先收拾。** |
| 本机路径 | 高 | **✅ species 默认写死 `/home/xrx/miniconda3/...`；GSE48603 和 raw FASTQ 靠本机软链。当前能跑，不代表别人能跑。** |
| 版本 | 中 | **✅ 环境无 pixi/lock；R 包已有版本警告。依赖漂移后，老结果很难解释，也很难向外交付。** |

## 下一步最该做什么

| 优先级 | 行动 | 为什么 | Definition of Done |
|---|---|---|---|
| 1 | **修 GSE132441 上游。** | 默认入口先要可信。 | `make upstream STUDY=GSE132441` 先出非空 `all.ribo` 和实验 `.ribo`。 |
| 2 | **固定 serial-fallback。** | shared 模式现在已知会炸。 | 一条命令从 prepare 到 TE 表，日志写明 serial。 |
| 3 | **整理 vendor 合同。** | 复现风险最大。 | git 不再显示 vendor 删除；补丁可重放。 |
| 4 | **清理中间文件。** | 空间会挡批量跑，也会拖慢排错。 | 保留 `.ribo`/关键日志，删可重建中间件。 |
| 5 | **修测试入口。** | 后续改动要红绿灯。 | `PYTHONPATH=src pytest tests -q` 全绿，裸 pytest 不扫 `data/processed`。 |

建议先做 GSE132441 上游闭环。
