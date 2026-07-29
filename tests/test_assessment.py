import random

from app.services.assessment import (
    load_questions,
    questions_in_order,
    shuffled_questions,
    summarize,
)


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


def test_questions_are_shuffled_inside_grade_blocks() -> None:
    questions = load_questions()
    shuffled = shuffled_questions(questions, random.Random(42))
    assert [question.level for question in shuffled] == (
        ["Junior"] * 40 + ["Middle"] * 35 + ["Senior"] * 25
    )
    assert {question.id for question in shuffled} == {question.id for question in questions}
    assert [question.id for question in shuffled] != [question.id for question in questions]


def test_saved_question_order_can_be_restored() -> None:
    questions = load_questions()
    shuffled = shuffled_questions(questions, random.Random(7))
    restored = questions_in_order(questions, [question.id for question in shuffled])
    assert restored == shuffled
