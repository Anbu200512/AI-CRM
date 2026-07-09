import json
import re
import time
from typing import Any, Dict, Optional
from langchain_groq import ChatGroq
from langchain_core.tools import tool
from app.config.settings import settings
from app.langgraph.prompts.system_prompts import FOLLOWUP_PROMPT
from app.database.connection import SessionLocal
from app.models.ai_log import AILog
from app.models.interaction import Interaction
from app.models.hcp import HCP
from sqlalchemy import desc

llm = ChatGroq(api_key=settings.GROQ_API_KEY, model="llama-3.1-8b-instant")


def _find_latest_interaction(db, user_id: int, doctor_name: Optional[str] = None):
    query = (
        db.query(Interaction, HCP.doctor_name.label("hcp_name"), HCP.hospital, HCP.speciality)
        .join(HCP, Interaction.hcp_id == HCP.id, isouter=True)
        .filter(Interaction.created_by == user_id)
    )
    if doctor_name and doctor_name.lower() != "unknown":
        query = query.filter(HCP.doctor_name.ilike(f"%{doctor_name}%"))
    return query.order_by(desc(Interaction.created_at)).first()


@tool
def followup_tool(interaction_summary: str, user_id: Optional[int] = None, doctor_name: Optional[str] = None) -> Dict[str, Any]:
    """Recommend follow-up actions based on the latest CRM interaction record."""
    start = time.time()

    interaction_data = interaction_summary  # fallback
    result_doctor_name = doctor_name or "Unknown"
    result_hospital = ""

    if user_id:
        db = SessionLocal()
        try:
            row = _find_latest_interaction(db, user_id, doctor_name)
            if row:
                interaction = row[0]
                hcp_name = row[1] or "Unknown Doctor"
                hospital = row[2] or ""
                interaction_date = str(interaction.interaction_date) if interaction.interaction_date else ""
                interaction_data = (
                    f"Doctor: {hcp_name}\n"
                    f"Hospital: {hospital}\n"
                    f"Date: {interaction_date}\n"
                    f"Type: {interaction.interaction_type or ''}\n"
                    f"Products Discussed: {interaction.products or ''}\n"
                    f"Interest Level: {interaction.interest_level or ''}\n"
                    f"Sentiment: {interaction.sentiment or ''}\n"
                    f"Follow-up Date: {str(interaction.follow_up_date) if interaction.follow_up_date else 'Not set'}\n"
                    f"Discussion: {interaction.discussion or ''}\n"
                    f"Summary: {interaction.summary or ''}"
                )
                result_doctor_name = hcp_name
                result_hospital = hospital
            else:
                db.close()
                name_hint = f" for {doctor_name}" if doctor_name and doctor_name.lower() != "unknown" else ""
                return {
                    "next_follow_up": "N/A",
                    "priority": "N/A",
                    "talking_points": [],
                    "suggested_products": [],
                    "clinical_evidence": [],
                    "next_visit_agenda": [],
                    "reasoning": f"No previous interaction found{name_hint}. Please log an interaction first.",
                    "found_in_db": False,
                    "doctor_name": doctor_name or "Unknown",
                    "hospital": "",
                }
        finally:
            db.close()

    response = llm.invoke(f"{FOLLOWUP_PROMPT}\n\nInteraction Data:\n{interaction_data}")
    elapsed = time.time() - start

    result = {}
    try:
        cleaned = response.content.strip()
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
        result = json.loads(cleaned.strip())
    except Exception:
        result = {
            "next_follow_up": "1 week",
            "priority": "Medium",
            "talking_points": [],
            "suggested_products": [],
            "clinical_evidence": [],
            "next_visit_agenda": [],
            "reasoning": response.content,
        }
    result["found_in_db"] = True
    result["doctor_name"] = result_doctor_name
    result["hospital"] = result_hospital

    db2 = SessionLocal()
    try:
        log = AILog(prompt=interaction_data[:500], response=json.dumps(result), tool="followup", execution_time=elapsed)
        db2.add(log)
        db2.commit()
    finally:
        db2.close()

    return result
