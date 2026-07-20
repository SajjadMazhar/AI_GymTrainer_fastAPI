from app.feedback.generator import POSITIVE_FEEDBACK, FeedbackGenerator


def test_no_errors_returns_positive_feedback():
    gen = FeedbackGenerator()
    assert gen.generate([]) == [POSITIVE_FEEDBACK]


def test_single_error_returns_matching_message():
    gen = FeedbackGenerator()
    messages = gen.generate(["KNEE_VALGUS"])
    assert len(messages) == 1
    assert "knee" in messages[0].lower()


def test_respects_max_messages():
    gen = FeedbackGenerator()
    messages = gen.generate(["KNEE_VALGUS", "TORSO_LEANING_FORWARD", "SQUAT_NOT_DEEP_ENOUGH"], max_messages=2)
    assert len(messages) == 2


def test_prioritizes_injury_risk_over_depth_errors():
    gen = FeedbackGenerator()
    messages = gen.generate(["SQUAT_NOT_DEEP_ENOUGH", "KNEE_VALGUS"], max_messages=1)
    assert "knee" in messages[0].lower()


def test_deduplicates_repeated_errors():
    gen = FeedbackGenerator()
    messages = gen.generate(["KNEE_VALGUS", "KNEE_VALGUS"], max_messages=2)
    assert len(messages) == 1


def test_unknown_error_code_falls_back_to_code_itself():
    gen = FeedbackGenerator()
    messages = gen.generate(["SOME_UNMAPPED_CODE"])
    assert messages == ["SOME_UNMAPPED_CODE"]
