from __future__ import annotations

import argparse
import json
import logging
import pathlib
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.evaluation.ablation import AblationConfig, AblationResult, get_standard_configs
from app.evaluation.data_loader import (
    get_default_retrieval_path,
    get_default_segmentation_path,
    load_retrieval_gold,
    load_segmentation_gold,
)
from app.evaluation.report import build_report
from app.evaluation.schemas import GroundTruthQuery

log = logging.getLogger(__name__)

_STANDARD_NAMES = ["baseline", "+OCR", "+Context", "+OCR+Context", "+OCR+Context+Training"]

try:
    from clearml import Task as ClearMLTask

    _CLEARML_OK = True
except ImportError:
    _CLEARML_OK = False


def _merge_requirements(*paths: str) -> list[str]:
    lines = []
    for p in paths:
        for line in pathlib.Path(p).read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and line not in lines:
                lines.append(line)
    return lines


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m app.evaluation.cli")
    parser.add_argument(
        "--gold-retrieval",
        metavar="PATH",
        default=None,
        help="path to retrieval benchmark JSON",
    )
    parser.add_argument(
        "--gold-segmentation",
        metavar="PATH",
        default=None,
        help="path to segmentation benchmark JSON",
    )
    parser.add_argument(
        "--sentences-json",
        metavar="PATH",
        default=None,
        help="path to sentences export (from export.py); skips DB if provided",
    )
    parser.add_argument(
        "--output-dir",
        metavar="PATH",
        default="evaluation_output",
        help="output directory for results",
    )
    parser.add_argument(
        "--ablations",
        metavar="TEXT",
        default=",".join(_STANDARD_NAMES),
        help="ablations to run, comma-separated",
    )
    parser.add_argument(
        "--k-values",
        metavar="TEXT",
        default="1,3,5,10",
        help="k values for recall, comma-separated",
    )
    parser.add_argument("--seed", metavar="INT", type=int, default=42, help="random seed")
    parser.add_argument(
        "--dry-run", action="store_true", help="print config and exit without running"
    )
    parser.add_argument("--clearml-project", default="Seekr", help="ClearML project name")
    parser.add_argument("--clearml-task-name", default="evaluation", help="ClearML task name")
    parser.add_argument("--remote", action="store_true", help="execute remotely via ClearML agent")
    parser.add_argument(
        "--finetune-task-id",
        metavar="ID",
        default=None,
        help="ClearML task ID for the fine-tuned embedding model artifact",
    )
    parser.add_argument(
        "--use-hyde",
        action="store_true",
        help="expand conceptual queries with HyDE before embedding",
    )
    return parser


def _to_sync_url(url: str) -> str:
    if url.startswith("postgresql+asyncpg://"):
        return url.replace("postgresql+asyncpg://", "postgresql://", 1)
    if url.startswith("postgresql+psycopg2://"):
        return url.replace("postgresql+psycopg2://", "postgresql://", 1)
    return url


def _fetch_video_data(video_id: int) -> tuple[list[dict[str, object]], float]:
    # pulls sentences and duration for one video directly from DB
    from sqlalchemy import create_engine, select
    from sqlalchemy.orm import sessionmaker

    from app.core.config import get_settings
    from app.models.video import Sentence, Video

    settings = get_settings()
    engine = create_engine(_to_sync_url(settings.database_url), pool_pre_ping=True)
    Session = sessionmaker(bind=engine)

    with Session() as session:
        video = session.get(Video, video_id)
        duration = float(video.duration or 0.0) if video else 0.0

        rows = (
            session.execute(
                select(Sentence).where(Sentence.video_id == video_id).order_by(Sentence.start_time)
            )
            .scalars()
            .all()
        )

    sentences = [
        {"text": r.text, "start_time": float(r.start_time), "end_time": float(r.end_time)}
        for r in rows
    ]
    return sentences, duration


def _load_sentences_json(path: Path) -> dict[int, dict[str, Any]]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return {int(entry["video_id"]): entry for entry in raw["videos"]}


def _average_results(config: AblationConfig, per_video: list[AblationResult]) -> AblationResult:
    if not per_video:
        return AblationResult(
            config=config,
            retrieval_metrics={},
            segmentation_metrics={},
            query_type_breakdown={},
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    n = len(per_video)
    ret_keys = {k for r in per_video for k in r.retrieval_metrics}
    retrieval = {
        k: sum(r.retrieval_metrics.get(k, 0.0) for r in per_video) / n for k in sorted(ret_keys)
    }

    seg_results = [r.segmentation_metrics for r in per_video if r.segmentation_metrics]
    if seg_results:
        seg_keys = {k for d in seg_results for k in d}
        segmentation = {
            k: sum(d.get(k, 0.0) for d in seg_results) / len(seg_results) for k in sorted(seg_keys)
        }
    else:
        segmentation = {}

    type_buckets: dict[str, list[dict[str, float]]] = defaultdict(list)
    for r in per_video:
        for qtype, metrics in r.query_type_breakdown.items():
            type_buckets[qtype].append(metrics)

    breakdown = {}
    for qtype, mlist in type_buckets.items():
        keys = {k for d in mlist for k in d}
        breakdown[qtype] = {k: sum(d.get(k, 0.0) for d in mlist) / len(mlist) for k in sorted(keys)}

    return AblationResult(
        config=config,
        retrieval_metrics=retrieval,
        segmentation_metrics=segmentation,
        query_type_breakdown=breakdown,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    output_dir = Path(args.output_dir)

    retrieval_path = (
        Path(args.gold_retrieval) if args.gold_retrieval else get_default_retrieval_path()
    )
    segmentation_path = (
        Path(args.gold_segmentation) if args.gold_segmentation else get_default_segmentation_path()
    )

    requested_names = [n.strip() for n in args.ablations.split(",") if n.strip()]
    all_standard = {cfg.name: cfg for cfg in get_standard_configs(seed=args.seed)}
    configs = []
    for name in requested_names:
        if name in all_standard:
            configs.append(all_standard[name])
        else:
            log.warning("unknown ablation %r, skipping (valid: %s)", name, list(all_standard))

    if not configs:
        log.error("no valid ablation configs, exiting")
        sys.exit(1)

    k_values = [int(k.strip()) for k in args.k_values.split(",") if k.strip()]

    if args.dry_run:
        log.info("dry run configuration:")
        log.info("  ablations : %s", [c.name for c in configs])
        log.info("  k_values  : %s", k_values)
        log.info("  seed      : %d  output_dir: %s", args.seed, output_dir)
        log.info("  retrieval : %s  segmentat.: %s", retrieval_path, segmentation_path)
        log.info("  sentences : %s", args.sentences_json or "live DB")
        log.info("dry run complete")
        return

    import os

    cl_task: Any = None
    if _CLEARML_OK:
        try:
            ClearMLTask.force_requirements_env_freeze(False)
            cl_task = ClearMLTask.init(
                project_name=args.clearml_project, task_name=args.clearml_task_name
            )
            cl_task.set_packages(_merge_requirements("requirements.txt", "requirements_ml.txt"))
            config_params = {
                "ablations": args.ablations,
                "k_values": args.k_values,
                "seed": args.seed,
            }
            cl_task.connect(config_params)

            if args.remote:
                running_on_agent = os.environ.get("CLEARML_TASK_ID") is not None
                if running_on_agent:
                    sentences_artifact = cl_task.artifacts.get("sentences_json")
                    if sentences_artifact:
                        args.sentences_json = sentences_artifact.get_local_copy()
                        log.info("downloaded sentences_json artifact to %s", args.sentences_json)
                    _ret_artifact = cl_task.artifacts.get("retrieval_gold")
                    if not _ret_artifact:
                        log.error("retrieval_gold artifact missing from task -- aborting")
                        sys.exit(1)
                    args.gold_retrieval = _ret_artifact.get_local_copy()
                    log.info("downloaded retrieval_gold artifact to %s", args.gold_retrieval)

                    _seg_artifact = cl_task.artifacts.get("segmentation_gold")
                    if not _seg_artifact:
                        log.error("segmentation_gold artifact missing from task -- aborting")
                        sys.exit(1)
                    args.gold_segmentation = _seg_artifact.get_local_copy()
                    log.info("downloaded segmentation_gold artifact to %s", args.gold_segmentation)
                    _CE_LOCAL_CANDIDATES = [
                        pathlib.Path.home()
                        / ".cache/hf/hub/models--cross-encoder--ms-marco-MiniLM-L-6-v2",
                        pathlib.Path.home()
                        / ".cache/huggingface/hub/models--cross-encoder--ms-marco-MiniLM-L-6-v2",
                        pathlib.Path(
                            "/home/celeryuser/.cache/huggingface/hub/models--cross-encoder--ms-marco-MiniLM-L-6-v2"
                        ),
                        pathlib.Path(__file__).parents[3]
                        / ".cache/hf/hub/models--cross-encoder--ms-marco-MiniLM-L-6-v2",
                    ]
                    _ce_local = next((p for p in _CE_LOCAL_CANDIDATES if p.exists()), None)
                    if _ce_local:
                        _snap = next(_ce_local.rglob("config.json"), None)
                        ce_path = str(_snap.parent) if _snap else str(_ce_local)
                        os.environ["CROSS_ENCODER_PATH"] = ce_path
                        log.info("cross-encoder model found locally at %s", ce_path)
                    else:
                        # fall back to artifact if local cache missing
                        ce_artifact = cl_task.artifacts.get("cross_encoder_model")
                        if ce_artifact:
                            ce_local = pathlib.Path(ce_artifact.get_local_copy())
                            _snap = next(ce_local.rglob("config.json"), None)
                            ce_path = str(_snap.parent) if _snap else str(ce_local)
                            os.environ["CROSS_ENCODER_PATH"] = ce_path
                            log.info("cross-encoder model set from artifact to %s", ce_path)

                    _ft_set = False
                    if args.finetune_task_id:
                        try:
                            from clearml import Task as _FTTask

                            _ft_task: Any = _FTTask.get_task(task_id=args.finetune_task_id)
                            _ft_artifact = _ft_task.artifacts.get("model")
                            if _ft_artifact:
                                _ft_local = pathlib.Path(_ft_artifact.get_local_copy())
                                # archive contains best/ and final/ so point to best/
                                _ft_path = next(
                                    (str(p.parent) for p in _ft_local.rglob("best/config.json")),
                                    str(_ft_local),
                                )
                                import time as _time

                                for _ in range(30):
                                    if pathlib.Path(_ft_path).is_dir():
                                        break
                                    _time.sleep(2)
                                os.environ["FINETUNED_EMBEDDING_MODEL"] = _ft_path
                                log.info("fine-tuned embedding model set to %s", _ft_path)
                                _ft_set = True
                        except Exception as ft_exc:
                            log.warning("could not load fine-tuned model from clearml: %s", ft_exc)
                    if not _ft_set:
                        # fall back to uploading from local disk if task was archived/deleted
                        _FT_CANDIDATES = [
                            pathlib.Path(__file__).parents[3] / "runs/finetune/model/best/best",
                        ]
                        _ft_found = next((p for p in _FT_CANDIDATES if p.exists()), None)
                        if _ft_found:
                            cl_task.upload_artifact(
                                "finetuned_model", artifact_object=str(_ft_found)
                            )
                            ft_artifact2 = cl_task.artifacts.get("finetuned_model")
                            if ft_artifact2:
                                _ft_local2 = pathlib.Path(ft_artifact2.get_local_copy())
                                _ft_path2 = next(
                                    (str(p.parent) for p in _ft_local2.rglob("config.json")),
                                    str(_ft_local2),
                                )
                                os.environ["FINETUNED_EMBEDDING_MODEL"] = _ft_path2
                                log.info("fine-tuned model uploaded and set to %s", _ft_path2)
                        else:
                            log.warning(
                                "fine-tuned model not found, +Training ablation will use base model"
                            )
                else:
                    # wait_on_upload=True makes each upload synchronous -> all three are committed to the server before execute_remotely
                    cl_task.upload_artifact(
                        "retrieval_gold",
                        artifact_object=str(retrieval_path),
                        wait_on_upload=True,
                    )
                    cl_task.upload_artifact(
                        "segmentation_gold",
                        artifact_object=str(segmentation_path),
                        wait_on_upload=True,
                    )
                    if args.sentences_json:
                        cl_task.upload_artifact(
                            "sentences_json",
                            artifact_object=str(args.sentences_json),
                            wait_on_upload=True,
                        )
                    output_dir.mkdir(parents=True, exist_ok=True)
                    (output_dir / "clearml_task_id.txt").write_text(cl_task.id, encoding="utf-8")
                    cl_task.flush(wait_for_uploads=True)
                    try:
                        cl_task.execute_remotely(queue_name="default")
                    except Exception as remote_exc:
                        log.error("execute_remotely failed, aborting: %s", remote_exc)
                        sys.exit(1)
                    sys.exit(0)
        except Exception as exc:
            if args.remote:
                log.error("ClearML setup failed for --remote execution, aborting: %s", exc)
                sys.exit(1)
            log.warning("clearml not configured, running without tracking: %s", exc)
            cl_task = None
    elif args.remote:
        log.warning("--remote set but clearml is not available, running locally")

    # load fixtures here so agent has already downloaded them from ClearML artifacts above
    retrieval_path = (
        Path(args.gold_retrieval) if args.gold_retrieval else get_default_retrieval_path()
    )
    segmentation_path = (
        Path(args.gold_segmentation) if args.gold_segmentation else get_default_segmentation_path()
    )
    all_queries = load_retrieval_gold(retrieval_path)
    seg_labels = load_segmentation_gold(segmentation_path)
    log.info("Loaded %d retrieval queries from %s", len(all_queries), retrieval_path)
    log.info("Loaded %d segmentation labels from %s", len(seg_labels), segmentation_path)

    queries_by_video: dict[int, list[GroundTruthQuery]] = defaultdict(list)
    for q in all_queries:
        queries_by_video[q.video_id].append(q)

    video_data: dict[int, dict[str, Any]] = {}
    if args.sentences_json:
        video_data = _load_sentences_json(Path(args.sentences_json))
        log.info("loaded sentence data for %d videos from %s", len(video_data), args.sentences_json)

    # defer heavy imports so they don't trigger CUDA init at module load
    from app.core.config import get_settings
    from app.evaluation.runner import EvaluationRunner
    from app.services.chunking import ChunkingService
    from app.services.embedding import EmbeddingService
    from app.services.qdrant_client import QdrantService

    settings = get_settings()
    chunking_svc = ChunkingService()
    embed_svc = EmbeddingService()  # type: ignore[no-untyped-call]
    qdrant_svc = QdrantService(in_memory=os.environ.get("CLEARML_TASK_ID") is not None)  # type: ignore[no-untyped-call]

    extra_embed_svcs: dict[str, EmbeddingService] = {}
    _ft_model_path = (
        os.environ.get("FINETUNED_EMBEDDING_MODEL") or settings.finetuned_embedding_model
    )
    if _ft_model_path:
        extra_embed_svcs["bge-m3-finetuned"] = EmbeddingService(  # type: ignore[no-untyped-call]
            model_path=_ft_model_path
        )
        log.info("loaded fine-tuned embedding model from %s", _ft_model_path)

    runner = EvaluationRunner(
        chunking_svc, embed_svc, qdrant_svc, extra_embed_svcs=extra_embed_svcs or None
    )

    results: list[AblationResult] = []
    for config in configs:
        log.info("running ablation: %s", config.name)
        per_video: list[AblationResult] = []

        for video_id, video_queries in sorted(queries_by_video.items()):
            if video_data:
                entry = video_data.get(video_id)
                if not entry:
                    log.warning("no entry for video %d in sentences JSON, skipping", video_id)
                    continue
                sentences = list(entry["sentences"])
                duration = float(entry.get("duration") or 0.0)
                video_title = str(entry.get("title") or "")
                slide_frames = entry.get("slide_frames") or None
                segments = entry.get("segments") or None
            else:
                try:
                    sentences, duration = _fetch_video_data(video_id)
                except Exception as exc:
                    log.warning(
                        "could not fetch sentences for video %d: %s, skipping", video_id, exc
                    )
                    continue
                video_title = ""
                slide_frames = None
                segments = None

            if not sentences:
                log.warning("no sentences found for video %d, skipping", video_id)
                continue

            log.info(
                "  video %d: %d sentences, %d queries", video_id, len(sentences), len(video_queries)
            )
            vr = runner.run_ablation(
                config,
                video_queries,
                sentences,
                duration,
                video_title=video_title,
                slide_frames=slide_frames,
                segments=segments,
                k_values=k_values,
                seg_labels=seg_labels,
                use_hyde=args.use_hyde,
            )
            per_video.append(vr)

        if not per_video:
            log.warning("ablation %s produced no results (no videos processed)", config.name)
            continue

        result = _average_results(config, per_video)
        rm = result.retrieval_metrics
        log.info(
            "  %s  hit@1=%.4f  mrr=%.4f  (avg over %d videos)",
            config.name,
            rm.get("hit@1", 0.0),
            rm.get("mrr", 0.0),
            len(per_video),
        )

        if cl_task is not None:
            cl_logger = cl_task.get_logger()
            for metric_key, value in rm.items():
                cl_logger.report_scalar(metric_key, config.name, value=value, iteration=0)
            seg_f1 = result.segmentation_metrics.get("f1")
            if seg_f1 is not None:
                cl_logger.report_scalar("seg_f1", config.name, value=seg_f1, iteration=0)

        results.append(result)

    if not results:
        log.error("no ablation results produced, exiting")
        sys.exit(1)

    report = build_report(results)

    print(report.to_table(k_values))

    output_dir.mkdir(parents=True, exist_ok=True)
    report.to_json(output_dir / "results.json")
    report.to_markdown(output_dir / "report.md", k_values)
    log.info("Saved results.json and report.md to %s", output_dir)

    try:
        saved = report.to_plots(output_dir / "plots", k_values)
        log.info("Saved plots: %s", saved)
        if cl_task is not None:
            cl_logger = cl_task.get_logger()
            for plot_path in saved:
                cl_logger.report_image(
                    "plots", Path(plot_path).stem, local_path=plot_path, iteration=0
                )
    except RuntimeError as exc:
        log.warning("Skipping plots: %s", exc)

    if args.remote and cl_task is not None:
        cl_task.upload_artifact("results_json", artifact_object=str(output_dir / "results.json"))
        cl_task.upload_artifact("report_md", artifact_object=str(output_dir / "report.md"))
        log.info("uploaded output artifacts to clearml")

    log.info("Evaluation complete. Results saved to %s", output_dir)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    main()
