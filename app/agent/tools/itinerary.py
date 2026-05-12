"""Itinerary builder — LLM-powered day-by-day plan generation."""
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from app.agent.llm import get_llm
from langchain_core.prompts import ChatPromptTemplate
from loguru import logger
import json


async def build_itinerary(
    destination: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    travelers: int = 1,
    budget_range: str = "mid-range",
    rag_context: str = "",
) -> Dict[str, Any]:
    """Generate a detailed day-by-day itinerary using the LLM."""

    # Calculate duration
    if start_date and end_date:
        try:
            s = datetime.strptime(start_date, "%Y-%m-%d")
            e = datetime.strptime(end_date, "%Y-%m-%d")
            days = max(1, (e - s).days)
        except Exception:
            days = 5
    else:
        days = 5

    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are an expert travel itinerary planner. Create a detailed, realistic, 
and engaging day-by-day travel itinerary. 

Return ONLY valid JSON in this exact format:
{{
  "destination": "city, country",
  "duration_days": <number>,
  "theme": "short theme description",
  "highlights": ["top highlight 1", "top highlight 2", "top highlight 3"],
  "days": [
    {{
      "day": 1,
      "date": "YYYY-MM-DD or Day 1",
      "title": "Arrival & First Impressions",
      "morning": {{
        "activity": "Activity name",
        "description": "Brief description",
        "duration": "2 hours",
        "cost_usd": 0,
        "tips": "Helpful tip"
      }},
      "afternoon": {{
        "activity": "Activity name",
        "description": "Brief description",
        "duration": "3 hours",
        "cost_usd": 25,
        "tips": "Helpful tip"
      }},
      "evening": {{
        "activity": "Activity name",
        "description": "Brief description",
        "duration": "2 hours",
        "cost_usd": 40,
        "tips": "Book in advance"
      }},
      "accommodation": "Hotel/area recommendation",
      "meals": {{
        "breakfast": "Recommendation",
        "lunch": "Recommendation",
        "dinner": "Recommendation"
      }},
      "daily_budget_usd": 150
    }}
  ],
  "practical_tips": ["tip 1", "tip 2"],
  "local_customs": ["custom 1", "custom 2"],
  "emergency_contacts": {{
    "tourist_police": "local number",
    "embassy_note": "Contact your country's embassy"
  }}
}}
"""),
        ("system", f"Additional travel context:\n{rag_context}" if rag_context else ""),
        ("human", f"""Create a {days}-day itinerary for {destination}.
Travel dates: {start_date or 'flexible'} to {end_date or 'flexible'}
Number of travelers: {travelers}
Budget preference: {budget_range}
Make it practical, exciting, and include local gems beyond typical tourist spots."""),
    ])

    try:
        llm = get_llm()
        chain = prompt | llm
        result = await chain.ainvoke({})
        raw = result.content.strip()

        # Extract JSON
        if "```json" in raw:
            raw = raw.split("```json")[1].split("```")[0].strip()
        elif "```" in raw:
            raw = raw.split("```")[1].split("```")[0].strip()

        parsed = json.loads(raw)
        return parsed

    except Exception as e:
        logger.error(f"Itinerary generation error: {e}")
        return {
            "destination": destination,
            "duration_days": days,
            "error": "Itinerary generation encountered an issue",
            "note": "Please try again or provide more specific details about your trip.",
        }
