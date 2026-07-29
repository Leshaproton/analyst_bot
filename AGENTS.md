# Repository Guidelines

## Project Structure & Module Organization

Application code lives in `app/`. `app/__main__.py` wires the aiogram dispatcher,
middleware, repositories, and routers. Telegram handlers are grouped under
`app/handlers/`; business logic and SQLite access belong in `app/services/`.
Shared reply keyboards are defined in `app/keyboards.py`, while access and
environment configuration live in `app/access.py` and `app/config.py`.

The question bank is stored in `app/data/questions.json`; keep
`questions_bot.json` synchronized when updating it. Tests mirror application
features under `tests/`. Runtime SQLite files belong in `data/` and must not be
committed.

## Build, Test, and Development Commands

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python -m app
```

The final command starts the bot in long-polling mode. Run the complete test
suite before every commit:

```bash
python -m pytest -q
python -m compileall -q app tests
```

## Coding Style & Naming Conventions

Use Python 3.9-compatible syntax, four-space indentation, type annotations, and
small single-purpose functions. Name modules, functions, and variables in
`snake_case`; classes and dataclasses use `PascalCase`; constants use
`UPPER_SNAKE_CASE`. Keep Telegram handlers thin and move calculations or storage
operations into services. Prefer explicit user-facing Russian text and concise
callback-data prefixes such as `admin:view:` or `test:save`.

## Testing Guidelines

Tests use pytest. Name files `test_<feature>.py` and functions
`test_<expected_behavior>`. Use `tmp_path` for SQLite tests and deterministic
random generators when verifying shuffled questions. Cover authorization,
database migrations, resume behavior, scoring, and report ownership whenever
those paths change. Do not call Telegram or other network services from unit
tests.

## Commit & Pull Request Guidelines

History uses short imperative commit messages, for example `Add chat history
cleanup` and `Randomize questions within grade sections`. Keep each commit
focused. Pull requests should explain user-visible behavior, configuration or
schema changes, test results, and deployment impact. Link the relevant issue and
include screenshots only for menu or message-layout changes.

## Security & Configuration

Never commit `.env`, tokens, private keys, SQLite databases, or exported user
reports. Add configuration examples only to `.env.example`. Production tokens
should use `BOT_TOKEN_FILE` with an encrypted systemd credential. Treat Telegram
IDs, answer reports, and test history as private data.
