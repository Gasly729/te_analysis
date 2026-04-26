# T2 — cutadapt pipe 竞争取证

**日期**：2026-04-21

## 失败 study：GSE100007, GSE123018

失败的 snakemake 命令（从 log 抄录）：

```
zcat input/fastq/GSE100007/GSM2667793/SRR5680919_1.fastq.gz \
  | head -n 4000000 \
  | tail -n 100000 \
  | cutadapt -j 0 -o /dev/null -u 5 -l 40 --quality-cutoff=28 --report=minimal - \
  > adapter_check_output/GSE100007/SRR5680919_cutadapt_stats.tsv 2> /dev/null
```

## 手动复跑结果

### 测试 A：失败 study SRR5680919（6.0 GB），`-j 0`

```
PIPESTATUS: zcat=141 head=141 tail=2 cutadapt=1
stdout (写入 .tsv): ERROR: Traceback (most recent call last):
  File ".../cutadapt/pipeline.py", line 407, in reader_process
    ...
  raise UnknownFileType('Input file format unknown')
cutadapt.seqio.UnknownFileType: Input file format unknown
```

**exit=1，stdout 被 traceback 污染（tsv 内容无效）**

### 测试 B：失败 study SRR5680919，`-j 1`

```
PIPESTATUS: zcat=141 head=141 tail=2 cutadapt=0
stdout: (空 —— cutadapt 退出前 pipe 已关闭，minimal report 丢失)
```

**exit=0，但 tsv 为空（0 字节），下游 check_adapter_stats 仍会 EmptyDataError**

> 注：`-j 1` 避免了 UnknownFileType，但输出文件为空。
> 空文件可被 `prepare_rna_stub.py` 的 overwrite 逻辑处理，
> 但 `check_adapter_stats` 必须在 stub 已在位才行。

### 测试 C：成功 study SRR966473（GSE50597，3.2 GB），`-j 0`

```
PIPESTATUS: all=0
stdout (valid TSV):
  status  in_reads  in_bp    too_short  too_long  too_many_n  out_reads  w/adapters  qualtrim_bp  out_bp
  OK      25000     1275000  1458       22661      0           881        0           165755       28595
```

**exit=0，TSV 有效**

## 根因分析

`cutadapt -j 0` 使用多进程，reader_process 在子进程中运行。
当 `tail` 输出 100000 行完毕后关闭 pipe，`zcat` 和 `head` 收到 SIGPIPE（exit 141）。
在管道关闭瞬间，cutadapt 的 reader_process 可能已经读取了部分数据块，
下一次读取时遇到关闭的 pipe 返回空数据，cutadapt 将其判断为非 FASTQ 格式，
抛出 `UnknownFileType`。

成功 study（GSE50597，3.2 GB）未触发此问题，原因是：
- 文件较小，`head -n 4000000` 可能读完全文就退出，pipe 关闭时 cutadapt 已完成读取
- 或者 timing 上恰好 reader_process 在 pipe 关闭前已读完所有块

这是**文件大小依赖的竞争条件（race condition）**，不是 study 特异性 bug。
GSE100007（6 GB/sample）和 GSE123018（大样本）均触发，小文件 study 不触发。

## 结论："可否全局改 -j 1"

**不能直接改 -j 1 解决问题**：`-j 1` 避免了 UnknownFileType，但 Ribo-Seq 样本
在 `-j 1` 下输出也可能为空（同样 pipe 竞争），需要额外验证。

**正确修复方向**（不在本任务范围）：
1. 将 `zcat | head | tail` 替换为 `zcat | head --lines=+X | tail`，或先写到临时文件
2. 或：对 Ribo-Seq 样本，在 check_adapter rule 前加 `set +o pipefail`，用 OR `|| true`
3. 或：更换为 `seqtk sample` 随机采样，避免 head/tail pipe 竞争

**当前可行 workaround**（不改 vendor 代码）：
- 在批次脚本里，对已知大文件 study，先手动运行 check_adapter 并捕获失败，
  用 `-j 1` 重试；若仍为空则注入 stub（与 RNA-Seq 一样处理）。
