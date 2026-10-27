from __future__ import annotations

import logging
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass

from openai import OpenAI

logger = logging.getLogger(__name__)

# Configure constraints for AI-generated summaries to maintain consistent note quality
SUMMARY_MODEL = "gpt-5-mini"
SUMMARY_MAX_OUTPUT_TOKENS = 2000

MIN_SENTENCES = 2
MAX_SENTENCES = 3
MIN_WORDS = 15
MAX_WORDS = 80

MIN_SEGMENT_CHARS = 20
MAX_INPUT_CHARS = 6_000
MAX_SLIDE_CHARS = 400
ADJACENT_EXCERPT_WORDS = 100


# Define input parameters including context from surrounding segments to improve flow
@dataclass(frozen=True)
class SummaryInput:
    segment_id: int
    title: str
    transcript_text: str
    start_time: float
    end_time: float
    slide_text: str = ""
    prev_title: str = ""
    next_title: str = ""
    prev_excerpt: str = ""  # last N words of previous segment
    next_excerpt: str = ""  # first N words of next segment


# Define output structure for the validated summary and its metadata
@dataclass(frozen=True)
class SummaryResult:
    segment_id: int
    summary: str
    sentence_count: int
    word_count: int


# Custom exception for summaries that violate length or structure constraints
class SummaryValidationError(Exception):
    pass


_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")


# Split text by terminal punctuation to determine sentence count
def count_sentences(text: str) -> int:
    sentences = [s.strip() for s in _SENTENCE_SPLIT.split(text) if s.strip()]
    return len(sentences)


# Split text by whitespace to determine total word count
def count_words(text: str) -> int:
    return len(text.split())


# Verify that the generated summary adheres to strict sentence and word count limits
def validate_summary(text: str) -> tuple[int, int]:
    text = text.strip()
    if not text:
        raise SummaryValidationError("Empty summary")

    sentence_count = count_sentences(text)
    word_count = count_words(text)

    if sentence_count < MIN_SENTENCES:
        raise SummaryValidationError(f"Too few sentences: {sentence_count} (min {MIN_SENTENCES})")
    if sentence_count > MAX_SENTENCES:
        raise SummaryValidationError(f"Too many sentences: {sentence_count} (max {MAX_SENTENCES})")
    if word_count < MIN_WORDS:
        raise SummaryValidationError(f"Too few words: {word_count} (min {MIN_WORDS})")
    if word_count > MAX_WORDS:
        raise SummaryValidationError(f"Too many words: {word_count} (max {MAX_WORDS})")

    return sentence_count, word_count


# Verify output with reduced constraints to handle difficult-to-summarize segments
def validate_summary_lenient(text: str) -> tuple[int, int]:
    text = text.strip()
    if not text:
        raise SummaryValidationError("Empty summary")
    sentence_count = count_sentences(text)
    word_count = count_words(text)
    if sentence_count < 1:
        raise SummaryValidationError(f"Too few sentences: {sentence_count} (min 1)")
    if word_count < MIN_WORDS:
        raise SummaryValidationError(f"Too few words: {word_count} (min {MIN_WORDS})")
    return sentence_count, word_count


# Instruct the AI on the required sentence count, language, and synthesis style
SYSTEM_PROMPT = (
    "You are an expert academic note-taker. Given a transcript excerpt from a "
    "lecture segment, write a concise summary suitable for study notes.\n\n"
    "Rules:\n"
    "- Write EXACTLY 2 or 3 sentences.\n"
    "- Each sentence must be complete and informative.\n"
    "- Use clear, precise academic language.\n"
    "- Do NOT start with 'This segment…' or 'In this section…'.\n"
    "- Synthesise what was covered and why it matters; do NOT reproduce definitions or examples verbatim.\n"
    "- You may reference the preceding or following section if it adds useful context.\n"
    "- Do NOT include filler or meta-commentary. And DO NOT include em dashes. Ensure it is written in UK English.\n"
    "- Return ONLY the summary sentences, nothing else."
)

# Instruct the AI on synthesizing multiple segment summaries into a global overview
OVERVIEW_SYSTEM_PROMPT = (
    "You are an expert academic note-taker. Given a list of topic titles and their summaries "
    "from a lecture, write a single cohesive paragraph that describes what the lecture covers as a whole.\n\n"
    "Rules:\n"
    "- Write 2 or 3 sentences.\n"
    "- Capture the overall narrative arc and key themes, not just a list of topics.\n"
    "- Use clear, precise academic language.\n"
    "- Do NOT start with 'This lecture…' or 'In this lecture…'.\n"
    "- Do NOT use bullet points or numbered lists.\n"
    "- DO NOT include em dashes. Ensure it is written in UK English.\n"
    "- Return ONLY the overview paragraph, nothing else."
)


# Format the transcript and multimodal context into the final user prompt
def build_user_prompt(seg: SummaryInput) -> str:
    text = seg.transcript_text.strip()
    if len(text) > MAX_INPUT_CHARS:
        text = text[:MAX_INPUT_CHARS] + " [truncated]"

    prompt = ""
    if seg.prev_title and seg.prev_excerpt:
        prompt += f"Previous section ({seg.prev_title}):\n{seg.prev_excerpt}\n\n"
    elif seg.prev_title:
        prompt += f"Previous section: {seg.prev_title}\n"

    prompt += f"Segment title: {seg.title}\n"

    if seg.slide_text.strip():
        slide = seg.slide_text.strip()
        if len(slide) > MAX_SLIDE_CHARS:
            slide = slide[:MAX_SLIDE_CHARS] + " [truncated]"
        prompt += f"Slide text: {slide}\n"

    prompt += f"\nTranscript:\n{text}"

    if seg.next_title and seg.next_excerpt:
        prompt += f"\n\nNext section ({seg.next_title}):\n{seg.next_excerpt}"
    elif seg.next_title:
        prompt += f"\n\nNext section: {seg.next_title}"

    return prompt


# Generate corrective feedback for the AI based on specific validation failures
def retry_instruction(error: str) -> str:
    if "Too many sentences" in error:
        return (
            f"Your previous summary failed validation: {error}. "
            "Combine your sentences so the summary is exactly 2 or 3 sentences total."
        )
    if "Too few sentences" in error:
        return (
            f"Your previous summary failed validation: {error}. "
            "Expand into exactly 2 or 3 complete sentences."
        )
    if "Too many words" in error:
        return (
            f"Your previous summary failed validation: {error}. "
            "Shorten each sentence so the whole summary is under 80 words."
        )
    if "Too few words" in error:
        return (
            f"Your previous summary failed validation: {error}. "
            "Expand your sentences with more detail to reach at least 15 words total."
        )
    return (
        f"Your previous summary failed validation: {error}. "
        "Please rewrite it as exactly 2 or 3 complete sentences."
    )


# Service class to orchestrate AI summary generation with error recovery and parallelism
class SummaryGenerator:
    def __init__(self, max_retries: int = 5):
        self.max_retries = max_retries
        self._client: OpenAI | None = None

    # Initialize the OpenAI client lazily
    def get_client(self) -> OpenAI:
        if self._client is None:
            self._client = OpenAI()
        return self._client

    # Generate and validate a segment summary using iterative retry logic
    def generate(self, seg: SummaryInput) -> SummaryResult:
        if len(seg.transcript_text.strip()) < MIN_SEGMENT_CHARS:
            # skip API call if too short to meaningfully summarise
            fallback = (
                f"{seg.title}. "
                "This section was very brief and contained minimal spoken content. "
                "No further detail is available for this segment."
            )
            return SummaryResult(
                segment_id=seg.segment_id,
                summary=fallback,
                sentence_count=count_sentences(fallback),
                word_count=count_words(fallback),
            )

        try:
            client = self.get_client()
        except Exception as exc:
            logger.warning("OpenAI client init failed: %s (using fallback)", exc)
            return self.fallback(seg)

        messages: list[dict[str, str]] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_user_prompt(seg)},
        ]

        last_error: str | None = None
        raw = ""

        # Attempt generation until validation passes or the retry limit is reached
        for attempt in range(1 + self.max_retries):
            if attempt > 0 and last_error:
                # include previous bad response so the model knows what to fix
                messages.append({"role": "assistant", "content": raw})
                messages.append({"role": "user", "content": retry_instruction(last_error)})
                logger.info(
                    "Retry %d/%d for segment %d: %s",
                    attempt,
                    self.max_retries,
                    seg.segment_id,
                    last_error,
                )

            try:
                response = client.responses.create(
                    model=SUMMARY_MODEL,
                    input=messages,  # type: ignore[arg-type]
                    max_output_tokens=SUMMARY_MAX_OUTPUT_TOKENS,
                )
                raw = (response.output_text or "").strip().strip('"').strip("'")
            except Exception as exc:
                logger.warning("OpenAI API call failed for segment %d: %s", seg.segment_id, exc)
                return self.fallback(seg)

            try:
                # apply lenient validation after repeated failures to avoid dropping content
                validator = (
                    validate_summary_lenient
                    if attempt >= 3 and last_error and "Too few sentences" in last_error
                    else validate_summary
                )
                sc, wc = validator(raw)
                return SummaryResult(
                    segment_id=seg.segment_id,
                    summary=raw,
                    sentence_count=sc,
                    word_count=wc,
                )
            except SummaryValidationError as exc:
                last_error = str(exc)

        logger.warning(
            "All retries failed for segment %d (%s), using last output as-is",
            seg.segment_id,
            last_error,
        )
        if not raw.strip():
            return self.fallback(seg)
        return SummaryResult(
            segment_id=seg.segment_id,
            summary=raw,
            sentence_count=count_sentences(raw),
            word_count=count_words(raw),
        )

    # Synthesize multiple segment titles and summaries into a single lecture overview
    def generate_overview(self, segments: list[tuple[str, str]]) -> str:
        if not segments:
            return ""

        lines = [f"{i + 1}. {title}: {summary}" for i, (title, summary) in enumerate(segments)]
        user_content = "Lecture segments:\n\n" + "\n".join(lines)

        messages: list[dict[str, str]] = [
            {"role": "system", "content": OVERVIEW_SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ]

        raw = ""
        last_error: str | None = None

        try:
            client = self.get_client()
        except Exception as exc:
            logger.warning("Overview generation failed (client init): %s", exc)
            return ". ".join(title for title, _ in segments) + "."

        # Perform a single retry if the overview fails sentence count validation
        for attempt in range(2):
            if attempt > 0 and last_error:
                messages.append({"role": "assistant", "content": raw})
                messages.append({"role": "user", "content": retry_instruction(last_error)})

            try:
                response = client.responses.create(
                    model=SUMMARY_MODEL,
                    input=messages,  # type: ignore[arg-type]
                    max_output_tokens=SUMMARY_MAX_OUTPUT_TOKENS,
                )
                raw = (response.output_text or "").strip()
            except Exception as exc:
                logger.warning("Overview generation failed: %s", exc)
                return ". ".join(title for title, _ in segments) + "."

            sc = count_sentences(raw)
            if MIN_SENTENCES <= sc <= MAX_SENTENCES:
                return raw
            last_error = (
                f"Too many sentences: {sc} (max {MAX_SENTENCES})"
                if sc > MAX_SENTENCES
                else f"Too few sentences: {sc} (min {MIN_SENTENCES})"
            )

        logger.warning("Overview sentence check failed after retry (%s), using as-is", last_error)
        if raw:
            return raw
        return ". ".join(title for title, _ in segments) + "."

    # Process multiple segment summaries concurrently using a thread pool
    def generate_all(self, segments: list[SummaryInput]) -> list[SummaryResult]:
        if not segments:
            return []

        results: dict[int, SummaryResult] = {}
        with ThreadPoolExecutor(max_workers=min(5, len(segments))) as pool:
            futures = {pool.submit(self.generate, seg): seg.segment_id for seg in segments}
            for future in as_completed(futures):
                seg_id = futures[future]
                result = future.result()
                results[seg_id] = result
                logger.info(
                    "Summary for segment %d: %d sentences, %d words",
                    seg_id,
                    result.sentence_count,
                    result.word_count,
                )

        return [results[seg.segment_id] for seg in segments]

    # Generate a rudimentary summary from a transcript excerpt if the API process fails
    @staticmethod
    def fallback(seg: SummaryInput) -> SummaryResult:
        words = seg.transcript_text.split()
        excerpt = " ".join(words[:25])
        fallback = f"{seg.title}. {excerpt}."
        return SummaryResult(
            segment_id=seg.segment_id,
            summary=fallback,
            sentence_count=count_sentences(fallback),
            word_count=count_words(fallback),
        )
