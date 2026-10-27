from __future__ import annotations

import json as _json
import logging
import os
import re
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# Safely import optional ML and computer vision dependencies
try:
    import torch as _torch
except ImportError:  # pragma: no cover
    _torch = None  # type: ignore[assignment]

torch: Any | None = _torch

try:
    from scenedetect import ContentDetector, SceneManager, open_video
except ImportError:  # pragma: no cover
    ContentDetector = None
    open_video = None
    SceneManager = None

_cv2_mod: Any | None
try:
    import cv2 as _cv2_imported

    _cv2_mod = _cv2_imported
except ImportError:  # pragma: no cover
    _cv2_mod = None

cv2: Any | None = _cv2_mod

try:
    import easyocr
except ImportError:  # pragma: no cover
    easyocr = None

log = logging.getLogger(__name__)

SCENE_THRESHOLD = 1.5
FIXED_INTERVAL_SECS = 30.0
MIN_SCENE_DURATION_SECS = 1.0


# Custom exception for failures during visual processing
class SlideExtractionError(Exception):
    pass


# Data structure representing a distinct visual segment in the video
@dataclass(frozen=True)
class SceneRange:
    start_time: float
    end_time: float


# Data structure holding the extracted image and parsed text for a specific slide
@dataclass(frozen=True)
class SlideFrameResult:
    frame_path: str
    ocr_text: str
    start_time: float
    end_time: float


# Service class to identify presentation slides and extract textual content via OCR
class SlideExtractor:
    def __init__(self):
        self.reader = None

    # Initialize the EasyOCR model, utilizing GPU acceleration if available
    def load_reader(self):
        if easyocr is None:
            raise SlideExtractionError("easyocr is not installed")
        if self.reader is None:
            if torch is not None:
                use_gpu = torch.cuda.is_available()
            else:
                use_gpu = False

            self.reader = easyocr.Reader(["en"], gpu=use_gpu)

        return self.reader

    # Analyze the video file to identify boundaries where visual content changes significantly
    def detect_scenes(self, video_path: str) -> list[SceneRange]:
        video_path_obj = Path(video_path)
        if not video_path_obj.is_file():
            raise SlideExtractionError(f"Input file does not exist: {video_path}")

        if open_video is None or SceneManager is None or ContentDetector is None:
            raise SlideExtractionError(
                "scenedetect is not installed. " "Install with: pip install scenedetect[opencv]"
            )

        import time

        video = open_video(video_path)
        scene_manager = SceneManager()
        scene_manager.add_detector(ContentDetector(threshold=SCENE_THRESHOLD))

        last_print = time.time()
        start_time = last_print
        total_frames = video.duration.get_frames() if getattr(video, "duration", None) else 0

        # Output progress updates periodically during lengthy detection operations
        def progress_callback(image, frame_num):
            nonlocal last_print
            now = time.time()
            if now - last_print >= 10.0:
                if total_frames > 0:
                    pct = (frame_num / float(total_frames)) * 100.0
                    log.info(
                        "Slide extraction progress: %.1f%% (%d/%d frames)",
                        pct,
                        frame_num,
                        total_frames,
                    )
                else:
                    log.info("Slide extraction progress: %d frames processed", frame_num)
                last_print = now

        scene_manager.detect_scenes(video, show_progress=False, callback=progress_callback)
        now = time.time()
        if now - start_time >= 10.0:
            if total_frames > 0:
                log.info(
                    "Slide extraction progress: 100.0%% (%d/%d frames)", total_frames, total_frames
                )
            else:
                log.info("Slide extraction progress: Complete")
        scene_list = scene_manager.get_scene_list()

        # Fall back to a fixed temporal interval if the video lacks distinct visual transitions
        if not scene_list:
            log.info(
                "No scenes detected in %s — falling back to %ss interval sampling",
                video_path,
                FIXED_INTERVAL_SECS,
            )
            return self.fixed_interval_scenes(video_path)

        scenes: list[SceneRange] = []
        for start_tc, end_tc in scene_list:
            start_s = start_tc.get_seconds()
            end_s = end_tc.get_seconds()
            if (end_s - start_s) >= MIN_SCENE_DURATION_SECS:
                scenes.append(SceneRange(start_time=start_s, end_time=end_s))

        # Fall back to a fixed temporal interval if all detected transitions were micro-scenes
        if not scenes:
            log.info(
                "All %d scenes were shorter than %.1fs — using interval fallback",
                len(scene_list),
                MIN_SCENE_DURATION_SECS,
            )
            return self.fixed_interval_scenes(video_path)

        log.info("Detected %d scenes in %s", len(scenes), video_path)
        return scenes

    # Generate synthetic scene boundaries at a strict, fixed interval
    def fixed_interval_scenes(self, video_path: str) -> list[SceneRange]:
        duration = self.probe_duration(video_path)
        if duration <= 0:
            raise SlideExtractionError(f"Could not determine duration of {video_path}")

        scenes: list[SceneRange] = []
        t = 0.0
        while t < duration:
            end = min(t + FIXED_INTERVAL_SECS, duration)
            scenes.append(SceneRange(start_time=t, end_time=end))
            t += FIXED_INTERVAL_SECS

        log.info("Fixed-interval fallback produced %d scenes", len(scenes))
        return scenes

    # Invoke ffmpeg to extract a single JPEG image at the specified timestamp
    def extract_frame(self, video_path: str, timestamp: float) -> str:
        fd, jpg_path = tempfile.mkstemp(suffix=".jpg")
        os.close(fd)

        cmd = [
            "ffmpeg",
            "-y",
            "-ss",
            str(timestamp),
            "-i",
            str(video_path),
            "-vframes",
            "1",
            "-q:v",
            "2",
            jpg_path,
        ]
        log.debug("Extracting frame: %s", " ".join(cmd))

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60,
            )
        except subprocess.TimeoutExpired as exc:
            self.cleanup(jpg_path)
            raise SlideExtractionError("ffmpeg frame extraction timed out") from exc

        if result.returncode != 0:
            self.cleanup(jpg_path)
            raise SlideExtractionError(
                f"ffmpeg frame extraction failed (rc={result.returncode}): "
                f"{result.stderr[:500]}"
            )

        if not os.path.isfile(jpg_path) or os.path.getsize(jpg_path) == 0:
            self.cleanup(jpg_path)
            raise SlideExtractionError("Extracted frame is empty or missing")

        return jpg_path

    # Extract a representative image frame for every detected scene
    def extract_frames(
        self, video_path: str, scenes: list[SceneRange]
    ) -> list[tuple[str, SceneRange]]:
        results: list[tuple[str, SceneRange]] = []
        for scene in scenes:
            midpoint = (scene.start_time + scene.end_time) / 2.0
            frame_path = self.extract_frame(video_path, midpoint)
            results.append((frame_path, scene))
        return results

    # Apply computer vision techniques to enhance image text legibility prior to OCR
    def preprocess_frame(self, frame_path: str):
        if cv2 is None:
            raise SlideExtractionError("opencv-python is not installed.")

        img = cv2.imread(frame_path)
        if img is None:
            raise SlideExtractionError(f"Could not read image: {frame_path}")

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # upscale if frame is small
        h, w = gray.shape
        if w < 1280:
            scale = 1280 / w
            gray = cv2.resize(gray, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_CUBIC)

        # clahe boosts local contrast without binarizing the image
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)

        # sharpen to help EasyOCR distinguish similar chars (e.g. 'c'/'e', 'n'/'m')
        import numpy as np

        sharpen = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]], dtype=np.float32)
        return cv2.filter2D(enhanced, -1, sharpen)

    # Read and digitize text from the image file
    def ocr_frame(self, frame_path: str) -> str:
        if easyocr is None:
            raise SlideExtractionError(
                "easyocr is not installed. Install with: pip install easyocr"
            )

        preprocessed = self.preprocess_frame(frame_path)

        reader = self.load_reader()
        results = reader.readtext(preprocessed)

        raw_lines = [text for (_, text, conf) in results if conf > 0.4]
        raw_text = "\n".join(raw_lines)
        return self.cleanup_ocr_text(raw_text)

    # Filter out formatting artifacts, punctuation noise, and duplicate strings
    @staticmethod
    def cleanup_ocr_text(raw: str) -> str:
        if not raw:
            return ""

        lines = raw.split("\n")
        cleaned: list[str] = []
        seen: set[str] = set()

        for line in lines:
            line = line.strip()

            # skip empty or near-empty lines
            if not line:
                continue

            # drop punctuation-only or single-char noise
            if len(line) <= 1 or re.fullmatch(r"[^\w]+", line):
                continue

            # case-insensitive deduplication
            key = line.lower()
            if key in seen:
                continue
            seen.add(key)

            cleaned.append(line)

        return "\n".join(cleaned).strip()

    # Orchestrate the entire visual pipeline from scene detection to text extraction
    def process_video(self, video_path: str) -> list[SlideFrameResult]:
        scenes = self.detect_scenes(video_path)
        frame_scene_pairs = self.extract_frames(video_path, scenes)

        results: list[SlideFrameResult] = []
        for frame_path, scene in frame_scene_pairs:
            try:
                ocr_text = self.ocr_frame(frame_path)
            except SlideExtractionError:
                log.warning(
                    "OCR failed for frame at %.1fs, storing without text",
                    scene.start_time,
                    exc_info=True,
                )
                ocr_text = ""

            results.append(
                SlideFrameResult(
                    frame_path=frame_path,
                    ocr_text=ocr_text,
                    start_time=scene.start_time,
                    end_time=scene.end_time,
                )
            )

        log.info(
            "Slide extraction complete: %d frames from %s",
            len(results),
            video_path,
        )
        return results

    # Remove temporary image files from the filesystem
    @staticmethod
    def cleanup(*paths: str) -> None:
        for p in paths:
            try:
                os.unlink(p)
            except OSError:
                pass

    # Retrieve total video length in seconds using ffprobe
    def probe_duration(self, file_path: str) -> float:
        cmd = [
            "ffprobe",
            "-v",
            "quiet",
            "-print_format",
            "json",
            "-show_format",
            file_path,
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        except subprocess.TimeoutExpired as exc:
            raise SlideExtractionError("ffprobe timed out") from exc

        if result.returncode != 0:
            raise SlideExtractionError(
                f"ffprobe failed (rc={result.returncode}): {result.stderr[:300]}"
            )
        try:
            data = _json.loads(result.stdout)
            return float(data["format"]["duration"])
        except (KeyError, ValueError) as exc:
            raise SlideExtractionError(f"Could not parse video duration: {exc}") from exc
