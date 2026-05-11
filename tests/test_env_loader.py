import os

from utils.env import load_dotenv_file


def test_load_dotenv_file_sets_values(tmp_path, monkeypatch) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text(
        """
        # comment
        PARSER_PROXY="http://user:pass@example.com:1000"
        PARSER_GEOIP=1
        """,
        encoding="utf-8",
    )
    monkeypatch.delenv("PARSER_PROXY", raising=False)
    monkeypatch.delenv("PARSER_GEOIP", raising=False)

    loaded = load_dotenv_file(env_path)

    assert loaded["PARSER_PROXY"] == "http://user:pass@example.com:1000"
    assert os.environ["PARSER_PROXY"] == "http://user:pass@example.com:1000"
    assert os.environ["PARSER_GEOIP"] == "1"


def test_load_dotenv_file_preserves_existing_without_override(tmp_path, monkeypatch) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text("PARSER_GEOIP=1", encoding="utf-8")
    monkeypatch.setenv("PARSER_GEOIP", "0")

    load_dotenv_file(env_path)

    assert os.environ["PARSER_GEOIP"] == "0"


def test_load_dotenv_file_can_override(tmp_path, monkeypatch) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text("PARSER_GEOIP=1", encoding="utf-8")
    monkeypatch.setenv("PARSER_GEOIP", "0")

    load_dotenv_file(env_path, override=True)

    assert os.environ["PARSER_GEOIP"] == "1"
