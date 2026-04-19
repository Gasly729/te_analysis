"""Thin wrapper: invoke vendor/TE_model/TE.R + transpose_TE.py.

TODO(T6): Implement per te_analysis_module_contracts_v1.md §M3.
Hard limits:
- <= 80 lines
- MUST NOT reimplement any TE.R math
- MUST NOT post-process (normalization, CLR, etc.) in Python
- artifacts copied to data/processed/te/<STUDY>/
"""
