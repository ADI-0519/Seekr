import logging
import re

from openai import OpenAI

from app.core.log_safety import safe_exception_message
from app.services.retrieval import RetrievalService

log = logging.getLogger(__name__)

QA_MODEL = "gpt-5-mini"
QA_MAX_TOKENS = 2000


# Convert raw seconds into a standard MM:SS time string
def fmt_time(t: float) -> str:
    mins, secs = divmod(int(t), 60)
    return f"{mins}:{secs:02d}"


# assemble LLM prompt with numbered transcript excerpts to enforce inline citations
def build_messages(question: str, chunks: list[dict]) -> list[dict]:
    context_parts = []
    for i, chunk in enumerate(chunks, 1):
        ts = f"{fmt_time(chunk['start_time'])}–{fmt_time(chunk['end_time'])}"
        context_parts.append(f"[{i}] ({ts})\n{chunk['text']}")

    context = "\n\n".join(context_parts)

    system = (
        "You are a knowledgeable teaching assistant helping a student understand a lecture. "
        "Answer the student's question using ONLY the transcript excerpts provided; do not draw on outside knowledge. "
        "Write in a clear, academic tone: precise, helpful, and direct, as a lecturer or TA would speak. "
        "Use full sentences and proper grammar. Do not use bullet points, lists, or emojis. "
        "Cite the excerpts you use with [N] markers inline (e.g. 'the lecturer explains X [2]'). "
        "If the answer spans multiple excerpts, synthesise them into a single coherent explanation rather than addressing each separately. "
        "For mathematical notation: use Unicode symbols directly (σ not \\sigma, μ not \\mu, ∫ not \\int). "
        "Write subscripts as x_{i} and superscripts as x^{2}. Write fractions as (a/b). Never use LaTeX macros. "
        'If the answer is not covered in the provided excerpts, say: "This doesn\'t appear to be covered in the lecture material provided."'
    )
    user = f"Transcript excerpts:\n\n{context}\n\nQuestion: {question}"

    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def parse_citations(answer: str, chunks: list[dict]) -> list[dict]:
    # pull out every [N] in the answer, deduplicate while preserving order
    seen: set[int] = set()
    citations = []
    for m in re.finditer(r"\[(\d+)\]", answer):
        idx = int(m.group(1)) - 1
        if idx < 0 or idx >= len(chunks) or idx in seen:
            continue
        seen.add(idx)
        c = chunks[idx]
        citations.append(
            {
                "start_time": c["start_time"],
                "end_time": c["end_time"],
                "text": c["text"],
                "segment_title": c.get("segment_title"),
            }
        )
    return citations


class QAService:
    def __init__(self) -> None:
        self._client: OpenAI | None = None

    def get_client(self) -> OpenAI:
        if self._client is None:
            self._client = OpenAI()
        return self._client

    def answer(
        self, video_id: int, question: str, top_k: int = 5, chunks: list[dict] | None = None
    ) -> dict:
        # Retrieve search results dynamically if context chunks not pre-loaded
        if chunks is None:
            chunks = RetrievalService().search(video_id, question, top_k)

        if not chunks:
            return {
                "question": question,
                "answer": "I cannot find this in the lecture.",
                "citations": [],
            }

        messages = build_messages(question, chunks)

        try:
            client = self.get_client()
            resp = client.responses.create(
                model=QA_MODEL,
                input=messages,  # type: ignore[arg-type]
                max_output_tokens=QA_MAX_TOKENS,
            )
            answer_text = (resp.output_text or "").strip()
        except Exception as e:
            log.warning("QA API call failed: %s: %s", type(e).__name__, safe_exception_message(e))
            return {
                "question": question,
                "answer": "Sorry, I couldn't generate an answer right now.",
                "citations": [],
            }

        citations = parse_citations(answer_text, chunks)

        return {"question": question, "answer": answer_text, "citations": citations}
