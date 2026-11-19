from __future__ import annotations

from weatui import weather


def test_weather_labels_and_conversions() -> None:
    assert weather.weather_text(0) == "clear sky"
    assert weather.weather_text(95) == "thunderstorm"
    assert weather.weather_text(1234) == "mixed weather"
    assert weather.weather_icon(0, True) == "☀"
    assert weather.weather_icon(0, False) == "☾"
    assert weather.format_temp(20, "C") == "20°C"
    assert weather.format_temp(20, "F") == "68°F"
    assert weather.format_wind(16.09344, "F") == "10 mph"
    assert weather.wind_direction(90) == "E"
    assert weather.wind_direction(359) == "N"


def test_search_cities_parses_results(monkeypatch) -> None:
    monkeypatch.setattr(
        weather,
        "_request_json",
        lambda *_a, **_k: {
            "results": [
                {
                    "name": "Manila",
                    "admin1": "Metro Manila",
                    "country": "Philippines",
                    "latitude": 14.5995,
                    "longitude": 120.9842,
                }
            ]
        },
    )
    cities = weather.search_cities(" ManilA ")
    assert len(cities) == 1
    assert cities[0].label == "Manila, Metro Manila, Philippines"
    assert cities[0].latitude == 14.5995


def test_fetch_forecast_parses_payload(monkeypatch) -> None:
    monkeypatch.setattr(
        weather,
        "_request_json",
        lambda *_a, **_k: {
            "current": {
                "time": "2026-01-01T12:00",
                "temperature_2m": 30,
                "apparent_temperature": 33,
                "relative_humidity_2m": 70,
                "precipitation": 0,
                "weather_code": 2,
                "is_day": 1,
                "wind_speed_10m": 12,
                "wind_direction_10m": 180,
                "uv_index": 6,
            },
            "hourly": {
                "time": ["2026-01-01T12:00", "2026-01-01T13:00"],
                "temperature_2m": [30, 31],
                "precipitation_probability": [10, 20],
                "weather_code": [2, 3],
            },
            "daily": {
                "time": ["2026-01-01"],
                "temperature_2m_max": [32],
                "temperature_2m_min": [25],
                "weather_code": [2],
                "precipitation_probability_max": [30],
                "uv_index_max": [7],
                "sunrise": ["2026-01-01T06:10"],
                "sunset": ["2026-01-01T17:40"],
            },
        },
    )
    city = weather.City("Manila", "", "Philippines", 14.6, 121.0)
    forecast = weather.fetch_forecast(city)
    assert forecast.temperature_c == 30
    assert forecast.humidity == 70
    assert forecast.hours[1].precipitation_chance == 20
    assert forecast.days[0].sunrise == "06:10"
    assert forecast.days[0].sunset == "17:40"
