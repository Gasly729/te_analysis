# Reproducibility

TODO(T13): Finalize after T12 with the full 5-step fresh-clone -> TE CSV flow.

## Partial recipe (as of Commit K4)

Assumes a clone has `vendor/` submodules initialized and `data/raw/{organism}/...fastq.gz`
already staged (download is out of T1-T4 scope).

```bash
# 1. Build environment
conda env create -f environment.yml
conda activate te_analysis

# 2. Enrich metadata.csv to run-level (only needed once per repo)
#    (already done for this checkout; see data/raw/metadata.csv.preH2.bak)
# python scripts/enrich_metadata_srr.py
# python scripts/align_fastq_paths.py

# 3. Verify metadata schema
python scripts/verify_t3_metadata.py

# 4. Stage one study (T4)
PYTHONPATH=src python -m te_analysis.stage_inputs \
    --metadata data/raw/metadata.csv \
    --study    GSE132441 \
    --out      data/interim/snakescale/GSE132441

# 5. Run upstream (T5, not yet implemented)
# 6. Run downstream (T6, not yet implemented)
```

Pinned versions: `.gitmodules` locks `vendor/snakescale` @
`b918e75f877262dca96665d18c3b472675f30a6d` and `vendor/TE_model` @
`0b42e3f756e20b9954548b65ff8a64ae063d9a89`.
