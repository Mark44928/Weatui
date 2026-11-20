from __future__ import annotations

from pathlib import Path

from textual.widgets import DataTable, ListView

import weatui.app as app_module
from weatui.app import CityPickerScreen, CompareScreen, WeatuiApp
from weatui.store import Store
from weatui.weather import Air, City, Forecast


def fake_air(city: City) -> Air:
    return Air(aqi=34, pm2_5=12.4, pm10=21.0)


def fake_forecast(city: City, days: int = 7) -> Forecast:
    return Forecast(
        current_time="2026-01-01T12:00",
        temperature_c=30,
        feels_like_c=33,
        humidity=70,
        precipitation_mm=0,
        code=2,
        is_day=True,
        wind_kmh=12,
        wind_direction=180,
        uv=6,
        hours=(),
        days=(),
    )


async def test_app_boots_without_cities(tmp_path: Path) -> None:
    app = WeatuiApp(store=Store(tmp_path / "config.json"))
    async with app.run_test(size=(100, 30)) as pilot:
        await pilot.pause()
        assert app.query_one("#cities") is not None
        assert "No cities yet" in str(app.query_one("#statusbar").render())


async def test_adding_two_cities_does_not_duplicate_ids(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(app_module, "fetch_forecast", fake_forecast)
    monkeypatch.setattr(app_module, "fetch_air_quality", fake_air)
    app = WeatuiApp(store=Store(tmp_path / "config.json"))
    async with app.run_test(size=(100, 30)) as pilot:
        app._add_city(City("Manila", "Metro Manila", "Philippines", 14.5995, 120.9842))
        await pilot.pause(0.1)
        app._add_city(City("Tokyo", "", "Japan", 35.6762, 139.6503))
        await pilot.pause(0.1)
        assert [city.name for city in app.store.config.cities] == ["Manila", "Tokyo"]
        assert app.store.config.selected == 1


async def test_city_picker_returns_selected_match(tmp_path: Path) -> None:
    app = WeatuiApp(store=Store(tmp_path / "config.json"))
    picked: list[City] = []
    async with app.run_test(size=(100, 30)) as pilot:
        app.push_screen(
            CityPickerScreen(
                [
                    City("Manila", "Metro Manila", "Philippines", 14.5995, 120.9842),
                    City("Tokyo", "", "Japan", 35.6762, 139.6503),
                ]
            ),
            picked.append,
        )
        await pilot.pause()
        matches = app.screen.query_one("#matches", ListView)
        matches.focus()
        await pilot.press("down", "enter")
        await pilot.pause()
        assert picked and picked[0].name == "Tokyo"


async def test_compare_view_lists_saved_city(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(app_module, "fetch_forecast", fake_forecast)
    monkeypatch.setattr(app_module, "fetch_air_quality", fake_air)
    app = WeatuiApp(store=Store(tmp_path / "config.json"))
    async with app.run_test(size=(100, 30)) as pilot:
        app._add_city(City("Manila", "Metro Manila", "Philippines", 14.5995, 120.9842))
        await pilot.pause(0.1)
        app.action_compare()
        await pilot.pause()
        assert isinstance(app.screen, CompareScreen)
        assert app.screen.query_one("#compare-table", DataTable).row_count == 1


async def test_brackets_reorder_cities(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(app_module, "fetch_forecast", fake_forecast)
    monkeypatch.setattr(app_module, "fetch_air_quality", fake_air)
    store = Store(tmp_path / "config.json")
    store.add_city(City("Manila", "Metro Manila", "Philippines", 14.5995, 120.9842))
    store.add_city(City("Tokyo", "", "Japan", 35.6762, 139.6503))
    app = WeatuiApp(store=store)
    async with app.run_test(size=(100, 30)) as pilot:
        await pilot.pause()
        assert store.config.selected == 1
        await pilot.press("[")
        await pilot.pause()
        assert [city.name for city in store.config.cities] == ["Tokyo", "Manila"]
        assert store.config.selected == 0
