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


def test_move_city_reorders_and_keeps_selection(tmp_path: Path) -> None:
    store = Store(tmp_path / "config.json")
    store.add_city(City("Manila", "", "Philippines", 14.6, 121.0))
    store.add_city(City("Tokyo", "", "Japan", 35.7, 139.7))
    store.add_city(City("Oslo", "", "Norway", 59.9, 10.7))
    store.select(1)
    store.move_city(1, -1)
    assert [city.name for city in store.config.cities] == ["Tokyo", "Manila", "Oslo"]
    assert store.config.selected == 0
    store.move_city(0, -1)
    assert [city.name for city in store.config.cities] == ["Tokyo", "Manila", "Oslo"]


def test_add_city_reports_duplicate_and_new(tmp_path: Path) -> None:
    store = Store(tmp_path / "config.json")
    city = City("Manila", "", "Philippines", 14.6, 121.0)
    assert store.add_city(city) is True
    assert store.add_city(City("Manila copy", "", "Philippines", 14.6, 121.0)) is False
    assert len(store.config.cities) == 1


def test_store_ignores_non_numeric_and_infinite_config(tmp_path: Path) -> None:
    path = tmp_path / "config.json"
    path.write_text(
        '{"refresh_seconds": "soon", "selected": 1e999}',
        encoding="utf-8",
    )
    store = Store(path)
    assert store.config.refresh_seconds == 600
    assert store.config.selected == 0
