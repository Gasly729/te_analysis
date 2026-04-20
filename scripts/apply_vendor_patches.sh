#!/usr/bin/env bash

set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
PATCH_DIR="$ROOT/patches/snakescale"

mapfile -t riboflow_paths < <(git -C "$ROOT/vendor/snakescale" ls-files 'riboflow/RiboFlow.groovy')
if [[ ${#riboflow_paths[@]} -ne 1 ]]; then
  echo "Expected exactly one tracked RiboFlow.groovy, got ${#riboflow_paths[@]}" >&2
  printf '%s\n' "${riboflow_paths[@]}" >&2
  exit 1
fi

RIBOFLOW_REL="${riboflow_paths[0]}"
RIBOFLOW_FILE="$ROOT/vendor/snakescale/$RIBOFLOW_REL"

if [[ ! -f "$RIBOFLOW_FILE" ]]; then
  echo "Resolved RiboFlow path does not exist: $RIBOFLOW_FILE" >&2
  exit 1
fi

count_bad_pattern() {
  BAD_COUNT="$(
    grep -F -- '-@ {task.cpus}' "$ROOT/vendor/snakescale/$RIBOFLOW_REL" | wc -l || true
  )"
  printf '%s\n' "$BAD_COUNT"
}

count_patched_pattern() {
  PATCHED_COUNT="$(
    grep -E -- 'samtools (index|idxstats) -@ \$\{task\.cpus\}' \
      "$ROOT/vendor/snakescale/$RIBOFLOW_REL" | wc -l || true
  )"
  printf '%s\n' "$PATCHED_COUNT"
}

is_already_applied() {
  local bad_count
  local patched_count
  bad_count="$(count_bad_pattern)"
  patched_count="$(count_patched_pattern)"
  [[ "$bad_count" -eq 0 && "$patched_count" -eq 15 ]]
}

shopt -s nullglob
patches=("$PATCH_DIR"/*.patch)
shopt -u nullglob

if [[ ${#patches[@]} -eq 0 ]]; then
  echo "No patch files found under $PATCH_DIR" >&2
  exit 1
fi

for patch_file in "${patches[@]}"; do
  abs_patch_path="$(cd "$(dirname "$patch_file")" && pwd)/$(basename "$patch_file")"

  if git -C "$ROOT/vendor/snakescale" apply --check "$abs_patch_path"; then
    git -C "$ROOT/vendor/snakescale" apply "$abs_patch_path"
    continue
  fi

  if is_already_applied; then
    echo "Patch already applied: $(basename "$abs_patch_path")"
    continue
  fi

  echo "Patch conflict: $(basename "$abs_patch_path")" >&2
  echo "Resolved vendor path: $RIBOFLOW_REL" >&2
  echo "BAD_COUNT=$(count_bad_pattern)" >&2
  echo "PATCHED_COUNT=$(count_patched_pattern)" >&2
  exit 1
done

echo "All vendor patches processed successfully."
