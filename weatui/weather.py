"""Open-Meteo client and small weather formatting helpers."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from http.client import HTTPException
from urllib.parse import urlencode
from urllib.request import Request, urlopen

GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
AIR_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"
USER_AGENT = "weatui/1.0 (Open-Meteo; terminal weather)"


class WeatherError(RuntimeError):
    """Network or API payload problem."""


@dataclass(frozen=True, slots=True)
class City:
    name: str
    admin: str
    country: str
    latitude: float
    longitude: float

    @property
    def label(self) -> str:
        bits = [self.name]
        if self.admin and self.admin.lower() != self.name.lower():
            bits.append(self.admin)
        if self.country:
            bits.append(self.country)
        return ", ".join(bits)


@dataclass(frozen=True, slots=True)
class Hour:
    time: str
    temperature_c: float
    precipitation_chance: int
    code: int


@dataclass(frozen=True, slots=True)
class Day:
    date: str
    high_c: float
    low_c: float
    code: int
    precipitation_chance: int
    uv: float
    sunrise: str
    sunset: str


@dataclass(frozen=True, slots=True)
class Air:
    aqi: int
    pm2_5: float
    pm10: float


@dataclass(frozen=True, slots=True)
class Forecast:
    current_time: str
    temperature_c: float
    feels_like_c: float
    humidity: int
    precipitation_mm: float
    code: int
    is_day: bool
    wind_kmh: float
    wind_direction: int
    uv: float
    hours: tuple[Hour, ...]
    days: tuple[Day, ...]


def _request_json(url: str, timeout: float = 12.0) -> dict:
    request = Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urlopen(request, timeout=timeout) as response:
            raw = response.read(2_000_000)
    except (OSError, ValueError, HTTPException) as exc:
        raise WeatherError(f"could not reach Open-Meteo: {exc}") from exc
    try:
        payload = json.loads(raw)
    except (TypeError, ValueError) as exc:
        raise WeatherError("Open-Meteo returned invalid JSON") from exc
    if not isinstance(payload, dict):
        raise WeatherError("Open-Meteo returned an unexpected response")
    return payload


def search_cities(name: str) -> list[City]:
    name = " ".join(name.split())[:80]
    if not name:
        raise WeatherError("city name is empty")
    url = f"{GEOCODE_URL}?{urlencode({'name': name, 'count': 6, 'language': 'en', 'format': 'json'})}"
    payload = _request_json(url)
    cities: list[City] = []
    for item in payload.get("results") or []:
        if not isinstance(item, dict):
            continue
        try:
            latitude = float(item["latitude"])
            longitude = float(item["longitude"])
        except (KeyError, TypeError, ValueError):
            continue
        if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
            continue
        city_name = (item.get("name") or "").strip()
        if not city_name:
            continue
        cities.append(
            City(
                name=city_name[:80],
                admin=(item.get("admin1") or "").strip()[:80],
                country=(item.get("country") or "").strip()[:80],
                latitude=latitude,
                longitude=longitude,
            )
        )
    if not cities:
        raise WeatherError(f"no city found for {name!r}")
    return cities


def _number(value: object, default: float = 0.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return number if math.isfinite(number) else default


def _required_number(value: object) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise WeatherError("response is missing a required reading") from None
    if not math.isfinite(number):
        raise WeatherError("response is missing a required reading")
    return number


def _time_list(value: object) -> list[str]:
    return [str(item) if item is not None else "" for item in value] if isinstance(value, list) else []


def fetch_forecast(city: City, days: int = 7) -> Forecast:
    days = max(1, min(16, int(days)))
    query = {
        "latitude": city.latitude,
        "longitude": city.longitude,
        "current": (
            "temperature_2m,relative_humidity_2m,apparent_temperature,"
            "is_day,precipitation,weather_code,cloud_cover,wind_speed_10m,"
            "wind_direction_10m,uv_index"
        ),
        "hourly": "temperature_2m,precipitation_probability,weather_code",
        "daily": (
            "weather_code,temperature_2m_max,temperature_2m_min,"
            "sunrise,sunset,uv_index_max,precipitation_probability_max,"
            "wind_speed_10m_max"
        ),
        "timezone": "auto",
        "forecast_days": days,
    }
    payload = _request_json(f"{FORECAST_URL}?{urlencode(query)}")
    current = payload.get("current")
    hourly = payload.get("hourly")
    daily = payload.get("daily")
    if not isinstance(current, dict) or not isinstance(hourly, dict) or not isinstance(daily, dict):
        raise WeatherError("Open-Meteo response is missing forecast sections")

    hour_times = _time_list(hourly.get("time"))
    hour_temps = hourly.get("temperature_2m") or []
    hour_rain = hourly.get("precipitation_probability") or []
    hour_codes = hourly.get("weather_code") or []
    hours: list[Hour] = []
    # Start from the current hour, not from 00:00 of today
    current_hour = str(current.get("time", ""))[:13]
    start = 0
    if current_hour:
        for i, t in enumerate(hour_times):
            if t[:13] >= current_hour:
                start = i
                break
    for offset, time in enumerate(hour_times[start:start + 24]):
        index = start + offset
        if index < len(hour_temps) and hour_temps[index] is None:
            continue
        try:
            temperature = _number(hour_temps[index])
            rain = int(_number(hour_rain[index]))
            code = int(_number(hour_codes[index]))
        except (IndexError, TypeError, ValueError):
            continue
        hours.append(Hour(time, temperature, max(0, min(100, rain)), code))

    daily_times = _time_list(daily.get("time"))
    highs = daily.get("temperature_2m_max") or []
    lows = daily.get("temperature_2m_min") or []
    day_codes = daily.get("weather_code") or []
    day_rain = daily.get("precipitation_probability_max") or []
    day_uv = daily.get("uv_index_max") or []
    sunrises = _time_list(daily.get("sunrise"))
    sunsets = _time_list(daily.get("sunset"))
    out_days: list[Day] = []
    for index, date in enumerate(daily_times[:days]):
        if index < len(highs) and highs[index] is None:
            continue
        if index < len(lows) and lows[index] is None:
            continue
        try:
            out_days.append(
                Day(
                    date=date,
                    high_c=_number(highs[index]),
                    low_c=_number(lows[index]),
                    code=int(_number(day_codes[index])),
                    precipitation_chance=max(0, min(100, int(_number(day_rain[index])))),
                    uv=_number(day_uv[index]),
                    sunrise=sunrises[index][-5:] if index < len(sunrises) else "--:--",
                    sunset=sunsets[index][-5:] if index < len(sunsets) else "--:--",
                )
            )
        except (IndexError, TypeError, ValueError):
            continue

    return Forecast(
        current_time=str(current.get("time", "")),
        temperature_c=_required_number(current.get("temperature_2m")),
        feels_like_c=_required_number(current.get("apparent_temperature")),
        humidity=int(_required_number(current.get("relative_humidity_2m"))),
        precipitation_mm=_number(current.get("precipitation")),
        code=int(_number(current.get("weather_code"))),
        is_day=bool(current.get("is_day", 1)),
        wind_kmh=_number(current.get("wind_speed_10m")),
        wind_direction=int(_number(current.get("wind_direction_10m"))),
        uv=_number(current.get("uv_index")),
        hours=tuple(hours),
        days=tuple(out_days),
    )


def fetch_air_quality(city: City) -> Air:
    query = {
        "latitude": city.latitude,
        "longitude": city.longitude,
        "current": "european_aqi,pm2_5,pm10",
        "timezone": "auto",
    }
    payload = _request_json(f"{AIR_URL}?{urlencode(query)}")
    current = payload.get("current")
    if not isinstance(current, dict):
        raise WeatherError("Open-Meteo air response is missing current data")
    aqi_raw = current.get("european_aqi")
    if aqi_raw is None:
        raise WeatherError("Open-Meteo air response is missing AQI")
    return Air(
        aqi=int(_number(aqi_raw)),
        pm2_5=_number(current.get("pm2_5")),
        pm10=_number(current.get("pm10")),
    )


def aqi_label(aqi: int) -> str:
    if aqi <= 20:
        return "good"
    if aqi <= 40:
        return "fair"
    if aqi <= 60:
        return "moderate"
    if aqi <= 80:
        return "poor"
    if aqi <= 100:
        return "very poor"
    return "extreme"


def sparkline(values: list[float] | tuple[float, ...], width: int = 12) -> str:
    points = [float(v) for v in values if math.isfinite(float(v))][:width]
    if not points:
        return ""
    low, high = min(points), max(points)
    if high - low < 0.1:
        return "─" * len(points)
    blocks = "▁▂▃▄▅▆▇█"
    return "".join(blocks[round((v - low) / (high - low) * (len(blocks) - 1))] for v in points)


def c_to_f(value: float) -> float:
    return value * 9 / 5 + 32


def format_temp(value_c: float, units: str) -> str:
    value = c_to_f(value_c) if units.upper() == "F" else value_c
    return f"{value:.0f}°{'F' if units.upper() == 'F' else 'C'}"


def format_wind(kmh: float, units: str) -> str:
    return f"{kmh * 0.621371:.0f} mph" if units.upper() == "F" else f"{kmh:.0f} km/h"


def wind_direction(degrees: float) -> str:
    names = ("N", "NE", "E", "SE", "S", "SW", "W", "NW")
    return names[round(degrees / 45) % 8]


def weather_text(code: int) -> str:
    table = {
        0: "clear sky",
        1: "mostly clear",
        2: "partly cloudy",
        3: "overcast",
        45: "fog",
        48: "freezing fog",
        51: "light drizzle",
        53: "drizzle",
        55: "heavy drizzle",
        56: "freezing drizzle",
        57: "heavy freezing drizzle",
        61: "light rain",
        63: "rain",
        65: "heavy rain",
        66: "freezing rain",
        67: "heavy freezing rain",
        71: "light snow",
        73: "snow",
        75: "heavy snow",
        77: "snow grains",
        80: "light showers",
        81: "showers",
        82: "violent showers",
        85: "snow showers",
        86: "heavy snow showers",
        95: "thunderstorm",
        96: "thunderstorm with hail",
        99: "severe thunderstorm",
    }
    return table.get(code, "mixed weather")


def weather_icon(code: int, is_day: bool = True) -> str:
    if code in (0, 1):
        return "☀" if is_day else "☾"
    if code in (2, 3, 45, 48):
        return "☁"
    if code in (71, 73, 75, 77, 85, 86):
        return "❄"
    if code in (95, 96, 99):
        return "⚡"
    return "☂"
