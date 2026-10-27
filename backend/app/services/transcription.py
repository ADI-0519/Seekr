import logging
import os
from typing import Any

log = logging.getLogger(__name__)


# Custom exception for errors occurring during the transcription process
class TranscriptionError(Exception):
    pass


# Service class to manage AI model loading and audio-to-text conversion
class TranscriptionService:
    def __init__(self, model_name: str = "large-v3-turbo", device: str = "auto"):
        self._model_name = model_name
        self._device = device
        self._model: Any = None

    # Load the Whisper model into memory, prioritizing GPU over CPU
    def load_model(self):
        if self._model is not None:
            return

        import faster_whisper

        device = self._device
        if device == "auto":
            device = "cuda"

        try:
            # Attempt to load with high-performance GPU settings
            self._model = faster_whisper.WhisperModel(
                self._model_name, device=device, compute_type="float16", local_files_only=True
            )
            log.info("loaded whisper model %s on %s", self._model_name, device)
        except Exception as e:
            if device == "cuda":
                # Fall back to CPU with 8-bit quantization if CUDA initialization fails
                log.warning("cuda unavailable (%s), falling back to cpu", e)
                self._model = faster_whisper.WhisperModel(
                    self._model_name, device="cpu", compute_type="int8", local_files_only=True
                )
                log.info("loaded whisper model %s on cpu", self._model_name)
            else:
                raise TranscriptionError(f"Failed to load model: {e}") from e

    # Pre-load the model to avoid latency during the first transcription request
    def warmup(self) -> None:
        self.load_model()

    # Transcribe audio and return only the flattened word-level data
    def transcribe(self, wav_path: str) -> list[dict[str, Any]]:
        words, _segment_ranges = self.transcribe_with_segments(wav_path)
        return words

    # Generate a timed word list and original segment boundaries from an audio file
    def transcribe_with_segments(
        self, wav_path: str
    ) -> tuple[list[dict[str, Any]], list[tuple[float, float]]]:
        if not os.path.isfile(wav_path):
            raise TranscriptionError(f"Audio file not found: {wav_path}")

        self.load_model()

        # Execute transcription with word-level timestamps enabled
        segments, _info = self._model.transcribe(wav_path, word_timestamps=True)
        words, segment_ranges = self.collect_words_and_segment_ranges(segments)

        if not words:
            raise TranscriptionError("No words transcribed - audio may be silent or corrupt")

        # Verify that word timestamps follow a logical chronological order
        for i in range(1, len(words)):
            if words[i]["start"] < words[i - 1]["start"]:
                log.warning(
                    "timestamp monotonicity violation at word %d: %.3f < %.3f",
                    i,
                    words[i]["start"],
                    words[i - 1]["start"],
                )

        log.info(
            "transcribed %d words across %d whisper segments from %s",
            len(words),
            len(segment_ranges),
            wav_path,
        )
        return words, segment_ranges

    # Flatten nested Whisper segments into a simple word list and a timing range list
    def collect_words_and_segment_ranges(
        self, segments
    ) -> tuple[list[dict[str, Any]], list[tuple[float, float]]]:
        words: list[dict[str, Any]] = []
        segment_ranges: list[tuple[float, float]] = []

        for segment in segments:
            # Extract high-level segment boundaries
            seg_start = float(getattr(segment, "start", 0.0) or 0.0)
            seg_end = float(getattr(segment, "end", seg_start) or seg_start)
            if seg_end < seg_start:
                seg_end = seg_start
            segment_ranges.append((seg_start, seg_end))

            if segment.words is None:
                continue

            # Extract granular word-level metadata
            for w in segment.words:
                words.append(
                    {
                        "word": w.word,
                        "start": w.start,
                        "end": w.end,
                        "probability": w.probability,
                    }
                )

        return words, segment_ranges


# Global singleton instance for use across worker processes
_instance: TranscriptionService | None = None


# Retrieve or initialize the global transcription service instance
def get_transcription_service(
    model_name: str = "large-v3-turbo", device: str = "auto"
) -> TranscriptionService:
    global _instance
    if _instance is None:
        _instance = TranscriptionService(model_name=model_name, device=device)
    return _instance
