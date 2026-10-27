from unittest.mock import MagicMock, patch

import pytest
from app.services.notes_generation import clean_latex
from app.services.summary_generation import (
    ADJACENT_EXCERPT_WORDS,
    MAX_INPUT_CHARS,
    MAX_SLIDE_CHARS,
    MAX_WORDS,
    MIN_WORDS,
    SUMMARY_MAX_OUTPUT_TOKENS,
    SummaryGenerator,
    SummaryInput,
    SummaryResult,
    SummaryValidationError,
    build_user_prompt,
    count_sentences,
    count_words,
    retry_instruction,
    validate_summary,
    validate_summary_lenient,
)


def make_input(**overrides) -> SummaryInput:
    defaults = dict(
        segment_id=1,
        title="Introduction to Neural Networks",
        transcript_text=(
            "Today we will discuss neural networks. A neural network is a "
            "computational model inspired by biological neurons. It consists of "
            "layers of interconnected nodes that transform input data into useful "
            "outputs through learned weights. The learning process uses an "
            "algorithm called backpropagation to adjust these weights."
        ),
        start_time=0.0,
        end_time=120.0,
        slide_text="",
        prev_title="",
        next_title="",
        prev_excerpt="",
        next_excerpt="",
    )
    defaults.update(overrides)
    return SummaryInput(**defaults)  # type: ignore[arg-type]


def mock_openai_response(text: str):
    response = MagicMock()
    response.output_text = text
    return response


class TestSentenceCounting:
    def test_two_sentences(self):
        assert count_sentences("First sentence. Second sentence.") == 2

    def test_three_sentences(self):
        assert count_sentences("One. Two. Three.") == 3

    def test_question_mark(self):
        assert count_sentences("What is this? It is a test.") == 2

    def test_exclamation(self):
        assert count_sentences("Wow! That is great. Really great.") == 3

    def test_single_sentence(self):
        assert count_sentences("Just one sentence here.") == 1


class TestWordCounting:
    def test_simple(self):
        assert count_words("hello world") == 2

    def test_realistic(self):
        assert count_words("Neural networks consist of interconnected layers.") == 6


class TestValidation:
    def test_valid_two_sentences(self):
        text = (
            "Neural networks are computational models inspired by the brain. "
            "They learn by adjusting weights through backpropagation."
        )
        sc, wc = validate_summary(text)
        assert sc == 2
        assert MIN_WORDS <= wc <= MAX_WORDS

    def test_valid_three_sentences(self):
        text = (
            "Neural networks are computational models. "
            "They consist of layers of connected nodes. "
            "Training uses backpropagation to adjust weights."
        )
        sc, wc = validate_summary(text)
        assert sc == 3

    def test_rejects_one_sentence(self):
        with pytest.raises(SummaryValidationError, match="Too few sentences"):
            validate_summary("Just one sentence here.")

    def test_rejects_four_sentences(self):
        with pytest.raises(SummaryValidationError, match="Too many sentences"):
            validate_summary("One. Two. Three. Four sentences here.")

    def test_rejects_empty(self):
        with pytest.raises(SummaryValidationError, match="Empty summary"):
            validate_summary("")

    def test_rejects_whitespace_only(self):
        with pytest.raises(SummaryValidationError, match="Empty summary"):
            validate_summary("   \n  ")

    def test_rejects_too_few_words(self):
        with pytest.raises(SummaryValidationError, match="Too few words"):
            validate_summary("Short. Too short.")

    def test_rejects_too_many_words(self):
        long_text = " ".join(["word"] * 60) + ". " + " ".join(["word"] * 70) + "."
        with pytest.raises(SummaryValidationError, match="Too many words"):
            validate_summary(long_text)


class TestShortSegments:
    def test_very_short_segment_gets_fallback(self):
        seg = make_input(transcript_text="Hi.", title="Intro")
        generator = SummaryGenerator()
        result = generator.generate(seg)
        assert isinstance(result, SummaryResult)
        assert "Intro" in result.summary

    def test_empty_transcript_gets_fallback(self):
        seg = make_input(transcript_text="", title="Empty")
        generator = SummaryGenerator()
        result = generator.generate(seg)
        assert isinstance(result, SummaryResult)

    def test_short_segment_fallback_passes_word_count(self):
        seg = make_input(transcript_text="Hi.", title="Intro")
        generator = SummaryGenerator()
        result = generator.generate(seg)
        assert result.word_count >= MIN_WORDS

    def test_short_segment_fallback_has_correct_sentence_count(self):
        seg = make_input(transcript_text="Hi.", title="Intro")
        generator = SummaryGenerator()
        result = generator.generate(seg)
        assert 2 <= result.sentence_count <= 3


class TestLongSegments:
    def test_prompt_truncates_long_transcript(self):
        long_text = "word " * 10_000
        seg = make_input(transcript_text=long_text)
        prompt = build_user_prompt(seg)
        assert "[truncated]" in prompt
        assert len(prompt) < MAX_INPUT_CHARS + 500

    def test_prompt_has_no_duration_line(self):
        seg = make_input(start_time=60.0, end_time=180.0)
        prompt = build_user_prompt(seg)
        assert "Duration" not in prompt
        assert "60s" not in prompt


class TestContextPrompt:
    def test_prev_excerpt_shown_with_title(self):
        seg = make_input(
            prev_title="Linear Algebra Basics",
            prev_excerpt="Vectors and matrices were introduced along with dot product operations.",
        )
        prompt = build_user_prompt(seg)
        assert "Linear Algebra Basics" in prompt
        assert "Vectors and matrices" in prompt

    def test_next_excerpt_shown_with_title(self):
        seg = make_input(
            next_title="Optimisation Methods",
            next_excerpt="Gradient descent is an iterative algorithm for minimising a loss function.",
        )
        prompt = build_user_prompt(seg)
        assert "Optimisation Methods" in prompt
        assert "Gradient descent is an iterative" in prompt

    def test_neither_shown_when_empty(self):
        seg = make_input(prev_title="", next_title="", prev_excerpt="", next_excerpt="")
        prompt = build_user_prompt(seg)
        assert "Previous section" not in prompt
        assert "Next section" not in prompt

    def test_first_segment_has_no_prev(self):
        seg = make_input(
            prev_title="",
            prev_excerpt="",
            next_title="Backpropagation",
            next_excerpt="The chain rule allows gradients to flow.",
        )
        prompt = build_user_prompt(seg)
        assert "Previous section" not in prompt
        assert "Backpropagation" in prompt

    def test_last_segment_has_no_next(self):
        seg = make_input(
            prev_title="Gradient Descent",
            prev_excerpt="Weights are updated proportional to gradient.",
            next_title="",
            next_excerpt="",
        )
        prompt = build_user_prompt(seg)
        assert "Gradient Descent" in prompt
        assert "Next section" not in prompt

    def test_segment_title_always_present(self):
        seg = make_input(prev_title="A", next_title="B")
        prompt = build_user_prompt(seg)
        assert "Segment title: Introduction to Neural Networks" in prompt

    def test_prev_title_only_when_no_excerpt(self):
        # if title exists but excerpt is empty, still show the title as a header
        seg = make_input(prev_title="Linear Algebra", prev_excerpt="")
        prompt = build_user_prompt(seg)
        assert "Previous section: Linear Algebra" in prompt

    def test_next_title_only_when_no_excerpt(self):
        seg = make_input(next_title="Optimisation", next_excerpt="")
        prompt = build_user_prompt(seg)
        assert "Next section: Optimisation" in prompt

    def test_excerpt_word_count_matches_constant(self):
        # _excerpt_tail/_excerpt_head in video_tasks uses ADJACENT_EXCERPT_WORDS -> excerpts shouldn't exceed that many words
        long_text = " ".join(f"word{i}" for i in range(500))
        words = long_text.split()
        tail = " ".join(words[-ADJACENT_EXCERPT_WORDS:])
        head = " ".join(words[:ADJACENT_EXCERPT_WORDS])
        assert len(tail.split()) == ADJACENT_EXCERPT_WORDS
        assert len(head.split()) == ADJACENT_EXCERPT_WORDS


class TestSlideTextPrompt:
    def test_included_when_present(self):
        seg = make_input(slide_text="Learning Rate \u03b7\nGradient Descent Steps")
        prompt = build_user_prompt(seg)
        assert "Slide text" in prompt
        assert "Learning Rate" in prompt

    def test_omitted_when_empty(self):
        seg = make_input(slide_text="")
        prompt = build_user_prompt(seg)
        assert "Slide text" not in prompt

    def test_omitted_when_whitespace_only(self):
        seg = make_input(slide_text="   \n  ")
        prompt = build_user_prompt(seg)
        assert "Slide text" not in prompt

    def test_truncated_when_long(self):
        seg = make_input(slide_text="word " * 500)
        prompt = build_user_prompt(seg)
        assert "[truncated]" in prompt
        assert len(prompt) < MAX_INPUT_CHARS + MAX_SLIDE_CHARS + 500


class TestGenerate:
    def test_successful_first_attempt(self):
        valid = (
            "Neural networks are computational models inspired by biological systems. "
            "They learn patterns from data by adjusting connection weights through backpropagation."
        )
        mock_client = MagicMock()
        mock_client.responses.create.return_value = mock_openai_response(valid)

        with patch("app.services.summary_generation.OpenAI", return_value=mock_client):
            generator = SummaryGenerator()
            result = generator.generate(make_input())

        assert result.summary == valid
        assert result.sentence_count == 2
        assert mock_client.responses.create.call_count == 1

    def test_retries_on_validation_failure(self):
        bad = "Just one sentence."
        good = (
            "Neural networks process data through layers of nodes. "
            "They are trained using backpropagation to minimize error."
        )
        mock_client = MagicMock()
        mock_client.responses.create.side_effect = [
            mock_openai_response(bad),
            mock_openai_response(good),
        ]

        with patch("app.services.summary_generation.OpenAI", return_value=mock_client):
            generator = SummaryGenerator(max_retries=2)
            result = generator.generate(make_input())

        assert result.sentence_count == 2
        assert mock_client.responses.create.call_count == 2

    def test_returns_last_output_after_exhausted_retries(self):
        one_sentence = (
            "Only one long sentence with enough words to pass the word count check easily enough."
        )
        mock_client = MagicMock()
        mock_client.responses.create.return_value = mock_openai_response(one_sentence)

        with patch("app.services.summary_generation.OpenAI", return_value=mock_client):
            generator = SummaryGenerator(max_retries=1)
            result = generator.generate(make_input())

        assert isinstance(result, SummaryResult)
        assert result.summary == one_sentence

    def test_strips_surrounding_quotes(self):
        quoted = '"Neural networks learn from data. They adjust weights iteratively."'
        mock_client = MagicMock()
        mock_client.responses.create.return_value = mock_openai_response(quoted)

        with patch("app.services.summary_generation.OpenAI", return_value=mock_client):
            generator = SummaryGenerator()
            result = generator.generate(make_input())

        assert not result.summary.startswith('"')

    def test_api_failure_returns_fallback(self):
        mock_client = MagicMock()
        mock_client.responses.create.side_effect = Exception("rate limit")

        with patch("app.services.summary_generation.OpenAI", return_value=mock_client):
            generator = SummaryGenerator()
            result = generator.generate(make_input())

        assert isinstance(result, SummaryResult)
        assert "Introduction to Neural Networks" in result.summary

    def test_client_reused_across_calls(self):
        valid = "Neural networks are computational models. " "They learn by adjusting weights."
        mock_client = MagicMock()
        mock_client.responses.create.return_value = mock_openai_response(valid)

        with patch("app.services.summary_generation.OpenAI", return_value=mock_client) as mock_cls:
            generator = SummaryGenerator()
            generator.generate(make_input(segment_id=1))
            generator.generate(make_input(segment_id=2))

        assert mock_cls.call_count == 1


class TestLenientValidation:
    def test_accepts_one_sentence_with_sufficient_words(self):
        text = (
            "Neural networks learn hierarchical representations directly from raw input data "
            "by iteratively adjusting weights during training."
        )
        sc, wc = validate_summary_lenient(text)
        assert sc == 1
        assert wc >= MIN_WORDS

    def test_rejects_empty(self):
        with pytest.raises(SummaryValidationError, match="Empty summary"):
            validate_summary_lenient("")

    def test_rejects_too_few_words(self):
        with pytest.raises(SummaryValidationError, match="Too few words"):
            validate_summary_lenient("Too short.")

    def test_accepts_over_word_limit(self):
        # lenient path has no upper word ceiling
        long_text = " ".join(["word"] * 90) + "."
        sc, wc = validate_summary_lenient(long_text)
        assert sc >= 1
        assert wc == 90

    def test_still_accepts_two_sentences(self):
        text = (
            "Neural networks learn rich representations from data across multiple layers in practice. "
            "They adjust weights through backpropagation to reduce prediction error over training steps."
        )
        sc, wc = validate_summary_lenient(text)
        assert sc == 2


class TestLenientValidationTiming:
    def test_lenient_path_accepts_one_sentence_at_attempt_4(self):
        # GPT consistently returns 1 sentence; strict validation rejects for first 3 attempts, accepts on 4th onward
        one_sentence = (
            "Neural networks are powerful models that learn hierarchical "
            "representations directly from raw data through gradient-based optimisation."
        )
        mock_client = MagicMock()
        mock_client.responses.create.return_value = mock_openai_response(one_sentence)

        with patch("app.services.summary_generation.OpenAI", return_value=mock_client):
            generator = SummaryGenerator(max_retries=5)
            result = generator.generate(make_input())

        assert result.summary == one_sentence
        assert result.sentence_count == 1
        assert mock_client.responses.create.call_count == 4

    def test_lenient_path_not_triggered_before_attempt_4(self):
        # 1-sentence response is returned as-is only after exhausting retries
        one_sentence = (
            "Neural networks are powerful models that learn hierarchical "
            "representations directly from raw data through gradient-based optimisation."
        )
        mock_client = MagicMock()
        mock_client.responses.create.return_value = mock_openai_response(one_sentence)

        with patch("app.services.summary_generation.OpenAI", return_value=mock_client):
            generator = SummaryGenerator(max_retries=2)
            result = generator.generate(make_input())

        # exhausted without lenient, returns last raw output as-is
        assert result.summary == one_sentence
        assert mock_client.responses.create.call_count == 3


class TestRetryInstruction:
    def test_too_many_sentences_tells_model_to_combine(self):
        msg = retry_instruction("Too many sentences: 4 (max 3)")
        assert "Combine" in msg or "combine" in msg

    def test_too_few_sentences_tells_model_to_expand(self):
        msg = retry_instruction("Too few sentences: 1 (min 2)")
        assert "2 or 3" in msg or "Expand" in msg

    def test_too_many_words_mentions_shortening(self):
        msg = retry_instruction("Too many words: 130 (max 120)")
        assert "Shorten" in msg or "shorten" in msg or "80" in msg

    def test_too_few_words_mentions_expanding(self):
        msg = retry_instruction("Too few words: 8 (min 15)")
        assert "15" in msg or "Expand" in msg or "expand" in msg

    def test_unknown_error_gives_generic_message(self):
        msg = retry_instruction("Empty summary")
        assert "2 or 3" in msg

    def test_max_output_tokens_is_2000(self):
        assert SUMMARY_MAX_OUTPUT_TOKENS == 2000


class TestEmptyRawFallback:
    def test_exhausted_retries_with_empty_response_uses_fallback(self):
        mock_client = MagicMock()
        mock_client.responses.create.return_value = mock_openai_response("")

        with patch("app.services.summary_generation.OpenAI", return_value=mock_client):
            generator = SummaryGenerator(max_retries=1)
            result = generator.generate(make_input())

        assert result.summary != ""
        assert "Introduction to Neural Networks" in result.summary


class TestGenerateAll:
    def test_generates_for_all_segments(self):
        valid = (
            "Key concepts and foundational ideas were introduced clearly in this part. "
            "The section covered essential foundational material needed for the rest of the course."
        )
        mock_client = MagicMock()
        mock_client.responses.create.return_value = mock_openai_response(valid)

        inputs = [make_input(segment_id=i) for i in range(5)]

        with patch("app.services.summary_generation.OpenAI", return_value=mock_client):
            generator = SummaryGenerator()
            results = generator.generate_all(inputs)

        assert len(results) == 5
        assert all(isinstance(r, SummaryResult) for r in results)
        assert mock_client.responses.create.call_count == 5

    def test_empty_input_returns_empty(self):
        generator = SummaryGenerator()
        assert generator.generate_all([]) == []

    def test_result_order_matches_input_order(self):
        # threads complete in arbitrary order, results must still be in input order
        summaries = {
            1: "Neural networks are models. They learn via backprop.",
            2: "Gradient descent minimises loss. It updates weights iteratively.",
            3: "Convolutional layers detect local features. They share weights across positions.",
        }
        mock_client = MagicMock()
        mock_client.responses.create.side_effect = [
            mock_openai_response(summaries[1]),
            mock_openai_response(summaries[2]),
            mock_openai_response(summaries[3]),
        ]

        inputs = [make_input(segment_id=i, title=f"Section {i}") for i in range(1, 4)]
        with patch("app.services.summary_generation.OpenAI", return_value=mock_client):
            generator = SummaryGenerator()
            results = generator.generate_all(inputs)

        assert [r.segment_id for r in results] == [1, 2, 3]


class TestGenerateOverview:
    def test_empty_input_returns_empty_string(self):
        assert SummaryGenerator().generate_overview([]) == ""

    def test_successful_response_returned(self):
        mock_client = MagicMock()
        mock_client.responses.create.return_value = mock_openai_response(
            "The lecture introduces greedy algorithms and applies them to graph problems. "
            "It covers minimum spanning trees in detail, proving correctness via exchange arguments."
        )

        with patch("app.services.summary_generation.OpenAI", return_value=mock_client):
            result = SummaryGenerator().generate_overview(
                [
                    ("Introduction", "Greedy algorithms build solutions step by step."),
                    (
                        "Minimum Spanning Trees",
                        "MSTs connect all nodes with minimum total edge weight.",
                    ),
                    ("Kruskal vs Prim", "Both algorithms find MSTs but differ in approach."),
                ]
            )

        assert "greedy" in result.lower() or "spanning" in result.lower()
        assert mock_client.responses.create.call_count == 1

    def test_api_failure_falls_back_to_titles(self):
        mock_client = MagicMock()
        mock_client.responses.create.side_effect = Exception("rate limit")

        segments = [
            ("Introduction", "Some summary."),
            ("Minimum Spanning Trees", "Another summary."),
        ]

        with patch("app.services.summary_generation.OpenAI", return_value=mock_client):
            result = SummaryGenerator().generate_overview(segments)

        # fallback joins titles so always something to display
        assert "Introduction" in result
        assert "Minimum Spanning Trees" in result

    def test_empty_api_response_falls_back_to_titles(self):
        mock_client = MagicMock()
        mock_client.responses.create.return_value = mock_openai_response("")

        segments = [("Graph Theory", "Covers basic graph concepts.")]

        with patch("app.services.summary_generation.OpenAI", return_value=mock_client):
            result = SummaryGenerator().generate_overview(segments)

        assert "Graph Theory" in result

    def test_too_many_sentences_triggers_retry(self):
        bad = "One. Two. Three. Four sentences here, too many."
        good = "Greedy algorithms build optimal solutions incrementally. MSTs are a classic application."
        mock_client = MagicMock()
        mock_client.responses.create.side_effect = [
            mock_openai_response(bad),
            mock_openai_response(good),
        ]

        with patch("app.services.summary_generation.OpenAI", return_value=mock_client):
            result = SummaryGenerator().generate_overview([("MSTs", "Minimum spanning trees.")])

        assert result == good
        assert mock_client.responses.create.call_count == 2

    def test_too_few_sentences_triggers_retry(self):
        bad = "Just one sentence."
        good = "Greedy algorithms build optimal solutions incrementally. MSTs are a classic application."
        mock_client = MagicMock()
        mock_client.responses.create.side_effect = [
            mock_openai_response(bad),
            mock_openai_response(good),
        ]

        with patch("app.services.summary_generation.OpenAI", return_value=mock_client):
            result = SummaryGenerator().generate_overview([("MSTs", "Minimum spanning trees.")])

        assert result == good

    def test_uses_last_output_if_retry_still_fails(self):
        # both attempts produce too many sentences -> still return something than title fallback
        bad = "One. Two. Three. Four."
        mock_client = MagicMock()
        mock_client.responses.create.return_value = mock_openai_response(bad)

        with patch("app.services.summary_generation.OpenAI", return_value=mock_client):
            result = SummaryGenerator().generate_overview([("Topic", "Summary.")])

        assert result == bad
        assert mock_client.responses.create.call_count == 2

    def test_prompt_includes_all_segment_titles(self):
        mock_client = MagicMock()
        mock_client.responses.create.return_value = mock_openai_response(
            "The lecture covers three topics in sequence. "
            "Each builds on the previous to develop a complete picture."
        )

        segments = [
            ("Topic A", "Summary A."),
            ("Topic B", "Summary B."),
            ("Topic C", "Summary C."),
        ]

        with patch("app.services.summary_generation.OpenAI", return_value=mock_client):
            SummaryGenerator().generate_overview(segments)

        call_args = mock_client.responses.create.call_args
        messages = call_args.kwargs["input"]
        combined = " ".join(m["content"] for m in messages)
        assert "Topic A" in combined
        assert "Topic B" in combined
        assert "Topic C" in combined

    def test_client_reused_for_overview(self):
        mock_client = MagicMock()
        mock_client.responses.create.return_value = mock_openai_response(
            "The lecture covers neural networks and their training. "
            "Key concepts include backpropagation and gradient descent."
        )

        segments = [("Intro", "Summary.")]

        with patch("app.services.summary_generation.OpenAI", return_value=mock_client) as mock_cls:
            gen = SummaryGenerator()
            gen.generate(make_input())
            gen.generate_overview(segments)  # should reuse, not re-init

        assert mock_cls.call_count == 1


class TestCleanLatex:
    def test_replaces_greek_letters(self):
        assert clean_latex(r"\sigma") == "σ"
        assert clean_latex(r"\mu") == "μ"
        assert clean_latex(r"\alpha") == "α"

    def test_replaces_frac(self):
        assert clean_latex(r"\frac{1}{2}") == "(1/2)"
        assert clean_latex(r"\tfrac{a}{b}") == "(a/b)"

    def test_replaces_sqrt(self):
        assert clean_latex(r"\sqrt{x}") == "√(x)"

    def test_replaces_operators(self):
        assert clean_latex(r"\leq") == "≤"
        assert clean_latex(r"\geq") == "≥"
        assert clean_latex(r"\times") == "×"

    def test_strips_decorators(self):
        result = clean_latex(r"\big( x \big)")
        assert "\\" not in result

    def test_passthrough_clean_text(self):
        text = "The variance is σ^{2} and mean is μ."
        assert clean_latex(text) == text
