# T1 — nohup 被 kill 原因取证

**日期**：2026-04-21  
**结论**：**session-cleanup（SIGHUP）**

## 证据

### 时间线
| 时间 | 事件 |
|------|------|
| 2026-04-20 22:09 | `run_p5_batch.sh` 启动，`nohup` 后台执行 |
| 2026-04-21 01:01:48 | `batch_master.log` 最后写入（GSE123564 启动行） |
| 2026-04-21 03:01:51 | `GSE123564.log` 最后写入（nextflow 失败退出） |

### 关键观察
1. **OOM 否定**：`dmesg` 无任何 `oom-kill` 或 `memory pressure` 记录。  
2. **bash 父进程 vs nextflow 子进程时间差**：`batch_master.log` 在 01:01 停写，但 `GSE123564.log`（由 nextflow 子进程直接写）持续到 03:01。说明 **bash 脚本本身在 01:01 被终止**，但 nextflow 作为孤儿进程继续运行直到自然失败。  
3. **xrx 的 last 记录**：xrx 用户最近的 pts session 是 `Apr 19 15:04 - 10:17`，在批次启动之前已离线。批次在 xrx 的 shell 中以直连 SSH 方式启动（非 tmux），session 超时或 SSH 断线导致 SIGHUP。  
4. **nohup 的局限**：`nohup` 使进程忽略 SIGHUP，但若启动 nohup 的 shell 本身未用 `disown`，某些系统在 SSH 断线时仍会向整个 process group 发 SIGHUP。bash 脚本（`run_p5_batch.sh`）收到 SIGHUP 退出；nextflow 子进程因有独立进程组而幸存。

### OOM 否定证据
```
dmesg | grep -iE "oom|killed|memory" → (无输出)
```

## 结论

**session-cleanup（非 OOM，非外部 kill）**

- bash 脚本 `run_p5_batch.sh` 在 GSE123564 启动后被 SIGHUP 终止  
- nextflow 子进程孤儿化，继续运行到 03:01 因 SIGTERM（143）终止各 task  
- 剩余 58 个 study（GSE123564 之后）**未运行**

## 修复建议（不在本任务范围）

重启批次时必须用 `tmux` 或 `screen` 包裹，保证 session 存活。
