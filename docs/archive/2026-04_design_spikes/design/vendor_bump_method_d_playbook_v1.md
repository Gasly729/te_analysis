# Vendor Bump Method d Playbook v1

> 本文档只做预演。**未获用户对路径 d 的明确 sign-off 前，不执行以下任何 fork / bump / push 操作。**

## 1. Fork 创建

上游仓库：

- `https://github.com/RiboBase/snakescale`

用户 fork 目标占位符：

- `https://github.com/<YOUR_GITHUB_USERNAME>/snakescale`

CLI 方案：

```bash
gh repo fork RiboBase/snakescale --clone=false --remote=false
```

Web UI 方案：

1. 打开 `https://github.com/RiboBase/snakescale`
2. 点击右上角 `Fork`
3. 记录你的 fork URL：`https://github.com/<YOUR_GITHUB_USERNAME>/snakescale`

## 2. 本地 patch + 提交 fork

```bash
rm -rf /tmp/snakescale_fork
git clone https://github.com/<YOUR_GITHUB_USERNAME>/snakescale /tmp/snakescale_fork
cd /tmp/snakescale_fork
git checkout -b fix/riboflow-task-cpus-for-te-analysis
git apply /tmp/upstream_pr_riboflow_task_cpus.patch
git commit -am "fix(riboflow): groovy interpolation 15x (vendored for te_analysis)"
git push origin fix/riboflow-task-cpus-for-te-analysis
NEW_SHA=$(git rev-parse HEAD)
echo "$NEW_SHA"
```

## 3. 本仓 vendor bump

`.gitmodules` 当前上游 URL：

- `https://github.com/RiboBase/snakescale`

路径 d 下要改成：

- `https://github.com/<YOUR_GITHUB_USERNAME>/snakescale`

本仓操作顺序：

```bash
cd /home/xrx/my_project/te_analysis

# edit .gitmodules
# [submodule "vendor/snakescale"]
#   path = vendor/snakescale
#   url = https://github.com/<YOUR_GITHUB_USERNAME>/snakescale

git submodule sync vendor/snakescale
git -C vendor/snakescale fetch origin fix/riboflow-task-cpus-for-te-analysis
git -C vendor/snakescale checkout "$NEW_SHA"
git add .gitmodules vendor/snakescale
git commit -m "vendor(bump): swap snakescale to fork — #8 groovy typo fix"
```

## 4. bump 后验证

```bash
cd /home/xrx/my_project/te_analysis
git submodule status
grep -nF -- '-@ {task.cpus}' vendor/snakescale/riboflow/RiboFlow.groovy
grep -nF -- '-@ ${task.cpus}' vendor/snakescale/riboflow/RiboFlow.groovy
source ~/miniconda3/etc/profile.d/conda.sh
conda activate te_analysis
PYTHONPATH=src python -m pytest tests/ -v
```

期望：

- `vendor/snakescale` SHA = `$NEW_SHA`
- 第一条 `grep` 无输出
- 第二条 `grep` 返回 15 行
- `pytest` 仍为 `42 passed`

## 5. T8 真跑前置（Method F）

```bash
cd /home/xrx/my_project/te_analysis
mkdir -p vendor/snakescale/staged_fastq
ln -s ../../data/interim/snakescale/GSE132441/staged_fastq/GSE132441 vendor/snakescale/staged_fastq/GSE132441

find data/interim/snakescale/GSE132441/staged_fastq -name '*_1.fastq.gz' | while read gz; do
  fastq="${gz%.gz}"
  touch -d '1 hour ago' "$fastq"
  touch -h "$gz"
done
```

## 6. T8 真跑

```bash
cd /home/xrx/my_project/te_analysis/vendor/snakescale
snakemake -p --cores 32 --config studies="['GSE132441']" override=True 2>&1 | tee /tmp/t8_real_run.log
```

## 7. 预期产物

```bash
ls -lh /home/xrx/my_project/te_analysis/vendor/snakescale/output/GSE132441/ribo/experiments
```

应至少看到：

- `GSM3863556.ribo`
- `GSM3863558.ribo`
- `GSM3863561.ribo`

并满足：

- 3 个文件都存在
- size > 0

## 8. 回滚预案

若 vendor bump 后任一步失败，停止并汇报，不自动继续。

回滚本仓：

```bash
cd /home/xrx/my_project/te_analysis
git reset --hard HEAD~1
git submodule sync vendor/snakescale
git -C vendor/snakescale checkout b918e75f877262dca96665d18c3b472675f30a6d
```

说明：

- 这只回滚本仓 submodule pointer 和 `.gitmodules`
- **不** 回滚已经 push 到 fork 的 commit
- 若失败发生在 T8 真跑阶段，应先保留 `/tmp/t8_real_run.log` 再决定下一步
