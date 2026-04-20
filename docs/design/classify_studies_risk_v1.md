# classify_studies Risk v1

## 1. Source Note

尝试读取 `reference_cenik_nbt2025_methods.md` 失败：

- `cat 'C:/Users/91640/AppData/Roaming/reference_cenik_nbt2025_methods.md'` -> no such file
- `find /home/xrx -name 'reference_cenik_nbt2025_methods.md'` -> no result

因此本稿采用 fallback：以 `vendor/snakescale/scripts/guess_adapters.py`、`vendor/snakescale/Snakefile` 和 `docs/snakescale_contract.md` 为准。凡是“CenikLab 方法学”相关表述，若不是直接来自这些文件，一律标为推断。

## 2. snakescale 的 adapter 猜测规则

已验证事实：

1. `guess_adapter` 只在 `adapter_yaml['has_low_adapter']` 为真时触发，且只对低 adapter presence 的样本跑猜测，见 `vendor/snakescale/Snakefile:673-706`。置信度：高
2. 其参数来自 `config['guess_adapter']`，默认值为：
   - `skipped_reads=1000000`
   - `sample_size=10000`
   - `min_length=10`
   - `max_length=15`
   - `skipped_nucleotides=10`
   - `seed_length=6`
   - `match_ratio=0.5`
   见 `vendor/snakescale/schemas/config.schema.yaml:41-73` 与 `vendor/snakescale/Snakefile:681-699`。置信度：高
3. `guess_adapters.py` 先维护一个已知 adapter 列表，再做 de novo 扩展：
   - 已知 adapter 列表见 `vendor/snakescale/scripts/guess_adapters.py:18-38`
   - 先检测已知 adapter 的前 `kmerlength` 个碱基是否在 reads 中达到阈值，再要求其前 `minlength` 个碱基的 anchor 频率达到阈值；阈值是 `KNOWN_ADAPTER_RATIO_THRESHOLD = 0.4`，见 `vendor/snakescale/scripts/guess_adapters.py:18, 493-540`
   - 若已知 adapter 失败，则对所有 `4^k` 个 k-mer 计数，选 top hits，按 `match_ratio` 逐位延长到 `minlength`，再继续逐碱基扩到 `maxlength`，见 `vendor/snakescale/scripts/guess_adapters.py:227-391`
4. 若采样 reads 长度不一致，`guess_adapter()` 会直接返回 `None`，把这批数据视作“可能 pre-clipped”，见 `vendor/snakescale/scripts/guess_adapters.py:395-417, 488-494`。置信度：高

我的复述：

- snakescale 的 adapter 猜测不是“全局比对”，而是“样本化 reads -> 已知 adapter 快速命中 -> 失败后做短 k-mer 频率扩展”。
- 它对“read 长度已不齐”的数据非常保守，优先把这种情况解释成 pre-clipped，而不是继续猜 adapter。

## 3. 与 handoff 中所谓 “CenikLab 方法学” 的关系

已验证事实：

- 仓内只有 `module_contracts` 的一句提示说“CenikLab 有这个”，见 `docs/te_analysis_module_contracts_v1.md:467`
- 本轮无法读取 handoff 提到的 `reference_cenik_nbt2025_methods.md`

推断：

- snakescale 当前实现看起来就是 CenikLab 一系的 heuristics：已知 adapter 优先，之后再做 de novo k-mer 扩展，并把 variable-length reads 作为 pre-clipped 信号。置信度：中
- 但我无法在本轮证明“NBT 2025 methods 的文字表述”与当前 `guess_adapters.py` 完全一致。置信度：低

## 4. classify_studies 的真正门控

已验证事实：

1. `check_adapter` 只抽样 FASTQ 的一小段送给 cutadapt，统计 `w/adapters` 占比，见 `vendor/snakescale/Snakefile:283-308`。置信度：高
2. `check_adapter_stats` 以 `adapter_threshold` 为门槛；默认 `<50%` 会进入 `low_adapter_files`，见 `vendor/snakescale/Snakefile:351-376` 与 `vendor/snakescale/schemas/config.schema.yaml:8-11`。置信度：高
3. `check_lengths` 抽每个 FASTQ 前 1000 条 reads，看长度是否一致；若某类样本“全部不齐”，则设置 `has_all_uneven_lengths=True`，并去掉 adapter 相关 cutadapt 参数，见 `vendor/snakescale/Snakefile:428-493`。置信度：高
4. `classify_studies` 只有在以下情况才会把 study 判 invalid，见 `vendor/snakescale/Snakefile:829-870`。置信度：高
   - 有低 adapter 文件，且不是“全部 uneven”，且没有 `consensus_adapter`
   - 有 uneven files，且不是“全部 uneven”，且没有 `consensus_adapter`
   - guessed adapters 多于 1 个

结论：

- “87/120 strict-invalid” 不是实际运行后的 invalid 数，而是按 `threep_adapter` 覆盖率做的静态风险代理。置信度：高
- 真正 invalid 还取决于 `check_lengths` 和 `guess_adapter` 的运行结果。置信度：高

## 5. `override=True` 到底放过了什么

已验证事实：

- `override=True` 不会跳过 `check_adapter`、`check_adapter_stats`、`check_lengths`、`guess_adapter`、`classify_studies`
- 它只是在 `run_riboflow` 时允许 invalid study 继续进入 nextflow，见 `vendor/snakescale/Snakefile:940-950`

因此：

- 会保留的 QC 信息：`*_adapter.yaml`、`*_length.yaml`、`*_guess.yaml`、`log/failed/{study}/modifications.log`
- 会被绕过的唯一 block：`classify_studies` 对 `run_riboflow` 的硬门控

推断：

- `override=True` 的风险不是“没有 QC”，而是“带着已知 QC 警告继续跑”。置信度：高
- 对 pre-clipped study，这种做法可能仍能产出 `.ribo`，但需要后续按 `log/failed/**` 分层解释，而不能把它们与 full-valid study 混为一个质量等级。置信度：高

## 6. 静态风险量化

已验证事实：

- `/tmp/t8_invalid_studies_audit.csv` 本轮已重算
- 全量 Ribo studies：120
- `threep_adapter` 覆盖率 `0%`：87
- `threep_adapter` 覆盖率 `<100%`：89
- `threep_adapter` 覆盖率 `100%`：31

这组数字的含义：

- `87/120 = 72.5%` 是 strict-risk proxy，不是运行后 invalid 的精确占比
- `31/120 = 25.8%` 是当前最适合做 MVP 的 full-valid 批次

## 7. 三种处置方案

### 方案 α：外部预计算 adapter，再填回 `metadata.csv`

优点：

- 理论上能把一部分 strict-risk study 拉回 full-valid 路径

缺点：

- 直接冲撞当前硬约束：本轮不能改 `data/raw/metadata.csv`
- 还会把“adapter 决策”从 vendor 内迁到我们自己的数据层

判断：

- 只能作为 T14 或显式数据治理任务讨论，不适合当前 T8 破局。置信度：高

### 方案 β：`override=True` 强跑

优点：

- 立刻解除 invalid gate，最有利于证明 `.ribo` 能否生成
- 对 #8 解后做单 study 真跑最直接

缺点：

- 输出将带着已知 QC 警告，不能直接与 full-valid study 同层解释
- 不解决大规模运行时的分层与资源分配问题

判断：

- 适合作为单 study 验证路径，尤其是 GSE132441 这种明确目标 study。置信度：高

### 方案 γ：分层执行

定义：

- 先跑 31 个 full-valid studies 作为 MVP
- 对 strict-risk / partial-risk study 另行分层，必要时才启用 `override=True`

优点：

- 与现有 QC 语义最一致
- 能最快形成一批“解释成本最低”的成功样本

缺点：

- 不能单独解除 #8；它只是大规模执行策略

判断：

- 应作为全局运营策略，与 β 配套，而不是替代 β。置信度：高

## 8. 推荐

推荐组合：**短期用 β 解单 study / 解 T8，批量执行用 γ 做分层**。置信度：高。

不推荐当前走 α。置信度：高。

## 9. 对 Session-P 的直接含义

1. 若用户批准路径 d，T8 真跑应继续使用 `override=True`
2. 但 `override=True` 只应用于已知目标 study，不应马上扩展到全部 87 个 strict-risk studies
3. 下一步最合理的规模化路径不是“全量开 override”，而是先做 31-study MVP 批次，再决定 strict-risk 样本的救援策略
