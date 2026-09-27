#!/usr/bin/env bash
# Copies the product guides in docs/ into apps/api/catalog/docs so the API image (Docker context apps/api) ships them.
# The delivery log (BATCHES.md) is internal and stays out. Run through `npm run sync:docs`; the API tests fail on drift.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEST="$ROOT/apps/api/catalog/docs"
mkdir -p "$DEST/images"
find "$DEST" -maxdepth 1 -name '*.md' -delete
for f in "$ROOT"/docs/*.md; do
  name="$(basename "$f")"
  [[ "$name" == "BATCHES.md" ]] && continue
  cp "$f" "$DEST/$name"
done
rm -f "$DEST"/images/*
cp "$ROOT"/docs/images/* "$DEST/images/"
echo "synced $(ls "$DEST"/*.md | wc -l | tr -d ' ') guides and $(ls "$DEST"/images | wc -l | tr -d ' ') images into apps/api/catalog/docs"
