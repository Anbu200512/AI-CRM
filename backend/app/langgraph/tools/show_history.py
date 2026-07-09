import re
import json
import time
from typing import Any, Dict, Optional
from langchain_groq import ChatGroq
from langchain_core.tools import tool
from app.config.settings import settings
from app.database.connection import SessionLocal
from app.models.interaction import Interaction
from app.models.hcp import HCP
from sqlalchemy import desc

llm = ChatGroq(api_key=settings.GROQ_API_KEY, model="llama-3.1-8b-instant")

LIMIT_EXTRACT_PROMPT = """Extract the number of interactions the user wants to see.
Return ONLY a JSON: {"limit": <number>, "doctor_name": null}
If user says "last 5" → limit: 5. If user says "last 10" → limit: 10. Default is 5.
Also extract doctor name if mentioned (for filtering).
Message: {message}"""


@tool
def show_history_tool(query_text: str, user_id: Optional[int] = None) -> Dict[str, Any]:
    """Show recent HCP interaction history from the CRM database."""
    # Extract limit and optional doctor filter
    try:
        response = llm.invoke(LIMIT_EXTRACT_PROMPT.format(message=query_text))
        cleaned = response.content.strip()
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
        params = json.loads(cleaned.strip())
    except Exception:
        params = {"limit": 5, "doctor_name": None}

    limit = int(params.get("limit") or 5)
    doctor_name = params.get("doctor_name")

    db = SessionLocal()
    try:
        query = (
            db.query(Interaction, HCP.doctor_name.label("hcp_name"), HCP.hospital, HCP.speciality)
            .join(HCP, Interaction.hcp_id == HCP.id, isouter=True)
            .filter(Interaction.created_by == user_id)
        )
        if doctor_name and doctor_name.lower() != "unknown":
            query = query.filter(HCP.doctor_name.ilike(f"%{doctor_name}%"))

        rows = query.order_by(desc(Interaction.created_at)).limit(limit).all()

        if not rows:
            return {"found": False, "count": 0, "results": [], "message": "No interactions found in your CRM."}

        results = []
        for row in rows:
            interaction = row[0]
            results.append({
                "id": interaction.id,
                "doctor_name": row[1] or "Unknown",
                "hospital": row[2] or "Unknown",
                "speciality": row[3] or "",
                "interaction_date": str(interaction.interaction_date) if interaction.interaction_date else "Unknown",
                "interaction_type": interaction.interaction_type or "Not specified",
                "products": interaction.products or "None",
                "interest_level": interaction.interest_level or "Not recorded",
                "follow_up_date": str(interaction.follow_up_date) if interaction.follow_up_date else None,
                "sentiment": interaction.sentiment or "Not recorded",
            })

        return {"found": True, "count": len(results), "results": results}
    finally:
        db.close()
