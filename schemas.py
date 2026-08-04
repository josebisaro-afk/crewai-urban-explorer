"""Pydantic models mirroring agent-content-ingest's exact ingestPoi/ingestEvent/
ingestBusiness field contracts (supabase/functions/agent-content-ingest/index.ts
in the urban-explorer-ai repo). Field names and requiredness must match that
file exactly — the edge function accepts unknown extra fields silently but
rejects a request item outright if a required field is missing or the wrong
type, and CrewAI has no visibility into that beyond what supabase_ingest.py
reports back.
"""
from typing import Literal, Optional

from pydantic import BaseModel, Field


class PoiItem(BaseModel):
    city: str
    name: str
    category: str
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)
    country: Optional[str] = None
    name_en: Optional[str] = None
    description_es: Optional[str] = None
    description_en: Optional[str] = None
    address: Optional[str] = None
    opening_hours: Optional[str] = None
    image_url: Optional[str] = None
    audio_url: Optional[str] = None
    premium_only: Optional[bool] = None
    accessibility_info: Optional[str] = None
    historical_period: Optional[str] = None
    fun_fact: Optional[str] = None
    rating: Optional[float] = Field(default=None, ge=0, le=5)


class EventItem(BaseModel):
    city: str
    title: str
    category: str
    date: str  # YYYY-MM-DD
    country: Optional[str] = None
    description: Optional[str] = None
    time_start: Optional[str] = None
    time_end: Optional[str] = None
    venue: Optional[str] = None
    address: Optional[str] = None
    price_info: Optional[str] = None
    image_url: Optional[str] = None
    is_free: Optional[bool] = None
    premium_only: Optional[bool] = None
    tags: Optional[list[str]] = None


class BusinessItem(BaseModel):
    city: str
    name: str
    category: str
    country: Optional[str] = None
    description: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    image_url: Optional[str] = None
    lat: Optional[float] = Field(default=None, ge=-90, le=90)
    lng: Optional[float] = Field(default=None, ge=-180, le=180)
    benefit_basic: Optional[str] = None
    benefit_premium: Optional[str] = None
    experience_premium: Optional[str] = None
    is_active: Optional[bool] = None
    canon_paid: Optional[bool] = None
    rating: Optional[float] = Field(default=None, ge=0, le=5)


class ContentBatch(BaseModel):
    """What the Director de Contenido agent assembles before calling
    send_to_content_ingest — one batch per content type, matching the
    {type, items} shape agent-content-ingest expects."""
    type: Literal["poi", "event", "business"]
    items: list[dict]


class CityJob(BaseModel):
    city: str
    country: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    poi_count: Optional[int] = None
    indexed_at: Optional[str] = None
