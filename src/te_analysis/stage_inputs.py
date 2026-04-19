"""metadata.csv -> snakescale-native project.yaml + staged FASTQ symlinks.

TODO(T4): Implement per te_analysis_module_contracts_v1.md §M1.
Hard limits:
- <= 250 lines single file
- MUST NOT validate FASTQ integrity (snakescale will)
- MUST NOT emit any _*.tsv audit files
- MUST NOT guess project.yaml fields — raise on missing schema info
- MUST be idempotent (repeat runs produce byte-identical output)
"""
