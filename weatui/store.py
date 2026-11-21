"""Persistent config for saved cities and display preferences."""

from __future__ import annotations

import contextlib
import json
import os
from dataclasses import asdict, dataclass, field, replace
from pathlib import Path

from .weather import City

UNITS = ("C", "F")
THEMES = ("greenit", "bluney", "yellen", "gruvbox", "catppuccin", "tokyonight", "mono")
MAX_CITIES = 24


def config_path() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME")
    root = Path(base).expanduser() if base else Path.home() / ".config"
    return root / "weatui" / "config.json"


def _clean_city(raw: object) -> City | None:
    if not isinstance(raw, dict):
        return None
    try:
        name = str(raw["name"]).strip()[:80]
        latitude = float(raw["latitude"])
        longitude = float(raw["longitude"])
    except (KeyError, TypeError, ValueError):
        return None
    if not name or not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        return None
    return City(
        name=name,
        admin=str(raw.get("admin", "")).strip()[:80],
        country=str(raw.get("country", "")).strip()[:80],
        latitude=latitude,
        longitude=longitude,
    )


def _safe_int(value: object, default: int) -> int:
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError, OverflowError):
        return default


@dataclass
class Config:
    cities: list[City] = field(default_factory=list)
    units: str = "C"
    theme: str = "greenit"
    refresh_seconds: int = 600
    selected: int = 0

    def sanitized(self) -> Config:
        cities = self.cities[:MAX_CITIES]
        units = self.units.upper() if self.units.upper() in UNITS else "C"
        theme = self.theme.lower() if self.theme.lower() in THEMES else "greenit"
        refresh = max(60, min(3600, _safe_int(self.refresh_seconds, 600)))
        selected = max(0, min(len(cities) - 1, _safe_int(self.selected, 0))) if cities else 0
        return replace(
            self,
            cities=cities,
            units=units,
            theme=theme,
            refresh_seconds=refresh,
            selected=selected,
        )


class Store:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or config_path()
        self.config = Config()
        self.load()

    def load(self) -> None:
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return
        if not isinstance(raw, dict):
            return
        cities = []
        raw_cities = raw.get("cities")
        if isinstance(raw_cities, list):
            for item in raw_cities[:MAX_CITIES]:
                city = _clean_city(item)
                if city is not None:
                    cities.append(city)
        config = Config(
            cities=cities,
            units=str(raw.get("units", "C")),
            theme=str(raw.get("theme", "greenit")),
            refresh_seconds=_safe_int(raw.get("refresh_seconds"), 600),
            selected=_safe_int(raw.get("selected"), 0),
        )
        self.config = config.sanitized()

    def save(self) -> None:
        payload = {**asdict(self.config), "cities": [asdict(city) for city in self.config.cities]}
        tmp = None
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.path.with_name(self.path.name + f".{os.getpid()}.tmp")
            tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            tmp.replace(self.path)
        except OSError:
            if tmp is not None:
                with contextlib.suppress(OSError):
                    tmp.unlink()

    def add_city(self, city: City) -> bool:
        if any(item.latitude == city.latitude and item.longitude == city.longitude for item in self.config.cities):
            return False
        if len(self.config.cities) >= MAX_CITIES:
            return False
        self.config.cities.append(city)
        self.config.selected = len(self.config.cities) - 1
        self.save()
        return True

    def remove_city(self, index: int) -> None:
        if 0 <= index < len(self.config.cities):
            self.config.cities.pop(index)
            self.config.selected = max(0, min(len(self.config.cities) - 1, index))
            self.save()

    def move_city(self, index: int, delta: int) -> None:
        target = index + delta
        if 0 <= index < len(self.config.cities) and 0 <= target < len(self.config.cities):
            self.config.cities[index], self.config.cities[target] = (
                self.config.cities[target],
                self.config.cities[index],
            )
            self.config.selected = target
            self.save()

    def set_units(self, units: str) -> None:
        self.config.units = units.upper() if units.upper() in UNITS else "C"
        self.save()

    def set_theme(self, theme: str) -> None:
        self.config.theme = theme.lower() if theme.lower() in THEMES else "greenit"
        self.save()

    def select(self, index: int) -> None:
        if 0 <= index < len(self.config.cities):
            self.config.selected = index
            self.save()
