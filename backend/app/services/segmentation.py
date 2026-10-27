from __future__ import annotations

import logging
import re
from dataclasses import dataclass

from app.services.sentence_reconstruction import ReconstructedSentence

logger = logging.getLogger(__name__)


# Define the output structure for a finalized lecture chapter
@dataclass(frozen=True)
class SegmentResult:
    segment_order: int
    title: str
    start_time: float
    end_time: float


# Custom exception for segmentation pipeline failures
class SegmentationError(Exception):
    pass


# Service to partition a continuous transcript into logical, titled chapters
class TopicSegmenter:
    def __init__(
        self,
        # min segment scales with lecture length so short and long videos both get reasonable splits
        min_segment_duration_ratio: float = 0.05,
        min_segment_duration_floor_secs: float = 30.0,
        min_segment_duration_cap_secs: float = 120.0,
        max_segments: int = 12,
        # w=20/k=6 — smaller blocks than default so short lectures don't get one giant tile
        texttiling_w: int = 20,
        texttiling_k: int = 6,
        hard_min_secs: float = 45.0,
        # OCR frames cover this fraction of the lecture -> skip TextTiling
        ocr_coverage_threshold: float = 0.7,
    ):
        self.min_segment_duration_ratio = min_segment_duration_ratio
        self.min_segment_duration_floor_secs = min_segment_duration_floor_secs
        self.min_segment_duration_cap_secs = min_segment_duration_cap_secs
        self.max_segments = max_segments
        self.texttiling_w = texttiling_w
        self.texttiling_k = texttiling_k
        self.hard_min_secs = hard_min_secs
        self.ocr_coverage_threshold = ocr_coverage_threshold

    # Execute the primary segmentation pipeline
    def segment(
        self,
        sentences: list[ReconstructedSentence],
        video_title: str = "",
        slide_frames: list[dict] | None = None,
    ) -> list[SegmentResult]:
        if not sentences:
            return []

        if len(sentences) < 3:
            return self.single_segment(sentences, video_title)

        total_duration = sentences[-1].end_time - sentences[0].start_time
        min_dur = max(
            self.min_segment_duration_floor_secs,
            min(
                total_duration * self.min_segment_duration_ratio, self.min_segment_duration_cap_secs
            ),
        )

        boundary_indices, ocr_protected = self.find_boundaries(sentences, slide_frames)

        raw_segments = self.boundaries_to_segments(sentences, boundary_indices)

        merged = self.merge_short_segments(raw_segments, ocr_protected, min_dur)

        capped = self.cap_segments(merged, max_segs=self._scaled_max_segments(total_duration))

        results = self.generate_titles(capped, video_title, slide_frames)

        return results

    # Determine optimal split points using OCR metadata or NLP text tiling
    def find_boundaries(
        self, sentences: list[ReconstructedSentence], slide_frames: list[dict] | None = None
    ) -> tuple[list[int], set[float]]:
        # OCR slide boundaries tend to be more reliable than TextTiling, try those first
        ocr_boundaries: list[int] = []
        ocr_protected: set[float] = set()
        if slide_frames:
            common = find_common_lines(slide_frames)
            ocr_boundaries = self.ocr_change_boundaries(slide_frames, sentences, common)
            if self.ocr_coverage_sufficient(slide_frames, sentences):
                logger.info(
                    "using OCR boundaries (%d found), skipping TextTiling", len(ocr_boundaries)
                )
                ocr_protected = {sentences[idx].start_time for idx in ocr_boundaries}
                return ocr_boundaries, ocr_protected

        # fall back to TextTiling when OCR coverage is sparse or unavailable
        boundary_indices = self.texttiling_boundaries(sentences)

        for idx in ocr_boundaries:
            ocr_protected.add(sentences[idx].start_time)
        if ocr_boundaries:
            boundary_indices = sorted(set(boundary_indices + ocr_boundaries))

        return boundary_indices, ocr_protected

    # Verify if a sufficient portion of the video duration is covered by slide text
    def ocr_coverage_sufficient(
        self, slide_frames: list[dict], sentences: list[ReconstructedSentence]
    ) -> bool:
        if not slide_frames or not sentences:
            return False
        total = sentences[-1].end_time - sentences[0].start_time
        if total <= 0:
            return False
        covered = 0.0
        for f in slide_frames:
            start = float(f.get("start_time", 0) or 0)
            end = float(f.get("end_time", 0) or 0)
            covered += end - start
        return (covered / total) >= self.ocr_coverage_threshold

    # Calculate logical topic shifts based on transcript vocabulary changes
    def texttiling_boundaries(self, sentences: list[ReconstructedSentence]) -> list[int]:
        import nltk
        from nltk.tokenize import TextTilingTokenizer

        nltk.download("stopwords", quiet=True)

        GROUP_SIZE = 5
        groups: list[list[int]] = []
        for i in range(0, len(sentences), GROUP_SIZE):
            groups.append(list(range(i, min(i + GROUP_SIZE, len(sentences)))))

        if len(groups) < 3:
            return []

        paragraphs = [" ".join(sentences[idx].text for idx in grp) for grp in groups]
        tiled_text = "\n\n".join(paragraphs)

        try:
            tt = TextTilingTokenizer(w=self.texttiling_w, k=self.texttiling_k)
            tiles = tt.tokenize(tiled_text)
        except ValueError:
            logger.warning("TextTiling failed, falling back to single segment")
            return []

        boundary_indices: list[int] = []
        group_cursor = 0
        for tile in tiles[:-1]:
            paras = [p.strip() for p in tile.split("\n\n") if p.strip()]
            group_cursor += len(paras)
            if group_cursor < len(groups):
                boundary_sentence = groups[group_cursor][0]
                if boundary_sentence < len(sentences):
                    boundary_indices.append(boundary_sentence)

        return boundary_indices

    # Identify segment boundaries based on significant changes in slide text or slide titles
    def ocr_change_boundaries(
        self,
        slide_frames: list[dict],
        sentences: list[ReconstructedSentence],
        common_lines: set[str] | None = None,
    ) -> list[int]:
        if len(slide_frames) < 2:
            return []

        common = common_lines or set()
        sorted_frames = sorted(slide_frames, key=lambda f: f["start_time"])

        change_times: list[float] = []
        for i in range(1, len(sorted_frames)):
            prev_text = normalize_ocr(sorted_frames[i - 1].get("ocr_text") or "")
            curr_text = normalize_ocr(sorted_frames[i].get("ocr_text") or "")

            prev_title = get_slide_title(sorted_frames[i - 1].get("ocr_text") or "", common)
            curr_title = get_slide_title(sorted_frames[i].get("ocr_text") or "", common)

            # title change primary signal but only fire if new title persists to nearby frame
            if prev_title and curr_title and prev_title != curr_title:
                if next_title_persists(sorted_frames, i, curr_title, common):
                    change_times.append(sorted_frames[i]["start_time"])
                continue

            # same title = same topic section, don't split it further
            if prev_title and curr_title and prev_title == curr_title:
                continue

            # no title on either slide — fall back to content similarity
            prev_words = {w for w in prev_text.split() if w not in common}
            curr_words = {w for w in curr_text.split() if w not in common}

            if not prev_words and not curr_words:
                continue

            union = prev_words | curr_words
            if not union:
                continue

            jaccard = len(prev_words & curr_words) / len(union)
            if jaccard < 0.5:
                change_times.append(sorted_frames[i]["start_time"])

        boundaries: list[int] = []
        for t in change_times:
            for idx, s in enumerate(sentences):
                if s.start_time >= t:
                    if idx > 0:
                        boundaries.append(idx)
                    break

        return boundaries

    # Convert index markers into raw segment objects populated with sentences
    def boundaries_to_segments(
        self,
        sentences: list[ReconstructedSentence],
        boundary_indices: list[int],
    ) -> list[_RawSegment]:
        all_boundaries = sorted(set([0] + boundary_indices + [len(sentences)]))
        segments: list[_RawSegment] = []

        for i in range(len(all_boundaries) - 1):
            start_idx = all_boundaries[i]
            end_idx = all_boundaries[i + 1]
            seg_sentences = sentences[start_idx:end_idx]

            segments.append(
                _RawSegment(
                    start_time=seg_sentences[0].start_time,
                    end_time=seg_sentences[-1].end_time,
                    sentences=seg_sentences,
                )
            )

        return segments

    # Combine consecutive segments that fall below the minimum duration threshold
    def merge_short_segments(
        self,
        segments: list[_RawSegment],
        ocr_protected: set[float] | None = None,
        min_duration_secs: float = 60.0,
    ) -> list[_RawSegment]:
        if len(segments) <= 1:
            return segments

        protected = ocr_protected or set()
        merged = list(segments)
        changed = True

        while changed:
            changed = False
            i = 0
            while i < len(merged):
                duration = merged[i].end_time - merged[i].start_time
                if duration < min_duration_secs and len(merged) > 1:
                    force = duration < self.hard_min_secs

                    # OCR slide transitions are hard boundaries (don't cross unless segment is so tiny it won't be useful)
                    can_merge_prev = i > 0 and (force or merged[i].start_time not in protected)
                    can_merge_next = i < len(merged) - 1 and (
                        force or merged[i + 1].start_time not in protected
                    )

                    if not can_merge_prev and not can_merge_next:
                        i += 1
                        continue

                    if can_merge_prev and can_merge_next:
                        prev_dur = merged[i - 1].end_time - merged[i - 1].start_time
                        next_dur = merged[i + 1].end_time - merged[i + 1].start_time
                        merge_target = i - 1 if prev_dur <= next_dur else i + 1
                    elif can_merge_prev:
                        merge_target = i - 1
                    else:
                        merge_target = i + 1

                    lo = min(i, merge_target)
                    hi = max(i, merge_target)
                    combined = _RawSegment(
                        start_time=merged[lo].start_time,
                        end_time=merged[hi].end_time,
                        sentences=merged[lo].sentences + merged[hi].sentences,
                    )
                    merged[lo] = combined
                    merged.pop(hi)
                    changed = True
                    break
                i += 1

        return merged

    # Enforce the absolute segment count limit by continually merging the shortest available segments
    def cap_segments(
        self, segments: list[_RawSegment], max_segs: int | None = None
    ) -> list[_RawSegment]:
        limit = max_segs if max_segs is not None else self.max_segments
        while len(segments) > limit:
            shortest_idx = min(
                range(len(segments)),
                key=lambda i: segments[i].end_time - segments[i].start_time,
            )
            if shortest_idx == 0:
                merge_with = 1
            elif shortest_idx == len(segments) - 1:
                merge_with = shortest_idx - 1
            else:
                prev_dur = (
                    segments[shortest_idx - 1].end_time - segments[shortest_idx - 1].start_time
                )
                next_dur = (
                    segments[shortest_idx + 1].end_time - segments[shortest_idx + 1].start_time
                )
                merge_with = shortest_idx - 1 if prev_dur <= next_dur else shortest_idx + 1

            lo = min(shortest_idx, merge_with)
            hi = max(shortest_idx, merge_with)
            combined = _RawSegment(
                start_time=segments[lo].start_time,
                end_time=segments[hi].end_time,
                sentences=segments[lo].sentences + segments[hi].sentences,
            )
            segments[lo] = combined
            segments.pop(hi)

        return segments

    # Format the final segment results and trigger title generation
    def generate_titles(
        self,
        segments: list[_RawSegment],
        video_title: str,
        slide_frames: list[dict] | None = None,
    ) -> list[SegmentResult]:
        common = find_common_lines(slide_frames or [])
        results: list[SegmentResult] = []

        for order, seg in enumerate(segments, start=1):
            ocr_hint = get_ocr_hint(slide_frames or [], seg.start_time, seg.end_time, common)
            title = generate_title_for_segment(seg, video_title, ocr_hint)
            results.append(
                SegmentResult(
                    segment_order=order,
                    title=title,
                    start_time=seg.start_time,
                    end_time=seg.end_time,
                )
            )

        return results

    # Construct a fallback single segment if the text is too short for division
    def single_segment(
        self,
        sentences: list[ReconstructedSentence],
        video_title: str,
    ) -> list[SegmentResult]:
        title = video_title if video_title else "Full Lecture"
        return [
            SegmentResult(
                segment_order=1,
                title=title,
                start_time=sentences[0].start_time,
                end_time=sentences[-1].end_time,
            )
        ]

    # max segments 12 up to 60 mins, +1 per 10 mins above that
    def _scaled_max_segments(self, duration_secs: float) -> int:
        if duration_secs <= 3600:
            return self.max_segments
        extra = int((duration_secs - 3600) / 600)
        return min(20, self.max_segments + extra)


# Internal data structure representing an unprocessed text segment
@dataclass
class _RawSegment:
    start_time: float
    end_time: float
    sentences: list[ReconstructedSentence]

    @property
    def text(self) -> str:
        return " ".join(s.text for s in self.sentences)

    @property
    def first_n_words(self, n: int = 300) -> str:
        words = self.text.split()
        return " ".join(words[:n])


# Clean raw OCR text for similarity comparisons
def normalize_ocr(text: str | None) -> str:
    if not text:
        return ""
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


# Verify if a newly detected slide title continues to appear in subsequent frames
def next_title_persists(
    sorted_frames: list[dict], idx: int, title: str, common: set[str], lookahead: int = 3
) -> bool:
    for j in range(idx + 1, min(idx + 1 + lookahead, len(sorted_frames))):
        t = get_slide_title(sorted_frames[j].get("ocr_text") or "", common)
        if t == title:
            return True
    return False


# Extract the likely title of a slide by locating the first non-boilerplate line
def get_slide_title(ocr_text: str, common_lines: set[str]) -> str:
    # first non-common, non-empty line is the section heading
    for line in ocr_text.split("\n"):
        key = line.strip().lower()
        if key and key not in common_lines:
            return key
    return ""


# Identify persistent boilerplate text (e.g., course names, dates) across all slides
def find_common_lines(slide_frames: list[dict]) -> set[str]:
    # persistent header lines can skew hints
    if not slide_frames:
        return set()

    counts: dict[str, int] = {}
    total = len(slide_frames)
    for frame in slide_frames:
        seen_this_frame: set[str] = set()
        for line in (frame.get("ocr_text") or "").split("\n"):
            key = line.strip().lower()
            if key and key not in seen_this_frame:
                counts[key] = counts.get(key, 0) + 1
                seen_this_frame.add(key)

    return {k for k, v in counts.items() if v / total >= 0.6}


# Extract relevant slide text from a specific time window to aid in title generation
def get_ocr_hint(
    slide_frames: list[dict],
    start_time: float,
    end_time: float,
    common_lines: set[str],
) -> str:
    overlapping = [
        f
        for f in slide_frames
        if (f.get("ocr_text") or "") and f["start_time"] < end_time and f["end_time"] > start_time
    ]
    if not overlapping:
        return ""

    seen: set[str] = set()
    lines: list[str] = []
    for frame in sorted(overlapping, key=lambda x: x["start_time"]):
        for line in (frame["ocr_text"] or "").split("\n"):
            line = line.strip()
            key = line.lower()
            if line and key not in seen and key not in common_lines:
                seen.add(key)
                lines.append(line)

    return "\n".join(lines[:8])


# Request an LLM to generate a concise, representative title for the segment
def generate_title_for_segment(seg: _RawSegment, video_title: str, ocr_hint: str = "") -> str:
    try:
        from openai import OpenAI

        client = OpenAI()

        words = seg.text.split()
        excerpt = " ".join(words[:300])

        context = f' from the lecture "{video_title}"' if video_title else ""
        slide_context = f"\n\nSlide text during this section:\n{ocr_hint}" if ocr_hint else ""

        prompt = (
            "Write one concise section title for this lecture excerpt.\n"
            "Rules:\n"
            "- Maximum 6 words\n"
            "- Only use terms and concepts that appear in the text below\n"
            "- Return only the title, nothing else\n"
            "- No quotation marks\n\n"
            "- Do not add 'Part clarifiers' (e.g. - part 1, part, 2, etc should NOT be present in the section title)\n\n"
            f"Excerpt{context}:{slide_context}\n\n{excerpt}"
        )
        response = client.responses.create(
            model="gpt-5-nano",
            input=prompt,
            max_output_tokens=60,
            reasoning={"effort": "minimal"},
        )

        raw = (response.output_text or "").strip()
        title = raw.strip('"').strip("'") if raw else ""
        if not title:
            words = seg.text.split()[:6]
            title = (" ".join(words) + "...") if words else "Untitled Section"
        return title

    except Exception as e:
        logger.warning(f"Title generation failed: {e}")
        words = seg.text.split()[:6]
        return " ".join(words) + "..."
