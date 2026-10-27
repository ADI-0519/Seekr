from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

# Define terminal punctuation and common abbreviations to prevent false sentence breaks
END_MARKS = (".", "!", "?")
COMMON_ABBREVIATIONS = {
    "mr.",
    "mrs.",
    "ms.",
    "dr.",
    "prof.",
    "sr.",
    "jr.",
    "etc.",
    "e.g.",
    "i.e.",
}

# sentences can share a word boundary by up to this many seconds without being flagged
_OVERLAP_TOLERANCE = 0.05


# Data structure for a finalized, timed sentence block
@dataclass(frozen=True)
class ReconstructedSentence:
    text: str
    start_time: float
    end_time: float
    word_start_idx: int
    word_end_idx: int


# Custom exception for input validation and span errors
class SentenceReconstructionError(Exception):
    pass


# Service to group individual word tokens into coherent sentence structures based on timing and punctuation
class SentenceReconstructor:
    def __init__(
        self,
        pause_threshold_secs: float = 0.7,
        max_words_per_sentence: int = 30,
        max_sentence_duration_secs: float = 20.0,
        segment_hint_tolerance_secs: float = 0.05,
        # whisper sometimes ends sentences a word or two early
        min_words_per_sentence: int = 4,
    ):
        self.pause_threshold_secs = pause_threshold_secs
        self.max_words_per_sentence = max_words_per_sentence
        self.max_sentence_duration_secs = max_sentence_duration_secs
        self.segment_hint_tolerance_secs = segment_hint_tolerance_secs
        self.min_words_per_sentence = min_words_per_sentence

    # Execute the primary reconstruction pipeline on a list of timestamped words
    def reconstruct_sentences(
        self,
        words: list[dict[str, Any]],
        segment_ranges: list[tuple[float, float]] | None = None,
    ) -> list[ReconstructedSentence]:
        if not words:
            return []

        # Sort words chronologically and check for malformed data
        ordered = sorted(words, key=lambda w: float(w["start"]))
        self.validate_words(ordered)

        sentence_ranges: list[tuple[int, int]] = []
        sentence_start = 0

        # Iterate through the word list to determine optimal split points
        for i in range(len(ordered) - 1):
            cur = ordered[i]
            nxt = ordered[i + 1]
            if self.should_break(
                ordered,
                sentence_start,
                i,
                cur,
                nxt,
                segment_ranges=segment_ranges,
            ):
                sentence_ranges.append((sentence_start, i))
                sentence_start = i + 1

        sentence_ranges.append((sentence_start, len(ordered) - 1))

        # fold any short spans into neighbours before building the final sentences
        sentence_ranges = self.merge_short_spans(sentence_ranges, ordered)

        sentences: list[ReconstructedSentence] = []

        # Compile final sentence objects and enforce terminal punctuation formatting
        for start_idx, end_idx in sentence_ranges:
            raw_text = self.join_tokens(ordered, start_idx, end_idx)
            text = self.ensure_terminal_punctuation(raw_text)
            sentences.append(
                ReconstructedSentence(
                    text=text,
                    start_time=float(ordered[start_idx]["start"]),
                    end_time=float(ordered[end_idx]["end"]),
                    word_start_idx=start_idx,
                    word_end_idx=end_idx,
                )
            )

        self.validate_output(sentences, ordered)
        return sentences

    # Combine orphaned fragments into adjacent sentences based on temporal proximity
    def merge_short_spans(
        self, spans: list[tuple[int, int]], words: list[dict[str, Any]]
    ) -> list[tuple[int, int]]:
        if len(spans) <= 1:
            return spans

        result = list(spans)
        changed = True
        while changed:
            changed = False
            i = 0
            while i < len(result):
                word_count = result[i][1] - result[i][0] + 1
                if word_count < self.min_words_per_sentence and len(result) > 1:
                    if i == 0:
                        neighbour = 1
                    elif i == len(result) - 1:
                        neighbour = i - 1
                    else:
                        gap_prev = float(words[result[i][0]]["start"]) - float(
                            words[result[i - 1][1]]["end"]
                        )
                        gap_next = float(words[result[i + 1][0]]["start"]) - float(
                            words[result[i][1]]["end"]
                        )
                        neighbour = i - 1 if gap_prev <= gap_next else i + 1

                    lo = min(i, neighbour)
                    hi = max(i, neighbour)
                    merged = (result[lo][0], result[hi][1])
                    result[lo] = merged
                    result.pop(hi)
                    changed = True
                    break
                i += 1

        return result

    # Evaluate whether a break should occur at the current word index
    def should_break(
        self,
        words: list[dict[str, Any]],
        sentence_start: int,
        i: int,
        cur: dict[str, Any],
        nxt: dict[str, Any],
        segment_ranges: list[tuple[float, float]] | None = None,
    ) -> bool:
        token = str(cur["word"]).strip()
        word_count = i - sentence_start + 1
        pause = float(nxt["start"]) - float(cur["end"])

        if self.has_sentence_ending(token):
            # Avoid tiny sentence fragments from Whisper punctuation noise.
            if word_count >= 6 or pause >= self.pause_threshold_secs:
                return True

        if self.near_segment_end(float(cur["end"]), float(nxt["start"]), segment_ranges):
            return True
        if pause >= self.pause_threshold_secs:
            return True

        if word_count >= self.max_words_per_sentence:
            return True

        sentence_duration = float(cur["end"]) - float(words[sentence_start]["start"])
        if sentence_duration >= self.max_sentence_duration_secs:
            return True

        return False

    # Check if the current word approaches a predefined segment boundary
    def near_segment_end(
        self,
        cur_end: float,
        nxt_start: float,
        segment_ranges: list[tuple[float, float]] | None,
    ) -> bool:
        if not segment_ranges:
            return False

        for _seg_start, seg_end in segment_ranges:
            if abs(cur_end - seg_end) <= self.segment_hint_tolerance_secs:
                return True
            if cur_end <= seg_end <= nxt_start:
                return True
        return False

    # Concatenate tokens into a single string while handling whitespace formatting
    def join_tokens(self, words: list[dict[str, Any]], start_idx: int, end_idx: int) -> str:
        text = "".join(str(words[i]["word"]) for i in range(start_idx, end_idx + 1)).strip()
        return re.sub(r"\s+", " ", text)

    # Append a period if the sentence lacks valid terminal punctuation
    def ensure_terminal_punctuation(self, text: str) -> str:
        if not text:
            return text

        trimmed = text.rstrip()
        if trimmed.endswith(END_MARKS):
            return trimmed

        if trimmed.endswith((",", ";", ":")):
            trimmed = trimmed[:-1].rstrip()

        return trimmed + "."

    # Determine if a token represents a natural sentence termination
    def has_sentence_ending(self, token: str) -> bool:
        lower = token.lower()
        if lower in COMMON_ABBREVIATIONS:
            return False

        if re.match(r"^\d+\.\d+$", token):
            return False

        return token.endswith(END_MARKS)

    # Verify input data integrity for required keys and chronological ordering
    def validate_words(self, words: list[dict[str, Any]]) -> None:
        required = ("word", "start", "end")
        for idx, word in enumerate(words):
            missing = [k for k in required if k not in word]
            if missing:
                raise SentenceReconstructionError(
                    f"Word #{idx} missing required keys: {', '.join(missing)}"
                )

            start = float(word["start"])
            end = float(word["end"])
            if end < start:
                raise SentenceReconstructionError(
                    f"Word #{idx} has invalid timestamps (start={start}, end={end})"
                )

            if idx > 0 and start < float(words[idx - 1]["start"]):
                raise SentenceReconstructionError("Words must be time-ordered")

    # Verify output data integrity to ensure no words were dropped or overlapped incorrectly
    def validate_output(
        self, sentences: list[ReconstructedSentence], words: list[dict[str, Any]]
    ) -> None:
        if not sentences:
            return

        next_expected = 0
        for sentence in sentences:
            if sentence.word_start_idx != next_expected:
                raise SentenceReconstructionError(
                    f"Sentence spans are not contiguous at index {next_expected}"
                )
            if sentence.word_end_idx < sentence.word_start_idx:
                raise SentenceReconstructionError("Invalid sentence span (end before start)")
            next_expected = sentence.word_end_idx + 1

        if next_expected != len(words):
            raise SentenceReconstructionError("Sentence spans do not cover all words")

        if abs(sentences[0].start_time - float(words[0]["start"])) > 1e-6:
            raise SentenceReconstructionError("First sentence must start at first word")
        if abs(sentences[-1].end_time - float(words[-1]["end"])) > 1e-6:
            raise SentenceReconstructionError("Last sentence must end at last word")

        for i in range(len(sentences) - 1):
            overlap = sentences[i].end_time - sentences[i + 1].start_time
            if overlap > _OVERLAP_TOLERANCE:
                raise SentenceReconstructionError(
                    f"Sentence time overlap between sentence {i} and {i + 1} ({overlap:.3f}s)"
                )
