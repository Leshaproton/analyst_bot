from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import json
import sqlite3

from app.services.assessment import Question, TestSummary


@dataclass(frozen=True)
class Attempt:
    id: int
    user_id: int
    username: str
    finished_at: str
    correct_count: int
    total_questions: int
    score: int
    max_score: int
    grade: str


@dataclass(frozen=True)
class Draft:
    answers: list[int]
    question_ids: list[str]


class ResultsRepository:
    def __init__(self, database_path: str) -> None:
        self.path = Path(database_path)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS attempts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    username TEXT NOT NULL DEFAULT '',
                    finished_at TEXT NOT NULL,
                    correct_count INTEGER NOT NULL,
                    total_questions INTEGER NOT NULL,
                    score INTEGER NOT NULL,
                    max_score INTEGER NOT NULL,
                    grade TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_attempts_user
                    ON attempts(user_id, id DESC);
                CREATE TABLE IF NOT EXISTS answers (
                    attempt_id INTEGER NOT NULL REFERENCES attempts(id) ON DELETE CASCADE,
                    position INTEGER NOT NULL,
                    question_id TEXT NOT NULL,
                    question_text TEXT NOT NULL,
                    selected_option_id INTEGER NOT NULL,
                    selected_text TEXT NOT NULL,
                    correct_option_id INTEGER NOT NULL,
                    correct_text TEXT NOT NULL,
                    is_correct INTEGER NOT NULL,
                    explanation TEXT NOT NULL,
                    PRIMARY KEY (attempt_id, position)
                );
                CREATE TABLE IF NOT EXISTS drafts (
                    user_id INTEGER PRIMARY KEY,
                    answers_json TEXT NOT NULL,
                    question_ids_json TEXT NOT NULL DEFAULT '[]',
                    updated_at TEXT NOT NULL
                );
            """)
            columns = {row["name"] for row in db.execute("PRAGMA table_info(drafts)")}
            if "question_ids_json" not in columns:
                db.execute(
                    "ALTER TABLE drafts ADD COLUMN question_ids_json TEXT NOT NULL DEFAULT '[]'"
                )

    def save_draft(self, user_id: int, selected: list[int], question_ids: list[str]) -> None:
        with self._connect() as db:
            db.execute(
                """INSERT INTO drafts (user_id, answers_json, question_ids_json, updated_at)
                   VALUES (?, ?, ?, ?)
                   ON CONFLICT(user_id) DO UPDATE SET
                       answers_json = excluded.answers_json,
                       question_ids_json = excluded.question_ids_json,
                       updated_at = excluded.updated_at""",
                (user_id, json.dumps(selected), json.dumps(question_ids),
                 datetime.now(timezone.utc).isoformat()),
            )

    def load_draft(self, user_id: int) -> Draft | None:
        with self._connect() as db:
            row = db.execute(
                "SELECT answers_json, question_ids_json FROM drafts WHERE user_id = ?",
                (user_id,),
            ).fetchone()
        if row is None:
            return None
        return Draft(
            answers=[int(value) for value in json.loads(row["answers_json"])],
            question_ids=[str(value) for value in json.loads(row["question_ids_json"])],
        )

    def delete_draft(self, user_id: int) -> None:
        with self._connect() as db:
            db.execute("DELETE FROM drafts WHERE user_id = ?", (user_id,))

    def save(self, user_id: int, username: str, questions: tuple[Question, ...],
             selected: list[int], summary: TestSummary) -> int:
        with self._connect() as db:
            cursor = db.execute(
                """INSERT INTO attempts
                   (user_id, username, finished_at, correct_count, total_questions, score, max_score, grade)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (user_id, username, datetime.now(timezone.utc).isoformat(), summary.correct_count,
                 summary.total_questions, summary.score, summary.max_score, summary.grade),
            )
            attempt_id = int(cursor.lastrowid)
            db.executemany(
                """INSERT INTO answers
                   (attempt_id, position, question_id, question_text, selected_option_id,
                    selected_text, correct_option_id, correct_text, is_correct, explanation)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                [(attempt_id, position, question.id, question.text, answer,
                  question.options[answer], question.correct_option_id,
                  question.options[question.correct_option_id], int(answer == question.correct_option_id),
                  question.explanation)
                 for position, (question, answer) in enumerate(zip(questions, selected), 1)],
            )
            db.execute("DELETE FROM drafts WHERE user_id = ?", (user_id,))
        return attempt_id

    def latest(self, user_id: int) -> Attempt | None:
        with self._connect() as db:
            row = db.execute("SELECT * FROM attempts WHERE user_id = ? ORDER BY id DESC LIMIT 1", (user_id,)).fetchone()
        return Attempt(**dict(row)) if row else None

    def recent_attempts(self, limit: int = 20) -> list[Attempt]:
        with self._connect() as db:
            rows = db.execute("SELECT * FROM attempts ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [Attempt(**dict(row)) for row in rows]

    def report(self, attempt_id: int, user_id: int) -> tuple[Attempt, list[sqlite3.Row]] | None:
        with self._connect() as db:
            row = db.execute("SELECT * FROM attempts WHERE id = ? AND user_id = ?", (attempt_id, user_id)).fetchone()
            if row is None:
                return None
            answers = db.execute("SELECT * FROM answers WHERE attempt_id = ? ORDER BY position", (attempt_id,)).fetchall()
        return Attempt(**dict(row)), answers

    def report_by_id(self, attempt_id: int) -> tuple[Attempt, list[sqlite3.Row]] | None:
        with self._connect() as db:
            row = db.execute("SELECT * FROM attempts WHERE id = ?", (attempt_id,)).fetchone()
            if row is None:
                return None
            answers = db.execute("SELECT * FROM answers WHERE attempt_id = ? ORDER BY position", (attempt_id,)).fetchall()
        return Attempt(**dict(row)), answers


def build_report(attempt: Attempt, answers: list[sqlite3.Row]) -> bytes:
    lines = ["ОТЧЕТ ПО ТЕСТИРОВАНИЮ СИСТЕМНОГО АНАЛИТИКА", "",
             f"Telegram ID: {attempt.user_id}", f"Username: {attempt.username or 'не указан'}",
             f"Дата (UTC): {attempt.finished_at}", f"Грейд: {attempt.grade}",
             f"Правильных ответов: {attempt.correct_count} из {attempt.total_questions}",
             f"Баллы: {attempt.score} из {attempt.max_score}", ""]
    for row in answers:
        mark = "ВЕРНО" if row["is_correct"] else "НЕВЕРНО"
        lines.extend([
            f'{row["position"]}. [{row["question_id"]}] {row["question_text"]}',
            f'Выбранный ответ: {"ABCD"[row["selected_option_id"]]}. {row["selected_text"]}',
            f'Правильный ответ: {"ABCD"[row["correct_option_id"]]}. {row["correct_text"]}',
            f"Результат: {mark}", f'Пояснение: {row["explanation"]}', "",
        ])
    return ("\n".join(lines) + "\n").encode("utf-8")
