# P5 批次失败尸检汇总

**日期**：2026-04-21
**尸检范围**：2026-04-20 22:09 ~ 2026-04-21 03:01 的批次运行

---

## 执行结果概览

- 计划运行：72 studies
- 实际运行：14 studies（批次在第14个后被终止）
- 成功：10 studies，产出 .ribo 文件
- 失败：4 studies（3 个程序失败 + 1 个被终止未完成）
- 未运行：58 studies

### 已产出 .ribo 文件（5 个，含 P4）

| study | .ribo 大小 | 物种 |
|-------|-----------|------|
| GSE125086 | 34 MB | Homo sapiens |
| GSE50597 | 92 MB | Arabidopsis thaliana |
| GSE109122 | 57 MB | Arabidopsis thaliana |
| GSE65885 | 219 MB | Homo sapiens |
| GSE64962 | (待确认) | Homo sapiens |

其余 4 个成功 study（GSE43703、GSE132441、GSE48140、GSE69602、GSE112705、GSE105082）
的 .ribo 未查到 output 目录，可能在 intermediates/ 或因某种原因未写出，需单独确认。

---

## 失败类型分析

### P0：批次被 SIGHUP 终止（session-cleanup）

**影响**：58 个 study 未运行；GSE123564 的 nextflow 孤儿进程继续运行到 03:01
后因 SIGTERM 自然失败

**根因**：`run_p5_batch.sh` 在非 tmux 的直连 SSH session 中用 `nohup` 启动，
SSH 断线后 bash 父进程收到 SIGHUP 退出（nohup 对 bash 本身保护有限）

**可否重启**：是
**重启前必做**：在 `tmux` 或 `screen` 内启动，确保 session 存活

---

### P1a：cutadapt -j 0 多线程 pipe 竞争（GSE100007、GSE123018）

**影响**：check_adapter rule 失败，pipeline 中止

**根因**：`cutadapt -j 0`（多进程）+ `zcat|head|tail` pipe。
tail 输出完毕关闭 pipe 后，cutadapt reader_process 子进程遇到已关闭的 fd，
抛出 `UnknownFileType` → exit 1。
文件越大（6 GB/sample）越容易触发，小文件 study 不受影响。

**测试结果**：
- `-j 0`：exit=1，stdout 含 Python traceback（TSV 无效）
- `-j 1`：exit=0，但 stdout 为空（TSV 为空文件）
- 成功 study（3.2 GB）用 `-j 0`：exit=0，TSV 有效（timing 幸运）

**可否重启**：是，但需 workaround
**重启前必做**：
- 对 check_adapter 产出为空或无效的 Ribo-Seq SRR，需要 prepare_rna_stub.py
  类似的 stub 注入逻辑（不可改 vendor 代码，在批次脚本里处理）
- 或者：在批次脚本里重试失败 study 时，先手动跑 check_adapter（`-j 1`），
  把空 TSV 替换为 stub，再 `--rerun-incomplete` 继续

---

### P1b：GSE123564 rnaseq_merge_bed exit=143（SIGTERM）

**影响**：rnaseq_merge_bed 6/10 失败，put_rnaseq_into_ribo 1/4 失败，.ribo 未产出

**根因**：不是程序 bug。exit=143 = SIGTERM，由 nextflow 的 `WARN: Killing pending tasks`
机制在父进程死亡后发出。task 本身逻辑（`cat bed | sort`）完全正常，
`rnaseq_merge_bed` 上游所有 10/10 process 均成功完成。

**可否重启**：是，`--rerun-incomplete` 即可
**重启前必做**：无（在 tmux 内重跑即可）

---

### P2：GSE56924 staging gap（2 个 SRR 无 `_1` 后缀）

**影响**：snakescale 触发 download_fastq_files → SSL 证书失败 → pipeline 中止

**根因**：2 个 SRR（SRR1257193、SRR1257250）的磁盘文件名为 `GSM_Type_SRR.fastq.gz`，
无 `_1` 端号后缀，不匹配 `stage_fastq.py` 的 glob pattern（要求 `_1.fastq.gz`）

**文件实际在磁盘**，只需手动补建 2 个 symlink

**可否重启**：是
**重启前必做**：手动建两个 symlink（见 t4_gse56924.md 的修复命令）

---

## 6 个 "SUCCESS 但无 .ribo" study 真相

`batch_master.log` 记录的 SUCCESS = snakemake exit=0，**不等于** .ribo 产出。

| study | riboflow_status | 根因 |
|-------|----------------|------|
| GSE43703 | Study GSE43703 failed. | classify_studies invalid：Ribo adapter hit rate 0% + no guessable adapter |
| GSE132441 | Study GSE132441 failed. | 同上 |
| GSE69602 | Study GSE69602 failed. | 同上（70 Ribo sample 全部 0%） |
| GSE112705 | Study GSE112705 failed. | 同上 |
| GSE105082 | Study GSE105082 failed. | Ribo adapter hit rate 0.5~0.8%（低于阈值）+ no guessable adapter |
| GSE48140 | 未执行 | generate_yaml 报 "More than one organism detected"，study 进入 ERROR_STUDIES_LIST |

**这 6 个 study 不是 pipeline bug，是 QC 过滤和数据问题**（见 t6_missing_ribo.md）。
重启批次时同样会失败，需要额外干预（手动指定 adapter 或修 db）。

---

## 重启决策

**结论：可以重启，必须先做以下 3 项修复**

| 优先级 | 修复项 | 操作 |
|--------|--------|------|
| P0（必须） | 用 tmux/screen 保护 session | 在 tmux 内执行 run_p5_batch.sh |
| P1（必须） | GSE56924 补 2 个 symlink | 手动 ln -s（见 t4）|
| P2（必须） | 大文件 study check_adapter workaround | 批次脚本增加对空 TSV 的 stub 注入逻辑 |

**重启起点**：从 GSE123564 开始（可用 `--rerun-incomplete` 续跑），
然后继续剩余 58 个 study。

**不需修复的问题**：
- GSE123564 的 rnaseq_merge_bed → `--rerun-incomplete` 自动重跑
- rnaseq_merge_bed 无新 bug → [confirmed, not unrecoverable]
