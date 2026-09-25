#!/usr/bin/env bash
# Builds the in-browser notebook runtime into apps/web/public/jupyterlite (about 19 MB, not committed).
set -euo pipefail
cd "$(dirname "$0")/.."
OUT="apps/web/public/jupyterlite"
TMP="$(mktemp -d)"
cat > "$TMP/jupyter_lite_config.json" <<'JSON'
{ "LiteBuildConfig": { "apps": ["lab", "repl"], "no_sourcemaps": true } }
JSON
# exposeAppInBrowser lets the playground page save and open generated notebooks through the runtime's own API.
cat > "$TMP/jupyter-lite.json" <<'JSON'
{ "jupyter-config-data": { "exposeAppInBrowser": true, "appName": "Playground notebooks" } }
JSON
( cd "$TMP" && uvx --with jupyterlite-pyodide-kernel --from jupyterlite-core jupyter lite build --output-dir "$OLDPWD/$OUT" )
echo "built $OUT"
