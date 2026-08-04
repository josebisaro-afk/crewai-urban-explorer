"""Overpass (OpenStreetMap) POI lookup — the geographic-data counterpart to
wikipedia_tool.py. Same free public API, bbox filter and User-Agent pattern
as supabase/functions/hiking-routes/index.ts's findTrails()/findNamedPaths(),
generalised from hiking trails to any OSM tag (restaurants, hotels, shops,
viewpoints, nightlife...) so each specialist agent can search the specific
tags relevant to its own domain.
"""
import math
from typing import Type

import httpx
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
USER_AGENT = "UrbanExplorerAI-CrewAI/1.0 (content research agent)"
REQUEST_TIMEOUT_S = 25.0


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

        try:
            res = httpx.post(
                OVERPASS_URL, content=query,
                headers={"Content-Type": "text/plain", "User-Agent": USER_AGENT},
                timeout=REQUEST_TIMEOUT_S,
            )
            res.raise_for_status()
        except httpx.HTTPError as exc:
            return f"ERROR: Overpass request failed: {exc}"

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
