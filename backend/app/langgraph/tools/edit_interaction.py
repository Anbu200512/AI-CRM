import json
import re
import time
from datetime import date, datetime, timedelta
from typing import Any, Dict, Optional
from langchain_groq import ChatGroq
from langchain_core.tools import tool
from app.config.settings import settings
from app.database.connection import SessionLocal
from app.models.interaction import Interaction
from app.models.hcp import HCP
from app.models.ai_log import AILog
from app.utils.websocket import manager

WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]

llm = ChatGroq(api_key=settings.GROQ_API_KEY, model="llama-3.1-8b-instant")


def _parse_date(value: str) -> date:
    today = date.today()
    val = str(value).strip().lower()
    try:
        return datetime.strptime(val, "%Y-%m-%d").date()
    except ValueError:
        pass
    try:
        return datetime.strptime(val, "%d-%m-%Y").date()
    except ValueError:
        pass
    if val in ("today", "now"):
        return today
    if val == "tomorrow":
        return today + timedelta(days=1)
    if val in WEEKDAYS:
        target = WEEKDAYS.index(val)
        current = today.weekday()
        days_ahead = target - current
        if days_ahead <= 0:
            days_ahead += 7
        return today + timedelta(days=days_ahead)
    if "next" in val:
        for w in WEEKDAYS:
            if w in val:
                target = WEEKDAYS.index(w)
                current = today.weekday()
                days_ahead = target - current
                if days_ahead <= 0:
                    days_ahead += 7
                return today + timedelta(days=days_ahead + 7)
        return today + timedelta(days=7)
    match = re.search(r"(\d+)\s*(day|week|month)s?", val)
    if match:
        num = int(match.group(1))
        unit = match.group(2)
        if unit == "day":
            return today + timedelta(days=num)
        elif unit == "week":
            return today + timedelta(weeks=num)
        elif unit == "month":
            return date(today.year + (today.month + num - 1) // 12, (today.month + num - 1) % 12 + 1, today.day)
    return today


DOCTOR_NAME_PROMPT = """Extract the doctor name from this edit request.
Return ONLY the doctor name as plain text, nothing else.
If no doctor name is found, return "unknown".

Edit request: {edit_request}"""


@tool
def edit_interaction_tool(edit_request: str, interaction_id: int = 0, user_id: Optional[int] = None) -> Dict[str, Any]:
    """Edit an existing interaction based on natural language instructions."""
    start = time.time()

    extract_prompt = f"""Given this edit request: "{edit_request}"
Analyze what fields to update in the interaction.
Return ONLY a valid JSON object with fields to update. Do NOT include any other text, markdown, or code blocks.
Valid fields: summary, discussion, products, competitors, sentiment, interest_level, follow_up_date, duration

Example: {{"sentiment": "Positive", "interest_level": "High", "follow_up_date": "2026-07-16"}}"""
    response = llm.invoke(extract_prompt)
    updates = {}
    try:
        cleaned = response.content.strip()
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
        cleaned = cleaned.strip()
        updates = json.loads(cleaned)
    except:
        pass

    if not updates:
        return {"success": False, "error": "Could not parse update fields from your request"}

    db = SessionLocal()
    try:
        interaction = None
        if interaction_id and interaction_id > 0:
            query = db.query(Interaction).filter(Interaction.id == interaction_id)
            if user_id:
                query = query.filter(Interaction.created_by == user_id)
            interaction = query.first()

        if not interaction:
            doctor_name_response = llm.invoke(DOCTOR_NAME_PROMPT.format(edit_request=edit_request))
            doctor_name = doctor_name_response.content.strip().lower()
            if doctor_name and doctor_name != "unknown":
                hcp = db.query(HCP).filter(HCP.doctor_name.ilike(f"%{doctor_name}%")).first()
                if hcp:
                    query = db.query(Interaction).filter(Interaction.hcp_id == hcp.id)
                    if user_id:
                        query = query.filter(Interaction.created_by == user_id)
                    interaction = query.order_by(Interaction.created_at.desc()).first()

        if not interaction:
            return {"success": False, "error": "No matching interaction found to edit"}

        for key, value in updates.items():
            if not hasattr(interaction, key) or value is None:
                continue
            if key in ("follow_up_date", "interaction_date") and isinstance(value, str):
                value = _parse_date(value)
            elif key == "duration" and isinstance(value, str):
                value = int(re.search(r"\d+", str(value)).group()) if re.search(r"\d+", str(value)) else 60
            setattr(interaction, key, value)

        db.commit()
        elapsed = time.time() - start
        log = AILog(prompt=edit_request, response=json.dumps(updates), tool="edit_interaction", execution_time=elapsed)
        db.add(log)
        db.commit()

        if user_id:
            manager.broadcast_sync(user_id, {"type": "DASHBOARD_UPDATED"})

        return {"success": True, "interaction_id": interaction.id, "updates": updates}
    except Exception as e:
        db.rollback()
        return {"success": False, "error": str(e)}
    finally:
        db.close()
