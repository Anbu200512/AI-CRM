import json
import re
import time
import logging
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional
from langchain_groq import ChatGroq
from langchain_core.tools import tool
from app.config.settings import settings
from app.database.connection import SessionLocal
from app.models.interaction import Interaction
from app.models.hcp import HCP
from app.models.ai_log import AILog
from app.utils.websocket import manager

logger = logging.getLogger(__name__)

WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]

llm = ChatGroq(api_key=settings.GROQ_API_KEY, model="llama-3.1-8b-instant", temperature=0)

EDIT_EXTRACTION_PROMPT = """Parse this CRM edit request into a JSON object.

User request: "{edit_request}"

Valid fields (include ONLY what the user explicitly wants to change):
- summary, discussion (free text)
- products, competitors (comma-separated string)
- sentiment (Positive / Neutral / Negative only)
- interest_level (High / Medium / Low only)
- follow_up_date, interaction_date (YYYY-MM-DD)
- duration (integer minutes)
- interaction_type (Initial Visit / Follow-up Visit / Product Discussion / Product Demo / Conference / Online Meeting / Phone Call / Other only)
- hospital, speciality, doctor_name (free text)

STRICT RULES:
- Return ONLY a JSON object. No code, no explanation.
- NEVER include fields the user did not mention.
- NEVER put command words as values. Words like "edit", "change", "update", "modify", "last", "previous", "the", "an", "interaction", "meeting" are commands, NOT data.
- interaction_type must be EXACTLY one of the 8 valid types listed above. Never put sentences or command text as interaction_type.
- If the user says "edit the last interaction" without specifying WHAT to change, return an empty object {{}}.
- If the user says "I want to modify" or "I want to edit" without saying WHICH field, return {{}}.
- If a field value is not explicitly stated, do NOT include it.
- NEVER return fields with empty string values. Only include fields that have a real, non-empty value.

Examples:
"Change interest level to High" -> {{"interest_level": "High"}}
"Edit the last interaction: change interest to High" -> {{"interest_level": "High"}}
"Change hospital to AM Hospital" -> {{"hospital": "AM Hospital"}}
"Update the sentiment to Negative" -> {{"sentiment": "Negative"}}
"Meeting lasted 30 minutes" -> {{"duration": 30}}
"I want to modify an interaction" -> {{}}
"I want to edit an interaction" -> {{}}"""


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
        elif unit == "month":
            return date(today.year + (today.month + num - 1) // 12, (today.month + num - 1) % 12 + 1, min(today.day, 28))
    return today


def _coerce_value(key: str, value: Any) -> Any:
    if value is None:
        return None
    if key in ("products", "competitors"):
        if isinstance(value, list):
            return ", ".join(str(v) for v in value)
        return str(value)
    if key == "duration":
        if isinstance(value, (int, float)):
            return int(value)
        m = re.search(r"(\d+)", str(value))
        return int(m.group(1)) if m else None
    if key in ("follow_up_date", "interaction_date"):
        if isinstance(value, str):
            return _parse_date(value)
        if isinstance(value, date):
            return value
        return value
    if key == "interest_level":
        val = str(value).strip().lower()
        if val in ("high", "very interested", "very interested in product"):
            return "High"
        if val in ("medium", "some interest", "moderate"):
            return "Medium"
        if val in ("low", "not interested", "no interest"):
            return "Low"
        return str(value).strip()
    return value


COMMAND_WORDS = {
    "edit", "change", "update", "modify", "last", "previous", "the", "an",
    "a", "to", "for", "with", "from", "interaction", "meeting", "log",
    "record", "entry", "sure", "ok", "yes", "please", "can", "you",
    "want", "would", "like", "that", "this", "my", "i",
}

VALID_INTERACTION_TYPES = {
    "initial visit", "follow-up visit", "product discussion", "product demo",
    "conference", "online meeting", "phone call", "other",
}

VALID_SENTIMENT = {"positive", "neutral", "negative"}
VALID_INTEREST = {"high", "medium", "low"}


def _validate_updates(updates: Dict[str, Any]) -> Dict[str, Any]:
    """Reject empty, command-text, and invalid values from extracted updates."""
    validated = {}
    for key, value in updates.items():
        if key not in FIELD_DISPLAY_NAMES:
            logger.info("Skipping unknown field: %s", key)
            continue

        # Reject None
        if value is None:
            logger.info("Skipping field '%s': value is None", key)
            continue

        # Reject empty strings, zero, and placeholder values
        str_val = str(value).strip()
        if str_val == "" or str_val.lower() in ("none", "null", "n/a"):
            logger.info("Skipping field '%s': empty value", key)
            continue
        if isinstance(value, (int, float)) and value == 0:
            logger.info("Skipping field '%s': zero value", key)
            continue

        # Reject values that are entirely command words
        words = set(str_val.lower().replace(",", " ").replace(".", " ").split())
        non_command_words = words - COMMAND_WORDS
        if not non_command_words:
            logger.info("Skipping field '%s': value is only command text: '%s'", key, str_val)
            continue

        # Validate interaction_type against allowed values
        if key == "interaction_type":
            if str_val.lower() not in VALID_INTERACTION_TYPES:
                logger.info("Skipping field '%s': invalid type '%s'", key, str_val)
                continue

        # Validate sentiment
        if key == "sentiment":
            if str_val.lower() not in VALID_SENTIMENT:
                logger.info("Skipping field '%s': invalid value '%s'", key, str_val)
                continue

        # Validate interest_level
        if key == "interest_level":
            if str_val.lower() not in VALID_INTEREST:
                logger.info("Skipping field '%s': invalid value '%s'", key, str_val)
                continue

        validated[key] = value

    return validated


FIELD_DISPLAY_NAMES = {
    "summary": "Summary",
    "discussion": "Discussion Notes",
    "products": "Products",
    "competitors": "Competitors",
    "sentiment": "Sentiment",
    "interest_level": "Interest Level",
    "follow_up_date": "Follow-up Date",
    "duration": "Duration",
    "interaction_type": "Interaction Type",
    "interaction_date": "Interaction Date",
    "hospital": "Hospital",
    "speciality": "Speciality",
    "doctor_name": "Doctor Name",
}

HCP_FIELDS = {"hospital", "speciality", "doctor_name"}


def _find_interaction(db, edit_request: str, interaction_id: int, user_id: Optional[int], edit_context: Dict, conversation_history: Optional[List[Dict[str, str]]]) -> Optional[Interaction]:
    """Find the interaction to edit using a 3-tier lookup strategy."""

    # Priority 1: Explicit interaction_id from state context
    context_id = edit_context.get("_edit_interaction_id") or 0
    if not interaction_id and context_id:
        interaction_id = context_id
        logger.info("Using interaction_id from edit_context: %s", interaction_id)

    if interaction_id and interaction_id > 0:
        query = db.query(Interaction).filter(Interaction.id == interaction_id)
        if user_id:
            query = query.filter(Interaction.created_by == user_id)
        interaction = query.first()
        logger.info("Lookup by interaction_id=%s: %s", interaction_id, "found" if interaction else "not found")
        if interaction:
            return interaction

    # Priority 2: Check for "last/latest/most recent" references
    lower_req = edit_request.lower()
    refers_to_latest = any(p in lower_req for p in [
        "last interaction", "latest interaction", "my interaction", "previous interaction",
        "that interaction", "most recent", "last meeting", "latest meeting", "last log",
        "latest log", "previous log", "recent log", "recent interaction",
    ])
    if refers_to_latest and user_id:
        interaction = (
            db.query(Interaction)
            .filter(Interaction.created_by == user_id)
            .order_by(Interaction.created_at.desc())
            .first()
        )
        logger.info("Lookup by 'latest' reference: %s", "found id=%s" % interaction.id if interaction else "not found")
        if interaction:
            return interaction

    # Priority 3: Extract doctor name and find their most recent interaction
    doctor_name = _extract_doctor_name_from_request(edit_request, conversation_history)
    if doctor_name:
        hcp = db.query(HCP).filter(HCP.doctor_name.ilike(f"%{doctor_name}%")).first()
        if hcp:
            query = db.query(Interaction).filter(Interaction.hcp_id == hcp.id)
            if user_id:
                query = query.filter(Interaction.created_by == user_id)
            interaction = query.order_by(Interaction.created_at.desc()).first()
            logger.info("Lookup by doctor name '%s' (hcp_id=%s): %s", doctor_name, hcp.id, "found id=%s" % interaction.id if interaction else "not found")
            if interaction:
                return interaction

    return None


def _format_interaction_summary(interaction: Interaction, hcp: Optional[HCP] = None) -> str:
    """Build a readable summary of the interaction for the edit prompt."""
    doctor = hcp.doctor_name if hcp else "Unknown"
    lines = []
    lines.append(f"Doctor: {doctor}")
    if hcp and hcp.hospital:
        lines.append(f"Hospital: {hcp.hospital}")
    if hcp and hcp.speciality:
        lines.append(f"Speciality: {hcp.speciality}")
    if interaction.interaction_date:
        lines.append(f"Date: {interaction.interaction_date}")
    if interaction.interaction_type:
        lines.append(f"Type: {interaction.interaction_type}")
    if interaction.products:
        lines.append(f"Products: {interaction.products}")
    if interaction.competitors:
        lines.append(f"Competitors: {interaction.competitors}")
    if interaction.interest_level:
        lines.append(f"Interest: {interaction.interest_level}")
    if interaction.sentiment:
        lines.append(f"Sentiment: {interaction.sentiment}")
    if interaction.follow_up_date:
        lines.append(f"Follow-up: {interaction.follow_up_date}")
    if interaction.duration:
        lines.append(f"Duration: {interaction.duration} min")
    if interaction.discussion:
        lines.append(f"Notes: {interaction.discussion[:200]}")
    if interaction.summary:
        lines.append(f"Summary: {interaction.summary[:200]}")
    return "\n".join(lines)


@tool
def edit_interaction_tool(
    edit_request: str,
    interaction_id: int = 0,
    user_id: Optional[int] = None,
    edit_context: Optional[Dict[str, Any]] = None,
    conversation_history: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, Any]:
    """Edit an existing interaction based on natural language instructions.

    Args:
        edit_request: The user's natural language edit instruction.
        interaction_id: ID of the interaction to edit (0 if not known).
        user_id: ID of the current user.
        edit_context: Previously stored edit context (e.g. _edit_interaction_id).
        conversation_history: Recent conversation messages for context.
    """
    start = time.time()

    if edit_context is None:
        edit_context = {}

    logger.info("edit_interaction_tool called: edit_request=%.100s, interaction_id=%s, user_id=%s", edit_request, interaction_id, user_id)
    logger.info("edit_context: %s", edit_context)

    # ── Step 1: Extract update fields via LLM ──────────────────────────────
    updates = {}
    try:
        response = llm.invoke(EDIT_EXTRACTION_PROMPT.format(edit_request=edit_request))
        raw = response.content.strip()
        # Strip any code fence (json, javascript, python, etc.)
        cleaned = re.sub(r"^```[\w]*\s*", "", raw)
        cleaned = re.sub(r"\s*```$", "", cleaned)
        cleaned = cleaned.strip()
        try:
            updates = json.loads(cleaned)
        except json.JSONDecodeError:
            # Try to find a JSON object {...} in the text
            match = re.search(r"\{[^{}]*\}", cleaned)
            if match:
                updates = json.loads(match.group())
        logger.info("LLM extracted updates: %s", updates)
    except json.JSONDecodeError as e:
        logger.error("LLM returned invalid JSON: %s | raw=%.300s", e, raw if response else "None")
    except Exception as e:
        logger.error("LLM extraction failed: %s", e)

    # ── Step 2: Coerce and validate values ──────────────────────────────────
    coerced_updates = {}
    if updates:
        for key, value in updates.items():
            coerced = _coerce_value(key, value)
            if coerced is not None:
                coerced_updates[key] = coerced
                logger.info("Coerced field '%s': %s -> %s", key, value, coerced)
    coerced_updates = _validate_updates(coerced_updates)

    # ── Step 3: Find the interaction ───────────────────────────────────────
    db = SessionLocal()
    try:
        interaction = _find_interaction(db, edit_request, interaction_id, user_id, edit_context, conversation_history)

        if not interaction:
            logger.warning("No matching interaction found for edit_request: %.100s", edit_request)
            return {"success": False, "error": "No matching interaction found to edit. Please specify the doctor name or interaction."}

        logger.info("Selected interaction: id=%s, hcp_id=%s, products=%s", interaction.id, interaction.hcp_id, interaction.products)

        # Get HCP name for display
        hcp = db.query(HCP).filter(HCP.id == interaction.hcp_id).first() if interaction.hcp_id else None

        # ── Step 4: If no fields to update, show current state and ask ─────
        if not coerced_updates:
            interaction_summary = _format_interaction_summary(interaction, hcp)
            logger.info("No update fields extracted, showing interaction details and asking what to change")
            return {
                "success": "awaiting_fields",
                "interaction_id": interaction.id,
                "interaction_summary": interaction_summary,
                "response_text": (
                    f"I found your interaction with {hcp.doctor_name if hcp else 'the doctor'} "
                    f"(ID: {interaction.id}). Here are the current details:\n\n"
                    f"{interaction_summary}\n\n"
                    f"What would you like to change? You can say things like:\n"
                    f"  - Change interest level to High\n"
                    f"  - Update products to Insulin, Metformin\n"
                    f"  - Move follow-up to next Monday\n"
                    f"  - Replace Dapagliflozin with Empagliflozin\n"
                    f"  - Meeting lasted 30 minutes"
                ),
            }

        # ── Step 5: Apply updates ──────────────────────────────────────────
        hcp_updates = {k: v for k, v in coerced_updates.items() if k in HCP_FIELDS}
        interaction_updates = {k: v for k, v in coerced_updates.items() if k not in HCP_FIELDS}

        updated_fields = []

        # Update Interaction fields
        for key, value in interaction_updates.items():
            if not hasattr(interaction, key):
                logger.warning("Field '%s' not found on Interaction model, skipping", key)
                continue
            old_value = getattr(interaction, key)
            setattr(interaction, key, value)
            updated_fields.append(key)
            logger.info("Interaction field '%s': %s -> %s", key, old_value, value)

        # Update HCP fields
        if hcp_updates and hcp:
            for key, value in hcp_updates.items():
                if hasattr(hcp, key):
                    old_value = getattr(hcp, key)
                    setattr(hcp, key, value)
                    updated_fields.append(key)
                    logger.info("HCP field '%s': %s -> %s", key, old_value, value)
                else:
                    logger.warning("Field '%s' not found on HCP model, skipping", key)
        elif hcp_updates and not hcp:
            logger.warning("HCP updates requested but no HCP record found (hcp_id=%s)", interaction.hcp_id)

        if not updated_fields:
            return {"success": False, "error": "No valid fields were updated"}

        db.commit()
        logger.info("Interaction %s updated successfully, fields: %s", interaction.id, updated_fields)

        # ── Step 6: Log and broadcast ──────────────────────────────────────
        elapsed = time.time() - start
        log_entry = AILog(
            prompt=edit_request,
            response=json.dumps({"interaction_id": interaction.id, "updates": coerced_updates}, default=str),
            tool="edit_interaction",
            execution_time=elapsed,
        )
        db.add(log_entry)
        db.commit()

        if user_id:
            manager.broadcast_sync(user_id, {"type": "DASHBOARD_UPDATED"})

        # Build display-friendly update names
        display_updates = {}
        for key in updated_fields:
            display_updates[FIELD_DISPLAY_NAMES.get(key, key.replace("_", " ").title())] = coerced_updates[key]

        return {
            "success": True,
            "interaction_id": interaction.id,
            "updated_fields": updated_fields,
            "updates": display_updates,
            "raw_updates": coerced_updates,
        }

    except Exception as e:
        db.rollback()
        logger.error("Database update failed: %s", e, exc_info=True)
        return {"success": False, "error": str(e)}
    finally:
        db.close()


def _extract_doctor_name_from_request(edit_request: str, conversation_history: Optional[List[Dict[str, str]]] = None) -> Optional[str]:
    """Extract doctor name from the edit request or conversation context."""
    prompt = f"""Extract the doctor/HCP name from this text. Return ONLY the name, nothing else.
If no doctor name is found, return "unknown".

Text: {edit_request}"""
    try:
        resp = llm.invoke(prompt)
        name = resp.content.strip()
        if name.lower() == "unknown" or not name:
            return None
        logger.info("Extracted doctor name from edit request: '%s'", name)
        return name
    except Exception as e:
        logger.error("Doctor name extraction failed: %s", e)
        return None
