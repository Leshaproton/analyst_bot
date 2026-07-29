from app.services.assessment import load_questions, summarize


def test_question_bank_is_complete() -> None:
    questions = load_questions()
    assert len(questions) == 100
    assert sum(question.score for question in questions) == 185
    assert all(len(question.options) == 4 for question in questions)


def test_all_correct_answers_produce_senior() -> None:
    questions = load_questions()
    summary = summarize(questions, [question.correct_option_id for question in questions])
    assert summary.correct_count == 100
    assert summary.score == 185
    assert summary.grade == "Senior"


def test_all_wrong_answers_produce_zero_score() -> None:
    questions = load_questions()
    selected = [(question.correct_option_id + 1) % 4 for question in questions]
    summary = summarize(questions, selected)
    assert summary.correct_count == 0
    assert summary.score == 0
    assert summary.grade == "Junior"
