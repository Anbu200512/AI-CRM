import re
import time
from typing import Any, Dict, Optional
from langchain_groq import ChatGroq
from langchain_core.tools import tool
from app.config.settings import settings
from app.database.connection import SessionLocal
from app.models.interaction import Interaction
from app.models.hcp import HCP
from app.models.ai_log import AILog
from app.utils.websocket import manager
from sqlalchemy import desc

llm = ChatGroq(api_key=settings.GROQ_API_KEY, model="llama-3.1-8b-instant")

DOCTOR_NAME_PROMPT = """Extract the doctor name from this message.
Return ONLY the doctor name as plain text, nothing else.
If no doctor name found, return "unknown".
Message: {message}"""


@tool
def delete_interaction_tool(query_text: str, user_id: Optional[int] = None, confirmed: bool = False) -> Dict[str, Any]:
    """Delete an HCP interaction. First call finds the record and asks for confirmation. Second call (confirmed=True) deletes it."""

    # Extract doctor name from user message
    try:
        response = llm.invoke(DOCTOR_NAME_PROMPT.format(message=query_text))
        doctor_name = response.content.strip().lower()
    except Exception:
        doctor_name = "unknown"

    db = SessionLocal()
    try:
        query = (
            db.query(Interaction, HCP.doctor_name.label("hcp_name"), HCP.hospital)
            .join(HCP, Interaction.hcp_id == HCP.id, isouter=True)
            .filter(Interaction.created_by == user_id)
        )
        if doctor_name and doctor_name != "unknown":
            query = query.filter(HCP.doctor_name.ilike(f"%{doctor_name}%"))

        row = query.order_by(desc(Interaction.created_at)).first()

        if not row:
            return {
                "found": False,
                "needs_confirmation": False,
                "message": f"No interaction found for '{doctor_name}'. Please check the doctor name.",
            }

        interaction = row[0]
        hcp_name = row[1] or "Unknown Doctor"
        hospital = row[2] or ""
        interaction_date = str(interaction.interaction_date) if interaction.interaction_date else "Unknown Date"

        if not confirmed:
            return {
                "found": True,
                "needs_confirmation": True,
                "interaction_id": interaction.id,
                "doctor_name": hcp_name,
                "hospital": hospital,
                "interaction_date": interaction_date,
                "interaction_type": interaction.interaction_type or "Not specified",
                "message": (
                    f"Are you sure you want to delete this interaction?\n\n"
                    f"📋 Interaction Details\n"
                    f"Doctor: {hcp_name}\n"
                    f"Hospital: {hospital}\n"
                    f"Date: {interaction_date}\n"
                    f"Type: {interaction.interaction_type or 'Not specified'}\n\n"
                    f"Reply 'yes' or 'confirm' to delete, or 'cancel' to abort."
                ),
            }

        # Confirmed — perform deletion
        interaction_id = interaction.id
        db.delete(interaction)
        db.commit()

        start = time.time()
        log = AILog(prompt=query_text, response=f"Deleted interaction {interaction_id}", tool="delete_interaction", execution_time=time.time() - start)
        db.add(log)
        db.commit()

        if user_id:
            manager.broadcast_sync(user_id, {"type": "DASHBOARD_UPDATED"})

        return {
            "found": True,
            "needs_confirmation": False,
            "deleted": True,
            "interaction_id": interaction_id,
            "doctor_name": hcp_name,
            "message": f"✅ Interaction with {hcp_name} from {interaction_date} has been deleted successfully.",
        }
    finally:
        db.close()
