#!/usr/bin/env bash
set -euo pipefail

CACHE_DIR="/home/celeryuser/.cache/huggingface"
SEED_DIR="/seed/hf"
WHISPER_MODEL_ID="mobiuslabsgmbh/faster-whisper-large-v3-turbo"
EMBED_MODEL_ID="BAAI/bge-m3"

mkdir -p "$CACHE_DIR"
rm -rf "$CACHE_DIR/hub/.locks" 2>/dev/null || true

# seed docker volume once (only if empty)
cache_empty=0
cache_incomplete=0

if [ -z "$(ls -A "$CACHE_DIR" 2>/dev/null || true)" ]; then
  cache_empty=1
fi

if find "$CACHE_DIR" -name "*.incomplete" -print -quit 2>/dev/null | grep -q .; then
  cache_incomplete=1
fi

if [ "$cache_empty" -eq 1 ] || [ "$cache_incomplete" -eq 1 ]; then
  echo "hf_cache_init: cache needs init (empty=$cache_empty incomplete=$cache_incomplete)"

  find "$CACHE_DIR" -name "*.incomplete" -delete 2>/dev/null || true

  # copy if repo-local seed exists
  if [ -d "$SEED_DIR" ] && [ -n "$(ls -A "$SEED_DIR" 2>/dev/null || true)" ]; then
    echo "hf_cache_init: seeding cache from $SEED_DIR"
    cp -a "$SEED_DIR"/. "$CACHE_DIR"/
  else
    echo "hf_cache_init: no seed found at $SEED_DIR (will download)"
  fi
else
  echo "hf_cache_init: cache volume already populated and clean"
fi

chown -R celeryuser:celeryuser "$CACHE_DIR"
mkdir -p /home/celeryuser/.EasyOCR/model
chown -R celeryuser:celeryuser /home/celeryuser/.EasyOCR
su -s /bin/bash -c "python /usr/local/bin/ensure_models.py" celeryuser

# backfill repo seed if empty
if [ -d "$SEED_DIR" ] && [ -z "$(ls -A "$SEED_DIR" 2>/dev/null || true)" ]; then
  echo "hf_cache_init: backfilling seed from cache"
  cp -a "$CACHE_DIR"/. "$SEED_DIR"/
fi

# clean up so worker isn't blocked
rm -rf "$CACHE_DIR/hub/.locks" 2>/dev/null || true
