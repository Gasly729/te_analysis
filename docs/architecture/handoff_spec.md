# Handoff Specification

## Primary handoff definition

The formal handoff between upstream and downstream is:

- a study-scoped experiment-level `.ribo` collection
- an optional study-scoped aggregate `all.ribo`
- required sidecar references needed to make downstream TE execution reproducible

## Canonical handoff shape

```text
handoff/
  <study_id>/
    ribo/
      experiments/
        <experiment_id>.ribo
      all.ribo                # optional aggregate artifact
    manifests/
      handoff_manifest.yaml   # future local wrapper artifact
    tables/
      pairing_reference.*
      sample_selection.*
      nonpolyA_reference.*
      infor_filter.*
```

## Required contract statements

1. Experiment-level `.ribo` files are the main downstream input object.
2. `all.ribo` may exist, but downstream must not be designed around it as the only input.
3. Downstream contracts may require extra tables or config references in addition to `.ribo`.
4. Handoff validation must check the presence of both primary `.ribo` artifacts and declared sidecars.

## Required sidecar categories

The local wrapper layer must support sidecar categories for:

- study manifest ownership: identify the study/run context that produced the handoff
- pairing references: support ribo/RNA sample pairing provenance
- sample selection tables: control downstream inclusion and exclusion scope
- non-polyA support tables: support gene exclusion semantics before TE regression
- info/filter support tables: support downstream grouping and aggregation semantics
- downstream run configuration: declare downstream behavioral context without legacy trial-path dependence

The exact file formats are intentionally deferred until logic migration begins.

## Handoff validity rules

A handoff is only valid if:

- at least one experiment-level `.ribo` artifact exists for the study
- the handoff manifest is present or explicitly declared as a required future artifact during transition
- declared sidecars are resolvable from the active local wrapper configuration
- validation fails closed if required sidecars are missing
- `all.ribo` alone is never sufficient to declare a valid downstream handoff

## Sidecar scope and ownership

Sidecars may exist at two scopes:

- study-scoped sidecars: bound to a single study or run and required to interpret that study's downstream context
- pipeline-global/shared sidecars: reusable references shared across studies, as long as they are declared explicitly rather than inferred from legacy relative paths

Examples:

- pairing references are typically study-scoped because pairing provenance is tied to a concrete study/run
- sample selection tables are often study-scoped because inclusion/exclusion rules are run-specific
- non-polyA references may be study-scoped or shared, depending on how the local wrapper declares them
- info/filter support tables may be study-scoped when they control downstream grouping for a particular run
- downstream run configuration is study-scoped even when it references shared global defaults

## Manifest minimum schema

The future handoff manifest should minimally enumerate:

- `study_id`
- `experiment_ids`
- `experiment_ribo_paths`
- optional `all_ribo_path`
- declared sidecar references
- validation status

This is a contract target only. It does not claim the manifest implementation already exists.

## What this contract prevents

This handoff contract is designed to prevent:

- implicit dependency on raw relative paths inside `raw_motheds/`
- treating `all.ribo` as a sufficient downstream API by itself
- silent omission of required downstream support tables
- tight coupling between the new architecture and legacy trial directory conventions
