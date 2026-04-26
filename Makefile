# te_analysis unified entry (module_contracts §M5).

STUDY     ?= GSE132441
CORES     ?= 4
METADATA  := data/raw/metadata.csv
STUDY_DIR := data/interim/snakescale/$(STUDY)
OUT_DIR   := data/processed/te/$(STUDY)
PY        := PYTHONPATH=src python -m
SNAKEMAKE_CONFIG ?=
SNAKEMAKE_ARGS ?=
SNAKEMAKE_CONFIG_ARGS := $(foreach cfg,$(SNAKEMAKE_CONFIG),--snakemake-config $(cfg))

.PHONY: help env submodules stage upstream upstream-gse132441 downstream downstream-gse132441 all clean

help:
	@echo "make env                     # create conda env (environment.yml)"
	@echo "make submodules              # init vendor/ submodules"
	@echo "make stage      STUDY=<GSE>  # metadata.csv -> project.yaml + symlinks"
	@echo "make upstream   STUDY=<GSE>  # run snakescale (depends on stage)"
	@echo "make upstream-gse132441      # run the GSE132441 upstream wrapper"
	@echo "make downstream STUDY=<GSE>  # run TE_model (depends on upstream)"
	@echo "make downstream-gse132441    # run GSE132441 TE_model downstream"
	@echo "make all        STUDY=<GSE>  # alias for downstream"
	@echo "make clean      STUDY=<GSE>  # remove interim + processed for STUDY"

env:
	conda env create -f environment.yml

submodules:
	git submodule update --init --recursive

stage:
	$(PY) te_analysis.stage_inputs --metadata $(METADATA) --study $(STUDY) --out $(STUDY_DIR)

upstream: stage
	$(PY) te_analysis.run_upstream --study-dir $(STUDY_DIR) --cores $(CORES) $(SNAKEMAKE_CONFIG_ARGS) $(SNAKEMAKE_ARGS)

upstream-gse132441:
	bash scripts/run_gse132441_upstream.sh

downstream: upstream
	$(PY) te_analysis.run_downstream --study-dir $(STUDY_DIR) --out-dir $(OUT_DIR)

downstream-gse132441:
	bash scripts/run_gse132441_downstream.sh

all: downstream

clean:
	rm -rf $(STUDY_DIR) $(OUT_DIR)
