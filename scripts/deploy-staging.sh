#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${STAGING_DEPLOY_COMMAND:-}" ]]; then
  echo "STAGING_DEPLOY_COMMAND is not set."
  echo "Configure repository secret STAGING_DEPLOY_COMMAND with your staging deploy command."
  exit 1
fi

echo "Running staging deployment command..."
bash -lc "${STAGING_DEPLOY_COMMAND}"
echo "Staging deployment completed."
