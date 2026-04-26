# T7 — P1a 修复路径决策简报

**日期**：2026-04-21
**问题**：check_adapter rule 对大文件（≥6 GB）Ribo-Seq 样本，cutadapt -j 0 + zcat|head|tail
pipe 竞争，导致 TSV 包含 Python traceback（exit=1）或为空（-j 1 时 exit=0 但无输出）。

---

## 路径 A：Ribo-Seq stub 注入（扩展 prepare_rna_stub.py）

**思路**：对 check_adapter 失败/输出无效的 Ribo-Seq 样本，注入与 RNA-Seq stub 相同格式的
固定 TSV（in_reads=25000, w/adapters=0）。classify_studies 读到 w/adapters=0 会将这些 SRR
列入 low_adapter_files，触发 adapter 猜测逻辑。

### 实现步骤（共 3 步，约 8 个 task）

1. **修改 prepare_rna_stub.py**（1 task）
   - 增加 `--include-ribo` flag，对 type='Ribo-Seq' 样本也生成 stub TSV
   - stub 内容：`w/adapters=0`（与 RNA-Seq 相同）

2. **修改 run_p5_batch.sh**（1 task）
   - 在每个 study 的 snakemake 运行失败后，检查 adapter_check_output/ 下哪些 TSV
     无效（空文件或含 traceback），调用 prepare_rna_stub.py --include-ribo 注入 stub，
     再用 --rerun-incomplete 重启

3. **验证**（2 task：GSE100007 + GSE123018 各 1 次）

### 阻断风险

- **TE 数值污染**：stub 的 w/adapters=0 会让这些 Ribo-Seq SRR 进入 `low_adapter_files`，
  classify_studies 会尝试猜 adapter。若猜不到（consensus_adapter=null），study 仍判 invalid。
  若猜到，adapter 可能不正确，导致 clip 步骤产出低质量 reads，.ribo 数值失真。
- **与 RNA-Seq stub 混淆**：Ribo-Seq stub 和 RNA-Seq stub 内容相同但语义不同，
  下游审查时难以区分哪些是真实 QC 数据。
- **掩盖真正的数据问题**：这些大文件样本可能本身就有问题（非 FASTQ 格式、截断等），
  stub 跳过了真正的验证。

### 预期完成
约 4 个 task（修改 2 文件 + 验证 2 study）

---

## 路径 B：真实 adapter 预计算（新脚本 prepare_adapter_stats.py）

**思路**：新建 `scripts/prepare_adapter_stats.py`，对每个 Ribo-Seq SRR，
使用 `-j 1`（单线程）+ `|| true`（忽略 pipe 错误）重跑 cutadapt，
产出真实的 cutadapt minimal report TSV，再检查 TSV 是否有效（>0 行数据）；
若仍为空则回退到 stub。

### 实现步骤（共 5 步，约 12 个 task）

1. **新建 scripts/prepare_adapter_stats.py**（2 task）
   - 读 db，对指定 study 的 Ribo-Seq SRR，构造与 snakescale check_adapter rule
     完全相同的命令（参数从 project.yaml 读取），但改用 `-j 1` 并在管道末尾加 `|| true`
   - 将输出写到 `adapter_check_output/<GSE>/<SRR>_cutadapt_stats.tsv`（与 snakescale 期望路径一致）
   - 验证产出 TSV 是否有效（≥2 行），无效则写入 stub

2. **修改 run_p5_batch.sh**（1 task）
   - 在 snakemake 前调用 prepare_adapter_stats.py，提前填充所有 Ribo-Seq TSV

3. **验证**（2 task：GSE100007 + GSE123018 各 1 次）

4. **edge case 处理**（2 task）
   - 文件小于 4M 行时 head 不会触发 pipe break，需检测
   - cutadapt 版本兼容性（已知 snakemake-ribo 环境版本）

### 阻断风险

- **参数提取复杂**：project.yaml 里的 clip_arguments 需正确解析转换为
  cutadapt check_adapter 参数（不完全一样，check_adapter 用 -u/--maximum-length 而非 -a）
- **性能**：大文件（6 GB）-j 1 比 -j 0 慢，但 head -n 4000000 已限制读取量；
  实测应在 60s 内完成
- **无污染**：TSV 内容是真实 QC 数据，classify_studies 行为与正常流程一致

### 预期完成
约 8 个 task（新建 1 脚本 + 修改 1 脚本 + 验证 2 study + edge cases）

---

## 对比表

| 维度 | 路径 A（stub） | 路径 B（真实 adapter） |
|------|--------------|----------------------|
| 实现复杂度 | 低（改 1 文件） | 中（新建 1 脚本）|
| 数据质量 | 低（w/adapters=0 不真实） | 高（真实 hit rate）|
| TE 数值可信 | 否（adapter 推断可能错） | 是 |
| 阻断风险 | classify 仍可能 invalid | 参数解析复杂 |
| 预期 task 数 | ~4 | ~8 |
| 推荐场景 | 快速验证 pipeline 跑通 | 正式分析数据 |

**推荐**：若本 P5 目标是验证所有 study 能跑通 pipeline，用路径 A；
若目标是产出可用于 TE 分析的 .ribo 文件，用路径 B。
