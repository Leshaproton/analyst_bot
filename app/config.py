from dataclasses import dataclass
import os

from dotenv import load_dotenv


@dataclass(frozen=True)
class Config:
    bot_token: str
    allowed_user_ids: frozenset[int]
    admin_user_ids: frozenset[int]
    database_path: str


def load_bot_token() -> str:
    token_file = os.getenv("BOT_TOKEN_FILE", "").strip()
    if token_file:
        try:
            token = open(token_file, encoding="utf-8").read().strip()
        except OSError as exc:
            raise RuntimeError("BOT_TOKEN_FILE cannot be read") from exc
    else:
        token = os.getenv("BOT_TOKEN", "").strip()
    if not token:
        raise RuntimeError("Set BOT_TOKEN_FILE or BOT_TOKEN")
    return token


def load_config() -> Config:
    load_dotenv()
    token = load_bot_token()
    raw_ids = os.getenv("ALLOWED_USER_IDS", "")
    raw_admin_ids = os.getenv("ADMIN_USER_IDS", "")
    try:
        allowed_user_ids = frozenset(int(value.strip()) for value in raw_ids.split(",") if value.strip())
        admin_user_ids = frozenset(int(value.strip()) for value in raw_admin_ids.split(",") if value.strip())
    except ValueError as exc:
        raise RuntimeError("User ID settings must contain comma-separated integers") from exc
    if not allowed_user_ids:
        raise RuntimeError("ALLOWED_USER_IDS is empty; access would be denied to everyone")
    return Config(
        bot_token=token,
        allowed_user_ids=allowed_user_ids,
        admin_user_ids=admin_user_ids,
        database_path=os.getenv("DATABASE_PATH", "data/results.sqlite3").strip(),
    )
