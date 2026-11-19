from __future__ import annotations

from pathlib import Path

import weatui.app as app_module
from weatui.app import WeatuiApp
from weatui.store import Store
from weatui.weather import City, Forecast


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
    app = WeatuiApp(store=Store(tmp_path / "config.json"))
    async with app.run_test(size=(100, 30)) as pilot:
        app._add_city(City("Manila", "Metro Manila", "Philippines", 14.5995, 120.9842))
        await pilot.pause(0.1)
        app._add_city(City("Tokyo", "", "Japan", 35.6762, 139.6503))
        await pilot.pause(0.1)
        assert [city.name for city in app.store.config.cities] == ["Manila", "Tokyo"]
        assert app.store.config.selected == 1
