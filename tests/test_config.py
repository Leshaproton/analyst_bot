from app.config import load_bot_token


def test_token_is_loaded_from_credential_file(tmp_path, monkeypatch) -> None:
    token_file = tmp_path / "bot-token"
    token_file.write_text("secret-token\n", encoding="utf-8")
    monkeypatch.setenv("BOT_TOKEN", "fallback-token")
    monkeypatch.setenv("BOT_TOKEN_FILE", str(token_file))
    assert load_bot_token() == "secret-token"


def test_environment_token_is_fallback(monkeypatch) -> None:
    monkeypatch.delenv("BOT_TOKEN_FILE", raising=False)
    monkeypatch.setenv("BOT_TOKEN", "environment-token")
    assert load_bot_token() == "environment-token"
