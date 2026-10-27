from unittest.mock import patch

from app.services.query_router import classify_query
from app.tasks.retrieval_tasks import run_query


def test_single_word_is_retrieval():
    assert classify_query("backpropagation") == "retrieval"


def test_two_word_keyword_is_retrieval():
    # 2-word keyword searches with no QA opener should still be retrieval
    assert classify_query("gradient descent") == "retrieval"
    assert classify_query("neural networks") == "retrieval"
    assert classify_query("loss function") == "retrieval"


def test_two_word_qa_is_qa():
    # short QA openers should still route correctly even at 2 words
    assert classify_query("explain backpropagation") == "qa"
    assert classify_query("define entropy") == "qa"
    assert classify_query("simplify regularisation") == "qa"
    assert classify_query("compare transformers") == "qa"


def test_when_starter_is_retrieval():
    assert classify_query("when is the interval scheduling proof covered") == "retrieval"
    assert classify_query("when does he explain the attention mechanism") == "retrieval"


def test_where_starter_is_retrieval():
    assert classify_query("where does she cover backpropagation") == "retrieval"
    assert classify_query("where in the lecture is this introduced") == "retrieval"


def test_find_show_locate_are_retrieval():
    assert classify_query("find the part about gradient descent") == "retrieval"
    assert classify_query("show me where the proof starts") == "retrieval"
    assert classify_query("locate the section on overfitting") == "retrieval"


def test_jump_skip_seek_navigate_are_retrieval():
    assert classify_query("jump to the part about loss functions") == "retrieval"
    assert classify_query("skip to backpropagation in the lecture") == "retrieval"
    assert classify_query("seek to where she explains softmax") == "retrieval"
    assert classify_query("navigate to the neural networks section") == "retrieval"


def test_temporal_phrase_mid_query_no_qa_opener_is_retrieval():
    # navigational intent without a QA opener should still route as retrieval
    assert classify_query("can you show me the part where she derives it") == "retrieval"
    assert classify_query("i want the section where regularisation is introduced") == "retrieval"


def test_what_part_section_slide_are_retrieval():
    assert classify_query("what part of the lecture covers transformers") == "retrieval"
    assert classify_query("what section does she explain dropout in") == "retrieval"
    assert classify_query("what slide shows the loss function formula") == "retrieval"


def test_which_queries_are_retrieval():
    assert classify_query("which section covers the attention mechanism") == "retrieval"
    assert classify_query("which slide has the learning rate diagram") == "retrieval"
    assert classify_query("which minute does he start on backprop") == "retrieval"


def test_how_long_far_are_retrieval():
    # "how long/far/etc" is navigational, unlike "how does/do/..."
    assert classify_query("how long does he spend on gradient descent") == "retrieval"
    assert classify_query("how far into the lecture is the proof") == "retrieval"
    assert classify_query("how many minutes is the neural networks section") == "retrieval"


def test_the_slide_phrases_are_retrieval():
    assert classify_query("the slide showing the attention formula") == "retrieval"
    assert classify_query("the slide about recurrent networks") == "retrieval"
    assert classify_query("the slide with the loss function diagram") == "retrieval"


def test_timestamp_slide_shorthand_are_retrieval():
    assert classify_query("timestamp for the gradient descent explanation") == "retrieval"
    assert classify_query("slide for backpropagation in lecture three") == "retrieval"


def test_empty_query_is_retrieval():
    assert classify_query("") == "retrieval"
    assert classify_query("   ") == "retrieval"


def test_explain_is_qa():
    assert classify_query("explain how backpropagation works") == "qa"
    assert classify_query("explain the vanishing gradient problem in deep networks") == "qa"


def test_qa_starter_overrides_temporal_phrase_mid_query():
    # a QA verb at the start should win even if a temporal phrase appears later
    assert classify_query("explain the part about backpropagation") == "qa"
    assert classify_query("describe the section on attention mechanisms") == "qa"
    assert classify_query("summarise the part where she covers gradient descent") == "qa"
    assert (
        classify_query(
            "please simplify the explanation for how a* search finds an optimal solution"
        )
        == "qa"
    )


def test_simplify_is_qa():
    assert classify_query("simplify the proof for interval scheduling") == "qa"
    assert classify_query("please simplify the explanation of the chain rule") == "qa"


def test_please_prefix_is_qa():
    assert classify_query("please explain how backpropagation works") == "qa"
    assert classify_query("please describe the attention mechanism") == "qa"
    assert classify_query("please walk me through the gradient descent derivation") == "qa"
    assert classify_query("please clarify what the lecturer meant by regularisation") == "qa"


def test_describe_define_are_qa():
    assert classify_query("describe the attention mechanism in transformers") == "qa"
    assert classify_query("define what entropy means in information theory") == "qa"


def test_summarise_is_qa():
    assert classify_query("summarise the section on regularisation") == "qa"
    assert classify_query("summarize what was covered in the introduction") == "qa"


def test_compare_contrast_differentiate_are_qa():
    assert classify_query("compare SGD and Adam optimisers") == "qa"
    assert classify_query("contrast supervised and unsupervised learning") == "qa"
    assert classify_query("differentiate between precision and recall") == "qa"


def test_why_is_qa():
    assert classify_query("why does the loss diverge with a high learning rate") == "qa"
    assert classify_query("why is dropout used during training") == "qa"
    assert classify_query("why are residual connections useful") == "qa"


def test_how_does_do_are_qa():
    assert classify_query("how does attention work in transformers") == "qa"
    assert classify_query("how do convolutional layers extract features") == "qa"
    assert classify_query("how can we prevent overfitting") == "qa"


def test_what_is_are_does_are_qa():
    assert classify_query("what is the intuition behind gradient descent") == "qa"
    assert classify_query("what are the types of gradient descent") == "qa"
    assert classify_query("what does entropy measure in this context") == "qa"
    assert classify_query("what happens when the learning rate is too high") == "qa"


def test_is_are_does_are_qa():
    assert classify_query("is backpropagation the same as gradient descent") == "qa"
    assert classify_query("are vanishing gradients a problem in deep networks") == "qa"
    assert classify_query("does dropout help with overfitting") == "qa"


def test_conversational_starters_are_qa():
    assert classify_query("tell me about the chain rule") == "qa"
    assert classify_query("walk me through the backpropagation derivation") == "qa"
    assert classify_query("help me understand the vanishing gradient problem") == "qa"
    assert classify_query("break down how softmax is computed") == "qa"


def test_can_could_you_explain_are_qa():
    assert classify_query("can you explain what a loss function is") == "qa"
    assert classify_query("could you explain how regularisation works") == "qa"


def test_i_dont_understand_is_qa():
    assert classify_query("i don't understand why we use relu over sigmoid") == "qa"
    assert classify_query("i don't get how the chain rule applies here") == "qa"


def test_trailing_question_mark_is_qa():
    assert classify_query("does batch normalisation help with training stability?") == "qa"
    assert classify_query("is the proof for interval scheduling covered in the lecture?") == "qa"


def test_case_is_normalised():
    assert classify_query("EXPLAIN gradient descent") == "qa"
    assert classify_query("WHEN is backprop covered") == "retrieval"
    assert classify_query("What IS the learning rate") == "qa"


def test_extra_whitespace_handled():
    assert classify_query("  explain   gradient descent  ") == "qa"
    assert classify_query("when   is backprop covered") == "retrieval"


def test_explicit_retrieval_mode_bypasses_classifier():
    with patch("app.tasks.retrieval_tasks.RetrievalService") as mock_ret:
        mock_ret.return_value.search.return_value = []
        result = run_query(video_id=1, query="what is backpropagation", mode="retrieval")

    assert result["mode"] == "retrieval"


def test_explicit_qa_mode_bypasses_classifier():
    # retrieval always runs first now, so both services need mocking
    with (
        patch("app.tasks.retrieval_tasks.RetrievalService") as mock_ret,
        patch("app.tasks.retrieval_tasks.QAService") as mock_qa,
    ):
        mock_ret.return_value.search.return_value = []
        mock_qa.return_value.answer.return_value = {
            "question": "find the backprop section",
            "answer": "some answer",
            "citations": [],
        }
        result = run_query(video_id=1, query="find the backprop section", mode="qa")

    assert result["mode"] == "qa"


def test_retrieval_always_runs_regardless_of_mode():
    # even in qa mode, retrieval should run once before the LLM call
    with (
        patch("app.tasks.retrieval_tasks.RetrievalService") as mock_ret,
        patch("app.tasks.retrieval_tasks.QAService") as mock_qa,
    ):
        mock_ret.return_value.search.return_value = []
        mock_qa.return_value.answer.return_value = {"question": "q", "answer": "a", "citations": []}

        run_query(video_id=1, query="explain attention", mode="qa")

    mock_ret.return_value.search.assert_called_once()


def test_run_query_passes_fetched_chunks_to_qa():
    # chunks from retrieval should be handed to QAService directly, not re-fetched
    chunks = [
        {
            "text": "attention is used in transformers",
            "start_time": 0.0,
            "end_time": 30.0,
            "score": 0.9,
            "segment_title": None,
        }
    ]

    with (
        patch("app.tasks.retrieval_tasks.RetrievalService") as mock_ret,
        patch("app.tasks.retrieval_tasks.QAService") as mock_qa,
    ):
        mock_ret.return_value.search.return_value = chunks
        mock_qa.return_value.answer.return_value = {
            "question": "explain attention",
            "answer": "some answer",
            "citations": [],
        }

        run_query(video_id=1, query="explain attention", mode="qa")

    call_kwargs = mock_qa.return_value.answer.call_args
    assert call_kwargs.kwargs.get("chunks") == chunks
