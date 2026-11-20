"""Weatui Textual application."""

from __future__ import annotations

from datetime import datetime

from rich.text import Text
from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.css.query import NoMatches
from textual.screen import ModalScreen
from textual.widgets import DataTable, Input, Label, ListItem, ListView, Static

from .store import THEMES, Store
from .weather import (
    Air,
    City,
    Forecast,
    WeatherError,
    aqi_label,
    fetch_air_quality,
    fetch_forecast,
    format_temp,
    format_wind,
    search_cities,
    sparkline,
    weather_text,
    wind_direction,
)


class AddCityScreen(ModalScreen[str | None]):
    BINDINGS = [Binding("escape", "cancel", "Cancel")]

    def compose(self) -> ComposeResult:
        with Vertical(id="add-card"):
            yield Static("ADD A CITY", id="add-title")
            yield Input(placeholder="City name, e.g. Manila", id="city-input", max_length=80)
            yield Static("Enter to search · Esc to cancel", id="add-hint")

    def on_mount(self) -> None:
        self.query_one("#city-input", Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        name = event.value.strip()
        self.dismiss(name or None)

    def action_cancel(self) -> None:
        self.dismiss(None)


class CityPickerScreen(ModalScreen[City | None]):
    BINDINGS = [Binding("escape", "cancel", "Cancel")]

    def __init__(self, cities: list[City]) -> None:
        super().__init__()
        self.cities = cities

    def compose(self) -> ComposeResult:
        with Vertical(id="pick-card"):
            yield Static("MATCHES", id="add-title")
            yield ListView(
                *[ListItem(Label(city.label), id=f"match-{index}") for index, city in enumerate(self.cities)],
                id="matches",
            )
            yield Static("Enter to add · Esc to cancel", id="add-hint")

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        item = event.item
        if item is None or not item.id or not item.id.startswith("match-"):
            return
        try:
            index = int(item.id.removeprefix("match-"))
        except ValueError:
            return
        if 0 <= index < len(self.cities):
            self.dismiss(self.cities[index])

    def action_cancel(self) -> None:
        self.dismiss(None)


class CompareScreen(ModalScreen[None]):
    BINDINGS = [Binding("escape", "close", "Close"), Binding("v", "close", "Close")]

    def __init__(self, rows: list[tuple[str, ...]]) -> None:
        super().__init__()
        self.rows = rows

    def compose(self) -> ComposeResult:
        with Vertical(id="compare-card"):
            yield Static("ALL CITIES", id="add-title")
            yield DataTable(id="compare-table", zebra_stripes=True, cursor_type="none")
            yield Static("v / Esc close", id="add-hint")

    def on_mount(self) -> None:
        table = self.query_one("#compare-table", DataTable)
        table.add_columns("City", "Now", "Sky", "Feels", "Humidity", "Wind", "Rain", "AQI")
        for row in self.rows:
            table.add_row(*row)

    def action_close(self) -> None:
        self.dismiss()


class ConfirmRemoveScreen(ModalScreen[bool]):
    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
        Binding("n", "cancel", "Cancel"),
        Binding("y", "confirm", "Remove"),
    ]

    def __init__(self, city: City) -> None:
        super().__init__()
        self.city = city

    def compose(self) -> ComposeResult:
        with Vertical(id="confirm-card"):
            yield Static("REMOVE CITY?", id="add-title")
            yield Static(self.city.label, id="confirm-city")
            yield Static("y remove · n / Esc keep", id="add-hint")

    def action_confirm(self) -> None:
        self.dismiss(True)

    def action_cancel(self) -> None:
        self.dismiss(False)


class WeatuiApp(App[None]):
    CSS_PATH = "styles.tcss"
    TITLE = "Weatui"
    SUB_TITLE = "open weather, no account"
    BINDINGS = [
        Binding("a", "add_city", "Add"),
        Binding("d", "remove_city", "Remove"),
        Binding("r", "refresh", "Refresh"),
        Binding("[", "move_up", "Move up"),
        Binding("]", "move_down", "Move down"),
        Binding("u", "toggle_units", "Units"),
        Binding("t", "cycle_theme", "Theme"),
        Binding("v", "compare", "All cities"),
        Binding("q", "quit", "Quit"),
    ]

    def __init__(self, store: Store | None = None) -> None:
        super().__init__()
        self.store = store or Store()
        self.forecasts: dict[tuple[float, float], Forecast] = {}
        self.air: dict[tuple[float, float], Air] = {}
        self._pending_selection: tuple[float, float] | None = None
        self._last_update: datetime | None = None
        self._city_serial = 0

    def compose(self) -> ComposeResult:
        with Vertical(id="shell"):
            yield Static("WEATUI  ·  open weather, no account", id="topbar")
            with Horizontal(id="body"):
                with Vertical(id="sidebar"):
                    yield Static("CITIES", classes="section")
                    yield ListView(id="cities")
                    yield Static("a add  d remove  ↑↓ browse\n[ ] move  v all cities", id="side-hint")
                with Vertical(id="details"):
                    yield Static("CURRENT", classes="section")
                    yield Static(id="current")
                    yield Static("NEXT 7 DAYS", classes="section")
                    yield DataTable(id="days", zebra_stripes=True, cursor_type="none")
                    yield Static("NEXT HOURS", classes="section")
                    yield Static(id="hours")
            yield Static(self._footer_text(), id="statusbar")

    def on_mount(self) -> None:
        self._apply_theme()
        self._render_cities()
        self.refresh_interval = self.set_interval(self.store.config.refresh_seconds, self.action_refresh)
        self.action_refresh()

    def _footer_text(self) -> Text:
        if self.store.config.cities:
            city = self.store.config.cities[self.store.config.selected]
            updated = self._last_update.strftime("%H:%M") if self._last_update else "waiting"
            return Text(
                f"{city.name}  ·  {self.store.config.units}  ·  updated {updated}  ·  a add  r refresh  u units  t theme  ·  data © Open-Meteo.com (CC BY 4.0)",
                style="dim",
            )
        return Text(
            "No cities yet  ·  press a to add one  ·  data © Open-Meteo.com (CC BY 4.0)",
            style="dim",
        )

    def _apply_theme(self) -> None:
        for theme in THEMES:
            self.screen.remove_class(f"theme-{theme}")
        self.screen.add_class(f"theme-{self.store.config.theme}")

    def _shell_ready(self) -> bool:
        try:
            self.query_one("#current", Static)
        except NoMatches:
            return False
        return True

    def _render_cities(self) -> None:
        if not self._shell_ready():
            return
        city_list = self.query_one("#cities", ListView)
        city_list.clear()
        for city in self.store.config.cities:
            self._city_serial += 1
            city_list.append(ListItem(Label(city.name), id=f"city-{self._city_serial}"))
        if self.store.config.cities:
            city_list.index = self.store.config.selected

    def _render_selection(self) -> None:
        if not self._shell_ready():
            return
        cities = self.store.config.cities
        if not cities:
            self.query_one("#current", Static).update("Add a city to see the forecast.")
            self.query_one("#days", DataTable).clear(columns=True)
            self.query_one("#hours", Static).update("")
            self.query_one("#statusbar", Static).update(self._footer_text())
            return
        city = cities[self.store.config.selected]
        key = (city.latitude, city.longitude)
        self._pending_selection = key
        forecast = self.forecasts.get(key)
        if forecast is None:
            self.query_one("#current", Static).update(f"{city.label}\n\nLoading forecast…")
            self.query_one("#days", DataTable).clear(columns=True)
            self.query_one("#hours", Static).update("")
        else:
            self._render_forecast(city, forecast)
        self.query_one("#statusbar", Static).update(self._footer_text())

    def _render_forecast(self, city: City, forecast: Forecast) -> None:
        units = self.store.config.units
        current = Text()
        current.append(f"{city.label}\n\n", style="bold")
        current.append(f"{format_temp(forecast.temperature_c, units)}", style="bold")
        current.append(f"  ·  {weather_text(forecast.code)}\n", style="")
        current.append(
            f"feels {format_temp(forecast.feels_like_c, units)}  ·  "
            f"{forecast.humidity}% humidity  ·  "
            f"{format_wind(forecast.wind_kmh, units)} {wind_direction(forecast.wind_direction)}  ·  "
            f"UV {forecast.uv:.0f}\n",
            style="dim",
        )
        current.append(f"{forecast.precipitation_mm:.1f} mm now", style="dim")
        air = self.air.get((city.latitude, city.longitude))
        if air is not None:
            current.append(
                f"  ·  AQI {air.aqi} {aqi_label(air.aqi)}  ·  PM2.5 {air.pm2_5:.0f}  ·  PM10 {air.pm10:.0f}",
                style="dim",
            )
        trend = sparkline([hour.temperature_c for hour in forecast.hours[:12]])
        if trend:
            current.append(f"\n12h  {trend}", style="dim")
        self.query_one("#current", Static).update(current)

        table = self.query_one("#days", DataTable)
        table.clear(columns=True)
        table.add_columns("Day", "Sky", "High", "Low", "Rain", "UV", "Sun")
        for day in forecast.days:
            table.add_row(
                day.date[5:],
                weather_text(day.code),
                format_temp(day.high_c, units),
                format_temp(day.low_c, units),
                f"{day.precipitation_chance}%",
                f"{day.uv:.0f}",
                f"{day.sunrise}–{day.sunset}",
            )
        hours = "   ".join(
            f"{hour.time[-5:]} {format_temp(hour.temperature_c, units)} {hour.precipitation_chance}%"
            for hour in forecast.hours[:6]
        )
        self.query_one("#hours", Static).update(hours or "No hourly data")

    def _set_status(self, message: str) -> None:
        if not self._shell_ready():
            return
        self.query_one("#statusbar", Static).update(Text(message, style="dim"))

    def action_refresh(self) -> None:
        if not self.store.config.cities:
            self._render_selection()
            return
        self._refresh_worker()

    @work(thread=True, exclusive=True)
    def _refresh_worker(self) -> None:
        for city in list(self.store.config.cities):
            try:
                forecast = fetch_forecast(city)
            except WeatherError as exc:
                self.call_from_thread(self._set_status, f"{city.label}: {exc}")
                continue
            self.call_from_thread(self._store_forecast, city, forecast)
            try:
                air = fetch_air_quality(city)
            except WeatherError:
                continue
            self.call_from_thread(self._store_air, city, air)

    def _store_forecast(self, city: City, forecast: Forecast) -> None:
        self.forecasts[(city.latitude, city.longitude)] = forecast
        self._last_update = datetime.now()
        self._render_selection()

    def _store_air(self, city: City, air: Air) -> None:
        self.air[(city.latitude, city.longitude)] = air
        self._render_selection()

    def action_compare(self) -> None:
        rows: list[tuple[str, ...]] = []
        units = self.store.config.units
        for city in self.store.config.cities:
            forecast = self.forecasts.get((city.latitude, city.longitude))
            air = self.air.get((city.latitude, city.longitude))
            if forecast is None:
                rows.append((city.name, "loading", "—", "—", "—", "—", "—", "—"))
                continue
            rows.append(
                (
                    city.name,
                    format_temp(forecast.temperature_c, units),
                    weather_text(forecast.code),
                    format_temp(forecast.feels_like_c, units),
                    f"{forecast.humidity}%",
                    format_wind(forecast.wind_kmh, units),
                    f"{forecast.precipitation_mm:.1f} mm",
                    str(air.aqi) if air else "—",
                )
            )
        if rows:
            self.push_screen(CompareScreen(rows))
        else:
            self._set_status("no saved cities yet")

    def action_add_city(self) -> None:
        self.push_screen(AddCityScreen(), self._lookup_city)

    def _lookup_city(self, name: str | None) -> None:
        if name:
            self._set_status(f"searching {name}…")
            self._geocode_worker(name)

    @work(thread=True, exclusive=True)
    def _geocode_worker(self, name: str) -> None:
        try:
            cities = search_cities(name)
        except WeatherError as exc:
            self.call_from_thread(self._set_status, str(exc))
            return
        self.call_from_thread(self._pick_city, cities)

    def _pick_city(self, cities: list[City]) -> None:
        self.push_screen(CityPickerScreen(cities), self._add_city)

    def _add_city(self, city: City) -> None:
        if city is None:
            return
        self.store.add_city(city)
        self._render_cities()
        self._render_selection()
        self._set_status(f"added {city.label}")
        self._refresh_worker()

    def action_remove_city(self) -> None:
        if not self.store.config.cities:
            return
        city = self.store.config.cities[self.store.config.selected]
        self.push_screen(ConfirmRemoveScreen(city), self._remove_confirmed)

    def _remove_confirmed(self, confirmed: bool | None) -> None:
        if not confirmed or not self.store.config.cities:
            return
        city = self.store.config.cities[self.store.config.selected]
        self.store.remove_city(self.store.config.selected)
        key = (city.latitude, city.longitude)
        self.forecasts.pop(key, None)
        self.air.pop(key, None)
        self._render_cities()
        self._render_selection()
        self._set_status(f"removed {city.name}")

    def action_move_up(self) -> None:
        self._move_city(-1)

    def action_move_down(self) -> None:
        self._move_city(1)

    def _move_city(self, delta: int) -> None:
        if not self.store.config.cities:
            return
        self.store.move_city(self.store.config.selected, delta)
        self._render_cities()
        self._render_selection()

    def action_toggle_units(self) -> None:
        self.store.set_units("F" if self.store.config.units == "C" else "C")
        self._render_selection()

    def action_cycle_theme(self) -> None:
        index = THEMES.index(self.store.config.theme)
        self.store.set_theme(THEMES[(index + 1) % len(THEMES)])
        self._apply_theme()
        self._render_selection()

    def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        index = event.list_view.index
        if index is None or index < 0:
            return
        self.store.select(index)
        self._render_selection()


def run(store: Store | None = None) -> None:
    WeatuiApp(store=store).run()
