import json
import re
import time
from datetime import date, datetime, timedelta
from typing import Any, Dict, Optional
from langchain_groq import ChatGroq
from langchain_core.tools import tool
from app.config.settings import settings
from app.langgraph.prompts.system_prompts import HCP_EXTRACTION_PROMPT
from app.database.connection import SessionLocal
from app.models.hcp import HCP
from app.models.interaction import Interaction
from app.models.ai_log import AILog
from app.utils.websocket import manager

WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]

llm = ChatGroq(api_key=settings.GROQ_API_KEY, model="llama-3.1-8b-instant")


def _parse_date(value):
    if not value:
        return None
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
    try:
        return datetime.strptime(val, "%d/%m/%Y").date()
    except ValueError:
        pass
    if val in ("today", "now"):
        return today
    if val == "tomorrow":
        return today + timedelta(days=1)
    if val == "yesterday":
        return today - timedelta(days=1)
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
    return None


def _parse_duration(value):
    if not value:
        return None
    val = str(value).strip().lower()
    match = re.search(r"(\d+)\s*(?:hour|hr|h)", val)
    if match:
        hours = int(match.group(1))
        min_match = re.search(r"(\d+)\s*(?:min|minute|m)(?:ute)?", val)
        minutes = int(min_match.group(1)) if min_match else 0
        return hours * 60 + minutes
    match = re.search(r"(\d+)\s*(?:min|minute|m)(?:ute)?", val)
    if match:
        return int(match.group(1))
    return None


REQUIRED_FIELDS = {
    "doctor_name": "Doctor Name",
    "hospital": "Hospital",
    "interaction_date": "Interaction Date",
    "products_discussed": "Products Discussed",
    "interest_level": "Interest Level",
    "discussion_notes": "Discussion Notes",
}

OPTIONAL_FIELDS = {
    "speciality": "Speciality",
    "meeting_duration": "Meeting Duration",
    "interaction_type": "Interaction Type",
    "competitor_products": "Competitor Products",
    "follow_up_date": "Follow-up Date",
}

@tool
def log_interaction_tool(conversation_text: str, user_id: Optional[int] = None, current_state: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Log a new HCP interaction from natural language conversation, asking for missing fields."""
    start = time.time()
    
    if current_state is None:
        current_state = {}

    full_prompt = f"{HCP_EXTRACTION_PROMPT}\n\nText: {conversation_text}"
    response = llm.invoke(full_prompt)
    extracted = {}
    try:
        cleaned = response.content.strip()
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
        cleaned = cleaned.strip()
        extracted = json.loads(cleaned)
    except:
        extracted = {}

    # Merge current_state with newly extracted fields (new overrides old if present and non-null)
    merged_state = dict(current_state)
    for key, val in extracted.items():
        if val is not None and val != "" and val != []:
            # Special case for arrays like products_discussed to avoid overwriting with empty
            merged_state[key] = val

    # Check for missing required fields
    missing_fields = []
    for key, display_name in REQUIRED_FIELDS.items():
        val = merged_state.get(key)
        if val is None or val == "" or val == []:
            missing_fields.append(display_name)

    if missing_fields:
        # Build "I currently have" section
        FIELD_DISPLAY = {**REQUIRED_FIELDS, **OPTIONAL_FIELDS}
        have_lines = []
        for key, display in FIELD_DISPLAY.items():
            val = merged_state.get(key)
            if val is not None and val != "" and val != []:
                display_val = ", ".join(val) if isinstance(val, list) else str(val)
                have_lines.append(f"✓ {display}: {display_val}")
        
        missing_bullets = "\n".join([f"• {f}" for f in missing_fields])
        have_section = "\n".join(have_lines) if have_lines else ""
        
        response_text = "I can help log this interaction.\n\n"
        if have_section:
            response_text += f"I currently have:\n{have_section}\n\n"
        response_text += f"Please provide the remaining information:\n{missing_bullets}"
        
        return {
            "success": False,
            "missing_fields": missing_fields,
            "merged_state": merged_state,
            "response_text": response_text,
        }

    # All required fields are present, proceed to save
    db = SessionLocal()
    try:
        hcp = None
        doctor_name = merged_state.get("doctor_name")
        if doctor_name:
            hcp = db.query(HCP).filter(HCP.doctor_name.ilike(f"%{doctor_name}%")).first()
            if not hcp:
                hcp = HCP(
                    doctor_name=doctor_name,
                    hospital=merged_state.get("hospital"),
                    speciality=merged_state.get("speciality"),
                )
                db.add(hcp)
                db.flush()
            elif merged_state.get("speciality"):
                hcp.speciality = merged_state.get("speciality")
                db.flush()

        interaction = Interaction(
            hcp_id=hcp.id if hcp else None,
            summary=merged_state.get("summary"),
            discussion=merged_state.get("discussion_notes") or conversation_text,
            products=", ".join(merged_state.get("products_discussed", []) or []),
            competitors=", ".join(merged_state.get("competitor_products", []) or []),
            sentiment=merged_state.get("sentiment"),
            interest_level=merged_state.get("interest_level"),
            interaction_date=_parse_date(merged_state.get("interaction_date")),
            follow_up_date=_parse_date(merged_state.get("follow_up_date")),
            duration=_parse_duration(merged_state.get("meeting_duration")),
            interaction_type=merged_state.get("interaction_type"),
            created_by=user_id,
        )
        db.add(interaction)
        db.flush()
        db.commit()

        elapsed = time.time() - start
        log = AILog(prompt=conversation_text, response=json.dumps(merged_state), tool="log_interaction", execution_time=elapsed)
        db.add(log)
        db.commit()

        if user_id:
            manager.broadcast_sync(user_id, {"type": "DASHBOARD_UPDATED"})

        merged_state["success"] = True
        merged_state["interaction_id"] = interaction.id
        return merged_state
    except Exception as e:
        db.rollback()
        return {"success": False, "error": str(e), "merged_state": merged_state}
    finally:
        db.close()

