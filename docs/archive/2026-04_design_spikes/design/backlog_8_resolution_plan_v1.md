# Backlog #8 Resolution Plan v1

## 1. O1 调研结论

### Q1. upstream `main` 是否已修 15 处 typo？

结论：**没有。** 置信度：高。

证据：

- 本地锁定 SHA：`vendor/snakescale` = `b918e75`
- upstream 只读 clone 当前 HEAD：`git -C /tmp/snakescale_upstream rev-parse --short HEAD` -> `b918e75`
- `/tmp/snakescale_upstream/riboflow/RiboFlow.groovy` 仍含 15 处 `-@ {task.cpus}`，例如 `260, 261, 321, 322, 358, 359, 553, 1172, 1173, 1528, 1529, 1585, 1586, 1624, 1625`

### Q2. 如已修，是哪个 commit 修的？diff 多大？

结论：**不存在该修复 commit。** 置信度：高。

证据：

- `git -C /tmp/snakescale_upstream log --oneline --all -- riboflow/RiboFlow.groovy | head -20` 仅返回 `1f173bc initialized repo`
- `git -C /tmp/snakescale_upstream log -S 'task.cpus' --oneline riboflow/RiboFlow.groovy | head -10` 同样仅返回 `1f173bc initialized repo`

推断：

- 该文件自仓库初始化后没有出现独立修复提交。置信度：中

### Q3. 从锁定 SHA `b918e75` 到 upstream `main` 有多少 commit？有哪些非 typo 相关变更？

结论：**0 个 commit。** 置信度：高。

证据：

- `git -C /tmp/snakescale_upstream rev-list --count b918e75..HEAD` -> `0`
- 因 commit 距离为 0，不存在“中间非 typo 变更”可列。

### Q4. issue tracker 是否已有公开讨论？

结论：**未检索到公开 issue / PR。** 置信度：中。

证据：

- GitHub connector 搜索 issue：`task.cpus OR "samtools -@" OR "groovy interpolation" OR RiboFlow.groovy` -> 0 结果
- GitHub connector 搜索 PR：同查询 -> 0 结果

局限：

- 该结论依赖关键词搜索，不等价于“绝对不存在任何相关讨论”。

## 2. O3 合规判断

结论：**路径 b（本地 `vendor_patches/`）不合规。** 置信度：高。

证据：

- `docs/te_analysis_module_contracts_v1.md:318-324`
  - `M8/9.MUST.3`：vendor bug 优先走上游 issue；等不起就 fork，在 fork 里修，submodule 指向 fork
  - `M8/9.MUSTNOT.1`：禁止在 `vendor/*` 下直接 edit 文件
- `docs/te_analysis_top_level_design_v1.md:416`
  - “原作者管线的 bug 走上游 issue，不在本项目内部 patch”
- `docs/te_analysis_sprint_plan_v1.md:240`
  - T8 边界 MUST NOT：为了通过而在外壳打 patch

判断：

- 即便 patch 文件存放在 `vendor_patches/` 而不在 `vendor/` 内，只要执行时把 patch 应用到 `vendor/snakescale` 工作树，本质上仍是在本项目内部 patch vendor。

## 3. 三路径评估表

| 路径 | 代价 | 风险 | 复位难度 | 合规性 | 结论 |
|---|---|---|---|---|---|
| a. 提 upstream PR，待合并后 revendor | 跨多次 session | 低 | 低 | 合规 | **推荐** |
| b. 本地 `vendor_patches/` | 一次 session 可落地 | 高 | 中 | **不合规** | 否决 |
| c. 切换到已修 SHA / fork SHA | 目前不可执行 | 中 | 中 | 条件合规 | 暂不可选 |

补充：

- 路径 c 只有在“存在一个明确已修的 SHA 或 fork”时才成立。
- 当前 O1 结果表明 upstream `main` 仍等于 `b918e75`，所以 c 没有候选目标。

## 4. 推荐路径

推荐 **a. upstream PR -> merge -> revendor**。置信度：高。

原因：

1. b 被宪法直接否决。
2. c 目前没有可切换的目标 SHA。
3. a 是唯一同时满足“能解 bug”和“保持 vendor 合同不被撕开”的路径。

## 5. 路径 a 的实施 DAG

前置：

1. 提交一个只包含 15 处 `${task.cpus}` 修正的最小 PR 到 upstream
2. 在 PR 描述中附上失败日志：`samtools idxstats: failed to open "-@"`

执行：

1. 等 upstream 合并
2. 更新 submodule pointer 到合并后的 commit
3. 重跑本仓冷启动校验
4. 重跑 T8：先 `--until check_adapter`，再全流程
5. #8 解后再进入 #9 的 Method F 码化

验证：

1. `PYTHONPATH=src python -m pytest tests/ -v`
2. `PYTHONPATH=src python -m te_analysis.stage_inputs --metadata ... --study GSE132441 --out /tmp/t4_verify`
3. `python scripts/verify_t3_metadata.py`
4. `snakemake --until check_adapter`
5. `run_upstream` 全流程到 `.ribo`

回滚预案：

1. 若新 SHA 引入额外回归，回退 submodule pointer 到 `b918e75`
2. 保留本次 O1/O6 文档与日志，不保留任何本地 vendor patch

## 6. 若未来路径 c 变为可执行

需重跑的校验清单：

1. 全量 pytest（当前应为 42 passed）
2. T4 smoke
3. `verify_t3_metadata.py`
4. T8 `--until check_adapter`
5. T8 全流程 `.ribo`
6. T9 下游重算与 smoke fixture 对照
7. `docs/progress_snapshot.md` 与 `docs/backlog.md` 的 SHA / 风险同步
