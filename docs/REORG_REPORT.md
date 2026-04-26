# docs/ 重组报告

## 已移动文件清单

- `docs/te_analysis_top_level_design_v1.md` → `docs/ARCHITECTURE.md`
- `docs/te_analysis_module_contracts_v1.md` → `docs/CONTRACTS.md`
- `docs/gse132441_stage2_diagnosis_2026-04-26.md` → `docs/diagnostics/gse132441_stage2_diagnosis_2026-04-26.md`
- `docs/chatgpt_handoff_2026-04-20.md` → `docs/archive/2026-04_handoffs/chatgpt_handoff_2026-04-20.md`
- `docs/codex_handoff_2026-04-20_T8_session-O.md` → `docs/archive/2026-04_handoffs/codex_handoff_2026-04-20_T8_session-O.md`
- `docs/p5_study_inventory.tsv` → `docs/archive/2026-04_p5/p5_study_inventory.tsv`
- `docs/sqlite_build_report.md` → `docs/archive/2026-04_p5/sqlite_build_report.md`
- `docs/srr_resolution_design_v2.md` → `docs/archive/2026-04_p5/srr_resolution_design_v2.md`
- `docs/schema_reverse_engineering_report.md` → `docs/archive/2026-04_p5/schema_reverse_engineering_report.md`
- `docs/p5_postmortem` → `docs/archive/2026-04_p5/p5_postmortem`
- `docs/vendor_recon_prior` → `docs/archive/2026-04_p5/vendor_recon_prior`
- `docs/design` → `docs/archive/2026-04_design_spikes/design`
- `docs/arabidopsis_runtime_infor_filter_bridge.md` → `docs/archive/2026-04_design_spikes/arabidopsis_runtime_infor_filter_bridge.md`
- `docs/arabidopsis_second_species_preflight_audit.md` → `docs/archive/2026-04_design_spikes/arabidopsis_second_species_preflight_audit.md`
- `docs/homo_sapiens_species_serial_fallback_audit.md` → `docs/archive/2026-04_design_spikes/homo_sapiens_species_serial_fallback_audit.md`
- `docs/te_analysis_species_te_aggregation_spec.md` → `docs/archive/2026-04_design_spikes/te_analysis_species_te_aggregation_spec.md`
- `docs/te_analysis_species_te_contract_audit.md` → `docs/archive/2026-04_design_spikes/te_analysis_species_te_contract_audit.md`
- `docs/snakescale_contract.md` → `docs/archive/2026-04_design_spikes/snakescale_contract.md`
- `docs/te_model_contract.md` → `docs/archive/2026-04_design_spikes/te_model_contract.md`
- `docs/species_te_result_contract.md` → `docs/archive/2026-04_design_spikes/species_te_result_contract.md`
- `docs/species_downstream_runbook.md` → `docs/archive/2026-04_design_spikes/species_downstream_runbook.md`
- `docs/species_te_chain_runbook.md` → `docs/archive/2026-04_design_spikes/species_te_chain_runbook.md`
- `docs/progress_snapshot.md` → `docs/archive/2026-04_snapshots/progress_snapshot.md`
- `docs/current_project_progress.md` → `docs/archive/2026-04_snapshots/current_project_progress.md`
- `docs/te_analysis_next_phase_master_plan.md` → `docs/archive/2026-04_snapshots/te_analysis_next_phase_master_plan.md`
- `docs/te_analysis_sprint_plan_v1.md` → `docs/archive/2026-04_snapshots/te_analysis_sprint_plan_v1.md`
- `docs/backlog.md` → `docs/archive/2026-04_snapshots/backlog.md`
- `docs/architecture.md` → `docs/archive/2026-04_snapshots/architecture.md`
- `docs/reproducibility.md` → `docs/archive/2026-04_snapshots/reproducibility.md`
- `docs/vendor_sha_recommendation.md` → `docs/archive/2026-04_snapshots/vendor_sha_recommendation.md`

## 已创建占位文件清单

- `docs/README.md`
- `docs/STATUS.md`
- `docs/RUNBOOK.md`
- `docs/VENDOR_POLICY.md`
- `docs/DECISIONS.md`
- `docs/TROUBLESHOOTING.md`

## 未匹配文件（进入 unsorted 桶的）

无。

## 冲突跳过文件

无。

## 当前 docs/ 顶层 ls 结果

```text
ARCHITECTURE.md
CONTRACTS.md
DECISIONS.md
README.md
RUNBOOK.md
STATUS.md
TROUBLESHOOTING.md
VENDOR_POLICY.md
archive
diagnostics
metadata_schema.md
```

## 当前 git 状态

```text
 D docs/arabidopsis_runtime_infor_filter_bridge.md
 D docs/arabidopsis_second_species_preflight_audit.md
 D docs/architecture.md
 D docs/backlog.md
 D docs/codex_handoff_2026-04-20_T8_session-O.md
 D docs/current_project_progress.md
 D docs/design/backlog_8_resolution_plan_v1.md
 D docs/design/classify_studies_risk_v1.md
 D docs/design/contract_testing_gap_v1.md
 D docs/design/method_f_codification_v1.md
 D docs/design/upstream_pr_riboflow_fix_v1.md
 D docs/design/vendor_bump_method_d_playbook_v1.md
 D docs/homo_sapiens_species_serial_fallback_audit.md
 D docs/progress_snapshot.md
 D docs/reproducibility.md
 D docs/schema_reverse_engineering_report.md
 D docs/snakescale_contract.md
 D docs/species_downstream_runbook.md
 D docs/species_te_chain_runbook.md
 D docs/species_te_result_contract.md
 D docs/sqlite_build_report.md
 D docs/srr_resolution_design_v2.md
 D docs/te_analysis_module_contracts_v1.md
 D docs/te_analysis_next_phase_master_plan.md
 D docs/te_analysis_species_te_aggregation_spec.md
 D docs/te_analysis_species_te_contract_audit.md
 D docs/te_analysis_sprint_plan_v1.md
 D docs/te_analysis_top_level_design_v1.md
 D docs/te_model_contract.md
 D docs/vendor_recon_prior/upstream_input_contract.md
 D docs/vendor_sha_recommendation.md
?? docs/ARCHITECTURE.md
?? docs/CONTRACTS.md
?? docs/DECISIONS.md
?? docs/README.md
?? docs/RUNBOOK.md
?? docs/STATUS.md
?? docs/TROUBLESHOOTING.md
?? docs/VENDOR_POLICY.md
?? docs/archive/
?? docs/diagnostics/
```

## 已知遗留

`.git/` 目前只读，本次未做任何 git 索引登记，需用户后续在 `.git/` 可写后用 `git add -A docs/` 补 staging。
