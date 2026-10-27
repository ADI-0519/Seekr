from app.core.celery_app import celery_app
from app.services.qa import QAService
from app.services.query_router import classify_query
from app.services.retrieval import RetrievalService


@celery_app.task(name="app.tasks.retrieval_tasks.query", queue="retrieval")
def run_query(video_id: int, query: str, mode: str = "auto", top_k: int = 5):
    # fetch chunks first, then decide whether to return them directly or pass to gpt
    chunks = RetrievalService().search(video_id, query, top_k)
    resolved = mode if mode != "auto" else classify_query(query)

    if resolved == "qa":
        result = QAService().answer(video_id, query, chunks=chunks)
        result["mode"] = "qa"
        return result

    return {"mode": "retrieval", "query": query, "results": chunks}
