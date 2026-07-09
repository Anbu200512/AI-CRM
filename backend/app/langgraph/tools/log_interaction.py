import json
import logging
import re
import time
from datetime import date, datetime, timedelta
from typing import Any, Dict, Optional
from langchain_groq import ChatGroq
from langchain_core.tools import tool
from app.config.settings import settings
from app.langgraph.prompts.system_prompts import HCP_EXTRACTION_PROMPT, STEPWISE_EXTRACTION_PROMPT
from app.database.connection import SessionLocal
from app.models.hcp import HCP
from app.models.interaction import Interaction
from app.models.ai_log import AILog
from app.utils.websocket import manager

logger = logging.getLogger(__name__)

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


REQUIRED_FIELDS = [
    ("doctor_name", "Doctor Name"),
    ("hospital", "Hospital"),
    ("speciality", "Speciality"),
    ("interaction_date", "Interaction Date"),
    ("meeting_duration", "Meeting Duration"),
    ("interaction_type", "Interaction Type"),
    ("products_discussed", "Products Discussed"),
    ("interest_level", "Interest Level"),
    ("follow_up_date", "Follow-up Date"),
    ("discussion_notes", "Discussion Notes"),
]

ALL_FIELDS = REQUIRED_FIELDS + [("competitor_products", "Competitor Products")]

FIELD_QUESTIONS = {
    "doctor_name": "What is the doctor's name?",
    "hospital": lambda d: f"At which hospital or clinic does {d.get('doctor_name', 'the doctor')} practice?",
    "speciality": lambda d: f"What is {d.get('doctor_name', 'the doctor')}'s speciality?",
    "interaction_date": lambda d: f"When did you meet {d.get('doctor_name', 'the doctor')}?",
    "meeting_duration": "How long did the meeting last?",
    "interaction_type": "What type of interaction was this? (e.g., Initial Visit, Follow-up Visit, Product Discussion)",
    "products_discussed": "Which products were discussed?",
    "interest_level": lambda d: f"What was {d.get('doctor_name', 'the doctor')}'s interest level? (High, Medium, or Low)",
    "follow_up_date": lambda d: f"When is the follow-up with {d.get('doctor_name', 'the doctor')} scheduled?",
    "discussion_notes": "Any additional notes or key takeaways from the discussion?",
}


def _get_question(field_key, merged_state):
    q = FIELD_QUESTIONS.get(field_key)
    if callable(q):
        return q(merged_state)
    return q or f"Please provide the {field_key.replace('_', ' ')}."


def _is_valid(val):
    if val is None or val == "" or val == []:
        return False
    if isinstance(val, str) and val.strip().lower() == "null":
        return False
    return True


def _build_checklist_response(merged_state):
    collected = []
    for key, display in ALL_FIELDS:
        val = merged_state.get(key)
        if _is_valid(val):
            display_val = ", ".join(val) if isinstance(val, list) else str(val)
            collected.append(f"✅ {display}: {display_val}")
    if not collected:
        return ""
    return "I've recorded:\n" + "\n".join(collected)


def _build_success_card(merged_state, summary_text):
    lines = ["✅ Interaction Logged Successfully\n"]
    for key, display in ALL_FIELDS:
        val = merged_state.get(key)
        if _is_valid(val):
            display_val = ", ".join(val) if isinstance(val, list) else str(val)
            lines.append(f"{display}")
            lines.append(display_val)
            lines.append("")
    if summary_text:
        lines.append("Summary")
        lines.append(summary_text)
        lines.append("")
    lines.append("The interaction has been saved to your CRM. You can view it in Interaction History.")
    return "\n".join(lines)


@tool
def log_interaction_tool(conversation_text: str, user_id: Optional[int] = None, current_state: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Log a new HCP interaction step by step, asking one question at a time."""
    start = time.time()

    if current_state is None:
        current_state = {}
        logger.warning("log_interaction_tool called with None current_state, defaulting to {}")

    logger.info("log_interaction_tool called with current_state keys: %s", list(current_state.keys()))
    logger.info("conversation_text: %.100s", conversation_text)

    is_stepwise = bool(current_state and current_state.get("_stage") != "complete")
    if is_stepwise:
        full_prompt = STEPWISE_EXTRACTION_PROMPT.format(text=conversation_text)
        logger.info("Using STEPWISE_EXTRACTION_PROMPT (stepwise mode)")
    else:
        full_prompt = f"{HCP_EXTRACTION_PROMPT}\n\nText: {conversation_text}"
        logger.info("Using HCP_EXTRACTION_PROMPT (full extraction mode)")

    extracted = {}
    try:
        response = llm.invoke(full_prompt)
        cleaned = response.content.strip()
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
        cleaned = cleaned.strip()
        parsed = json.loads(cleaned)
        if isinstance(parsed, dict):
            extracted = parsed
            logger.info("LLM extracted keys: %s", list(extracted.keys()))
        else:
            logger.warning("LLM returned non-dict JSON: %s", type(parsed).__name__)
    except Exception as e:
        logger.error("LLM extraction failed: %s", str(e))
        extracted = {}

    merged_state = {}
    if isinstance(current_state, dict):
        merged_state = dict(current_state)
    else:
        logger.warning("current_state is not a dict, type=%s, starting fresh", type(current_state).__name__)

    merged_state.pop("_stage", None)

    for k, v in list(merged_state.items()):
        if isinstance(v, str) and v.strip().lower() == "null":
            logger.info("Sanitized 'null' string for key '%s'", k)
            merged_state[k] = None

    for key, val in extracted.items():
        if val is None or val == "" or val == []:
            continue
        if isinstance(val, str) and val.strip().lower() == "null":
            logger.info("Skipped 'null' string from extraction for key '%s'", key)
            continue
        existing = merged_state.get(key)
        if _is_valid(existing):
            logger.info("Preserving existing value for '%s', new extraction skipped", key)
            continue
        merged_state[key] = val
        logger.info("Merged new value for key '%s': %.80s", key, str(val))

    logger.info("merged_state after merging, keys: %s", list(merged_state.keys()))

    missing_fields = []
    for key, display_name in REQUIRED_FIELDS:
        val = merged_state.get(key)
        if val is None or val == "" or val == []:
            missing_fields.append(key)

    if missing_fields:
        next_field = missing_fields[0]
        logger.info("Missing fields: %s, next field: %s", missing_fields, next_field)

        checklist = _build_checklist_response(merged_state)
        question = _get_question(next_field, merged_state)

        parts = []
        if checklist:
            parts.append(checklist)
        else:
            parts.append("I'd be happy to log this interaction for you. Let's start.")
        parts.append("")
        parts.append(question)

        merged_state["_stage"] = "collecting"

        return {
            "success": "partial",
            "next_field": next_field,
            "missing_fields": missing_fields,
            "merged_state": merged_state,
            "response_text": "\n".join(parts),
        }

    logger.info("All required fields collected, saving to database")
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

        sentiment = merged_state.get("sentiment")
        if not sentiment:
            try:
                resp = llm.invoke(
                    f"Analyze the sentiment of this HCP interaction. Return ONLY one word: Positive, Neutral, or Negative.\n\nInteraction: {merged_state.get('discussion_notes', '')}"
                )
                sentiment = resp.content.strip()
            except Exception as e:
                logger.error("Sentiment analysis failed: %s", str(e))
                sentiment = "Neutral"

        discussion = merged_state.get("discussion_notes") or conversation_text

        summary_text = merged_state.get("summary")
        if not summary_text:
            try:
                resp = llm.invoke(
                    f"Generate a professional 2-sentence CRM summary of this HCP interaction:\n"
                    + f"Doctor: {doctor_name or 'Unknown'}\n"
                    + f"Hospital: {merged_state.get('hospital', '')}\n"
                    + f"Discussion: {discussion[:500]}"
                )
                summary_text = resp.content.strip()
            except Exception as e:
                logger.error("Summary generation failed: %s", str(e))
                summary_text = discussion[:200]

        interaction = Interaction(
            hcp_id=hcp.id if hcp else None,
            summary=summary_text,
            discussion=discussion,
            products=", ".join(merged_state.get("products_discussed", []) or []),
            competitors=", ".join(merged_state.get("competitor_products", []) or []),
            sentiment=sentiment,
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
        logger.info("Interaction saved, id=%s", interaction.id)

        elapsed = time.time() - start
        log = AILog(prompt=conversation_text, response=json.dumps(merged_state), tool="log_interaction", execution_time=elapsed)
        db.add(log)
        db.commit()

        if user_id:
            manager.broadcast_sync(user_id, {"type": "DASHBOARD_UPDATED"})

        success_msg = _build_success_card(merged_state, summary_text)

        merged_state["success"] = True
        merged_state["interaction_id"] = interaction.id
        merged_state["_stage"] = "complete"
        return {
            "success": True,
            "interaction_id": interaction.id,
            "response_text": success_msg,
            "merged_state": merged_state,
        }
    except Exception as e:
        db.rollback()
        logger.error("Database save failed: %s", str(e), exc_info=True)
        return {"success": False, "error": str(e), "merged_state": merged_state}
    finally:
        db.close()
