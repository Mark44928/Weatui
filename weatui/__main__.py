"""CLI entry point for Weatui."""

from __future__ import annotations

import argparse
from collections.abc import Sequence

from . import __version__
from .store import THEMES, UNITS, Store


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="weatui",
        description="A friendly terminal weather app powered by Open-Meteo.",
    )
    parser.add_argument("--version", "-v", action="version", version=f"weatui {__version__}")
    parser.add_argument("--list-cities", action="store_true", help="print saved cities and exit")
    parser.add_argument("--units", choices=UNITS, type=str.upper, help="set temperature units")
    parser.add_argument("--theme", choices=THEMES, help="set the interface theme")
    parser.add_argument("--list-themes", action="store_true", help="print available themes and exit")
    parser.add_argument("--tux", action="store_true", help="easter egg: a Tux dressed for the current weather")
    return parser


def tux_for_weather(code: int, is_day: bool, temp_c: float, units: str) -> str:
    from .weather import format_temp, weather_text

    if code in (0, 1):
        acc, label = ("☀" if is_day else "☾"), "clear"
    elif code in (2, 3):
        acc, label = "☁", "cloudy"
    elif code in (45, 48):
        acc, label = "≈", "fog"
    elif 51 <= code <= 67 or 80 <= code <= 82:
        acc, label = "☂", "rain"
    elif 71 <= code <= 77 or 85 <= code <= 86:
        acc, label = "❄", "snow"
    elif code >= 95:
        acc, label = "⚡", "storm"
    else:
        acc, label = "·", "mixed"
    tux = (
        "   .--.\n"
        "  |o_o |  " + acc + "\n"
        "  |:_/ |\n"
        " //   \\ \\\n"
        "(|     | )\n"
        "/'\\_   _/`\\\n"
        "\\___)=(___/"
    )
    return f"{tux}\n  {label} · {format_temp(temp_c, units)} · {weather_text(code)}"


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    store = Store()
    if args.units:
        store.set_units(args.units)
    if args.theme:
        store.set_theme(args.theme)
    if args.list_themes:
        print("available themes: " + ", ".join(THEMES))
        return 0
    if args.tux:
        from .weather import WeatherError, fetch_forecast

        if not store.config.cities:
            print("No saved cities. Add one first (run weatui, press a).")
            return 0
        city = store.config.cities[store.config.selected]
        try:
            forecast = fetch_forecast(city)
        except WeatherError as exc:
            print(f"weatui: {exc}")
            return 1
        print(tux_for_weather(forecast.code, forecast.is_day, forecast.temperature_c, store.config.units))
        return 0
    if args.list_cities:
        if not store.config.cities:
            print("No saved cities.")
            return 0
        for index, city in enumerate(store.config.cities, start=1):
            marker = "*" if index - 1 == store.config.selected else " "
            print(f"{marker} {index}. {city.label}  ({city.latitude:.4f}, {city.longitude:.4f})")
        return 0
    from .app import run

    run(store)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
