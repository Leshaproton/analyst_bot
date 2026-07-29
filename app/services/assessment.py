from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path


@dataclass(frozen=True)
class Question:
    id: str
    level: str
    type: str
    context: str
    text: str
    options: tuple[str, str, str, str]
    correct_option_id: int
    explanation: str
    topic: str
    tags: tuple[str, ...]
    score: int


@dataclass(frozen=True)
class TestSummary:
    correct_count: int
    total_questions: int
    score: int
    max_score: int
    grade: str


def load_questions(path: Path | None = None) -> tuple[Question, ...]:
    source = path or Path(__file__).resolve().parents[1] / "data" / "questions.json"
    payload = json.loads(source.read_text(encoding="utf-8"))
    raw = payload["questions"]
    questions = tuple(
        Question(
            id=item["id"], level=item["level"], type=item["type"], context=item["context"],
            text=item["question"], options=tuple(item["answers"].values()),
            correct_option_id="ABCD".index(item["correct_answer"]),
            explanation=item["explanation"], topic=item["topic"],
            tags=tuple(item["tags"]), score=item["score"],
        )
        for item in raw
    )
    if not questions:
        raise RuntimeError("Question bank is empty")
    return questions


def summarize(questions: tuple[Question, ...], selected: list[int]) -> TestSummary:
    if len(selected) != len(questions):
        raise ValueError("The number of answers does not match the question bank")
    if any(value not in range(4) for value in selected):
        raise ValueError("Answer index must be between 0 and 3")
    correct_count = sum(answer == question.correct_option_id for question, answer in zip(questions, selected))
    score = sum(question.score for question, answer in zip(questions, selected) if answer == question.correct_option_id)
    max_score = sum(question.score for question in questions)
    percent = score / max_score * 100
    grade = "Senior" if percent >= 75 else "Middle" if percent >= 50 else "Junior"
    return TestSummary(correct_count, len(questions), score, max_score, grade)
