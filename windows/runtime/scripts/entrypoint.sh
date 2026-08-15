#!/usr/bin/env bash
set -euo pipefail
mkdir -p "${VE_RUNTIME:-/workspace}/models" "${VE_RUNTIME:-/workspace}/runs" "${VE_RUNTIME:-/workspace}/exchange/inbox" "${VE_RUNTIME:-/workspace}/exchange/outbox"
if [[ -f "${VE_RUNTIME:-/workspace}/.Renviron" ]]; then
  sed -i 's/;/:/g' "${VE_RUNTIME:-/workspace}/.Renviron"
fi
exec Rscript --vanilla /opt/visioneval/ve-cli.R "$@"
