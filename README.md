# Weatui

**Friendly terminal weather TUI powered by Open-Meteo — saved cities, current conditions, 7-day + hourly forecast. No API key.**

Built with Python + Textual. Works on Termux and Linux.

<p align="center"><img src="assets/logo.svg" width="760" alt="Weatui logo"></p>

<p align="center"><img src="docs/screenshot-weather.png" width="720" alt="Weatui weather screen"></p>

[![CI](https://github.com/Mark44928/Weatui/actions/workflows/ci.yml/badge.svg)](https://github.com/Mark44928/Weatui/actions/workflows/ci.yml)
[![Pages](https://img.shields.io/badge/site-GitHub%20Pages-7DBBFF)](https://mark44928.github.io/Weatui/)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![Textual](https://img.shields.io/badge/Textual-1.0%2B-5e5ce6)
![License](https://img.shields.io/badge/license-MIT-green)

## Quick start

```bash
pipx install git+https://github.com/Mark44928/Weatui.git
weatui
```

Or:

```bash
git clone https://github.com/Mark44928/Weatui
cd Weatui
bash install.sh
weatui
```

## Features

- saved cities in a readable JSON config
- current conditions, feels-like, humidity, wind, UV, rain and air quality
- 12-hour temperature sparkline + next 7 days and next 6 hours
- city search with proper match picking
- all-cities compare table
- Celsius / Fahrenheit toggle
- themes: Greenit, Bluney, Yellen, Gruvbox, Catppuccin, Tokyo Night, Mono
- automatic refresh (10 min default)
- no API key, no account, no telemetry

## Keys

| Key | Action |
|---|---|
| `a` | add a city |
| `d` | remove the selected city |
| `↑` / `↓` | choose a saved city |
| `[` / `]` | move city up / down |
| `r` | refresh now |
| `u` | Celsius / Fahrenheit |
| `t` | cycle theme |
| `v` | compare all cities |
| `q` | quit |

## Related Mark44928 projects

- [FlufflessPrompt](https://github.com/Mark44928/FlufflessPrompt) — quiet Oh My Zsh theme
- [SnakTUI](https://github.com/Mark44928/SnakTUI) — neon terminal Snake
- [Solvamath](https://github.com/Mark44928/Solvamath) — math puzzle game
- [Greenit](https://github.com/Mark44928/Greenit) · [Bluney](https://github.com/Mark44928/Bluney) · [Yellen](https://github.com/Mark44928/Yellen) — theme families
- Full hub: [Mark44928](https://mark44928.github.io/Mark44928/)

## License

MIT. Weather data by Open-Meteo under CC BY 4.0.

---

<div align="center">
<img width="100%" src="https://api.star-history.com/svg?repos=Mark44928/Weatui&type=Date" alt="Star history" />
</div>
