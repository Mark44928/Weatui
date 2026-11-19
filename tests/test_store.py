from __future__ import annotations

from pathlib import Path

from weatui.store import Config, Store
from weatui.weather import City


def test_store_round_trip_and_sanitizing(tmp_path: Path) -> None:
    path = tmp_path / "config.json"
    store = Store(path)
    store.add_city(City("Manila", "Metro Manila", "Philippines", 14.5995, 120.9842))
    store.add_city(City("Tokyo", "", "Japan", 35.6762, 139.6503))
    store.set_units("f")
    store.set_theme("yellen")
    store.select(1)

    loaded = Store(path)
    assert [city.name for city in loaded.config.cities] == ["Manila", "Tokyo"]
    assert loaded.config.units == "F"
    assert loaded.config.theme == "yellen"
    assert loaded.config.selected == 1


def test_bad_config_falls_back(tmp_path: Path) -> None:
    path = tmp_path / "config.json"
    path.write_text("{not json")
    assert Store(path).config.cities == []

    config = Config(
        cities=[City("X", "", "", 200, 300)],
        units="K",
        theme="bogus",
        refresh_seconds=1,
        selected=99,
    ).sanitized()
    assert config.units == "C"
    assert config.theme == "greenit"
    assert config.refresh_seconds == 60
