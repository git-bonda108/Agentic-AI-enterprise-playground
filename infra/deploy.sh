#!/usr/bin/env bash
# Deploys the Enterprise AI Playground to Azure in four steps: resource group, registry and images, infrastructure, smoke test.
# Usage:  PG_PASSWORD=... PLAYGROUND_INTERNAL_KEY=... AUTH_SECRET=... ANTHROPIC_API_KEY=... infra/deploy.sh <resource-group> <location> [prefix] [tag]
# Requires: az CLI signed in (az login). Images are built by `az acr build` in the cloud, so no local Docker is needed.
set -euo pipefail

RG="${1:?resource group}"
LOCATION="${2:-westeurope}"
PREFIX="${3:-aiplay}"
TAG="${4:-$(git rev-parse --short HEAD 2>/dev/null || echo latest)}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

: "${PG_PASSWORD:?set PG_PASSWORD}"
: "${PLAYGROUND_INTERNAL_KEY:?set PLAYGROUND_INTERNAL_KEY}"
: "${AUTH_SECRET:?set AUTH_SECRET}"

echo "1/4 resource group $RG in $LOCATION"
az group create --name "$RG" --location "$LOCATION" --output none

echo "2/4 registry and images (built in Azure)"
ACR_NAME=$(az acr list --resource-group "$RG" --query "[?starts_with(name, '${PREFIX}acr')].name | [0]" -o tsv)
if [[ -z "$ACR_NAME" ]]; then
  # First run: create the registry with a deterministic name the template will adopt (same prefix, same resource group hash).
  ACR_NAME="${PREFIX}acr$(az group show --name "$RG" --query id -o tsv | shasum | cut -c1-13)"
  az acr create --resource-group "$RG" --name "$ACR_NAME" --sku Basic --admin-enabled true --output none
fi
LOGIN_SERVER=$(az acr show --name "$ACR_NAME" --query loginServer -o tsv)
( cd "$ROOT" && npm run build:jupyterlite >/dev/null )
az acr build --registry "$ACR_NAME" --image "playground-api:$TAG" --file "$ROOT/apps/api/Dockerfile" "$ROOT/apps/api" --output none
az acr build --registry "$ACR_NAME" --image "playground-web:$TAG" --file "$ROOT/apps/web/Dockerfile" "$ROOT" --output none

echo "3/4 infrastructure"
az deployment group create \
  --resource-group "$RG" \
  --template-file "$ROOT/infra/bicep/main.bicep" \
  --parameters prefix="$PREFIX" \
               apiImage="$LOGIN_SERVER/playground-api:$TAG" \
               webImage="$LOGIN_SERVER/playground-web:$TAG" \
               postgresPassword="$PG_PASSWORD" \
               internalKey="$PLAYGROUND_INTERNAL_KEY" \
               authSecret="$AUTH_SECRET" \
               anthropicApiKey="${ANTHROPIC_API_KEY:-}" \
               openaiApiKey="${OPENAI_API_KEY:-}" \
               geminiApiKey="${GEMINI_API_KEY:-}" \
               deepseekApiKey="${DEEPSEEK_API_KEY:-}" \
               entraClientId="${AUTH_MICROSOFT_ENTRA_ID_ID:-}" \
               entraClientSecret="${AUTH_MICROSOFT_ENTRA_ID_SECRET:-}" \
               entraIssuer="${AUTH_MICROSOFT_ENTRA_ID_ISSUER:-}" \
  --query "properties.outputs" -o json > "$ROOT/infra/last-deployment.json"

WEB_URL=$(python3 -c "import json; print(json.load(open('$ROOT/infra/last-deployment.json'))['webUrl']['value'])")

echo "4/4 smoke test"
for _ in $(seq 1 30); do
  if curl -fsS "$WEB_URL/api/health" >/dev/null 2>&1; then echo "web is up: $WEB_URL"; exit 0; fi
  sleep 10
done
echo "web did not answer within five minutes; check: az containerapp logs show -n ${PREFIX}-web -g $RG --follow" >&2
exit 1
