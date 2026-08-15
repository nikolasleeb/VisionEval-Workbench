#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

TARGET_TRIPLE="$(rustc -Vv | awk '/host:/ { print $2 }')"
PYTHON_BIN="${PYTHON:-python3}"
DOCUMENTATION_SOURCE="${WORKBENCH_DOCUMENTATION_SOURCE:-docs/user-intel}"
COMPARISON_MAP_3D="${WORKBENCH_COMPARISON_MAP_3D:-enabled}"

"$PYTHON_BIN" packaging/build_backend.py \
  --comparison-map-3d "$COMPARISON_MAP_3D" \
  --documentation-source "$DOCUMENTATION_SOURCE" \
  --target-triple "$TARGET_TRIPLE"
