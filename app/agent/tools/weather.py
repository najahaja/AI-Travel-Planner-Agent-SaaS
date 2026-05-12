"""Weather tool — uses OpenWeatherMap API with graceful fallback."""
import httpx
from typing import Optional, Dict, Any
from datetime import datetime
from app.core.config import settings
from loguru import logger


async def get_weather_info(destination: str, travel_date: Optional[str] = None) -> Dict[str, Any]:
    """
    Fetch current weather and climate info for a destination.
    Falls back to LLM-generated info if API key is unavailable.
    """
    if not settings.OPENWEATHER_API_KEY:
        return _get_fallback_weather(destination)

    try:
        # 1. Geocode destination to lat/lon
        geo_url = "http://api.openweathermap.org/geo/1.0/direct"
        async with httpx.AsyncClient(timeout=10.0) as client:
            geo_resp = await client.get(
                geo_url,
                params={"q": destination, "limit": 1, "appid": settings.OPENWEATHER_API_KEY},
            )
            geo_data = geo_resp.json()

            if not geo_data:
                return _get_fallback_weather(destination)

            lat, lon = geo_data[0]["lat"], geo_data[0]["lon"]
            country = geo_data[0].get("country", "")

            # 2. Get current weather
            weather_url = "https://api.openweathermap.org/data/2.5/weather"
            weather_resp = await client.get(
                weather_url,
                params={
                    "lat": lat,
                    "lon": lon,
                    "appid": settings.OPENWEATHER_API_KEY,
                    "units": "metric",
                },
            )
            weather_data = weather_resp.json()

            return {
                "destination": destination,
                "country": country,
                "current": {
                    "temperature_c": weather_data["main"]["temp"],
                    "feels_like_c": weather_data["main"]["feels_like"],
                    "humidity_pct": weather_data["main"]["humidity"],
                    "description": weather_data["weather"][0]["description"].title(),
                    "wind_kph": round(weather_data["wind"]["speed"] * 3.6, 1),
                },
                "best_time_to_visit": _get_best_time(destination),
                "packing_tips": _get_packing_tips(weather_data["weather"][0]["main"]),
                "travel_advisory": "Check your government's official travel advisory before departure.",
                "source": "OpenWeatherMap",
            }

    except Exception as e:
        logger.warning(f"Weather API error for {destination}: {e}")
        return _get_fallback_weather(destination)


def _get_best_time(destination: str) -> str:
    """Simple heuristic for best travel time."""
    dest_lower = destination.lower()
    if any(x in dest_lower for x in ["bali", "thailand", "indonesia", "sri lanka"]):
        return "April to October (dry season)"
    elif any(x in dest_lower for x in ["europe", "paris", "rome", "london", "barcelona"]):
        return "April to June and September to October"
    elif any(x in dest_lower for x in ["japan", "tokyo", "kyoto", "osaka"]):
        return "March to May (cherry blossom) or September to November"
    elif any(x in dest_lower for x in ["maldives", "dubai", "uae"]):
        return "November to April (cooler, drier months)"
    elif any(x in dest_lower for x in ["new york", "usa", "united states"]):
        return "April to June and September to November"
    else:
        return "Research specific seasonal patterns for this destination"


def _get_packing_tips(weather_main: str) -> list:
    tips_map = {
        "Clear": ["Sunscreen SPF 50+", "Sunglasses", "Light breathable clothing"],
        "Clouds": ["Light layers", "Umbrella", "Comfortable walking shoes"],
        "Rain": ["Waterproof jacket", "Umbrella", "Waterproof shoes"],
        "Snow": ["Heavy winter coat", "Thermal layers", "Waterproof boots", "Gloves & hat"],
        "Thunderstorm": ["Waterproof gear", "Avoid open areas during storms"],
        "Drizzle": ["Light rain jacket", "Umbrella"],
    }
    return tips_map.get(weather_main, ["Check local weather forecasts before packing"])


def _get_fallback_weather(destination: str) -> Dict[str, Any]:
    return {
        "destination": destination,
        "note": "Live weather data unavailable (API key not configured). Please check weather.com or AccuWeather.",
        "best_time_to_visit": _get_best_time(destination),
        "packing_tips": ["Check local weather forecasts", "Pack layers for versatility", "Bring comfortable walking shoes"],
        "travel_advisory": "Check your government's official travel advisory before departure.",
        "source": "Fallback",
    }
