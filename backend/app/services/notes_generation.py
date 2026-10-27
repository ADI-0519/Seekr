from __future__ import annotations

import logging
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass

from openai import OpenAI

logger = logging.getLogger(__name__)

NOTES_MODEL = "gpt-5-mini"
NOTES_MAX_TOKENS = 2500

MAX_INPUT_CHARS = 8_000
MAX_SLIDE_CHARS = 400
MIN_SEGMENT_CHARS = 30

# latex macro -> unicode substitutions, runs on generated output as a fallback
_LATEX_SUBS = [
    (re.compile(r"\\sigma"), "σ"),
    (re.compile(r"\\mu"), "μ"),
    (re.compile(r"\\alpha"), "α"),
    (re.compile(r"\\beta"), "β"),
    (re.compile(r"\\gamma"), "γ"),
    (re.compile(r"\\delta"), "δ"),
    (re.compile(r"\\epsilon"), "ε"),
    (re.compile(r"\\lambda"), "λ"),
    (re.compile(r"\\theta"), "θ"),
    (re.compile(r"\\pi"), "π"),
    (re.compile(r"\\rho"), "ρ"),
    (re.compile(r"\\tau"), "τ"),
    (re.compile(r"\\phi"), "φ"),
    (re.compile(r"\\omega"), "ω"),
    (re.compile(r"\\Sigma"), "Σ"),
    (re.compile(r"\\Delta"), "Δ"),
    (re.compile(r"\\Omega"), "Ω"),
    (re.compile(r"\\infty"), "∞"),
    (re.compile(r"\\partial"), "∂"),
    (re.compile(r"\\nabla"), "∇"),
    (re.compile(r"\\int"), "∫"),
    (re.compile(r"\\sum"), "Σ"),
    (re.compile(r"\\prod"), "Π"),
    (re.compile(r"\\sqrt\{([^}]+)\}"), r"√(\1)"),
    (re.compile(r"\\frac\{([^}]+)\}\{([^}]+)\}"), r"(\1/\2)"),
    (re.compile(r"\\tfrac\{([^}]+)\}\{([^}]+)\}"), r"(\1/\2)"),
    (re.compile(r"\\dfrac\{([^}]+)\}\{([^}]+)\}"), r"(\1/\2)"),
    (re.compile(r"\\exp"), "exp"),
    (re.compile(r"\\ln"), "ln"),
    (re.compile(r"\\log"), "log"),
    (re.compile(r"\\sin"), "sin"),
    (re.compile(r"\\cos"), "cos"),
    (re.compile(r"\\tan"), "tan"),
    (re.compile(r"\\leq"), "≤"),
    (re.compile(r"\\geq"), "≥"),
    (re.compile(r"\\neq"), "≠"),
    (re.compile(r"\\approx"), "≈"),
    (re.compile(r"\\times"), "×"),
    (re.compile(r"\\cdot"), "·"),
    (re.compile(r"\\pm"), "±"),
    (re.compile(r"\\in"), "∈"),
    (re.compile(r"\\subset"), "⊂"),
    (re.compile(r"\\cup"), "∪"),
    (re.compile(r"\\cap"), "∩"),
    (re.compile(r"\\to"), "→"),
    (re.compile(r"\\rightarrow"), "→"),
    (re.compile(r"\\leftarrow"), "←"),
    # strip remaining LaTeX decorators that don't map cleanly
    (re.compile(r"\\big[lr]?[({[]"), ""),
    (re.compile(r"\\big[lr]?[)}\]]"), ""),
    (re.compile(r"\\![, ]?"), ""),
    (re.compile(r"\\,"), " "),
    (re.compile(r"\\;"), " "),
    (re.compile(r"\\:"), " "),
    (re.compile(r"\\\s"), " "),
]


def clean_latex(text: str) -> str:
    for pattern, replacement in _LATEX_SUBS:
        text = pattern.sub(replacement, text)
    return text


@dataclass(frozen=True)
class NotesInput:
    segment_id: int
    title: str
    transcript_text: str
    start_time: float
    end_time: float
    slide_text: str = ""


@dataclass(frozen=True)
class NotesResult:
    segment_id: int
    title: str
    notes_markdown: str
    start_time: float
    end_time: float


SYSTEM_PROMPT = (
    "You are an expert academic note-taker. Given a transcript excerpt from a "
    "lecture segment, generate thorough study notes suitable for learning and revision.\n\n"
    "Rules:\n"
    "- Start with a brief overview paragraph (2-3 sentences) that synthesises the main idea.\n"
    "- Then cover all key concepts, definitions, results, and examples using bullet points.\n"
    "- Use indented sub-bullets (two leading spaces before the dash) to show hierarchy. "
    "Items that belong under a heading bullet must be indented beneath it. "
    "Always use a hyphen-dash (- ) as the bullet character, not ■ or any other symbol. For example:\n"
    "- **Key concept**\n"
    "  - First point explaining it.\n"
    "  - Second point explaining it.\n"
    "- Synthesise and paraphrase in your own words. "
    "Do NOT copy definitions, proofs, or examples verbatim from the transcript.\n"
    "- Explain dense or technical content clearly so a student can understand it.\n"
    "- Bold key terms using **term**. Write subscripts as x_{i} and superscripts as x^{2}.\n"
    "- For mathematical symbols use Unicode characters directly: σ not \\sigma, μ not \\mu, "
    "∫ not \\int, and so on. Never use LaTeX macros or backslash commands.\n"
    "- Write fractions as (a/b), not \\frac{a}{b} or \\tfrac{a}{b}.\n"
    "- Use clear, precise academic language written in UK English.\n"
    "- Do NOT include meta-commentary like 'The lecturer discusses...', 'Overview:...', or 'The segment discusses...'.\n"
    "- Return ONLY the notes content, no titles or headers."
)


# Assemble the transcript, slide text, and metadata into a single prompt string
def build_prompt(seg: NotesInput) -> str:
    text = seg.transcript_text.strip()
    if len(text) > MAX_INPUT_CHARS:
        text = text[:MAX_INPUT_CHARS] + " [truncated]"

    prompt = (
        f"Segment title: {seg.title}\n" f"Duration: {seg.start_time:.0f}s - {seg.end_time:.0f}s\n\n"
    )

    if seg.slide_text.strip():
        slide = seg.slide_text.strip()
        if len(slide) > MAX_SLIDE_CHARS:
            slide = slide[:MAX_SLIDE_CHARS] + " [truncated]"
        prompt += f"Slide text: {slide}\n\n"

    prompt += f"Transcript:\n{text}"
    return prompt


# Service class to manage calls to the OpenAI API and process lecture segments
class NotesGenerator:
    def __init__(self) -> None:
        self._client: OpenAI | None = None

    def get_client(self) -> OpenAI:
        if self._client is None:
            self._client = OpenAI()
        return self._client

    # Send a single segment to the LLM for processing with retry logic
    def generate(self, seg: NotesInput) -> NotesResult:
        if len(seg.transcript_text.strip()) < MIN_SEGMENT_CHARS:
            return NotesResult(
                segment_id=seg.segment_id,
                title=seg.title,
                notes_markdown="This segment contained minimal content.",
                start_time=seg.start_time,
                end_time=seg.end_time,
            )

        try:
            client = self.get_client()
        except Exception as exc:
            logger.warning("OpenAI client init failed for segment %d: %s", seg.segment_id, exc)
            return self.fallback(seg)

        messages: list[dict[str, str]] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_prompt(seg)},
        ]

        # retry if the api returns empty or raises
        for attempt in range(2):
            try:
                response = client.responses.create(
                    model=NOTES_MODEL,
                    input=messages,  # type: ignore[arg-type]
                    max_output_tokens=NOTES_MAX_TOKENS,
                )
                raw = (response.output_text or "").strip()
                if not raw:
                    logger.warning(
                        "Notes API returned empty response for segment %d (attempt %d)",
                        seg.segment_id,
                        attempt + 1,
                    )
                    continue
                return NotesResult(
                    segment_id=seg.segment_id,
                    title=seg.title,
                    notes_markdown=clean_latex(raw),
                    start_time=seg.start_time,
                    end_time=seg.end_time,
                )
            except Exception as exc:
                logger.warning(
                    "Notes API call failed for segment %d (attempt %d): %s",
                    seg.segment_id,
                    attempt + 1,
                    exc,
                )

        return self.fallback(seg)

    # Execute note generation for multiple segments concurrently using a thread pool
    def generate_all(self, segments: list[NotesInput]) -> list[NotesResult]:
        if not segments:
            return []

        results: dict[int, NotesResult] = {}
        with ThreadPoolExecutor(max_workers=min(5, len(segments))) as pool:
            futures = {pool.submit(self.generate, seg): seg.segment_id for seg in segments}
            for future in as_completed(futures):
                seg_id = futures[future]
                result = future.result()
                results[seg_id] = result
                logger.info("Generated notes for segment %d: %s", seg_id, result.title)

        return [results[seg.segment_id] for seg in segments]

    # Provide a basic text summary if the API call fails repeatedly
    @staticmethod
    def fallback(seg: NotesInput) -> NotesResult:
        excerpt = seg.transcript_text[:200].strip()
        return NotesResult(
            segment_id=seg.segment_id,
            title=seg.title,
            notes_markdown=f"Notes could not be generated. Summary: {excerpt}...",
            start_time=seg.start_time,
            end_time=seg.end_time,
        )
