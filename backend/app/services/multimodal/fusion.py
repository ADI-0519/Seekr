import logging
from types import ModuleType

# Safely attempt to load the OpenAI tokenizer
tiktoken: ModuleType | None
try:
    import tiktoken as _tiktoken

    tiktoken = _tiktoken
except ImportError:
    tiktoken = None

log = logging.getLogger(__name__)

# Set limits to prevent context window overflow during LLM processing
_MAX_SLIDE_TOKENS = 150
_CHAR_FALLBACK = 500  # Backstop for token-dense text if tiktoken fails


# Utility class to deduplicate and truncate OCR text from slides within a specific time window
class SlideChunkFusion:
    def __init__(self, max_slide_tokens: int = _MAX_SLIDE_TOKENS):
        self.max_slide_tokens = max_slide_tokens
        self._enc = None

        if tiktoken is not None:
            try:
                self._enc = tiktoken.get_encoding("cl100k_base")
            except Exception:
                log.warning("tiktoken encoder failed to load, falling back to char limit")

    def get_slide_text(self, win_start: float, win_end: float, frames: list[dict] | None) -> str:
        if not frames:
            return ""

        seen: set[str] = set()
        parts = []

        # Aggregate unique OCR text from slides that overlap with the requested time window
        for frame in frames:
            if frame["start_time"] >= win_end or frame["end_time"] <= win_start:
                continue
            ocr = (frame.get("ocr_text") or "").strip()
            if ocr and ocr not in seen:
                seen.add(ocr)
                parts.append(ocr)

        if not parts:
            return ""

        combined = " ".join(parts)

        # Truncate the combined text based on accurate token counts if the encoder loaded
        if self._enc is not None:
            tokens = self._enc.encode(combined)
            if len(tokens) > self.max_slide_tokens:
                combined = self._enc.decode(tokens[: self.max_slide_tokens])

        return combined[:_CHAR_FALLBACK]
