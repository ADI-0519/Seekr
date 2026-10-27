from __future__ import annotations

import logging

log = logging.getLogger(__name__)

_HYDE_PROMPT = """\
You are a university lecturer mid-way through a technical lecture.
Write 3-4 sentences from your lecture transcript that directly address the following question.

Rules:
- Write in natural spoken lecture style: short sentences, thinking aloud, casual but precise
- Use phrases like "so", "right", "the key idea here is", "and that's why", "if you think about it"
- Be technically accurate — use correct terminology from the domain
- Do NOT write in textbook or essay style
- Do NOT start with "In this lecture" or "Today we will"
- Write as if you are currently explaining this concept to students verbally

Question: {query}

Transcript passage:"""

_client = None


def get_client():
    global _client
    if _client is None:
        from openai import OpenAI

        _client = OpenAI()
    return _client


def expand_query_with_hyde(query_text: str) -> str:
    # do for conceptual queries (have biggest embedding gap between question form and lecture transcript form)
    try:
        client = get_client()
        resp = client.responses.create(
            model="gpt-5-mini",
            input=_HYDE_PROMPT.format(query=query_text),
            max_output_tokens=200,
            reasoning={"effort": "low"},
        )
        expanded = (resp.output_text or "").strip()
        if len(expanded.split()) < 10:
            # degenerate output, fall back to original
            return query_text
        log.debug("HyDE expanded '%s' -> '%s'", query_text[:60], expanded[:80])
        return expanded
    except Exception as e:
        log.warning("HyDE expansion failed, using original query: %s", e)
        return query_text
