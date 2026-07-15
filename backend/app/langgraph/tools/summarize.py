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
    SUMMARIZE_FILTER_PROMPT,
    SUMMARIZER_PROMPT,
    SUMMARIZER_MULTI_PROMPT,
    SUMMARIZER_EXECUTIVE_PROMPT,
    SUMMARIZER_TAKEAWAYS_PROMPT,
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

    prompt = SUMMARIZE_FILTER_PROMPT.format(
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
        logger.info("Summarize filters extracted: %s", params)
        return params
    except Exception as e:
        logger.warning("Filter extraction failed, defaulting to single summary: %s", str(e))
        return {"summary_type": "single"}


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


def _generate_summary(interactions: List[Dict[str, Any]], summary_type: str, filters: Dict) -> str:
    """Generate summary based on type."""
    if summary_type == "executive":
        text = _format_interactions_text(interactions)
        date_range = f"{filters.get('date_from', 'N/A')} to {filters.get('date_to', 'N/A')}"
        response = llm.invoke(
            f"{SUMMARIZER_EXECUTIVE_PROMPT}\n\nTotal Interactions: {len(interactions)}\nDate Range: {date_range}\n\n{text}"
        )
    elif summary_type == "takeaways":
        text = _format_interactions_text(interactions)
        response = llm.invoke(f"{SUMMARIZER_TAKEAWAYS_PROMPT}\n\n{text}")
    elif summary_type == "multiple" or len(interactions) > 1:
        text = _format_interactions_text(interactions)
        doctors = set(i["doctor_name"] for i in interactions if i["doctor_name"] != "Unknown")
        hospitals = set(i["hospital"] for i in interactions if i["hospital"] != "Unknown")
        products = set()
        for i in interactions:
            if i["products"] and i["products"] != "None":
                products.update(p.strip() for p in i["products"].split(","))
        stats = (
            f"Total Interactions: {len(interactions)}\n"
            f"Unique Doctors: {len(doctors)}\n"
            f"Unique Hospitals: {len(hospitals)}\n"
            f"Products Mentioned: {', '.join(products) if products else 'None'}"
        )
        response = llm.invoke(f"{SUMMARIZER_MULTI_PROMPT}\n\n{stats}\n\n{text}")
    else:
        text = _format_interaction_text(interactions[0])
        response = llm.invoke(f"{SUMMARIZER_PROMPT}\n\n{text}")

    return response.content


def _log_ai(db, prompt: str, response: str, start_time: float, tool_name: str = "summarize"):
    """Log AI interaction to database."""
    try:
        elapsed = time.time() - start_time
        log = AILog(
            prompt=prompt[:500],
            response=response[:2000],
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
def summarize_tool(query_text: str, user_id: Optional[int] = None) -> Dict[str, Any]:
    """Summarize HCP interactions from the CRM database. Supports single, multiple, executive, and key takeaways summaries."""
    start = time.time()
    logger.info("Summarize tool called: query_text=%.100s, user_id=%s", query_text, user_id)

    if not user_id:
        return {"summary": "Please log in to summarize interactions.", "found_in_db": False}

    db = SessionLocal()
    try:
        filters = _extract_filters(query_text)
        summary_type = filters.pop("summary_type", "single")
        logger.info("Detected filters: %s, summary_type: %s", filters, summary_type)

        query = _build_query(db, user_id, filters)
        rows = query.order_by(desc(Interaction.interaction_date)).all()
        logger.info("Query returned %d interactions", len(rows))

        if not rows:
            return {"summary": "No interactions were found matching your request.", "found_in_db": False}

        interactions = _format_interactions(rows)

        summary = _generate_summary(interactions, summary_type, filters)
        logger.info("Summary generated successfully: type=%s, length=%d", summary_type, len(summary))

        _log_ai(db, f"Summarize ({summary_type}): {query_text[:200]}", summary, start)

        return {
            "summary": summary,
            "found_in_db": True,
            "summary_type": summary_type,
            "count": len(rows),
        }
    except Exception as e:
        logger.error("Summarize tool failed: %s", str(e), exc_info=True)
        return {"summary": "An error occurred while generating the summary. Please try again.", "found_in_db": False}
    finally:
        db.close()
