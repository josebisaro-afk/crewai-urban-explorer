"""Weather context tool — shared by clima_contexto (Discovery) and
clima_montana (Hiker). Uses Open-Meteo (https://open-meteo.com), a free
public weather API that needs no API key — same "free public data source"
pattern already used by wikipedia_tool.py and overpass_tool.py. No secret
to configure, nothing to break if unset.
"""
from typing import Type

import httpx
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
REQUEST_TIMEOUT_S = 15.0

WEATHER_CODES = {
    0: "despejado", 1: "mayormente despejado", 2: "parcialmente nublado", 3: "nublado",
    45: "niebla", 48: "niebla con escarcha",
    51: "llovizna ligera", 53: "llovizna moderada", 55: "llovizna intensa",
    61: "lluvia ligera", 63: "lluvia moderada", 65: "lluvia intensa",
    71: "nevada ligera", 73: "nevada moderada", 75: "nevada intensa",
    80: "chubascos ligeros", 81: "chubascos moderados", 82: "chubascos intensos",
    95: "tormenta", 96: "tormenta con granizo", 99: "tormenta con granizo fuerte",
}


class WeatherInput(BaseModel):
    lat: float = Field(description="Latitude.")
    lng: float = Field(description="Longitude.")


class WeatherContextTool(BaseTool):
    name: str = "weather_context"
    description: str = (
        "Gets the current weather and today's forecast (temperature, condition, "
        "wind) for a coordinate. Use this for real, current conditions — never "
        "invent weather. Useful for seasonal/practical notes in content "
        "(e.g. 'llevá agua, hace calor hoy') and for flagging unsafe hiking "
        "conditions (storms, heavy snow, high wind)."
    )
    args_schema: Type[BaseModel] = WeatherInput

    def _run(self, lat: float, lng: float) -> str:
        try:
            res = httpx.get(
                OPEN_METEO_URL,
                params={
                    "latitude": lat, "longitude": lng,
                    "current": "temperature_2m,weather_code,wind_speed_10m,precipitation",
                    "daily": "temperature_2m_max,temperature_2m_min,weather_code",
                    "forecast_days": 1,
                    "timezone": "auto",
                },
                timeout=REQUEST_TIMEOUT_S,
            )
            res.raise_for_status()
        except httpx.HTTPError as exc:
            return f"ERROR: no se pudo obtener el clima: {exc}"

        data = res.json()
        current = data.get("current", {})
        daily = data.get("daily", {})

        code = current.get("weather_code")
        condition = WEATHER_CODES.get(code, "condición desconocida")
        temp = current.get("temperature_2m")
        wind = current.get("wind_speed_10m")
        precip = current.get("precipitation")
        tmax = (daily.get("temperature_2m_max") or [None])[0]
        tmin = (daily.get("temperature_2m_min") or [None])[0]

        return (
            f"Ahora mismo: {condition}, {temp}°C, viento {wind} km/h, "
            f"precipitación {precip} mm. Hoy: mínima {tmin}°C, máxima {tmax}°C."
        )
