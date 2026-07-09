import re
import time
from typing import Any, Dict, Optional
from langchain_groq import ChatGroq
from langchain_core.tools import tool
from app.config.settings import settings
from app.langgraph.prompts.system_prompts import SUMMARIZER_PROMPT
from app.database.connection import SessionLocal
from app.models.ai_log import AILog
from app.models.interaction import Interaction
from app.models.hcp import HCP
from sqlalchemy import desc

llm = ChatGroq(api_key=settings.GROQ_API_KEY, model="llama-3.1-8b-instant")


def _find_latest_interaction(db, user_id: int, doctor_name: Optional[str] = None):
    """Find the most recent interaction for a user, optionally filtering by doctor name."""
    query = (
        db.query(Interaction, HCP.doctor_name.label("hcp_name"), HCP.hospital, HCP.speciality)
        .join(HCP, Interaction.hcp_id == HCP.id, isouter=True)
        .filter(Interaction.created_by == user_id)
    )
    if doctor_name and doctor_name.lower() != "unknown":
        query = query.filter(HCP.doctor_name.ilike(f"%{doctor_name}%"))
    row = query.order_by(desc(Interaction.created_at)).first()
    return row


@tool
def summarize_tool(text: str, user_id: Optional[int] = None, doctor_name: Optional[str] = None) -> Dict[str, Any]:
    """Summarize a past HCP interaction by retrieving it from the CRM database."""
    start = time.time()

    if user_id:
        db = SessionLocal()
        try:
            row = _find_latest_interaction(db, user_id, doctor_name)
            if row:
                interaction = row[0]
                hcp_name = row[1] or "Unknown Doctor"
                hospital = row[2] or "Unknown Hospital"
                speciality = row[3] or ""
                interaction_date = str(interaction.interaction_date) if interaction.interaction_date else "Unknown Date"
                interaction_data = (
                    f"Doctor: {hcp_name}\n"
                    f"Hospital: {hospital}\n"
                    f"Speciality: {speciality}\n"
                    f"Date: {interaction_date}\n"
                    f"Type: {interaction.interaction_type or 'Not specified'}\n"
                    f"Products Discussed: {interaction.products or 'None'}\n"
                    f"Interest Level: {interaction.interest_level or 'Not recorded'}\n"
                    f"Sentiment: {interaction.sentiment or 'Not recorded'}\n"
                    f"Discussion: {interaction.discussion or 'No notes'}\n"
                    f"Existing Summary: {interaction.summary or 'None'}"
                )
                response = llm.invoke(f"{SUMMARIZER_PROMPT}\n\n{interaction_data}")
                elapsed = time.time() - start
                log = AILog(prompt=f"Summarize: {hcp_name}", response=response.content, tool="summarize", execution_time=elapsed)
                db.add(log)
                db.commit()
                return {
                    "summary": response.content,
                    "doctor_name": hcp_name,
                    "hospital": hospital,
                    "interaction_date": interaction_date,
                    "found_in_db": True,
                }
            else:
                db.close()
                name_hint = f" with {doctor_name}" if doctor_name and doctor_name.lower() != "unknown" else ""
                return {"summary": f"No previous interaction found{name_hint}. Please log an interaction first.", "found_in_db": False}
        finally:
            db.close()

    # Fallback: summarize the raw text provided (no user_id)
    response = llm.invoke(f"{SUMMARIZER_PROMPT}\n\n{text}")
    elapsed = time.time() - start
    db2 = SessionLocal()
    try:
        log = AILog(prompt=text[:500], response=response.content, tool="summarize", execution_time=elapsed)
        db2.add(log)
        db2.commit()
    finally:
        db2.close()
    return {"summary": response.content, "found_in_db": False}
