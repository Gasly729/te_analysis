# te_analysis unified entry (module_contracts §M5).

STUDY     ?= GSE132441
CORES     ?= 4
METADATA  := data/raw/metadata.csv
STUDY_DIR := data/interim/snakescale/$(STUDY)
OUT_DIR   := data/processed/te/$(STUDY)
PY        := PYTHONPATH=src python -m

.PHONY: help env submodules stage upstream downstream all clean

help:
	@echo "make env                     # create conda env (environment.yml)"
	@echo "make submodules              # init vendor/ submodules"
	@echo "make stage      STUDY=<GSE>  # metadata.csv -> project.yaml + symlinks"
	@echo "make upstream   STUDY=<GSE>  # run snakescale (depends on stage)"
	@echo "make downstream STUDY=<GSE>  # run TE_model (depends on upstream)"
	@echo "make all        STUDY=<GSE>  # alias for downstream"
	@echo "make clean      STUDY=<GSE>  # remove interim + processed for STUDY"

env:
	conda env create -f environment.yml

submodules:
	git submodule update --init --recursive

stage:
	$(PY) te_analysis.stage_inputs --metadata $(METADATA) --study $(STUDY) --out $(STUDY_DIR)

upstream: stage
	$(PY) te_analysis.run_upstream --study-dir $(STUDY_DIR) --cores $(CORES)

downstream: upstream
	$(PY) te_analysis.run_downstream --study-dir $(STUDY_DIR) --out-dir $(OUT_DIR)

all: downstream

clean:
	rm -rf $(STUDY_DIR) $(OUT_DIR)
