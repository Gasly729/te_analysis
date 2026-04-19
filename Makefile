# te_analysis unified entry
# Target contract: te_analysis_module_contracts_v1.md §M5.
# All business targets `@false` until their task (T4/T5/T6) is done.

STUDY ?=

.PHONY: help env submodules stage upstream downstream all clean

help:
	@echo "make env                     # create conda env"
	@echo "make submodules              # init vendor/ submodules"
	@echo "make stage      STUDY=<GSE>  # TODO(T4)"
	@echo "make upstream   STUDY=<GSE>  # TODO(T5) depends on stage"
	@echo "make downstream STUDY=<GSE>  # TODO(T6) depends on upstream"
	@echo "make all        STUDY=<GSE>  # alias for downstream"
	@echo "make clean      STUDY=<GSE>  # remove interim/processed for STUDY"

env:
	conda env create -f environment.yml

submodules:
	git submodule update --init --recursive

stage:
	@echo "TODO(T4): stage_inputs not implemented yet" >&2
	@false

upstream: stage
	@echo "TODO(T5): run_upstream not implemented yet" >&2
	@false

downstream: upstream
	@echo "TODO(T6): run_downstream not implemented yet" >&2
	@false

all: downstream

clean:
	@echo "TODO(T7): clean STUDY=$(STUDY) not implemented yet" >&2
	@false
