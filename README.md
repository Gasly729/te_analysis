# ccds-translation-efficiency

CCDS wrapper over [RiboBase/snakescale](https://github.com/RiboBase/snakescale)
and [CenikLab/TE_model](https://github.com/CenikLab/TE_model).

## Quickstart
```bash
make env
make submodules
make all STUDY=<GSE_ID>
```

## Design
Architecture, module contracts, and task breakdown live outside this repo in:
- te_analysis_top_level_design_v1.md
- te_analysis_module_contracts_v1.md
- te_analysis_sprint_plan_v1.md
