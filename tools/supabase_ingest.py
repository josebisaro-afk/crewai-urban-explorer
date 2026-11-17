"""send_to_content_ingest — the only tool in this crew that writes to Supabase.
Only the Director de Contenido agent (tasks/director_contenido.py) is given
this tool, matching the skill doc's flow: agents investigate and draft,
the Director validates and is the one who actually sends content.

Wraps supabase/functions/agent-content-ingest/index.ts:
  POST {SUPABASE_URL}/functions/v1/agent-content-ingest
  Authorization: Bearer <CREWAI_INGEST_SECRET>
  Body: {"type": "poi"|"event"|"business", "items": [...]}

That endpoint enforces max 50 items/request and ~60 req/min — this tool
chunks larger batches accordingly and reports per-item failures back to the
agent instead of swallowing them, since the edge function itself returns
200 even when individual items fail validation.
"""
import math
import time
from typing import Literal, Type

import httpx
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from config import AGENT_CONTENT_INGEST_URL, CREWAI_INGEST_SECRET, VALID_CATEGORIES, supabase

MAX_ITEMS_PER_REQUEST = 50
FOOD_CATEGORIES = {"restaurant", "bar", "gastronomy"}
REQUEST_TIMEOUT_S = 30.0


class SupabaseIngestInput(BaseModel):
    type: Literal["poi", "event", "business"] = Field(
        description='Content type: "poi", "event" or "business".'
    )
    items: list[dict] = Field(
        description=(
            "List of items to upsert. Field names must exactly match the "
            "target schema — for POIs: city, name, category, lat, lng "
            "required (description_es, country, rating, etc. optional); "
            "for events: city, title, category, date (YYYY-MM-DD) required; "
            "for businesses: city, name, category required. "
            "See agentes-urban.md for the full field list."
        )
    )
    location: str = Field(
        default="", description="City this batch is for (used only for logging)."
    )


class SupabaseIngestTool(BaseTool):
    name: str = "send_to_content_ingest"
    description: str = (
        "Sends approved POI, event or business content to Urban Explorer AI's "
        "Supabase database via the agent-content-ingest edge function. This is "
        "the ONLY way content this crew produces ever reaches the app — nothing "
        "is saved unless this tool is called. Returns how many items were "
        "inserted, updated, or failed (with the reason for each failure)."
    )
    args_schema: Type[BaseModel] = SupabaseIngestInput

    @staticmethod
    def _merge_with_existing_pois(items: list[dict]) -> list[dict]:
        """Un lugar a menos de 80 m de otro ya guardado es el mismo sitio
        (p. ej. "Catedral de Santa Isabel" y "Catedral de Santa Isabel
        (Košice)"): se usa el nombre guardado para que sea una actualización
        y no un duplicado."""
        cities = {it.get("city") for it in items if it.get("city")}
        existing: list[dict] = []
        for city in cities:
            try:
                res = supabase.table("points_of_interest").select("name,lat,lng").eq("city", city).execute()
                existing += [dict(r, city=city) for r in (res.data or [])]
            except Exception:  # noqa: BLE001
                return items
        def dist_m(a_lat, a_lng, b_lat, b_lng):
            k = math.pi / 180
            x = (b_lng - a_lng) * k * math.cos((a_lat + b_lat) * k / 2)
            y = (b_lat - a_lat) * k
            return 6371000 * math.hypot(x, y)
        for it in items:
            lat, lng = it.get("lat"), it.get("lng")
            if not isinstance(lat, (int, float)) or not isinstance(lng, (int, float)):
                continue
            best = None
            for ex in existing:
                if ex["city"] != it.get("city") or ex.get("lat") is None or ex.get("lng") is None:
                    continue
                d = dist_m(lat, lng, float(ex["lat"]), float(ex["lng"]))
                if d <= 80 and (best is None or d < best[0]):
                    best = (d, ex["name"])
            if best and best[1] != it.get("name"):
                it["name"] = best[1]
        return items

    def _run(self, type: str, items: list[dict], location: str = "") -> str:
        if type == "poi":
            items = self._merge_with_existing_pois(items)
        unknown_categories = {
            item.get("category") for item in items
            if item.get("category") not in VALID_CATEGORIES
        }
        if unknown_categories:
            return (
                f"REJECTED before sending — unknown categories {unknown_categories}. "
                f"Valid categories: {sorted(VALID_CATEGORIES)}"
            )

        total_inserted = total_updated = total_failed = 0
        errors: list[str] = []

        with httpx.Client(timeout=REQUEST_TIMEOUT_S) as client:
            for start in range(0, len(items), MAX_ITEMS_PER_REQUEST):
                chunk = items[start:start + MAX_ITEMS_PER_REQUEST]
                result = self._post_with_retry(client, type, chunk)
                if "error" in result:
                    errors.append(result["error"])
                    continue
                total_inserted += result.get("inserted", 0)
                total_updated += result.get("updated", 0)
                total_failed += result.get("failed", 0)
                for r in result.get("results", []):
                    if not r.get("ok"):
                        errors.append(f"{r.get('key')}: {r.get('error')}")

        # Restaurantes y bares con coordenadas también van como lugares del
        # mapa: la app arma su sección "Restaurantes" con esos lugares.
        if type == "business":
            food = [
                {k: v for k, v in {
                    "city": it.get("city"), "country": it.get("country"),
                    "name": it.get("name"), "category": it.get("category"),
                    "lat": it.get("lat"), "lng": it.get("lng"),
                    "address": it.get("address"),
                    "description_es": it.get("description"),
                }.items() if v not in (None, "")}
                for it in items
                if it.get("category") in FOOD_CATEGORIES
                and isinstance(it.get("lat"), (int, float)) and isinstance(it.get("lng"), (int, float))
            ]
            with httpx.Client(timeout=REQUEST_TIMEOUT_S) as client:
                for start in range(0, len(food), MAX_ITEMS_PER_REQUEST):
                    result = self._post_with_retry(client, "poi", food[start:start + MAX_ITEMS_PER_REQUEST])
                    if "error" in result:
                        errors.append(f"poi(restaurantes): {result['error']}")

        summary = (
            f"[{location or type}] inserted={total_inserted} "
            f"updated={total_updated} failed={total_failed}"
        )
        if errors:
            summary += "\nErrors:\n" + "\n".join(f"- {e}" for e in errors[:20])
        return summary

    def _post_with_retry(self, client: httpx.Client, type_: str, chunk: list[dict], attempt: int = 1) -> dict:
        try:
            res = client.post(
                AGENT_CONTENT_INGEST_URL,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {CREWAI_INGEST_SECRET}",
                },
                json={"type": type_, "items": chunk},
            )
        except httpx.HTTPError as exc:
            return {"error": f"request failed: {exc}"}

        if res.status_code == 429 and attempt <= 3:
            time.sleep(2 * attempt)
            return self._post_with_retry(client, type_, chunk, attempt + 1)
        if res.status_code >= 400:
            return {"error": f"HTTP {res.status_code}: {res.text[:300]}"}
        try:
            return res.json()
        except ValueError:
            return {"error": f"non-JSON response: {res.text[:300]}"}
