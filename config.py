"""Shared configuration: env vars, Supabase client, country -> language inference."""
import os

from supabase import create_client, Client

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_SERVICE_ROLE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
CREWAI_INGEST_SECRET = os.environ["CREWAI_INGEST_SECRET"]
CREWAI_KICKOFF_TOKEN = os.environ["CREWAI_KICKOFF_TOKEN"]
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]

AGENT_CONTENT_INGEST_URL = f"{SUPABASE_URL}/functions/v1/agent-content-ingest"

# supabase-py client, service role — same table access as the edge functions.
# Only used by the admin UI (GET /) to read content counts; agents never
# write to Postgres directly, they always go through agent-content-ingest
# so the same validation/upsert logic the app relies on applies here too.
supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

# Mirrors the country strings poi-discovery/Nominatim and agent-content-ingest's
# default ("Spain") produce for city_index.country. Falls back to English for
# any country not listed rather than guessing.
COUNTRY_LANGUAGE = {
    "spain": "es", "españa": "es", "mexico": "es", "méxico": "es",
    "argentina": "es", "colombia": "es", "chile": "es", "peru": "es",
    "perú": "es", "venezuela": "es", "ecuador": "es", "uruguay": "es",
    "paraguay": "es", "bolivia": "es", "cuba": "es", "guatemala": "es",
    "france": "fr", "belgium": "fr",
    "germany": "de", "austria": "de", "switzerland": "de",
    "italy": "it", "italia": "it",
    "portugal": "pt", "brazil": "pt", "brasil": "pt",
    "united kingdom": "en", "united states": "en", "ireland": "en",
    "usa": "en", "uk": "en", "australia": "en", "canada": "en",
    "netherlands": "nl", "japan": "ja", "china": "zh",
}


def language_for_country(country: str | None) -> str:
    if not country:
        return "es"
    return COUNTRY_LANGUAGE.get(country.strip().lower(), "en")


# Categories agent-content-ingest actually accepts — mirrors
# supabase/functions/agent-content-ingest/index.ts's VALID_CATEGORIES exactly.
# Keep both lists in sync if categories ever change.
VALID_CATEGORIES = {
    "monument", "museum", "church", "park", "viewpoint", "gastronomy",
    "culture", "nature", "hidden_gem", "route", "concert", "theatre",
    "flamenco", "festival", "market", "exhibition", "sport", "cinema",
    "family", "restaurant", "bar", "hotel", "shop", "experience", "tour",
    "art", "history", "nightlife", "architecture",
}
