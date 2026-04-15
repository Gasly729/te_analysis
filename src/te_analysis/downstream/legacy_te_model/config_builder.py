from __future__ import annotations

import json

from .contracts import ExecutionMode, LegacyTeModelContractError


def build_trial_config(*, run_id: str, execution_mode: ExecutionMode, experiment_aliases: list[str]) -> str:
    aliases_literal = json.dumps(experiment_aliases)
    if execution_mode is ExecutionMode.LEGACY_DEFAULT_COUNTS:
        return "\n".join(
            (
                "from src.ribo_counts_to_csv import main",
                "import os",
                "",
                "workdir = os.path.dirname(os.path.realpath(__file__))",
                "sample_filter = lambda df: df",
                "ribo_dedup = False",
                "rna_seq_dedup = True",
                f"custom_experiment_list = {aliases_literal}",
                "",
                "if __name__ == \"__main__\":",
                "    main(",
                "        workdir,",
                "        sample_filter,",
                "        ribo_dedup,",
                "        rna_seq_dedup,",
                "        custom_experiment_list=custom_experiment_list,",
                "    )",
                "",
            )
        )

    if execution_mode is ExecutionMode.LEGACY_WINSORIZED_COUNTS:
        return "\n".join(
            (
                "from src.ribo_counts_to_csv import main",
                "from src.utils import get_cds_range_lookup, cap_outliers_cds_only",
                "import os",
                "",
                "workdir = os.path.dirname(os.path.realpath(__file__))",
                "sample_filter = lambda df: df",
                "ribo_dedup = False",
                "rna_seq_dedup = True",
                f"custom_experiment_list = {aliases_literal}",
                "",
                "def process_coverage_fn(coverage, gene, ribo):",
                "    boundary_lookup = get_cds_range_lookup(ribo)",
                "    return cap_outliers_cds_only(coverage, gene, boundary_lookup, 99.5).sum()",
                "",
                "if __name__ == \"__main__\":",
                "    main(",
                "        workdir,",
                "        sample_filter,",
                "        ribo_dedup,",
                "        rna_seq_dedup,",
                "        process_coverage_fn,",
                "        custom_experiment_list=custom_experiment_list,",
                "    )",
                "",
            )
        )

    raise LegacyTeModelContractError(
        "unsupported-execution-mode",
        f"Unsupported execution mode: {execution_mode}",
    )
