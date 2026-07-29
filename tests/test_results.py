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


def test_draft_can_be_saved_loaded_and_deleted(tmp_path) -> None:
    repository = ResultsRepository(str(tmp_path / "results.sqlite3"))
    repository.initialize()
    repository.save_draft(42, [0, 3, 1])
    assert repository.load_draft(42) == [0, 3, 1]
    repository.delete_draft(42)
    assert repository.load_draft(42) is None
