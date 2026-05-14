"""Google Places API (New) tool for destination attraction search."""
from typing import Any, Dict, List, Optional

import httpx
from loguru import logger

from app.core.config import settings


PLACES_TEXT_SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"

PLACE_FIELD_MASK = ",".join(
    [
        "places.id",
        "places.displayName",
        "places.formattedAddress",
        "places.location",
        "places.rating",
        "places.userRatingCount",
        "places.priceLevel",
        "places.types",
        "places.websiteUri",
        "places.googleMapsUri",
        "places.editorialSummary",
    ]
)


async def search_places_to_visit(
    destination: str,
    query: Optional[str] = None,
    max_results: int = 8,
    language_code: str = "en",
) -> Dict[str, Any]:
    """
    Search Google Places API (New) for attractions and places to visit.

    Uses Text Search (New), which is a POST endpoint and requires an explicit
    response field mask.
    """
    if not destination:
        return _fallback_places(destination)

    if not settings.GOOGLE_PLACES_API_KEY:
        return _fallback_places(destination)

    text_query = query or f"top tourist attractions and places to visit in {destination}"
    safe_max_results = min(max(int(max_results or 8), 1), 20)

    payload: Dict[str, Any] = {
        "textQuery": text_query,
        "maxResultCount": safe_max_results,
        "languageCode": language_code,
    }

    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": settings.GOOGLE_PLACES_API_KEY,
        "X-Goog-FieldMask": PLACE_FIELD_MASK,
    }

    try:
        async with httpx.AsyncClient(timeout=12.0) as client:
            response = await client.post(PLACES_TEXT_SEARCH_URL, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()

        places = [_normalize_place(place) for place in data.get("places", [])]
        return {
            "destination": destination,
            "query": text_query,
            "places": places,
            "count": len(places),
            "source": "Google Places API (New)",
        }
    except Exception as e:
        logger.warning(f"Google Places search error for {destination}: {e}")
        return _fallback_places(destination)


def format_places_for_prompt(places_data: Optional[Dict[str, Any]]) -> str:
    """Render place search data into compact text for LLM prompts."""
    if not places_data or not places_data.get("places"):
        return ""

    lines = []
    for index, place in enumerate(places_data["places"], start=1):
        rating = place.get("rating")
        reviews = place.get("user_rating_count")
        rating_text = f" - {rating}/5"
        if reviews:
            rating_text += f" ({reviews} reviews)"
        if not rating:
            rating_text = ""

        summary = place.get("summary")
        address = place.get("address")
        maps_url = place.get("google_maps_url")
        line = f"{index}. {place.get('name', 'Unnamed place')}{rating_text}"
        if address:
            line += f"\n   Address: {address}"
        if summary:
            line += f"\n   Summary: {summary}"
        if maps_url:
            line += f"\n   Map: {maps_url}"
        lines.append(line)

    return "\n".join(lines)


def _normalize_place(place: Dict[str, Any]) -> Dict[str, Any]:
    display_name = place.get("displayName") or {}
    location = place.get("location") or {}
    editorial_summary = place.get("editorialSummary") or {}

    return {
        "id": place.get("id"),
        "name": display_name.get("text"),
        "address": place.get("formattedAddress"),
        "latitude": location.get("latitude"),
        "longitude": location.get("longitude"),
        "rating": place.get("rating"),
        "user_rating_count": place.get("userRatingCount"),
        "price_level": place.get("priceLevel"),
        "types": place.get("types", []),
        "website_url": place.get("websiteUri"),
        "google_maps_url": place.get("googleMapsUri"),
        "summary": editorial_summary.get("text"),
    }


def _fallback_places(destination: str) -> Dict[str, Any]:
    return {
        "destination": destination,
        "places": [],
        "count": 0,
        "note": "Live Google Places data unavailable. Configure GOOGLE_PLACES_API_KEY to enable place search.",
        "source": "Fallback",
    }
