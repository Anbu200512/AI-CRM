import json
import time
from typing import Any, Dict, Optional
from langchain_groq import ChatGroq
from langchain_core.tools import tool
from app.config.settings import settings
from app.langgraph.prompts.system_prompts import DASHBOARD_QUERY_PROMPT
from app.database.connection import SessionLocal
from app.services.interaction_service import get_dashboard_data

llm = ChatGroq(api_key=settings.GROQ_API_KEY, model="llama-3.1-8b-instant")


@tool
def dashboard_assistant_tool(question: str, user_id: Optional[int] = None) -> Dict[str, Any]:
    """Answer natural language questions about CRM dashboard statistics."""
    if not user_id:
        return {"answer": "I need you to be logged in to access your dashboard statistics.", "stats": {}}

    db = SessionLocal()
    try:
        data = get_dashboard_data(db, user_id)
        stats = data.get("stats", {})

        # Build upcoming follow-ups summary
        upcoming = data.get("upcoming_followups", [])
        upcoming_summary = ""
        if upcoming:
            names = [f.get("doctor_name", "Unknown") for f in upcoming[:3]]
            upcoming_summary = f"Upcoming follow-ups: {', '.join(names)}" + (f" and {len(upcoming)-3} more" if len(upcoming) > 3 else "")

        stats_text = (
            f"Total HCPs in CRM: {stats.get('total_hcps', 0)}\n"
            f"Interactions logged today: {stats.get('interactions_today', 0)}\n"
            f"Pending follow-ups: {stats.get('pending_followups', 0)}\n"
            f"Meetings this week: {stats.get('weekly_meetings', 0)}\n"
        )
        if upcoming_summary:
            stats_text += f"{upcoming_summary}\n"

        response = llm.invoke(DASHBOARD_QUERY_PROMPT.format(stats=stats_text, question=question))
        return {
            "answer": response.content.strip(),
            "stats": stats,
        }
    finally:
        db.close()
