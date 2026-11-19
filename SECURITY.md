# Security

Weatui stores only city names, coordinates and display preferences in a local
JSON config. It has no accounts, telemetry or analytics.

Network requests go only to `geocoding-api.open-meteo.com` and
`api.open-meteo.com` over HTTPS. Forecast and geocoding responses are treated as
untrusted data and validated before display.

Report vulnerabilities privately through GitHub Security Advisories.
