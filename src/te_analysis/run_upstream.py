"""Thin wrapper: invoke vendor/snakescale native entry point.

TODO(T5): Implement per te_analysis_module_contracts_v1.md §M2.
Hard limits:
- <= 80 lines
- MUST NOT parse snakescale logs
- MUST NOT retry / schedule / modify snakescale config
- subprocess.run(..., check=False) and passthrough exit code
"""
