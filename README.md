# ccds-translation-efficiency

CCDS wrapper over [RiboBase/snakescale](https://github.com/RiboBase/snakescale)
and [CenikLab/TE_model](https://github.com/CenikLab/TE_model).

## Quickstart
```bash
make env
make submodules
make all STUDY=<GSE_ID>
```

## GSE125086 downstream
已有的 snakescale 结果可以直接接到 TE_model 下游：运行 `bash scripts/run_gse125086_downstream.sh`。脚本读取 `vendor/snakescale/output/GSE125086/ribo/`，使用 `snakemake-ribo` 环境里的 Rscript 和 serial fallback 跑完 TE_model Stage 0-3，并写出 `data/processed/te/GSE125086/GSE125086_TE.csv`。

## GSE132441 upstream
默认示例 GSE132441 是 Arabidopsis 的固定 55nt、无 adapter Ribo-Seq 数据；本仓库 staging 会把 Ribo reads 截到 RiboFlow 支持的 40nt，并在 upstream wrapper 中用 `adapter_threshold=0` 跳过 vendor 的 adapter-present 假设。运行 `bash scripts/run_gse132441_upstream.sh`（或 `make upstream-gse132441`）会重新生成 `data/interim/snakescale/GSE132441/project.yaml`，再运行 snakescale，目标产物是 `vendor/snakescale/output/GSE132441/ribo/all.ribo`。

## GSE132441 downstream
已有的 `vendor/snakescale/output/GSE132441/ribo/all.ribo` 可以复用 GSE125086 的 TE_model 下游路径：运行 `bash scripts/run_gse132441_downstream.sh`（或 `make downstream-gse132441`）。`run_downstream` 会把 snakescale output 作为 TE_model runtime ribo 输入，使用 serial fallback 跑 Stage 0-3，并写出 `data/processed/te/GSE132441/GSE132441_TE.csv`。

## Design
Architecture, module contracts, and task breakdown live outside this repo in:
- te_analysis_top_level_design_v1.md
- te_analysis_module_contracts_v1.md
- te_analysis_sprint_plan_v1.md
