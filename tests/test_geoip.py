import sys

from utils.geoip import ROOT_DIR, app_root, geoip_database_path


def test_app_root_source_mode() -> None:
    assert app_root() == ROOT_DIR


def test_geoip_database_path_prefers_env(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "GeoLite2-City.mmdb"
    db_path.write_bytes(b"fake")
    monkeypatch.setenv("GEOIP_PATH", str(db_path))

    assert geoip_database_path() == db_path


def test_geoip_database_path_frozen_near_exe(tmp_path, monkeypatch) -> None:
    exe_path = tmp_path / "ParserRIba.exe"
    db_path = tmp_path / "GeoLite2-City.mmdb"
    exe_path.write_bytes(b"exe")
    db_path.write_bytes(b"fake")
    monkeypatch.delenv("GEOIP_PATH", raising=False)
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(exe_path), raising=False)

    assert geoip_database_path() == db_path
