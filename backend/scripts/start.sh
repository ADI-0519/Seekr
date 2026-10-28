#!/usr/bin/env bash
set -euo pipefail

# Optional ClearML task containing the production-approved fine-tuned model.
# Set FINETUNE_TASK_ID in the deployment environment; leave it unset to use the base model.
FINETUNE_TASK_ID="${FINETUNE_TASK_ID:-}"

mode="${1:-cpu}"
case "$mode" in
  cpu)
    stack_files=(-f docker-compose.yml -f docker-compose.cpu.yml)
    ;;
  gpu)
    stack_files=(-f docker-compose.yml)
    ;;
  *)
    echo "Usage: $0 [cpu|gpu]" >&2
    exit 2
    ;;
esac

setup_files=("${stack_files[@]}" -f docker-compose.hf.yml)

echo "Selected ${mode^^} mode"

echo "Cleaning local cache artifacts"
mkdir -p ../.cache/hf/hub
rm -rf ../.cache/hf/hub/.locks
rm -rf ../.cache/hf/hub/models--BAAI--bge-m3/.no_exist
find ../.cache/hf -name "*.incomplete" -delete 2>/dev/null || true

echo "Stopping any containers currently running"
docker compose "${setup_files[@]}" down

if ! docker volume inspect huggingface_cache > /dev/null 2>&1; then
  echo "Creating HuggingFace cache volume"
  docker volume create huggingface_cache
else
  echo "HuggingFace cache volume already exists, skipping"
fi

if ! docker volume inspect easyocr_cache > /dev/null 2>&1; then
  echo "Creating EasyOCR cache volume"
  docker volume create easyocr_cache
else
  echo "EasyOCR cache volume already exists, skipping"
fi

echo "Building images"
mkdir -p runs/finetune
docker compose "${setup_files[@]}" build

echo "Initialising model cache"
max_attempts=5
attempt=1
until docker compose -f docker-compose.hf.yml run --rm hf_cache_init; do
  if [ "$attempt" -ge "$max_attempts" ]; then
    echo "Model download failed after $max_attempts attempts, giving up"
    exit 1
  fi
  echo "Model download interrupted (attempt $attempt/$max_attempts), retrying in 10s..."
  attempt=$((attempt + 1))
  sleep 10
done

echo "Starting stack"
if [ -n "${FINETUNE_TASK_ID}" ] && python -c "import clearml; clearml.Task.get_task" 2>/dev/null; then
  echo "Exporting fine-tuned embedding model from ClearML task ${FINETUNE_TASK_ID}..."
  python scripts/export_finetuned_model.py --task-id "${FINETUNE_TASK_ID}" --output-dir runs/finetune || echo "Fine-tuned model export failed, falling back to base model"
fi
docker compose "${stack_files[@]}" up -d

echo "Setup complete"
