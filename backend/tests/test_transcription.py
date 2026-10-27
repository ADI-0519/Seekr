import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest
from app.services.transcription import TranscriptionError, TranscriptionService

pytestmark = pytest.mark.integration


def make_word(word="hello", start=0.0, end=0.5, probability=0.95):
    w = MagicMock()
    w.word = word
    w.start = start
    w.end = end
    w.probability = probability
    return w


def make_segment(words):
    seg = MagicMock()
    seg.words = words
    return seg


def model_returning(words):
    model = MagicMock()
    model.transcribe.return_value = (iter([make_segment(words)]), MagicMock())
    return model


def wav_file():
    # minimal temp file so os.path.isfile passes
    f = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    f.write(b"\x00" * 44)
    f.close()
    return f.name


class TestWordDictStructure:
    @patch("faster_whisper.WhisperModel")
    def test_returns_correct_keys(self, MockModel):
        MockModel.return_value = model_returning(
            [
                make_word("the", 0.0, 0.2, 0.99),
                make_word("cat", 0.3, 0.6, 0.95),
            ]
        )
        svc = TranscriptionService("tiny", device="cpu")
        path = wav_file()
        try:
            result = svc.transcribe(path)
        finally:
            os.unlink(path)

        assert len(result) == 2
        for item in result:
            assert set(item.keys()) == {"word", "start", "end", "probability"}

    @patch("faster_whisper.WhisperModel")
    def test_values_match_whisper_output(self, MockModel):
        MockModel.return_value = model_returning([make_word("gradient", 1.23, 1.89, 0.87)])
        svc = TranscriptionService("tiny", device="cpu")
        path = wav_file()
        try:
            result = svc.transcribe(path)
        finally:
            os.unlink(path)

        assert result[0]["word"] == "gradient"
        assert result[0]["start"] == 1.23
        assert result[0]["end"] == 1.89
        assert result[0]["probability"] == 0.87

    @patch("faster_whisper.WhisperModel")
    def test_segment_with_none_words_skipped(self, MockModel):
        seg_none = MagicMock()
        seg_none.words = None
        seg_ok = make_segment([make_word("hello", 0.0, 0.3)])
        model = MagicMock()
        model.transcribe.return_value = (iter([seg_none, seg_ok]), MagicMock())
        MockModel.return_value = model

        svc = TranscriptionService("tiny", device="cpu")
        path = wav_file()
        try:
            result = svc.transcribe(path)
        finally:
            os.unlink(path)

        assert len(result) == 1


class TestTimestampMonotonicity:
    @patch("faster_whisper.WhisperModel")
    def test_clean_timestamps_no_warning(self, MockModel):
        MockModel.return_value = model_returning(
            [
                make_word("a", 0.0, 0.3),
                make_word("b", 0.4, 0.8),
                make_word("c", 0.9, 1.2),
            ]
        )
        svc = TranscriptionService("tiny", device="cpu")
        path = wav_file()
        try:
            with patch("app.services.transcription.log") as mock_log:
                svc.transcribe(path)
        finally:
            os.unlink(path)

        mock_log.warning.assert_not_called()

    @patch("faster_whisper.WhisperModel")
    def test_out_of_order_timestamps_logs_warning(self, MockModel):
        MockModel.return_value = model_returning(
            [
                make_word("a", 1.0, 1.3),
                make_word("b", 0.5, 0.8),  # starts before previous
            ]
        )
        svc = TranscriptionService("tiny", device="cpu")
        path = wav_file()
        try:
            with patch("app.services.transcription.log") as mock_log:
                svc.transcribe(path)
        finally:
            os.unlink(path)

        mock_log.warning.assert_called_once()
        assert "monotonicity" in mock_log.warning.call_args[0][0]


class TestTranscribeWithSegments:
    @patch("faster_whisper.WhisperModel")
    def test_returns_words_and_segment_ranges_with_valid_shape(self, MockModel):
        seg1 = MagicMock()
        seg1.start = 0.0
        seg1.end = 1.0
        seg1.words = [make_word("hello", 0.0, 0.5, 0.97)]

        seg2 = MagicMock()
        seg2.start = 1.0
        seg2.end = 2.0
        seg2.words = [make_word("world", 1.1, 1.6, 0.96)]

        model = MagicMock()
        model.transcribe.return_value = (iter([seg1, seg2]), MagicMock())
        MockModel.return_value = model

        svc = TranscriptionService("tiny", device="cpu")
        path = wav_file()
        try:
            words, ranges = svc.transcribe_with_segments(path)
        finally:
            os.unlink(path)

        assert isinstance(words, list)
        assert isinstance(ranges, list)
        assert len(words) == 2
        assert len(ranges) == 2
        assert words[0]["word"] == "hello"
        assert words[1]["word"] == "world"

        # Segment range sanity checks
        assert ranges == [(0.0, 1.0), (1.0, 2.0)]
        assert all(end >= start for start, end in ranges)
        assert ranges == sorted(ranges, key=lambda p: p[0])


class TestEmptyAudioRaisesError:
    @patch("faster_whisper.WhisperModel")
    def test_no_segments_raises(self, MockModel):
        model = MagicMock()
        model.transcribe.return_value = (iter([]), MagicMock())
        MockModel.return_value = model

        svc = TranscriptionService("tiny", device="cpu")
        path = wav_file()
        try:
            with pytest.raises(TranscriptionError, match="No words"):
                svc.transcribe(path)
        finally:
            os.unlink(path)

    @patch("faster_whisper.WhisperModel")
    def test_segment_with_empty_words_raises(self, MockModel):
        MockModel.return_value = model_returning([])
        svc = TranscriptionService("tiny", device="cpu")
        path = wav_file()
        try:
            with pytest.raises(TranscriptionError, match="No words"):
                svc.transcribe(path)
        finally:
            os.unlink(path)

    def test_missing_file_raises(self):
        svc = TranscriptionService("tiny", device="cpu")
        with pytest.raises(TranscriptionError, match="not found"):
            svc.transcribe("/nonexistent/audio.wav")


class TestGpuFallback:
    def test_falls_back_to_cpu_when_cuda_fails(self):
        with patch("faster_whisper.WhisperModel") as MockModel:
            good_model = MagicMock()
            MockModel.side_effect = [RuntimeError("CUDA unavailable"), good_model]

            svc = TranscriptionService("tiny", device="auto")
            svc.load_model()

        assert MockModel.call_count == 2
        first_device = (
            MockModel.call_args_list[0][1].get("device") or MockModel.call_args_list[0][0][1]
        )
        second_device = (
            MockModel.call_args_list[1][1].get("device") or MockModel.call_args_list[1][0][1]
        )
        assert first_device == "cuda"
        assert second_device == "cpu"

    def test_non_cuda_error_raises(self):
        with patch("faster_whisper.WhisperModel") as MockModel:
            MockModel.side_effect = RuntimeError("model files missing")

            svc = TranscriptionService("tiny", device="cpu")
            with pytest.raises(TranscriptionError):
                svc.load_model()

    def test_model_only_loaded_once(self):
        with patch("faster_whisper.WhisperModel") as MockModel:
            MockModel.return_value = MagicMock()

            svc = TranscriptionService("tiny", device="cpu")
            svc.load_model()
            svc.load_model()

        assert MockModel.call_count == 1


class TestTranscriptionPersistence:
    @patch("faster_whisper.WhisperModel")
    def test_correct_rows_inserted(self, MockModel):
        MockModel.return_value = model_returning(
            [
                make_word("deep", 0.0, 0.4, 0.98),
                make_word("learning", 0.5, 1.0, 0.96),
            ]
        )

        from app.tasks.video_tasks import run_transcription

        session = MagicMock()
        video = MagicMock()
        video.audio_path = "videos/1/audio.wav"
        session.get.return_value = video

        storage_mock = MagicMock()
        transcription_mock = MagicMock()
        words = [
            {"word": "deep", "start": 0.0, "end": 0.4, "probability": 0.98},
            {"word": "learning", "start": 0.5, "end": 1.0, "probability": 0.96},
        ]
        transcription_mock.transcribe_with_segments.return_value = (words, [(0.0, 1.0)])

        def fake_download(key, fobj):
            fobj.write(b"\x00" * 44)

        storage_mock.download_to_fileobj.side_effect = fake_download

        with (
            patch("app.tasks.video_tasks.StorageService", return_value=storage_mock),
            patch(
                "app.services.transcription.TranscriptionService", return_value=transcription_mock
            ),
        ):
            run_transcription(session, 1)

        assert session.add_all.call_count == 2

        word_rows = session.add_all.call_args_list[0][0][0]
        sentence_rows = session.add_all.call_args_list[1][0][0]

        assert len(word_rows) == 2
        assert word_rows[0].word == "deep"
        assert word_rows[0].start_time == 0.0
        assert word_rows[1].word == "learning"
        assert word_rows[1].probability == 0.96

        assert len(sentence_rows) >= 1
        assert all(hasattr(s, "text") for s in sentence_rows)

        session.commit.assert_called()

    def test_missing_audio_path_raises(self):
        from app.tasks.video_tasks import run_transcription

        session = MagicMock()
        video = MagicMock()
        video.audio_path = None
        session.get.return_value = video

        with pytest.raises(ValueError, match="audio_path"):
            run_transcription(session, 1)
