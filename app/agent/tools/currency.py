"""Currency converter tool using ExchangeRate-API."""
import httpx
from typing import Optional, Dict, Any
from app.core.config import settings
from loguru import logger


# Approximate offline rates vs USD (updated periodically)
OFFLINE_RATES = {
    "USD": 1.0, "EUR": 0.92, "GBP": 0.79, "JPY": 153.5, "AUD": 1.53,
    "CAD": 1.36, "CHF": 0.90, "INR": 83.5, "THB": 35.1, "SGD": 1.34,
    "MYR": 4.7, "IDR": 15800, "PHP": 57.5, "VND": 24800, "KRW": 1350,
    "CNY": 7.24, "AED": 3.67, "SAR": 3.75, "QAR": 3.64, "TRY": 32.5,
    "LKR": 302.5, "NPR": 133.6, "BDT": 110.0, "PKR": 278.5, "NZD": 1.63,
    "ZAR": 18.6, "BRL": 4.96, "MXN": 17.2, "SEK": 10.4, "NOK": 10.6,
    "DKK": 6.88, "PLN": 3.96, "CZK": 22.9, "HUF": 356.0,
}


async def convert_currency(
    amount: float,
    from_currency: str,
    to_currency: str,
) -> Dict[str, Any]:
    """Convert currency amount. Uses live API if key available, else offline rates."""
    from_currency = from_currency.upper()
    to_currency = to_currency.upper()

    if settings.EXCHANGE_RATE_API_KEY:
        try:
            url = f"https://v6.exchangerate-api.com/v6/{settings.EXCHANGE_RATE_API_KEY}/pair/{from_currency}/{to_currency}/{amount}"
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url)
                data = resp.json()

                if data.get("result") == "success":
                    return {
                        "from": from_currency,
                        "to": to_currency,
                        "amount": amount,
                        "converted": round(data["conversion_result"], 2),
                        "rate": data["conversion_rate"],
                        "source": "ExchangeRate-API (Live)",
                    }
        except Exception as e:
            logger.warning(f"Live currency API error: {e}")

    # Fallback to offline rates
    if from_currency not in OFFLINE_RATES or to_currency not in OFFLINE_RATES:
        return {
            "error": f"Currency {from_currency} or {to_currency} not found",
            "supported": list(OFFLINE_RATES.keys()),
        }

    rate_from_usd_from = OFFLINE_RATES[from_currency]
    rate_from_usd_to = OFFLINE_RATES[to_currency]
    rate = rate_from_usd_to / rate_from_usd_from
    converted = round(amount * rate, 2)

    return {
        "from": from_currency,
        "to": to_currency,
        "amount": amount,
        "converted": converted,
        "rate": round(rate, 4),
        "source": "Offline rates (approximate — configure EXCHANGE_RATE_API_KEY for live rates)",
    }


def get_popular_currencies_for_destination(destination: str) -> list:
    """Return common currencies for a destination."""
    dest = destination.lower()
    currency_map = {
        "japan": ["JPY", "USD"], "europe": ["EUR", "USD"], "paris": ["EUR"],
        "london": ["GBP"], "uk": ["GBP"], "thailand": ["THB"], "bali": ["IDR"],
        "indonesia": ["IDR"], "india": ["INR"], "dubai": ["AED"], "uae": ["AED"],
        "singapore": ["SGD"], "australia": ["AUD"], "new zealand": ["NZD"],
        "canada": ["CAD"], "mexico": ["MXN"], "turkey": ["TRY"],
        "south africa": ["ZAR"], "brazil": ["BRL"], "maldives": ["USD", "MVR"],
    }
    for key, currencies in currency_map.items():
        if key in dest:
            return currencies
    return ["USD"]
