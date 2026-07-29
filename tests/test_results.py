import sqlite3

from app.services.assessment import load_questions, summarize
from app.services.results import ResultsRepository, build_report


def test_attempt_is_saved_and_exported(tmp_path) -> None:
    repository = ResultsRepository(str(tmp_path / "results.sqlite3"))
    repository.initialize()
    questions = load_questions()
    selected = [question.correct_option_id for question in questions]
    summary = summarize(questions, selected)

    attempt_id = repository.save(42, "analyst", questions, selected, summary)
    attempt = repository.latest(42)
    assert attempt is not None
    assert attempt.id == attempt_id
    assert attempt.correct_count == 100

    stored_attempt, answers = repository.report(attempt_id, 42)
    report = build_report(stored_attempt, answers).decode("utf-8")
    assert "Правильных ответов: 100 из 100" in report
    assert "Выбранный ответ:" in report
    assert repository.report(attempt_id, 99) is None
    assert repository.report_by_id(attempt_id)[0].user_id == 42
    assert repository.recent_attempts()[0].id == attempt_id


def test_draft_can_be_saved_loaded_and_deleted(tmp_path) -> None:
    repository = ResultsRepository(str(tmp_path / "results.sqlite3"))
    repository.initialize()
    repository.save_draft(42, [0, 3, 1], ["J003", "J001", "J002"])
    draft = repository.load_draft(42)
    assert draft.answers == [0, 3, 1]
    assert draft.question_ids == ["J003", "J001", "J002"]
    repository.delete_draft(42)
    assert repository.load_draft(42) is None


def test_existing_drafts_table_is_migrated(tmp_path) -> None:
    database = tmp_path / "legacy.sqlite3"
    with sqlite3.connect(database) as connection:
        connection.execute(
            """CREATE TABLE drafts (
                user_id INTEGER PRIMARY KEY,
                answers_json TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )"""
        )
    repository = ResultsRepository(str(database))
    repository.initialize()
    repository.save_draft(42, [1], ["J001"])
    assert repository.load_draft(42).question_ids == ["J001"]
