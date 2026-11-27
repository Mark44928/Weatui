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
    return parser


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
