# Upstream Input Contract for Production FASTQ Consumption

## Purpose

This document locks the upstream production input contract for the rebuilt TE-only pipeline.

The default production path consumes externally prepared FASTQ files that have already been staged locally. Production runs do not acquire sequencing data over the network.

## Authoritative FASTQ Staging Directory

The authoritative raw FASTQ input directory is:

`/home/xrx/my_project/te_analysis/data/raw/fastq/`

Rules:

- `data/raw/` is a container directory.
- `data/raw/fastq/` is the canonical FASTQ staging directory.
- Future production manifests and preflight checks must resolve FASTQ inputs against this canonical local staging location.

## Production Input Rule

Production runs consume externally prepared FASTQ files only.

This means:

- acquisition happens outside the production pipeline
- staging happens locally before the pipeline is invoked
- the pipeline only validates and consumes locally present FASTQ files

## External Acquisition vs Local Staging vs Pipeline Consumption

### External acquisition

External acquisition is any action that obtains sequencing inputs from outside this repository, including downloaders, shared storage export, or operator-managed transfer.

This is outside the default production path.

### Local staging

Local staging places the prepared FASTQ files under:

`/home/xrx/my_project/te_analysis/data/raw/fastq/`

This step must complete before production validation begins.

### Pipeline consumption

Pipeline consumption starts only after local FASTQ presence can be validated against the study manifest and pairing contract.

The pipeline consumes local files only. It does not fetch missing inputs.

## Downloader Policy

Downloader-driven acquisition is disabled in the default production path.

Rules:

- downloader behavior must remain disabled by default
- missing FASTQ files must cause validation failure
- missing FASTQ files must not trigger downloader fallback
- no future production shortcut may convert a local-file validation failure into a network acquisition attempt

## Validation Rule

Future `te_analysis/upstream/preflight.py` and manifest validation must check:

- local file presence
- local path resolution under the canonical FASTQ root
- study-level consistency between declared inputs and staged files

They must not:

- discover alternate download locations
- auto-fetch missing FASTQ files
- rewrite the production input contract around downloader availability
