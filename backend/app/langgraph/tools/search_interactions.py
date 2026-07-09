import json
import re
import time
from typing import Any, Dict, Optional
from langchain_groq import ChatGroq
from langchain_core.tools import tool
from app.config.settings import settings
from app.langgraph.prompts.system_prompts import SEARCH_QUERY_PROMPT
from app.database.connection import SessionLocal
from app.models.interaction import Interaction
from app.models.hcp import HCP
from sqlalchemy import desc

llm = ChatGroq(api_key=settings.GROQ_API_KEY, model="llama-3.1-8b-instant")


@tool
def search_interactions_tool(query_text: str, user_id: Optional[int] = None) -> Dict[str, Any]:
    """Search CRM interactions by doctor name, product name, speciality, or keyword."""
    # Extract search parameters from user's message
    try:
        response = llm.invoke(f"{SEARCH_QUERY_PROMPT}\n\nMessage: {query_text}")
        cleaned = response.content.strip()
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
        params = json.loads(cleaned.strip())
    except Exception:
        params = {"keyword": query_text, "limit": 5}

    doctor_name = params.get("doctor_name")
    product_name = params.get("product_name")
    speciality = params.get("speciality")
    keyword = params.get("keyword")
    limit = int(params.get("limit") or 5)

    db = SessionLocal()
    try:
        query = (
            db.query(Interaction, HCP.doctor_name.label("hcp_name"), HCP.hospital, HCP.speciality)
            .join(HCP, Interaction.hcp_id == HCP.id, isouter=True)
            .filter(Interaction.created_by == user_id)
        )

        if doctor_name:
            query = query.filter(HCP.doctor_name.ilike(f"%{doctor_name}%"))
        if product_name:
            query = query.filter(Interaction.products.ilike(f"%{product_name}%"))
        if speciality:
            query = query.filter(HCP.speciality.ilike(f"%{speciality}%"))
        if keyword and not any([doctor_name, product_name, speciality]):
            query = query.filter(
                HCP.doctor_name.ilike(f"%{keyword}%") |
                Interaction.products.ilike(f"%{keyword}%") |
                Interaction.summary.ilike(f"%{keyword}%") |
                Interaction.discussion.ilike(f"%{keyword}%")
            )

        rows = query.order_by(desc(Interaction.created_at)).limit(limit).all()

        if not rows:
            search_term = doctor_name or product_name or speciality or keyword or query_text
            return {
                "found": False,
                "count": 0,
                "results": [],
                "message": f"No interactions found matching '{search_term}'."
            }

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
                "sentiment": interaction.sentiment or "Not recorded",
            })

        return {"found": True, "count": len(results), "results": results}

    finally:
        db.close()
