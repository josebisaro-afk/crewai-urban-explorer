"""Overpass (OpenStreetMap) POI lookup — the geographic-data counterpart to
wikipedia_tool.py. Same free public API, bbox filter and User-Agent pattern
as supabase/functions/hiking-routes/index.ts's findTrails()/findNamedPaths(),
generalised from hiking trails to any OSM tag (restaurants, hotels, shops,
viewpoints, nightlife...) so each specialist agent can search the specific
tags relevant to its own domain.
"""
import math
import time
from typing import Type

import httpx
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
# Si el servidor principal está saturado (502/504/429), se prueba un espejo.
OVERPASS_MIRRORS = (
    OVERPASS_URL,
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
)
USER_AGENT = "UrbanExplorerAI-CrewAI/1.0 (content research agent)"
REQUEST_TIMEOUT_S = 12.0
# Si todos los servidores fallan, no se vuelve a intentar durante 30 min:
# antes los agentes repetían la búsqueda 8-10 veces seguidas (minutos y
# dinero tirados) cuando Overpass no respondía desde GitHub.
_DOWN_FOR_S = 1800
_down_until = 0.0


def _bbox_from_radius(lat: float, lng: float, radius_m: float) -> tuple[float, float, float, float]:
    lat_delta = radius_m / 111_320
    lng_delta = radius_m / (111_320 * math.cos(math.radians(lat)))
    return (lat - lat_delta, lng - lng_delta, lat + lat_delta, lng + lng_delta)


class OverpassPOIInput(BaseModel):
    lat: float = Field(description="Centre latitude (city centre, or a known landmark).")
    lng: float = Field(description="Centre longitude.")
    tags: list[str] = Field(
        description=(
            'OSM tag filters as "key=value" strings, e.g. '
            '["amenity=restaurant", "amenity=bar"] or ["tourism=hotel"] or '
            '["shop=market"] or ["leisure=park"]. Pick tags matching your '
            "agent's domain — see https://wiki.openstreetmap.org/wiki/Map_features."
        )
    )
    radius_m: int = Field(default=6000, description="Search radius in metres.")
    limit: int = Field(default=25, description="Max results.")


class OverpassPOITool(BaseTool):
    name: str = "overpass_poi_search"
    description: str = (
        "Finds real, currently-mapped places (restaurants, hotels, shops, parks, "
        "viewpoints, nightlife venues, etc.) near a coordinate using OpenStreetMap "
        "data via the Overpass API. Returns name, coordinates and address when "
        "available. Use this to verify a place actually exists and get accurate "
        "lat/lng before writing a POI or business entry — never invent coordinates."
    )
    args_schema: Type[BaseModel] = OverpassPOIInput

    def _run(self, lat: float, lng: float, tags: list[str], radius_m: int = 6000, limit: int = 25) -> str:
        global _down_until
        if time.monotonic() < _down_until:
            return ("OVERPASS NO DISPONIBLE ahora. No vuelvas a usar esta herramienta en esta tarea: "
                    "trabajá solo con la información que ya tenés y no inventes sitios ni coordenadas.")
        south, west, north, east = _bbox_from_radius(lat, lng, radius_m)
        clauses = []
        for tag in tags:
            if "=" not in tag:
                continue
            key, value = tag.split("=", 1)
            clauses.append(f'node["{key}"="{value}"]({south},{west},{north},{east});')
            clauses.append(f'way["{key}"="{value}"]({south},{west},{north},{east});')
        if not clauses:
            return "ERROR: no valid tags provided (expected 'key=value' strings)."

        query = f"""
        [out:json][timeout:20];
        (
          {"".join(clauses)}
        );
        out center tags {limit};
        """

        res = None
        last_error = ""
        for url in OVERPASS_MIRRORS:
            try:
                res = httpx.post(
                    url, content=query,
                    headers={"Content-Type": "text/plain", "User-Agent": USER_AGENT},
                    timeout=REQUEST_TIMEOUT_S,
                )
                res.raise_for_status()
                break
            except httpx.HTTPError as exc:
                last_error = str(exc)
                res = None
        if res is None:
            _down_until = time.monotonic() + _DOWN_FOR_S
            return (f"ERROR: Overpass no responde ({last_error[:80]}). OVERPASS NO DISPONIBLE: no vuelvas a "
                    "usar esta herramienta en esta tarea; trabajá con lo que ya tenés y no inventes sitios.")

        elements = res.json().get("elements", [])[:limit]
        if not elements:
            return "No OpenStreetMap results for these tags in this area."

        lines = []
        for el in elements:
            name = (el.get("tags") or {}).get("name")
            if not name:
                continue
            point_lat = el.get("lat") or (el.get("center") or {}).get("lat")
            point_lng = el.get("lon") or (el.get("center") or {}).get("lon")
            addr_parts = [
                (el.get("tags") or {}).get(k)
                for k in ("addr:street", "addr:housenumber")
            ]
            address = " ".join(p for p in addr_parts if p)
            lines.append(f"- {name} (lat={point_lat}, lng={point_lng}){f', address={address}' if address else ''}")
        return "\n".join(lines) if lines else "No named results for these tags in this area."
