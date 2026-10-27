from __future__ import annotations

import argparse
import json
import logging
import os
import random
import re
import shutil
import sys
from pathlib import Path

import torch
import torch.nn.functional as F
from app.finetune.dataset import (
    ChunkMeta,
    load_triplets_jsonl,
    materialize_triplets_structured,
)
from app.finetune.eval import evaluate_retrieval
from sentence_transformers import InputExample, SentenceTransformer
from torch.optim.lr_scheduler import CosineAnnealingLR, LinearLR, SequentialLR
from tqdm import tqdm

log = logging.getLogger(__name__)
try:
    from clearml import Task as ClearMLTask

    _CLEARML_OK = True
except ImportError:
    _CLEARML_OK = False

BASE_MODEL = "BAAI/bge-m3"
_SCALE = 20.0

_LECTURE_RE = re.compile(r"\[LECTURE:\s*([^\]]+)\]")


def _encode(model, texts, device):
    features = model.tokenize(texts)
    features = {
        k: v.to(device).to(torch.bfloat16) if v.is_floating_point() else v.to(device)
        for k, v in features.items()
    }
    return model(features)["sentence_embedding"]


def _mnrl_loss(q_emb, p_emb, n_emb, scale=_SCALE):
    # queries match their positive at same index, everything else is a negative
    q = F.normalize(q_emb, p=2, dim=-1)
    p = F.normalize(p_emb, p=2, dim=-1)
    n = F.normalize(n_emb, p=2, dim=-1)
    docs = torch.cat([p, n], dim=0)
    sim = scale * torch.mm(q, docs.T)
    labels = torch.arange(q.shape[0], device=q.device)
    return F.cross_entropy(sim, labels)


def _lecture_key(text: str) -> str:
    m = _LECTURE_RE.search(text)
    return m.group(1) if m else ""


def _diversify_batches(
    examples: list[InputExample], batch_size: int, rng: random.Random
) -> list[InputExample]:
    # group by lecture -> each batch spans multiple lectures (reduces in-batch near duplicate false negatives)
    by_lecture: dict[str, list[InputExample]] = {}
    for ex in examples:
        key = _lecture_key(ex.texts[1])
        by_lecture.setdefault(key, []).append(ex)

    # shuffle within each group
    groups = list(by_lecture.values())
    for g in groups:
        rng.shuffle(g)
    rng.shuffle(groups)

    # round-robin interleave so consecutive examples are from different lectures
    interleaved: list[InputExample] = []
    while any(groups):
        for g in groups:
            if g:
                interleaved.append(g.pop())
        groups = [g for g in groups if g]

    return interleaved


def check_metrics(model, check_examples, device, full_corpus_texts: list[str] | None = None):
    # eval against a large corpus rather than just check positives
    model.eval()

    unique_positives = list(dict.fromkeys(ex.texts[1] for ex in check_examples))

    corpus = full_corpus_texts if full_corpus_texts else unique_positives

    # one representative query per unique positive (first one encountered per positive)
    pos_to_query: dict[str, str] = {}
    for ex in check_examples:
        pos = ex.texts[1]
        if pos not in pos_to_query:
            pos_to_query[pos] = ex.texts[0]

    eval_queries = list(pos_to_query.values())
    eval_positives = list(pos_to_query.keys())

    positive_indices = [corpus.index(p) if p in corpus else -1 for p in eval_positives]

    # drop any positives not found in corpus (shouldn't happen but guard anyway)
    pairs = [(q, i) for q, i in zip(eval_queries, positive_indices) if i >= 0]
    if not pairs:
        log.warning("check_metrics: no positives found in corpus, skipping eval")
        model.train()
        from app.finetune.eval import RetrievalMetrics

        return RetrievalMetrics(hit_at_1=0.0, hit_at_5=0.0, hit_at_10=0.0, mrr=0.0)

    eval_queries_f, pos_indices_f = zip(*pairs)

    with torch.no_grad():
        q_vecs = model.encode(list(eval_queries_f), batch_size=32, convert_to_numpy=True)
        c_vecs = model.encode(corpus, batch_size=32, convert_to_numpy=True)

    metrics = evaluate_retrieval(
        query_embeddings=q_vecs.tolist(),
        doc_embeddings=c_vecs.tolist(),
        positive_doc_indices=list(pos_indices_f),
    )
    model.train()
    return metrics


def run_training(
    train_examples,
    check_examples,
    model,
    output_dir,
    epochs,
    batch_size,
    seed,
    grad_accum=1,
    scale=_SCALE,
    lr=2e-5,
    warmup_ratio=0.0,
    on_epoch=None,
    full_corpus_texts: list[str] | None = None,
):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = model.to(device)
    if device == "cuda":
        model = model.to(torch.bfloat16)
        try:
            model[0].auto_model.gradient_checkpointing_enable(
                gradient_checkpointing_kwargs={"use_reentrant": False}
            )
        except (TypeError, AttributeError):
            pass

    torch.manual_seed(seed)
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=0.01)

    scheduler = None
    if warmup_ratio > 0.0:
        steps_per_epoch = max(len(train_examples) // batch_size, 1)
        total_steps = steps_per_epoch * epochs
        warmup_steps = max(int(warmup_ratio * total_steps), 1)
        warmup = LinearLR(optimizer, start_factor=1e-3, end_factor=1.0, total_iters=warmup_steps)
        decay = CosineAnnealingLR(optimizer, T_max=total_steps - warmup_steps, eta_min=0)
        scheduler = SequentialLR(optimizer, schedulers=[warmup, decay], milestones=[warmup_steps])

    rng = random.Random(seed)

    best_recall = -1.0
    epoch_losses = []

    for epoch in range(epochs):
        model.train()

        # interleave examples across lectures each epoch to keep in-batch negs diverse
        shuffled = _diversify_batches(list(train_examples), batch_size, rng)

        total_loss = 0.0
        steps = 0
        optimizer.zero_grad()

        for i in tqdm(
            range(0, len(shuffled), batch_size), desc=f"epoch {epoch + 1}/{epochs}", leave=False
        ):
            batch = shuffled[i : i + batch_size]
            if len(batch) < 2:
                # batch too small for in-batch negatives to be meaningful
                continue

            queries = [ex.texts[0] for ex in batch]
            positives = [ex.texts[1] for ex in batch]
            negatives = [ex.texts[2] for ex in batch]

            all_texts = queries + positives + negatives
            all_embs = _encode(model, all_texts, device)
            b = len(batch)
            q_emb, p_emb, n_emb = all_embs[:b], all_embs[b : 2 * b], all_embs[2 * b :]

            loss = _mnrl_loss(q_emb, p_emb, n_emb, scale=scale) / grad_accum
            loss.backward()

            total_loss += loss.item() * grad_accum
            steps += 1

            if steps % grad_accum == 0 or (i + batch_size) >= len(shuffled):
                optimizer.step()
                if scheduler is not None:
                    scheduler.step()
                optimizer.zero_grad()

        avg_loss = total_loss / max(steps, 1)
        epoch_losses.append(round(avg_loss, 6))

        m = check_metrics(model, check_examples, device, full_corpus_texts=full_corpus_texts)
        print(
            f"epoch {epoch + 1}/{epochs}  loss={avg_loss:.4f}"
            f"  check_hit@1={m.hit_at_1:.3f}"
            f"  check_hit@5={m.hit_at_5:.3f}"
            f"  check_mrr={m.mrr:.3f}"
        )

        if on_epoch is not None:
            on_epoch(epoch + 1, avg_loss, m)

        if m.hit_at_1 > best_recall:
            best_recall = m.hit_at_1
            model.save(str(output_dir / "best"))
            log.info("new best checkpoint hit@1=%.3f", m.hit_at_1)

    model.save(str(output_dir / "final"))

    return {"epoch_losses": epoch_losses, "best_hit": best_recall}


def _load_chunk_meta(chunks_file: Path) -> tuple[list[str], list[ChunkMeta], dict[str, ChunkMeta]]:
    from app.finetune.synth import load_chunks_jsonl

    chunks = load_chunks_jsonl(chunks_file)
    corpus = [c.context_template or c.text for c in chunks]
    corpus_meta = [ChunkMeta(video_id=c.video_id, section_title=c.section_title) for c in chunks]
    lookup = {text: meta for text, meta in zip(corpus, corpus_meta)}
    return corpus, corpus_meta, lookup


def _assign_meta(triplets, lookup: dict[str, ChunkMeta]) -> list[ChunkMeta]:
    # map each triplet to chunk's metadata via positive text
    fallback = ChunkMeta(video_id=0)
    return [lookup.get(t.positive, fallback) for t in triplets]


def main(argv=None):
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")

    parser = argparse.ArgumentParser()
    parser.add_argument("--train-data", type=Path, required=True)
    parser.add_argument("--check-data", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--grad-accum", type=int, default=1)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--base-model", default=BASE_MODEL)
    parser.add_argument("--structured", action="store_true")
    parser.add_argument("--chunks-file", type=Path, default=None)
    parser.add_argument("--hard-frac", type=float, default=0.4)
    parser.add_argument("--medium-frac", type=float, default=0.3)
    parser.add_argument("--similarity-threshold", type=float, default=0.45)
    parser.add_argument("--mining-hard-frac", type=float, default=0.4)
    parser.add_argument("--mining-medium-frac", type=float, default=0.3)
    parser.add_argument("--clearml-project", default="Seekr")
    parser.add_argument("--clearml-task-name", default="finetune-bge-m3")
    parser.add_argument(
        "--allow-model-download",
        action="store_true",
    )
    parser.add_argument("--scale", type=float, default=_SCALE)
    parser.add_argument("--lr", type=float, default=2e-5)
    parser.add_argument("--warmup-ratio", type=float, default=0.06)
    parser.add_argument("--remote", action="store_true")

    args = parser.parse_args(argv)

    if args.structured and args.chunks_file is None:
        parser.error("--chunks-file is required when --structured is set")

    args.output_dir.mkdir(parents=True, exist_ok=True)

    cl_task = None
    if _CLEARML_OK:
        try:
            ClearMLTask.force_requirements_env_freeze(False)
            cl_task = ClearMLTask.init(
                project_name=args.clearml_project, task_name=args.clearml_task_name
            )
            cl_task.set_packages("requirements_ml.txt")
            if args.remote:
                running_on_agent = os.environ.get("CLEARML_WORKER_ID") is not None
                if running_on_agent:
                    args.train_data.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy(
                        cl_task.artifacts["train_data"].get_local_copy(), str(args.train_data)
                    )
                    shutil.copy(
                        cl_task.artifacts["check_data"].get_local_copy(), str(args.check_data)
                    )
                    if args.chunks_file is not None:
                        args.chunks_file.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy(
                            cl_task.artifacts["chunks"].get_local_copy(), str(args.chunks_file)
                        )
                else:
                    # write task id before exiting so pipeline can poll for completion
                    (args.output_dir / "clearml_task_id.txt").write_text(
                        cl_task.id, encoding="utf-8"
                    )
                    cl_task.upload_artifact("train_data", artifact_object=str(args.train_data))
                    cl_task.upload_artifact("check_data", artifact_object=str(args.check_data))
                    if args.chunks_file is not None:
                        cl_task.upload_artifact("chunks", artifact_object=str(args.chunks_file))
                    cl_task.execute_remotely(queue_name="default")
                    sys.exit(0)
        except Exception as exc:
            log.warning("ClearML not configured, running without tracking: %s", exc)
            cl_task = None
    elif args.remote:
        log.warning("--remote set but clearml is not available, running locally")

    train_triplets = load_triplets_jsonl(args.train_data)
    check_triplets = load_triplets_jsonl(args.check_data)

    full_corpus_texts: list[str] | None = None

    if args.structured:
        corpus, corpus_meta, lookup = _load_chunk_meta(args.chunks_file)
        full_corpus_texts = corpus  # used by check_metrics for realistic eval

        train_meta = _assign_meta(train_triplets, lookup)
        train_triplets = materialize_triplets_structured(
            train_triplets,
            train_meta,
            corpus=corpus,
            corpus_metadata=corpus_meta,
            seed=args.seed,
            hard_frac=args.hard_frac,
            medium_frac=args.medium_frac,
            similarity_threshold=args.similarity_threshold,
        )

        check_meta = _assign_meta(check_triplets, lookup)
        check_triplets = materialize_triplets_structured(
            check_triplets,
            check_meta,
            corpus=corpus,
            corpus_metadata=corpus_meta,
            seed=args.seed,
            hard_frac=args.hard_frac,
            medium_frac=args.medium_frac,
            similarity_threshold=args.similarity_threshold,
        )

    # fall back to positive if negative is missing (shouldn't happen after build_triplets)
    train_examples = [
        InputExample(texts=[t.query, t.positive, t.negative or t.positive]) for t in train_triplets
    ]
    check_examples = [
        InputExample(texts=[t.query, t.positive, t.negative or t.positive]) for t in check_triplets
    ]

    log.info("train=%d  check=%d", len(train_examples), len(check_examples))

    config = {
        "seed": args.seed,
        "epochs": args.epochs,
        "batch_size": args.batch_size,
        "grad_accum": args.grad_accum,
        "scale": args.scale,
        "lr": args.lr,
        "warmup_ratio": args.warmup_ratio,
        "base_model": args.base_model,
        "structured": args.structured,
        "hard_frac": args.hard_frac,
        "medium_frac": args.medium_frac,
        "similarity_threshold": args.similarity_threshold,
        "mining_hard_frac": args.mining_hard_frac,
        "mining_medium_frac": args.mining_medium_frac,
        "allow_model_download": bool(args.allow_model_download),
        "train_count": len(train_examples),
        "check_count": len(check_examples),
    }
    (args.output_dir / "training_config.json").write_text(
        json.dumps(config, indent=2), encoding="utf-8"
    )

    if cl_task is not None:
        cl_task.connect(config)

    on_epoch = None
    if cl_task is not None:
        cl_logger = cl_task.get_logger()

        def on_epoch(ep, loss, m):
            cl_logger.report_scalar("loss", "train", value=loss, iteration=ep)
            cl_logger.report_scalar("hit@1", "check", value=m.hit_at_1, iteration=ep)
            cl_logger.report_scalar("hit@5", "check", value=m.hit_at_5, iteration=ep)
            cl_logger.report_scalar("mrr", "check", value=m.mrr, iteration=ep)

    base_model = args.base_model
    if not Path(base_model).exists() and args.allow_model_download:
        log.info("base model path not found locally, falling back to %s", BASE_MODEL)
        base_model = BASE_MODEL

    log.info("Load pretrained SentenceTransformer: %s", base_model)
    model = SentenceTransformer(base_model, local_files_only=not args.allow_model_download)

    run_training(
        train_examples,
        check_examples,
        model,
        args.output_dir,
        args.epochs,
        args.batch_size,
        args.seed,
        grad_accum=args.grad_accum,
        scale=args.scale,
        lr=args.lr,
        warmup_ratio=args.warmup_ratio,
        on_epoch=on_epoch,
        full_corpus_texts=full_corpus_texts,
    )

    # upload completed model so pipeline can retrieve it after remote execute
    if args.remote and cl_task is not None:
        cl_task.upload_artifact("model", artifact_object=str(args.output_dir))


if __name__ == "__main__":
    main()
