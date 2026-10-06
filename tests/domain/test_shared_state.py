from src.domain.shared_state import SharedState


def test_creates_a_state_with_the_two_required_texts() -> None:
    state = SharedState(
        candidate_cv_text="cv text",
        job_description_text="job text",
    )

    assert state.candidate_cv_text == "cv text"
    assert state.job_description_text == "job text"


def test_starts_empty_with_a_variance_of_one_and_no_attempts() -> None:
    state = SharedState(
        candidate_cv_text="cv text",
        job_description_text="job text",
    )

    assert state.extracted_profile == ""
    assert state.gap_analysis == ""
    assert state.optimized_text == ""
    assert state.variance_score == 1.0
    assert state.writer_attempts == 0


def test_is_mutable_so_nodes_can_write_into_it() -> None:
    state = SharedState(
        candidate_cv_text="cv text",
        job_description_text="job text",
    )

    state.extracted_profile = "profile"
    state.writer_attempts = 1

    assert state.extracted_profile == "profile"
    assert state.writer_attempts == 1
