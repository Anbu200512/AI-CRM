import json
import logging
import re
import time
from datetime import date, timedelta
from typing import Any, Dict, List, Optional
from langchain_groq import ChatGroq
from langchain_core.tools import tool
from app.config.settings import settings
from app.langgraph.prompts.system_prompts import (
    FOLLOWUP_FILTER_PROMPT,
    FOLLOWUP_PROMPT,
    FOLLOWUP_MULTI_PROMPT,
)
from app.database.connection import SessionLocal
from app.models.ai_log import AILog
from app.models.interaction import Interaction
from app.models.hcp import HCP
from sqlalchemy import desc

logger = logging.getLogger(__name__)

llm = ChatGroq(api_key=settings.GROQ_API_KEY, model="llama-3.1-8b-instant")


def _extract_filters(query_text: str) -> Dict[str, Any]:
    """Extract search filters from user message using LLM."""
    today = date.today()
    yesterday = today - timedelta(days=1)
    week_start = today - timedelta(days=today.weekday())
    month_start = today.replace(day=1)

    prompt = FOLLOWUP_FILTER_PROMPT.format(
        today=today.isoformat(),
        yesterday=yesterday.isoformat(),
        week_start=week_start.isoformat(),
        month_start=month_start.isoformat(),
    )

    try:
        response = llm.invoke(f"{prompt}\n\nMessage: {query_text}")
        cleaned = response.content.strip()
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
        params = json.loads(cleaned.strip())
        logger.info("Followup filters extracted: %s", params)
        return params
    except Exception as e:
        logger.warning("Filter extraction failed, defaulting to single recommendation: %s", str(e))
        return {"recommendation_type": "single"}


def _build_query(db, user_id: int, filters: Dict):
    """Build SQLAlchemy query with filters."""
    query = (
        db.query(Interaction, HCP.doctor_name.label("hcp_name"), HCP.hospital, HCP.speciality)
        .join(HCP, Interaction.hcp_id == HCP.id, isouter=True)
        .filter(Interaction.created_by == user_id)
    )

    if filters.get("doctor_name"):
        query = query.filter(HCP.doctor_name.ilike(f"%{filters['doctor_name']}%"))
    if filters.get("hospital"):
        query = query.filter(HCP.hospital.ilike(f"%{filters['hospital']}%"))
    if filters.get("speciality"):
        query = query.filter(HCP.speciality.ilike(f"%{filters['speciality']}%"))
    if filters.get("product_name"):
        query = query.filter(Interaction.products.ilike(f"%{filters['product_name']}%"))
    if filters.get("interaction_date"):
        query = query.filter(Interaction.interaction_date == filters["interaction_date"])
    if filters.get("date_from"):
        query = query.filter(Interaction.interaction_date >= filters["date_from"])
    if filters.get("date_to"):
        query = query.filter(Interaction.interaction_date <= filters["date_to"])
    if filters.get("interest_level"):
        query = query.filter(Interaction.interest_level.ilike(f"%{filters['interest_level']}%"))
    if filters.get("interaction_type"):
        query = query.filter(Interaction.interaction_type.ilike(f"%{filters['interaction_type']}%"))

    return query


def _format_interactions(rows) -> List[Dict[str, Any]]:
    """Format query results into structured data."""
    interactions = []
    for row in rows:
        interaction = row[0]
        interactions.append({
            "doctor_name": row[1] or "Unknown",
            "hospital": row[2] or "Unknown",
            "speciality": row[3] or "",
            "interaction_date": str(interaction.interaction_date) if interaction.interaction_date else "Unknown",
            "interaction_type": interaction.interaction_type or "Not specified",
            "products": interaction.products or "None",
            "competitors": interaction.competitors or "None",
            "interest_level": interaction.interest_level or "Not recorded",
            "sentiment": interaction.sentiment or "Not recorded",
            "duration": interaction.duration,
            "discussion": interaction.discussion or "No notes available",
            "summary": interaction.summary or "None",
            "follow_up_date": str(interaction.follow_up_date) if interaction.follow_up_date else "Not scheduled",
        })
    return interactions


def _format_interaction_text(interaction: Dict[str, Any]) -> str:
    """Format a single interaction dict into text for the LLM."""
    return "\n".join([f"{k}: {v}" for k, v in interaction.items()])


def _format_interactions_text(interactions: List[Dict[str, Any]]) -> str:
    """Format multiple interactions into text for the LLM."""
    parts = []
    for i, item in enumerate(interactions, 1):
        parts.append(f"Interaction {i}:\n" + "\n".join([f"{k}: {v}" for k, v in item.items()]))
    return "\n\n".join(parts)


def _generate_recommendation(interactions: List[Dict[str, Any]], recommendation_type: str) -> Dict[str, Any]:
    """Generate recommendation based on type. Returns parsed JSON dict."""
    if recommendation_type == "multiple" or len(interactions) > 1:
        text = _format_interactions_text(interactions)
        response = llm.invoke(f"{FOLLOWUP_MULTI_PROMPT}\n\n{text}")
    else:
        text = _format_interaction_text(interactions[0])
        response = llm.invoke(f"{FOLLOWUP_PROMPT}\n\n{text}")

    try:
        cleaned = response.content.strip()
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
        result = json.loads(cleaned.strip())
    except Exception:
        logger.warning("Failed to parse LLM response as JSON, using fallback")
        if recommendation_type == "multiple" or len(interactions) > 1:
            result = _fallback_multi_recommendation(interactions)
        else:
            result = _fallback_single_recommendation(interactions[0])

    return result


def _fallback_single_recommendation(interaction: Dict[str, Any]) -> Dict[str, Any]:
    """Fallback recommendation when LLM JSON parsing fails."""
    return {
        "doctor_name": interaction.get("doctor_name", "Unknown"),
        "hospital": interaction.get("hospital", "Unknown"),
        "priority": "Medium",
        "next_follow_up": interaction.get("follow_up_date", "In 1 week"),
        "reasoning": "Follow-up recommended based on interaction data.",
        "talking_points": ["Review previous discussion", "Discuss product updates", "Address any questions"],
        "suggested_products": [p.strip() for p in interaction.get("products", "").split(",") if p.strip() and p.strip() != "None"],
        "clinical_evidence": ["Present relevant clinical data"],
        "next_visit_agenda": [
            "Greet and review previous discussion",
            "Discuss requested materials or evidence",
            "Introduce product updates",
            "Address objections or concerns",
            "Collect feedback",
            "Schedule next meeting",
        ],
    }


def _fallback_multi_recommendation(interactions: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Fallback multi-recommendation when LLM JSON parsing fails."""
    high = []
    medium = []
    low = []
    for item in interactions:
        entry = {
            "doctor_name": item.get("doctor_name", "Unknown"),
            "hospital": item.get("hospital", "Unknown"),
            "priority": item.get("interest_level", "Medium"),
            "reasoning": f"Follow-up recommended for {item.get('doctor_name', 'Unknown')}.",
            "next_follow_up": item.get("follow_up_date", "In 1 week"),
        }
        level = (item.get("interest_level") or "").lower()
        if level == "high":
            high.append(entry)
        elif level == "low":
            low.append(entry)
        else:
            medium.append(entry)

    return {
        "summary": f"Follow-up recommendations generated for {len(interactions)} interactions.",
        "high_priority": high,
        "medium_priority": medium,
        "low_priority": low,
        "recommended_schedule": "Prioritize high priority doctors first, then medium, then low.",
        "upcoming_followups": [
            {"doctor_name": i.get("doctor_name"), "follow_up_date": i.get("follow_up_date"), "priority": i.get("interest_level", "Medium")}
            for i in interactions if i.get("follow_up_date") != "Not scheduled"
        ],
    }


def _log_ai(db, prompt: str, response: str, start_time: float, tool_name: str = "followup"):
    """Log AI interaction to database."""
    try:
        elapsed = time.time() - start_time
        log = AILog(
            prompt=prompt[:500],
            response=response[:2000] if isinstance(response, str) else json.dumps(response)[:2000],
            tool=tool_name,
            execution_time=elapsed,
        )
        db.add(log)
        db.commit()
        logger.info("AI log recorded: tool=%s, execution_time=%.2fs", tool_name, elapsed)
    except Exception as e:
        logger.warning("Failed to log AI interaction: %s", str(e))
        db.rollback()


@tool
def followup_tool(query_text: str, user_id: Optional[int] = None) -> Dict[str, Any]:
    """Recommend follow-up actions based on CRM interaction records. Supports single and multi-doctor recommendations."""
    start = time.time()
    logger.info("Followup tool called: query_text=%.100s, user_id=%s", query_text, user_id)

    if not user_id:
        return {
            "error": "Please log in to get follow-up recommendations.",
            "found_in_db": False,
            "doctor_name": "Unknown",
            "hospital": "",
        }

    db = SessionLocal()
    try:
        filters = _extract_filters(query_text)
        recommendation_type = filters.pop("recommendation_type", "single")
        logger.info("Detected filters: %s, recommendation_type: %s", filters, recommendation_type)

        query = _build_query(db, user_id, filters)
        rows = query.order_by(desc(Interaction.interaction_date)).all()
        logger.info("Query returned %d interactions", len(rows))

        if not rows:
            return {
                "error": "No interactions were found matching your request.",
                "found_in_db": False,
                "doctor_name": "Unknown",
                "hospital": "",
            }

        interactions = _format_interactions(rows)

        result = _generate_recommendation(interactions, recommendation_type)
        logger.info("Recommendation generated successfully: type=%s", recommendation_type)

        _log_ai(db, f"Followup ({recommendation_type}): {query_text[:200]}", result, start)

        result["found_in_db"] = True
        result["recommendation_type"] = recommendation_type
        result["count"] = len(rows)
        if "doctor_name" not in result and len(interactions) == 1:
            result["doctor_name"] = interactions[0].get("doctor_name", "Unknown")
            result["hospital"] = interactions[0].get("hospital", "Unknown")
        return result
    except Exception as e:
        logger.error("Followup tool failed: %s", str(e), exc_info=True)
        return {
            "error": "An error occurred while generating recommendations. Please try again.",
            "found_in_db": False,
            "doctor_name": "Unknown",
            "hospital": "",
        }
    finally:
        db.close()
