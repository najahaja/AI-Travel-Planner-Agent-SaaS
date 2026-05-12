"""Budget estimation tool — generates realistic cost breakdowns."""
from typing import Optional, Dict, Any
from loguru import logger

# Cost database (USD per person per day) by budget tier and region
COST_PROFILES = {
    "budget": {
        "Southeast Asia": {"hotel": 20, "food": 15, "transport": 10, "activities": 15},
        "Europe": {"hotel": 50, "food": 30, "transport": 20, "activities": 25},
        "North America": {"hotel": 60, "food": 35, "transport": 25, "activities": 30},
        "Middle East": {"hotel": 45, "food": 25, "transport": 15, "activities": 20},
        "South Asia": {"hotel": 18, "food": 12, "transport": 8, "activities": 10},
        "Oceania": {"hotel": 70, "food": 40, "transport": 30, "activities": 35},
        "Default": {"hotel": 40, "food": 25, "transport": 15, "activities": 20},
    },
    "mid-range": {
        "Southeast Asia": {"hotel": 60, "food": 35, "transport": 20, "activities": 35},
        "Europe": {"hotel": 120, "food": 60, "transport": 40, "activities": 60},
        "North America": {"hotel": 150, "food": 70, "transport": 50, "activities": 70},
        "Middle East": {"hotel": 120, "food": 60, "transport": 35, "activities": 55},
        "South Asia": {"hotel": 50, "food": 25, "transport": 15, "activities": 25},
        "Oceania": {"hotel": 160, "food": 80, "transport": 60, "activities": 70},
        "Default": {"hotel": 100, "food": 50, "transport": 30, "activities": 50},
    },
    "luxury": {
        "Southeast Asia": {"hotel": 250, "food": 100, "transport": 80, "activities": 120},
        "Europe": {"hotel": 400, "food": 150, "transport": 100, "activities": 150},
        "North America": {"hotel": 500, "food": 180, "transport": 120, "activities": 180},
        "Middle East": {"hotel": 450, "food": 150, "transport": 100, "activities": 150},
        "South Asia": {"hotel": 200, "food": 80, "transport": 60, "activities": 100},
        "Oceania": {"hotel": 450, "food": 160, "transport": 110, "activities": 150},
        "Default": {"hotel": 350, "food": 130, "transport": 90, "activities": 130},
    },
}

REGION_MAP = {
    "thailand": "Southeast Asia", "bali": "Southeast Asia", "vietnam": "Southeast Asia",
    "indonesia": "Southeast Asia", "malaysia": "Southeast Asia", "singapore": "Southeast Asia",
    "cambodia": "Southeast Asia", "philippines": "Southeast Asia",
    "france": "Europe", "italy": "Europe", "spain": "Europe", "germany": "Europe",
    "uk": "Europe", "united kingdom": "Europe", "portugal": "Europe", "greece": "Europe",
    "paris": "Europe", "rome": "Europe", "london": "Europe", "barcelona": "Europe",
    "amsterdam": "Europe", "prague": "Europe",
    "usa": "North America", "united states": "North America", "canada": "North America",
    "new york": "North America", "los angeles": "North America", "chicago": "North America",
    "mexico": "North America",
    "dubai": "Middle East", "uae": "Middle East", "qatar": "Middle East",
    "saudi arabia": "Middle East", "jordan": "Middle East", "turkey": "Middle East",
    "india": "South Asia", "sri lanka": "South Asia", "nepal": "South Asia",
    "maldives": "South Asia", "pakistan": "South Asia",
    "australia": "Oceania", "new zealand": "Oceania", "sydney": "Oceania", "melbourne": "Oceania",
}

FLIGHT_COST_ESTIMATES = {
    "budget": {"short": 150, "medium": 400, "long": 600},
    "mid-range": {"short": 300, "medium": 700, "long": 1200},
    "luxury": {"short": 800, "medium": 2000, "long": 5000},
}


def _get_region(destination: str) -> str:
    dest_lower = destination.lower()
    for key, region in REGION_MAP.items():
        if key in dest_lower:
            return region
    return "Default"


def _calculate_days(start_date: Optional[str], end_date: Optional[str]) -> int:
    if start_date and end_date:
        from datetime import datetime
        try:
            s = datetime.strptime(start_date, "%Y-%m-%d")
            e = datetime.strptime(end_date, "%Y-%m-%d")
            days = (e - s).days
            return max(1, days)
        except Exception:
            pass
    return 5  # Default to 5 days


async def estimate_budget(
    destination: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    travelers: int = 1,
    budget_range: str = "mid-range",
) -> Dict[str, Any]:
    """Calculate a detailed budget breakdown for the trip."""
    try:
        tier = budget_range if budget_range in COST_PROFILES else "mid-range"
        region = _get_region(destination)
        days = _calculate_days(start_date, end_date)
        costs = COST_PROFILES[tier].get(region, COST_PROFILES[tier]["Default"])

        # Per person totals
        hotel_total = costs["hotel"] * days
        food_total = costs["food"] * days
        transport_local = costs["transport"] * days
        activities_total = costs["activities"] * days

        # Flight estimate (per person)
        flight_tier = FLIGHT_COST_ESTIMATES[tier]
        if region in ["Southeast Asia", "South Asia"]:
            flight_pp = flight_tier["long"]
        elif region in ["Europe", "North America", "Middle East"]:
            flight_pp = flight_tier["medium"]
        else:
            flight_pp = flight_tier["medium"]

        misc_per_person = round((hotel_total + food_total + activities_total) * 0.10)

        per_person_subtotal = hotel_total + food_total + transport_local + activities_total + misc_per_person
        total_all_travelers = (per_person_subtotal + flight_pp) * travelers

        return {
            "destination": destination,
            "duration_days": days,
            "travelers": travelers,
            "budget_tier": tier,
            "region": region,
            "per_person": {
                "flight_usd": flight_pp,
                "accommodation_usd": hotel_total,
                "food_usd": food_total,
                "local_transport_usd": transport_local,
                "activities_usd": activities_total,
                "miscellaneous_usd": misc_per_person,
                "subtotal_usd": per_person_subtotal + flight_pp,
            },
            "total_usd": total_all_travelers,
            "currency_note": "Estimates in USD. Actual costs vary based on season, booking timing, and specific choices.",
            "money_saving_tips": _get_money_tips(tier),
        }
    except Exception as e:
        logger.error(f"Budget estimation error: {e}")
        return {"error": "Budget estimation failed", "destination": destination}


def _get_money_tips(tier: str) -> list:
    tips = {
        "budget": [
            "Book flights 6-8 weeks in advance for best prices",
            "Use local street food and markets",
            "Choose hostels or guesthouses",
            "Use public transportation",
            "Visit free attractions and parks",
        ],
        "mid-range": [
            "Book accommodations directly for best rates",
            "Mix restaurant dining with local eateries",
            "Consider city tourism cards for transport + attractions",
            "Travel shoulder season (Apr-May, Sep-Oct for Europe)",
        ],
        "luxury": [
            "Book business class with points/miles for max value",
            "Consider luxury hotel loyalty programs",
            "Private guides enhance experience significantly",
            "Splurge on one signature experience per destination",
        ],
    }
    return tips.get(tier, tips["mid-range"])
