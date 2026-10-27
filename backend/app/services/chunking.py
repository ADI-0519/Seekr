import logging

from app.services.multimodal.fusion import SlideChunkFusion

log = logging.getLogger(__name__)
_fusion = SlideChunkFusion()

# 30s window, 10s step
WINDOW_SIZE = 30.0
WINDOW_STEP = 10.0

# Define relative time buckets to provide structural context to the LLM
BUCKETS = [
    (0.0, 0.15, "beginning"),
    (0.15, 0.35, "early-middle"),
    (0.35, 0.65, "middle"),
    (0.65, 0.85, "late-middle"),
    (0.85, 1.01, "end"),  # 1.01 so pct==1.0 hits here
]


# Service to partition video transcripts and multimodal metadata into overlapping context chunks for vector embedding
class ChunkingService:
    def create_chunks(
        self,
        sentences: list,
        video_duration: float,
        slide_frames: list[dict] | None = None,
        segments: list[dict] | None = None,
        video_title: str = "",
    ) -> list[dict]:
        if not sentences:
            return []

        # normalise; accepts either ReconstructedSentence objects or plain dicts
        normed = []
        for s in sentences:
            if isinstance(s, dict):
                normed.append(s)
            else:
                normed.append(
                    {
                        "text": s.text,
                        "start_time": s.start_time,
                        "end_time": s.end_time,
                    }
                )

        # if video is shorter than 30s just do one chunk
        if video_duration <= WINDOW_SIZE:
            windows = [(0.0, video_duration)]
        else:
            win_starts: set[float] = set()

            start = 0.0
            while start < video_duration:
                win_starts.add(start)
                end = min(start + WINDOW_SIZE, video_duration)
                if end >= video_duration:
                    break
                start += WINDOW_STEP

            if segments:
                for seg in segments:
                    t = float(seg["start_time"])
                    if 0.0 <= t < video_duration:
                        win_starts.add(t)

            windows = [(ws, min(ws + WINDOW_SIZE, video_duration)) for ws in sorted(win_starts)]

        chunks: list[dict] = []
        prev_ids: frozenset | None = None

        # Build composite chunks by aggregating transcript sentences within each time window
        for win_start, win_end in windows:
            in_window = [
                s for s in normed if s["start_time"] < win_end and s["end_time"] > win_start
            ]

            if not in_window:
                continue

            curr_ids = frozenset(id(s) for s in in_window)
            if curr_ids == prev_ids:
                continue
            prev_ids = curr_ids

            text = " ".join(s["text"].strip() for s in in_window)

            # Extract concurrent metadata to enrich the chunk
            position_cat = get_position(win_start, video_duration)
            slide_text = _fusion.get_slide_text(win_start, win_end, slide_frames)
            section_title = get_section_title((win_start + win_end) / 2.0, segments)

            speech_snippet = text[:300]
            if len(text) > 300:
                log.debug("speech truncated at chunk %.1fs (was %d chars)", win_start, len(text))

            context = (
                f"[LECTURE: {video_title}]"
                f" [SECTION: {section_title}]"
                f" [POSITION: {position_cat}]"
                f" [SLIDE: {slide_text}]"
                f" [SPEECH: {speech_snippet}]"
            )

            chunks.append(
                {
                    "index": len(chunks),
                    "text": text,
                    "start_time": win_start,
                    "end_time": in_window[-1]["end_time"],
                    "position_category": position_cat,
                    "slide_text": slide_text,
                    "section_title": section_title,
                    "context_template": context,
                }
            )

        return chunks


# Determine relative position bucket based on the chunk start time
def get_position(chunk_start: float, duration: float) -> str:
    if duration <= 0:
        return "beginning"
    pct = chunk_start / duration
    for low, high, label in BUCKETS:
        if low <= pct < high:
            return label
    return "end"


# Identify the overarching topic segment that covers the chunk's midpoint
def get_section_title(midpoint: float, segments: list[dict] | None) -> str:
    if not segments:
        return ""
    for seg in segments:
        if seg["start_time"] <= midpoint <= seg["end_time"]:
            return str(seg.get("title", ""))
    return ""
