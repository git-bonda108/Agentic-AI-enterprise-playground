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
# The playground helper ships in the runtime's file drive, so `import playground` works in the browser without a fetch.
mkdir -p "$TMP/contents"
cp apps/api/app/notebook_helper.py "$TMP/contents/playground.py"
( cd "$TMP" && uvx --with jupyterlite-pyodide-kernel --with jupyter-server --from jupyterlite-core jupyter lite build --contents contents --output-dir "$OLDPWD/$OUT" )
echo "built $OUT"
