"""Wikipedia research tool shared by every investigador/agente_* agent.

Generalises supabase/functions/poi-discovery/index.ts's wikiGeosearch +
wikiPageDetails to any Wikipedia language edition (poi-discovery only ever
hits en.wikipedia.org + es.wikipedia.org) — agents pass the target
language's ISO code and the tool hits <lang>.wikipedia.org directly, so
content research already happens in the language it needs to be written in
instead of being translated after the fact.

Two modes:
  - "geosearch": articles near a lat/lng (finding POIs/monuments physically
    near the city centre) — same use as poi-discovery's Wikipedia pass.
  - "search": free-text search (finding topical content — "flamenco",
    "gastronomía local", festival names — that has no fixed coordinate).
"""
from typing import Literal, Optional, Type

import httpx
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

USER_AGENT = "UrbanExplorerAI-CrewAI/1.0 (content research agent)"
REQUEST_TIMEOUT_S = 15.0


class WikipediaSearchInput(BaseModel):
    mode: Literal["geosearch", "search"] = Field(
        description='"geosearch" to find articles near coordinates, "search" for a free-text query.'
    )
    language: str = Field(default="es", description='ISO 639-1 code, e.g. "es", "en", "fr".')
    query: Optional[str] = Field(default=None, description="Free-text query. Required when mode='search'.")
    lat: Optional[float] = Field(default=None, description="Required when mode='geosearch'.")
    lng: Optional[float] = Field(default=None, description="Required when mode='geosearch'.")
    radius_m: int = Field(default=8000, description="Search radius in metres for geosearch (max 10000).")
    limit: int = Field(default=15, description="Max results.")


class WikipediaSearchTool(BaseTool):
    name: str = "wikipedia_search"
    description: str = (
        "Searches Wikipedia for real, verifiable content about places, history, "
        "culture, gastronomy or events. Use mode='geosearch' with lat/lng to find "
        "articles about physical places near a point; use mode='search' with a "
        "free-text query for topical research with no fixed location. Always "
        "returns article extracts you must summarise in your own words — never "
        "copy extract text verbatim into final POI/event descriptions."
    )
    args_schema: Type[BaseModel] = WikipediaSearchInput

    def _run(
        self,
        mode: str,
        language: str = "es",
        query: Optional[str] = None,
        lat: Optional[float] = None,
        lng: Optional[float] = None,
        radius_m: int = 8000,
        limit: int = 15,
    ) -> str:
        base = f"https://{language}.wikipedia.org/w/api.php"
        with httpx.Client(timeout=REQUEST_TIMEOUT_S, headers={"User-Agent": USER_AGENT}) as client:
            if mode == "geosearch":
                if lat is None or lng is None:
                    return "ERROR: lat and lng are required for mode='geosearch'."
                pages = self._geosearch(client, base, lat, lng, radius_m, limit)
            elif mode == "search":
                if not query:
                    return "ERROR: query is required for mode='search'."
                pages = self._textsearch(client, base, query, limit)
            else:
                return f"ERROR: unknown mode '{mode}'."

        if not pages:
            return f"No Wikipedia results for this {mode} in {language}."

        lines = []
        for p in pages:
            lines.append(
                f"- \"{p['title']}\" (pageid={p['pageid']}, "
                f"coords={p.get('lat')},{p.get('lon')}): {p.get('extract', '')[:500]}"
            )
        return "\n".join(lines)

    def _geosearch(self, client, base, lat, lng, radius_m, limit):
        geo_res = client.get(base, params={
            "action": "query", "list": "geosearch",
            "gscoord": f"{lat}|{lng}", "gsradius": min(radius_m, 10000),
            "gslimit": limit, "format": "json", "origin": "*",
        })
        geo_res.raise_for_status()
        results = geo_res.json().get("query", {}).get("geosearch", [])
        if not results:
            return []
        pageids = [str(r["pageid"]) for r in results]
        detail_res = client.get(base, params={
            "action": "query", "pageids": "|".join(pageids),
            "prop": "extracts|coordinates", "exintro": 1, "explaintext": 1,
            "exsentences": 5, "format": "json", "origin": "*",
        })
        detail_res.raise_for_status()
        pages = detail_res.json().get("query", {}).get("pages", {})
        out = []
        for r in results:
            page = pages.get(str(r["pageid"]))
            if not page or not page.get("extract"):
                continue
            coords = page.get("coordinates", [{}])[0]
            out.append({
                "pageid": r["pageid"], "title": page["title"],
                "extract": page["extract"],
                "lat": coords.get("lat", r.get("lat")),
                "lon": coords.get("lon", r.get("lon")),
            })
        return out

    def _textsearch(self, client, base, query, limit):
        search_res = client.get(base, params={
            "action": "query", "list": "search", "srsearch": query,
            "srlimit": limit, "format": "json", "origin": "*",
        })
        search_res.raise_for_status()
        results = search_res.json().get("query", {}).get("search", [])
        if not results:
            return []
        pageids = [str(r["pageid"]) for r in results]
        detail_res = client.get(base, params={
            "action": "query", "pageids": "|".join(pageids),
            "prop": "extracts", "exintro": 1, "explaintext": 1,
            "exsentences": 5, "format": "json", "origin": "*",
        })
        detail_res.raise_for_status()
        pages = detail_res.json().get("query", {}).get("pages", {})
        out = []
        for r in results:
            page = pages.get(str(r["pageid"]))
            if not page or not page.get("extract"):
                continue
            out.append({"pageid": r["pageid"], "title": page["title"], "extract": page["extract"]})
        return out
