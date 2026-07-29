from dataclasses import dataclass
import os

from dotenv import load_dotenv


@dataclass(frozen=True)
class Config:
    bot_token: str
    allowed_user_ids: frozenset[int]
    database_path: str


def load_config() -> Config:
    load_dotenv()
    token = os.getenv("BOT_TOKEN", "").strip()
    if not token:
        raise RuntimeError("BOT_TOKEN is not set. Copy .env.example to .env and add the token.")
    raw_ids = os.getenv("ALLOWED_USER_IDS", "")
    try:
        allowed_user_ids = frozenset(int(value.strip()) for value in raw_ids.split(",") if value.strip())
    except ValueError as exc:
        raise RuntimeError("ALLOWED_USER_IDS must contain comma-separated integer IDs") from exc
    if not allowed_user_ids:
        raise RuntimeError("ALLOWED_USER_IDS is empty; access would be denied to everyone")
    return Config(
        bot_token=token,
        allowed_user_ids=allowed_user_ids,
        database_path=os.getenv("DATABASE_PATH", "data/results.sqlite3").strip(),
    )
