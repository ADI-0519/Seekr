import json
import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest
from app.services.slide_extraction import (
    FIXED_INTERVAL_SECS,
    SceneRange,
    SlideExtractionError,
    SlideExtractor,
    SlideFrameResult,
)


def ffprobe_duration_json(duration: float = 120.0) -> str:
    return json.dumps({"format": {"duration": str(duration)}})


def mock_ffprobe_run(duration: float = 120.0):
    def side_effect(cmd, **kwargs):
        mock = MagicMock()
        mock.returncode = 0
        mock.stderr = ""
        if cmd[0] == "ffprobe":
            mock.stdout = ffprobe_duration_json(duration)
        else:
            # ffmpeg frame extraction
            mock.stdout = ""
        return mock

    return side_effect


def make_fake_scene_list(ranges: list[tuple[float, float]]):
    scenes = []
    for start, end in ranges:
        start_tc = MagicMock()
        start_tc.get_seconds.return_value = start
        end_tc = MagicMock()
        end_tc.get_seconds.return_value = end
        scenes.append((start_tc, end_tc))
    return scenes


# Tests for fallback to fixed-interval scene detection when no scenes are detected
class TestFallbackToFixedInterval:
    @patch("app.services.slide_extraction.subprocess.run")
    def test_empty_scene_list_uses_interval_fallback(self, mock_run, tmp_path):
        src = tmp_path / "lecture.mp4"
        src.write_bytes(b"fake-video")

        duration = 120.0
        mock_run.side_effect = mock_ffprobe_run(duration)

        mock_video = MagicMock()
        mock_scene_manager = MagicMock()
        mock_scene_manager.get_scene_list.return_value = []

        with (
            patch("app.services.slide_extraction.open_video", return_value=mock_video),
            patch("app.services.slide_extraction.SceneManager", return_value=mock_scene_manager),
            patch("app.services.slide_extraction.ContentDetector"),
        ):
            extractor = SlideExtractor()
            scenes = extractor.detect_scenes(str(src))

        expected_count = int(duration / FIXED_INTERVAL_SECS)
        if duration % FIXED_INTERVAL_SECS:
            expected_count += 1

        assert len(scenes) == expected_count
        assert all(isinstance(s, SceneRange) for s in scenes)

        # Verify intervals are correct
        assert scenes[0].start_time == 0.0
        assert scenes[0].end_time == FIXED_INTERVAL_SECS

    @patch("app.services.slide_extraction.subprocess.run")
    def test_fallback_covers_entire_duration(self, mock_run, tmp_path):
        src = tmp_path / "lecture.mp4"
        src.write_bytes(b"fake-video")

        duration = 95.0
        mock_run.side_effect = mock_ffprobe_run(duration)

        mock_video = MagicMock()
        mock_scene_manager = MagicMock()
        mock_scene_manager.get_scene_list.return_value = []

        with (
            patch("app.services.slide_extraction.open_video", return_value=mock_video),
            patch("app.services.slide_extraction.SceneManager", return_value=mock_scene_manager),
            patch("app.services.slide_extraction.ContentDetector"),
        ):
            extractor = SlideExtractor()
            scenes = extractor.detect_scenes(str(src))

        assert scenes[0].start_time == 0.0
        assert scenes[-1].end_time == duration


class TestOcrCleanupDedupeRules:
    def test_duplicate_lines_removed(self):
        raw = "Introduction\nOverview\nIntroduction\nIntroduction\nDetails"
        result = SlideExtractor.cleanup_ocr_text(raw)
        lines = result.split("\n")
        assert lines.count("Introduction") == 1
        assert "Overview" in lines
        assert "Details" in lines

    def test_case_insensitive_dedup(self):
        raw = "Hello World\nhello world\nHELLO WORLD"
        result = SlideExtractor.cleanup_ocr_text(raw)
        assert result.count("Hello World") == 1 or result.count("hello world") == 1

        # Only one variant should survive
        assert len(result.split("\n")) == 1

    def test_punctuation_only_lines_removed(self):
        raw = "Real content\n---\n...\n!!!\nMore content"
        result = SlideExtractor.cleanup_ocr_text(raw)
        lines = result.split("\n")
        assert "Real content" in lines
        assert "More content" in lines
        assert "---" not in lines
        assert "..." not in lines

    def test_single_char_lines_removed(self):
        raw = "Title\nA\n.\nBody text"
        result = SlideExtractor.cleanup_ocr_text(raw)
        lines = result.split("\n")
        assert "Title" in lines
        assert "Body text" in lines
        assert "A" not in lines

    def test_whitespace_stripped(self):
        raw = "  Leading spaces  \n  Trailing spaces  "
        result = SlideExtractor.cleanup_ocr_text(raw)
        lines = result.split("\n")
        assert lines[0] == "Leading spaces"
        assert lines[1] == "Trailing spaces"

    def test_empty_input_returns_empty(self):
        assert SlideExtractor.cleanup_ocr_text("") == ""
        assert SlideExtractor.cleanup_ocr_text("   ") == ""

    def test_blank_lines_collapsed(self):
        raw = "Line1\n\n\n\nLine2"
        result = SlideExtractor.cleanup_ocr_text(raw)

        # blank lines should be dropped, leaving just the content lines
        assert result == "Line1\nLine2"


class TestSceneDetection:
    def test_progress_callback_accepts_frame_timecode(self, tmp_path):
        src = tmp_path / "video.mp4"
        src.write_bytes(b"fake-video")

        mock_video = MagicMock()
        mock_video.duration.get_frames.return_value = 100
        mock_scene_manager = MagicMock()
        mock_scene_manager.get_scene_list.return_value = make_fake_scene_list([(0.0, 10.0)])

        class FrameTimecodeLike:
            frame_num = 50

        def run_detection(_video, *, show_progress, callback):
            assert show_progress is False
            callback(None, FrameTimecodeLike())

        mock_scene_manager.detect_scenes.side_effect = run_detection

        with (
            patch("app.services.slide_extraction.open_video", return_value=mock_video),
            patch("app.services.slide_extraction.SceneManager", return_value=mock_scene_manager),
            patch("app.services.slide_extraction.ContentDetector"),
            patch("time.time", side_effect=[0.0, 11.0, 11.0]),
            patch("app.services.slide_extraction.log") as mock_log,
        ):
            scenes = SlideExtractor().detect_scenes(str(src))

        assert scenes == [SceneRange(start_time=0.0, end_time=10.0)]
        mock_log.info.assert_any_call(
            "Slide extraction progress: %.1f%% (%d/%d frames)", 50.0, 50, 100
        )

    @patch("app.services.slide_extraction.subprocess.run")
    def test_scenes_parsed_correctly(self, mock_run, tmp_path):
        src = tmp_path / "video.mp4"
        src.write_bytes(b"fake-video")
        mock_run.side_effect = mock_ffprobe_run(90.0)

        fake_scenes = make_fake_scene_list([(0.0, 15.0), (15.0, 45.0), (45.0, 90.0)])

        mock_video = MagicMock()
        mock_scene_manager = MagicMock()
        mock_scene_manager.get_scene_list.return_value = fake_scenes

        with (
            patch("app.services.slide_extraction.open_video", return_value=mock_video),
            patch("app.services.slide_extraction.SceneManager", return_value=mock_scene_manager),
            patch("app.services.slide_extraction.ContentDetector"),
        ):
            extractor = SlideExtractor()
            scenes = extractor.detect_scenes(str(src))

        assert len(scenes) == 3
        assert scenes[0] == SceneRange(start_time=0.0, end_time=15.0)
        assert scenes[1] == SceneRange(start_time=15.0, end_time=45.0)
        assert scenes[2] == SceneRange(start_time=45.0, end_time=90.0)

    @patch("app.services.slide_extraction.subprocess.run")
    def test_short_scenes_filtered_out(self, mock_run, tmp_path):
        src = tmp_path / "video.mp4"
        src.write_bytes(b"fake-video")
        mock_run.side_effect = mock_ffprobe_run(10.5)

        # One normal scene of 10s and one very short scene of 0.5s
        fake_scenes = make_fake_scene_list([(0.0, 10.0), (10.0, 10.5)])

        mock_video = MagicMock()
        mock_scene_manager = MagicMock()
        mock_scene_manager.get_scene_list.return_value = fake_scenes

        with (
            patch("app.services.slide_extraction.open_video", return_value=mock_video),
            patch("app.services.slide_extraction.SceneManager", return_value=mock_scene_manager),
            patch("app.services.slide_extraction.ContentDetector"),
        ):
            extractor = SlideExtractor()
            scenes = extractor.detect_scenes(str(src))

        assert len(scenes) == 1
        assert scenes[0].end_time == 10.0

    def test_input_file_missing_raises(self):
        extractor = SlideExtractor()
        with pytest.raises(SlideExtractionError, match="does not exist"):
            extractor.detect_scenes("/nonexistent/video.mp4")


class TestFrameExtraction:
    @patch("app.services.slide_extraction.subprocess.run")
    def test_ffmpeg_command_has_correct_flags(self, mock_run, tmp_path):
        src = tmp_path / "video.mp4"
        src.write_bytes(b"fake-video")

        def side_effect(cmd, **kwargs):
            mock = MagicMock()
            mock.returncode = 0
            mock.stderr = ""
            mock.stdout = ""
            if cmd[0] == "ffmpeg":
                output_path = cmd[-1]
                with open(output_path, "wb") as f:
                    f.write(b"JPEG-data")
            return mock

        mock_run.side_effect = side_effect

        extractor = SlideExtractor()
        result = extractor.extract_frame(str(src), 42.5)

        call_args = mock_run.call_args[0][0]
        assert call_args[0] == "ffmpeg"
        assert "-ss" in call_args
        assert "42.5" in call_args
        assert "-vframes" in call_args
        assert "1" in call_args
        assert result.endswith(".jpg")

        if os.path.exists(result):
            os.unlink(result)

    @patch("app.services.slide_extraction.subprocess.run")
    def test_ffmpeg_failure_raises(self, mock_run, tmp_path):
        src = tmp_path / "video.mp4"
        src.write_bytes(b"fake-video")

        mock_run.return_value = MagicMock(returncode=1, stderr="Error", stdout="")

        extractor = SlideExtractor()
        with pytest.raises(SlideExtractionError, match="frame extraction failed"):
            extractor.extract_frame(str(src), 10.0)

    @patch("app.services.slide_extraction.subprocess.run")
    def test_extract_frames_uses_midpoint(self, mock_run, tmp_path):
        src = tmp_path / "video.mp4"
        src.write_bytes(b"fake-video")

        def side_effect(cmd, **kwargs):
            mock = MagicMock()
            mock.returncode = 0
            mock.stderr = ""
            mock.stdout = ""
            if cmd[0] == "ffmpeg":
                output_path = cmd[-1]
                with open(output_path, "wb") as f:
                    f.write(b"JPEG-data")
            return mock

        mock_run.side_effect = side_effect

        scenes = [
            SceneRange(start_time=0.0, end_time=20.0),
            SceneRange(start_time=20.0, end_time=60.0),
        ]

        extractor = SlideExtractor()
        results = extractor.extract_frames(str(src), scenes)

        assert len(results) == 2

        # midpoints should be 10.0 and 40.0
        calls = mock_run.call_args_list
        first_cmd = calls[0][0][0]
        second_cmd = calls[1][0][0]

        ss_idx_1 = first_cmd.index("-ss")
        assert first_cmd[ss_idx_1 + 1] == "10.0"

        ss_idx_2 = second_cmd.index("-ss")
        assert second_cmd[ss_idx_2 + 1] == "40.0"

        for frame_path, _ in results:
            if os.path.exists(frame_path):
                os.unlink(frame_path)


class TestPreprocessFrame:
    @patch("app.services.slide_extraction.cv2")
    def test_preprocessing_pipeline_order(self, mock_cv2, tmp_path):
        frame = tmp_path / "slide.jpg"
        frame.write_bytes(b"fake-jpeg")

        mock_img = MagicMock()
        mock_cv2.imread.return_value = mock_img
        mock_gray = MagicMock()
        mock_gray.shape = (720, 1280)  # already 1280px wide so no upscale branch
        mock_cv2.cvtColor.return_value = mock_gray
        mock_clahe = MagicMock()
        mock_cv2.createCLAHE.return_value = mock_clahe
        mock_enhanced = MagicMock()
        mock_clahe.apply.return_value = mock_enhanced
        mock_sharpened = MagicMock()
        mock_cv2.filter2D.return_value = mock_sharpened

        extractor = SlideExtractor()
        result = extractor.preprocess_frame(str(frame))

        mock_cv2.imread.assert_called_once_with(str(frame))
        mock_cv2.cvtColor.assert_called_once_with(mock_img, mock_cv2.COLOR_BGR2GRAY)
        mock_cv2.createCLAHE.assert_called_once()
        mock_clahe.apply.assert_called_once_with(mock_gray)
        mock_cv2.filter2D.assert_called_once()
        assert result is mock_sharpened

    @patch("app.services.slide_extraction.cv2")
    def test_unreadable_image_raises(self, mock_cv2):
        mock_cv2.imread.return_value = None

        extractor = SlideExtractor()
        with pytest.raises(SlideExtractionError, match="Could not read image"):
            extractor.preprocess_frame("/nonexistent.jpg")


class TestCleanupTempFiles:
    def test_cleanup_removes_existing_files(self):
        fd1, p1 = tempfile.mkstemp(suffix=".jpg")
        os.close(fd1)
        fd2, p2 = tempfile.mkstemp(suffix=".jpg")
        os.close(fd2)

        assert os.path.exists(p1)
        assert os.path.exists(p2)

        SlideExtractor.cleanup(p1, p2)

        assert not os.path.exists(p1)
        assert not os.path.exists(p2)

    def test_cleanup_ignores_missing_files(self):
        SlideExtractor.cleanup("/tmp/no-such-slide-12345.jpg")


class TestProcessVideo:
    def test_process_video_returns_results(self, tmp_path):
        src = tmp_path / "lecture.mp4"
        src.write_bytes(b"fake-video")

        fake_scenes = [
            SceneRange(start_time=0.0, end_time=30.0),
            SceneRange(start_time=30.0, end_time=60.0),
        ]

        extractor = SlideExtractor()

        with (
            patch.object(extractor, "detect_scenes", return_value=fake_scenes),
            patch.object(extractor, "extract_frames") as mock_extract,
            patch.object(extractor, "ocr_frame", return_value="Slide text"),
        ):
            frame1 = tmp_path / "frame0.jpg"
            frame1.write_bytes(b"jpeg1")
            frame2 = tmp_path / "frame1.jpg"
            frame2.write_bytes(b"jpeg2")

            mock_extract.return_value = [
                (str(frame1), fake_scenes[0]),
                (str(frame2), fake_scenes[1]),
            ]

            results = extractor.process_video(str(src))

        assert len(results) == 2
        assert all(isinstance(r, SlideFrameResult) for r in results)
        assert results[0].ocr_text == "Slide text"
        assert results[0].start_time == 0.0
        assert results[1].end_time == 60.0

    def test_ocr_failure_stores_empty_text(self, tmp_path):
        src = tmp_path / "lecture.mp4"
        src.write_bytes(b"fake-video")

        fake_scenes = [SceneRange(start_time=0.0, end_time=30.0)]

        extractor = SlideExtractor()

        with (
            patch.object(extractor, "detect_scenes", return_value=fake_scenes),
            patch.object(extractor, "extract_frames") as mock_extract,
            patch.object(
                extractor,
                "ocr_frame",
                side_effect=SlideExtractionError("OCR failed"),
            ),
        ):
            frame = tmp_path / "frame0.jpg"
            frame.write_bytes(b"jpeg")
            mock_extract.return_value = [(str(frame), fake_scenes[0])]

            results = extractor.process_video(str(src))

        assert len(results) == 1
        assert results[0].ocr_text == ""
