import json
import logging
import re
import time
from typing import Dict, Literal, Optional
from langgraph.graph import StateGraph, END
from langchain_groq import ChatGroq
from app.config.settings import settings
from app.langgraph.state import AgentState
from app.langgraph.prompts.system_prompts import (
    SYSTEM_PROMPT, INTENT_DETECTION_PROMPT, DOCTOR_NAME_EXTRACT_PROMPT
)
from app.langgraph.tools.log_interaction import log_interaction_tool

logger = logging.getLogger(__name__)
from app.langgraph.tools.edit_interaction import edit_interaction_tool
from app.langgraph.tools.summarize import summarize_tool
from app.langgraph.tools.followup import followup_tool
from app.langgraph.tools.entity_extraction import entity_extraction_tool
from app.langgraph.tools.sentiment import sentiment_analysis_tool
from app.langgraph.tools.meeting_classifier import meeting_classifier_tool
from app.langgraph.tools.search_interactions import search_interactions_tool
from app.langgraph.tools.show_history import show_history_tool
from app.langgraph.tools.delete_interaction import delete_interaction_tool
from app.langgraph.tools.dashboard_assistant import dashboard_assistant_tool

llm = ChatGroq(api_key=settings.GROQ_API_KEY, model="llama-3.1-8b-instant")

CONFIRM_WORDS = {"yes", "confirm", "delete", "proceed", "go ahead", "sure", "ok", "okay", "do it"}
CANCEL_WORDS = {"no", "cancel", "abort", "stop", "nevermind", "never mind"}
GREETING_WORDS = ["hi", "hello", "hey", "good morning", "good afternoon", "good evening", "greetings", "howdy"]
FORGOT_PATTERNS = ["forgot", "add more", "add one more", "add another", "missed something", "also want", "also need"]
EDIT_PATTERNS = ["edit", "update", "modify", "replace", "change", "correct", "reschedule"]

LOG_INTERACTION_NARRATIVE_PATTERNS = [
    r"\bi\s+met\b",
    r"\bi\s+visited\b",
    r"\bi\s+had\s+a\s+meeting\b",
    r"\bi\s+had\s+a\s+visit\b",
    r"\bwe\s+discussed\b",
    r"\bi\s+discussed\b",
    r"\bi\s+presented\b",
    r"\bi\s+introduced\b",
    r"\bi\s+demonstrated\b",
    r"\bvisited\s+(?:dr\.?|doctor)",
    r"\bmet\s+(?:dr\.?|doctor)",
    r"\bmeeting\s+lasted\b",
    r"\bmeeting\s+duration\b",
    r"\blog\s+(?:a|an|the|this|my|that|new)?\s*(?:new\s+)?(?:log|meeting|interaction|visit|call|entry)",
    r"\badd\s+(?:a\s+)?(?:new\s+)?(?:log|interaction|meeting|visit|call|entry)",
    r"\badd\s+this\s+as\s+(?:a\s+)?(?:log|interaction|meeting|visit|call)",
    r"\brecord\s+(?:a|an|the|this|my|that)\s+(?:meeting|interaction|visit|call)",
    r"\bsave\s+(?:this|the|a|my|that)\s+(?:meeting|interaction|visit|call|log)",
    r"\bproduct\s+discussion",
    r"\bproduct\s+demo",
]

NARRATIVE_DETAIL_SIGNALS = [
    (r"(?:dr\.?|doctor)\s+\w+(?:\s+\w+)?", "doctor_name"),
    (r"(?:hospital|clinic|medical\s+center|healthcare)", "hospital"),
    (r"(?:cardiolog|neurolog|oncolog|pediatr|dermatolog|orthoped|endocrin|gastro|pulmon|urol|ophthalm|general\s+pract|physician|surgeon)", "speciality"),
    (r"(?:discussed|presented|introduced|demonstrated|showed|explained)", "discussion_verb"),
    (r"(?:product|drug|medication|medicine|therap|tablet|capsule|injection|dose|mg\b|dosage)", "product"),
    (r"(?:interest(?:ed)?|enthusiastic|positive\s+response)", "interest"),
    (r"(?:follow.?up|next\s+(?:visit|meeting|call|appointment))", "follow_up"),
    (r"(?:duration|lasted|minutes?|hours?|mins?)", "duration"),
    (r"(?:requested|asked\s+for|wanted|needs)\s+(?:clinical|evidence|data|samples|information|brochure)", "requested_material"),
    (r"(?:high|medium|low)\s+(?:interest|level)", "interest_level"),
    (r"(?:positive|negative|neutral)", "sentiment"),
    (r"(?:initial\s+visit|follow.?up\s+visit|product\s+discussion|product\s+demo|conference|phone\s+call|online\s+meeting)", "interaction_type"),
]


def _is_greeting(text: str) -> bool:
    t = text.strip().lower()
    words = t.split()
    if len(words) > 5:
        return False
    for g in GREETING_WORDS:
        if t == g or t.startswith(g + " ") or t.endswith(" " + g) or (" " + g + " ") in " " + t + " ":
            return True
    return False


def _extract_doctor_name(message: str) -> Optional[str]:
    """Extract doctor name from a user message using LLM."""
    try:
        resp = llm.invoke(DOCTOR_NAME_EXTRACT_PROMPT.format(message=message))
        name = resp.content.strip()
        return name if name.lower() != "unknown" else None
    except Exception:
        return None


def _get_full_conversation_text(messages: list) -> str:
    """Build full conversation context for extraction."""
    recent = messages[-10:] if isinstance(messages, list) else []
    parts = []
    for m in recent:
        if isinstance(m, dict):
            role = m.get("role", "unknown").upper()
            content = m.get("content", "")
            parts.append(f"{role}: {content}")
    return "\n".join(parts)


def _has_explicit_search_intent(text: str) -> bool:
    """Check if the message is an EXPLICIT search request like 'show interactions' or 'find Dr. X'."""
    lower = text.strip().lower()
    has_search_verb = any(re.search(r'\b' + p + r'\b', lower) for p in ["show", "search", "find", "list", "display", "get", "retrieve"])
    has_search_target = any(re.search(p, lower) for p in [
        r"(?:all|my|the|recent|last)\s+(?:interactions?|meetings?|visits?|records?|history|logs?|doctors?)",
        r"interactions?\s+(?:with|at|from|for|related)",
        r"meetings?\s+(?:with|at|from|for)",
    ])
    return has_search_verb and has_search_target


def _detect_explicit_action_intent(text: str) -> Optional[str]:
    """Check if the message starts with an explicit action verb that determines the intent.

    Returns the intent string if found, None otherwise.
    This runs BEFORE narrative detection so that 'Summarize my interaction with Dr. X'
    is correctly classified as summarize, not log_interaction.
    """
    lower = text.strip().lower()

    if re.match(r'^\s*(?:summarize|summary|recap|give\s+(?:me\s+)?(?:a\s+)?summary|overview|takeaway)', lower):
        return "summarize"

    if re.match(r'^\s*(?:recommend|suggest|follow.?up|what\s+should|what\s+(?:is|are)\s+(?:the\s+)?(?:recommended|suggested|priority|next)|how\s+should|next\s+(?:action|visit|meeting)|(?:generate|give|provide|create)\s+(?:me\s+)?(?:a\s+)?(?:follow.?up|recommendation|suggestion|talking\s+points|priority|clinical\s+evidence|visit\s+agenda|action\s+plan))', lower):
        return "followup_recommendation"

    if re.match(r'^\s*(?:edit|update|modify|replace|change|correct|reschedule)', lower):
        return "edit_interaction"

    if re.match(r'^\s*(?:show|search|find|list|display|get|retrieve)', lower):
        return "search_interactions"

    if re.match(r'^\s*(?:delete|remove)', lower):
        return "delete_interaction"

    if re.match(r'^\s*(?:log|record|save|add\s+(?:a\s+)?(?:new\s+)?(?:log|interaction|meeting|visit|call|entry))', lower):
        return "log_interaction"

    return None


def _detect_interaction_narrative(text: str) -> Dict[str, any]:
    """Detect if the message is a complete interaction narrative.

    Returns a dict with:
      - is_narrative: bool
      - confidence: float  (0.0 - 1.0)
      - matched_patterns: list of pattern descriptions
      - reason: str explaining why it was classified this way
    """
    lower = text.strip().lower()
    words = lower.split()
    matched = []
    reason_parts = []

    if re.match(r'^\s*(?:generate|give|provide|create|recommend|suggest|follow.?up|what\s+should|what\s+(?:is|are)\s+(?:the\s+)?(?:recommended|suggested|priority|next)|how\s+should|next\s+(?:action|visit|meeting))', lower):
        return {
            "is_narrative": False,
            "confidence": 0.0,
            "matched_patterns": [],
            "reason": "follow-up/recommendation keyword at start, not a narrative",
        }

    has_log_verb = any(re.search(p, lower) for p in LOG_INTERACTION_NARRATIVE_PATTERNS)
    if has_log_verb:
        matched.append("log_verb")
        reason_parts.append("explicit log/action verb detected")

    detail_count = 0
    detail_types = []
    for pattern, label in NARRATIVE_DETAIL_SIGNALS:
        if re.search(pattern, lower):
            detail_count += 1
            detail_types.append(label)

    if detail_count >= 1:
        matched.extend(detail_types)

    length_score = min(len(words) / 20.0, 1.0)
    has_doctor = "doctor_name" in detail_types

    if has_log_verb:
        confidence = 0.6 + (detail_count * 0.1) + (length_score * 0.15)
        confidence = min(confidence, 1.0)
        is_narrative = True
    elif has_doctor and detail_count >= 2 and len(words) >= 4:
        confidence = 0.45 + (detail_count * 0.12) + (length_score * 0.15)
        confidence = min(confidence, 0.9)
        is_narrative = True
        reason_parts.append("doctor name with %d detail signals" % detail_count)
    elif detail_count >= 3 and len(words) >= 8:
        confidence = 0.4 + (detail_count * 0.1) + (length_score * 0.15)
        confidence = min(confidence, 0.85)
        is_narrative = True
        reason_parts.append("%d detail signals in long message" % detail_count)
    else:
        confidence = 0.0
        is_narrative = False
        reason_parts.append("insufficient narrative signals (details=%d, words=%d)" % (detail_count, len(words)))

    reason = "; ".join(reason_parts) if reason_parts else "no narrative indicators"

    return {
        "is_narrative": is_narrative,
        "confidence": round(confidence, 2),
        "matched_patterns": matched,
        "reason": reason,
    }


def detect_intent(state: AgentState) -> AgentState:
    start_time = time.time()
    messages = state.get("conversation", [])
    last_message = ""
    if messages and isinstance(messages, list) and len(messages) > 0:
        last = messages[-1]
        if isinstance(last, dict):
            last_message = last.get("content", "")
    entities = state.get("entities", {})
    if not isinstance(entities, dict):
        logger.warning("entities is not a dict in detect_intent, type=%s, resetting", type(entities).__name__)
        entities = {}

    lower_msg = last_message.strip().lower()
    detected_intent = None
    confidence = 0.0
    tool_name = "general_node"
    reason = ""

    if not last_message.strip():
        state["intent"] = "general_query"
        _log_intent_detection(last_message, "general_query", 0.0, "general_node", 0.0, "empty message")
        return state

    if entities.get("_stage") == "collecting":
        override_intent = _detect_explicit_action_intent(last_message)
        if override_intent and override_intent != "log_interaction":
            logger.info(
                "[INTENT_DETECT] Breaking out of collecting state: user expressed %s, clearing entities",
                override_intent,
            )
            state["entities"] = {}
        else:
            detected_intent = "log_interaction"
            confidence = 1.0
            tool_name = "log_interaction_node"
            reason = "mid-interaction collection in progress"
            state["intent"] = detected_intent
            _log_intent_detection(last_message, detected_intent, confidence, tool_name, time.time() - start_time, reason)
            return state

    pending = state.get("pending_deletion")
    if pending and pending.get("needs_confirmation"):
        if any(w in lower_msg for w in CONFIRM_WORDS):
            detected_intent = "confirm_delete"
            confidence = 1.0
            tool_name = "confirm_delete_node"
            reason = "user confirmed pending deletion"
        elif any(w in lower_msg for w in CANCEL_WORDS):
            detected_intent = "cancel_delete"
            confidence = 1.0
            tool_name = "cancel_delete_node"
            reason = "user cancelled pending deletion"
        else:
            detected_intent = "delete_interaction"
            confidence = 0.8
            tool_name = "delete_node"
            reason = "pending deletion awaiting confirmation"
        state["intent"] = detected_intent
        _log_intent_detection(last_message, detected_intent, confidence, tool_name, time.time() - start_time, reason)
        return state

    explicit_intent = _detect_explicit_action_intent(last_message)
    if explicit_intent:
        detected_intent = explicit_intent
        if explicit_intent == "log_interaction":
            confidence = 0.95
            tool_name = "log_interaction_node"
            reason = "explicit log/record/save verb at message start"
        elif explicit_intent == "summarize":
            confidence = 0.95
            tool_name = "summarize_node"
            reason = "explicit summarize/summary keyword at message start"
        elif explicit_intent == "followup_recommendation":
            confidence = 0.9
            tool_name = "followup_node"
            reason = "explicit recommend/suggest/follow-up keyword at message start"
        elif explicit_intent == "edit_interaction":
            confidence = 0.9
            tool_name = "edit_interaction_node"
            reason = "explicit edit/update/modify verb at message start"
        elif explicit_intent == "search_interactions":
            confidence = 0.85
            tool_name = "search_node"
            reason = "explicit show/search/find verb at message start"
        elif explicit_intent == "delete_interaction":
            confidence = 0.9
            tool_name = "delete_node"
            reason = "explicit delete/remove verb at message start"
        else:
            confidence = 0.8
            tool_name = route_intent({"intent": explicit_intent})
            reason = "explicit action verb detected at message start"
        state["intent"] = detected_intent
        _log_intent_detection(last_message, detected_intent, confidence, tool_name, time.time() - start_time, reason)
        return state

    narrative_result = _detect_interaction_narrative(last_message)
    if narrative_result["is_narrative"]:
        detected_intent = "log_interaction"
        confidence = narrative_result["confidence"]
        tool_name = "log_interaction_node"
        reason = "interaction narrative detected: %s (matched: %s)" % (narrative_result["reason"], ", ".join(narrative_result["matched_patterns"]))
        state["intent"] = detected_intent
        _log_intent_detection(last_message, detected_intent, confidence, tool_name, time.time() - start_time, reason)
        return state

    if any(p in lower_msg for p in FORGOT_PATTERNS):
        detected_intent = "edit_interaction"
        confidence = 0.95
        tool_name = "edit_interaction_node"
        reason = "forgot/add-more pattern detected (edit context)"
        state["intent"] = detected_intent
        _log_intent_detection(last_message, detected_intent, confidence, tool_name, time.time() - start_time, reason)
        return state

    if any(re.search(r'\b' + p + r'\b', lower_msg) for p in EDIT_PATTERNS):
        detected_intent = "edit_interaction"
        confidence = 0.85
        tool_name = "edit_interaction_node"
        reason = "edit verb detected in message"
        state["intent"] = detected_intent
        _log_intent_detection(last_message, detected_intent, confidence, tool_name, time.time() - start_time, reason)
        return state

    SEARCH_PATTERNS = ["show", "search", "find", "list", "display", "get", "retrieve"]
    if any(re.search(r'\b' + p + r'\b', lower_msg) for p in SEARCH_PATTERNS):
        detected_intent = "search_interactions"
        confidence = 0.7
        tool_name = "search_node"
        reason = "search verb detected (no narrative or edit signals)"
        state["intent"] = detected_intent
        _log_intent_detection(last_message, detected_intent, confidence, tool_name, time.time() - start_time, reason)
        return state

    SUMMARIZE_PATTERNS = ["summarize", "summary", "recap", "overview", "takeaway"]
    if any(re.search(r'\b' + p + r'\b', lower_msg) for p in SUMMARIZE_PATTERNS):
        detected_intent = "summarize"
        confidence = 0.95
        tool_name = "summarize_node"
        reason = "summarize keyword detected (no narrative/edit/search signals)"
        state["intent"] = detected_intent
        _log_intent_detection(last_message, detected_intent, confidence, tool_name, time.time() - start_time, reason)
        return state

    FOLLOWUP_PATTERNS = ["recommend", "recommendation", "recommended", "followup", "follow-up", "follow up", "agenda", "talking", "priority"]
    FOLLOWUP_PHRASES = [r"next\s+(?:action|visit|meeting)", r"what\s+should\s+I\s+(?:do|discuss)\s+next", r"action\s+plan", r"(?:generate|give|provide|create)\s+(?:me\s+)?(?:a\s+)?(?:follow.?up|recommendation|suggestion|talking\s+points|clinical\s+evidence|visit\s+agenda)"]
    if any(re.search(r'\b' + p + r'\b', lower_msg) for p in FOLLOWUP_PATTERNS) or \
       any(re.search(p, lower_msg) for p in FOLLOWUP_PHRASES):
        detected_intent = "followup_recommendation"
        confidence = 0.9
        tool_name = "followup_node"
        reason = "follow-up keyword detected (no narrative/edit/search signals)"
        state["intent"] = detected_intent
        _log_intent_detection(last_message, detected_intent, confidence, tool_name, time.time() - start_time, reason)
        return state

    try:
        response = llm.invoke(f"{INTENT_DETECTION_PROMPT}\n\nMessage: {last_message}")
        detected_intent = response.content.strip().lower()
        confidence = 0.6
        tool_name = route_intent({"intent": detected_intent})
        reason = "LLM fallback classification"
    except Exception:
        detected_intent = "general_query"
        confidence = 0.3
        tool_name = "general_node"
        reason = "LLM call failed, defaulting to general"
    state["intent"] = detected_intent
    _log_intent_detection(last_message, detected_intent, confidence, tool_name, time.time() - start_time, reason)
    return state


def _log_intent_detection(message: str, intent: str, confidence: float, tool: str, elapsed: float, reason: str = ""):
    """Log structured intent detection with full diagnostics."""
    logger.info(
        "[INTENT_DETECT] message=%.150s | intent=%s | confidence=%.2f | tool=%s | reason=%s | elapsed=%.3fs",
        message.strip(), intent, confidence, tool, reason, elapsed,
    )


def route_intent(state: AgentState) -> str:
    intent = state.get("intent", "")
    if "log_interaction" in intent:
        return "log_interaction_node"
    elif "edit_interaction" in intent:
        return "edit_interaction_node"
    elif "summarize" in intent:
        return "summarize_node"
    elif "followup" in intent:
        return "followup_node"
    elif "extract" in intent:
        return "extract_entities_node"
    elif "sentiment" in intent:
        return "sentiment_node"
    elif "classify" in intent:
        return "classify_node"
    elif "search_interactions" in intent:
        return "search_node"
    elif "show_history" in intent:
        return "history_node"
    elif "delete_interaction" in intent:
        return "delete_node"
    elif "confirm_delete" in intent:
        return "confirm_delete_node"
    elif "cancel_delete" in intent:
        return "cancel_delete_node"
    elif "dashboard" in intent:
        return "dashboard_node"
    else:
        return "general_node"


# ─── LOG INTERACTION ────────────────────────────────────────────────────────

def log_interaction_node(state: AgentState) -> AgentState:
    messages = state.get("conversation", [])
    text = ""
    if messages and isinstance(messages, list) and len(messages) > 0:
        last = messages[-1]
        if isinstance(last, dict):
            text = last.get("content", "")

    raw_entities = state.get("entities")
    current_state = raw_entities if isinstance(raw_entities, dict) else {}
    if not isinstance(raw_entities, dict):
        logger.warning("entities is not a dict, type=%s, defaulting to {}", type(raw_entities).__name__)

    logger.info(
        "log_interaction_node: user_text=%.80s, current_state keys=%s, _stage=%s",
        text,
        list(current_state.keys()),
        current_state.get("_stage"),
    )

    try:
        result = log_interaction_tool.invoke({
            "conversation_text": text,
            "user_id": state.get("user_id"),
            "current_state": current_state,
        })
    except Exception as e:
        logger.error("log_interaction_tool.invoke failed: %s", str(e), exc_info=True)
        state["response"] = f"Sorry, I encountered an error. Please try again. ({str(e)})"
        state["tool_used"] = "log_interaction"
        state["entities"] = current_state
        return state

    if not isinstance(result, dict):
        logger.error("log_interaction_tool returned non-dict: %s", type(result).__name__)
        state["response"] = "Sorry, I encountered an unexpected error. Please try again."
        state["tool_used"] = "log_interaction"
        state["entities"] = current_state
        return state

    state["database_result"] = result
    state["tool_used"] = "log_interaction"

    merged = result.get("merged_state")
    if not isinstance(merged, dict):
        logger.error("merged_state from tool is not a dict, type=%s", type(merged).__name__)
        merged = {}
    state["entities"] = merged

    if result.get("success") == "partial":
        state["response"] = result.get("response_text", "")
    elif result.get("success") is True and merged.get("_stage") == "complete":
        state["response"] = result.get("response_text", "✅ Interaction Logged Successfully")
        state["entities"] = {}
    elif result.get("success") is False:
        state["response"] = f"Failed to log interaction: {result.get('error', 'Unknown error')}"
        state["entities"] = merged
    else:
        state["response"] = "I couldn't process that request. Please try again."

    return state


# ─── EDIT INTERACTION ────────────────────────────────────────────────────────

def edit_interaction_node(state: AgentState) -> AgentState:
    messages = state.get("conversation", [])
    text = messages[-1]["content"] if messages else ""
    entities = state.get("entities", {})
    if not isinstance(entities, dict):
        entities = {}

    # Build conversation context for the tool (last 10 messages)
    recent_messages = messages[-10:] if isinstance(messages, list) else []

    # Pass interaction_id from entities (for edit context persistence)
    interaction_id = state.get("interaction", {}).get("id", 0)
    if not interaction_id:
        interaction_id = entities.get("_edit_interaction_id", 0)

    logger.info(
        "edit_interaction_node: text=%.80s, interaction_id=%s, user_id=%s, entities_keys=%s",
        text, interaction_id, state.get("user_id"), list(entities.keys()),
    )

    try:
        result = edit_interaction_tool.invoke({
            "edit_request": text,
            "interaction_id": interaction_id,
            "user_id": state.get("user_id"),
            "edit_context": entities,
            "conversation_history": recent_messages,
        })
    except Exception as e:
        logger.error("edit_interaction_tool.invoke failed: %s", str(e), exc_info=True)
        state["response"] = "Sorry, I encountered an error editing the interaction. Please try again."
        state["tool_used"] = "edit_interaction"
        return state

    state["database_result"] = result
    state["tool_used"] = "edit_interaction"

    # Handle "awaiting_fields" — user expressed edit intent but didn't specify what
    if result.get("success") == "awaiting_fields":
        interaction_id_result = result.get("interaction_id", 0)
        new_entities = dict(entities)
        new_entities["_edit_interaction_id"] = interaction_id_result
        state["entities"] = new_entities
        state["response"] = result.get("response_text", "What would you like to change?")
        return state

    if result.get("success"):
        updates = result.get("updates", {})
        updated_fields = result.get("updated_fields", [])
        interaction_id_result = result.get("interaction_id", 0)

        # Persist interaction_id in entities for subsequent edits
        new_entities = dict(entities)
        new_entities["_edit_interaction_id"] = interaction_id_result
        state["entities"] = new_entities

        # Build professional confirmation
        field_lines = "\n".join([f"  {name}: {val}" for name, val in updates.items()])
        state["response"] = (
            f"Updated Fields:\n{field_lines}\n\n"
            f"The interaction has been updated successfully."
        )
    else:
        state["response"] = f"Could not update the interaction. {result.get('error', 'Record not found.')}"

    return state


# ─── SUMMARIZE ───────────────────────────────────────────────────────────────

def summarize_node(state: AgentState) -> AgentState:
    messages = state.get("conversation", [])
    text = messages[-1]["content"] if messages else ""

    try:
        result = summarize_tool.invoke({
            "query_text": text,
            "user_id": state.get("user_id"),
        })
    except Exception as e:
        logger.error("summarize_tool.invoke failed: %s", str(e), exc_info=True)
        state["response"] = "Sorry, I encountered an error generating the summary. Please try again."
        state["tool_used"] = "summarize"
        return state
    state["summary"] = result.get("summary")
    state["tool_used"] = "summarize"
    state["response"] = result.get("summary", "No interaction found.")
    return state


# ─── FOLLOW-UP ────────────────────────────────────────────────────────────────

def followup_node(state: AgentState) -> AgentState:
    messages = state.get("conversation", [])
    text = ""
    if messages and isinstance(messages, list) and len(messages) > 0:
        last = messages[-1]
        if isinstance(last, dict):
            text = last.get("content", "")

    try:
        result = followup_tool.invoke({
            "query_text": text,
            "user_id": state.get("user_id"),
        })
    except Exception as e:
        logger.error("followup_tool.invoke failed: %s", str(e), exc_info=True)
        state["response"] = "Sorry, I encountered an error generating follow-up recommendations. Please try again."
        state["tool_used"] = "followup"
        return state
    state["database_result"] = result
    state["tool_used"] = "followup"

    if result.get("error"):
        state["response"] = result["error"]
        return state

    if not result.get("found_in_db", True):
        state["response"] = result.get("reasoning", "No interactions were found matching your request.")
        return state

    if result.get("recommendation_type") == "multiple" or result.get("count", 0) > 1:
        state["response"] = _format_multi_recommendation(result)
    else:
        state["response"] = _format_single_recommendation(result)
    return state


def _format_single_recommendation(result: Dict) -> str:
    """Format a single follow-up recommendation into readable text."""
    lines = []
    lines.append("Follow-up Recommendation")
    lines.append("")

    doctor = result.get("doctor_name", "Unknown")
    lines.append("Doctor")
    lines.append(doctor)
    lines.append("")

    hospital = result.get("hospital", "")
    if hospital:
        lines.append("Hospital")
        lines.append(hospital)
        lines.append("")

    priority = result.get("priority", "N/A")
    lines.append("Priority")
    lines.append(priority)
    lines.append("")

    followup_date = result.get("next_follow_up", "N/A")
    lines.append("Next Follow-up Date")
    lines.append(followup_date)
    lines.append("")

    reasoning = result.get("reasoning")
    if reasoning:
        lines.append("Reasoning")
        lines.append(reasoning)
        lines.append("")

    tp = result.get("talking_points", [])
    if tp:
        lines.append("Talking Points")
        for t in tp:
            lines.append(f"  • {t}")
        lines.append("")

    sp = result.get("suggested_products", [])
    if sp:
        lines.append("Recommended Products")
        for p in sp:
            lines.append(f"  • {p}")
        lines.append("")

    ce = result.get("clinical_evidence", [])
    if ce:
        lines.append("Clinical Evidence")
        for c in ce:
            lines.append(f"  • {c}")
        lines.append("")

    agenda = result.get("next_visit_agenda", [])
    if agenda:
        lines.append("Next Visit Agenda")
        for a in agenda:
            lines.append(f"  • {a}")
        lines.append("")

    return "\n".join(lines)


def _format_multi_recommendation(result: Dict) -> str:
    """Format a multi follow-up recommendation into readable text."""
    lines = []
    lines.append("Follow-up Recommendations")
    lines.append("")

    summary = result.get("summary", "")
    if summary:
        lines.append("Overall Summary")
        lines.append(summary)
        lines.append("")

    high = result.get("high_priority", [])
    if high:
        lines.append("High Priority Doctors")
        for doc in high:
            lines.append(f"  • {doc.get('doctor_name', 'Unknown')} – {doc.get('hospital', '')} | Follow-up: {doc.get('next_follow_up', 'N/A')}")
            if doc.get("reasoning"):
                lines.append(f"    {doc['reasoning']}")
        lines.append("")

    medium = result.get("medium_priority", [])
    if medium:
        lines.append("Medium Priority Doctors")
        for doc in medium:
            lines.append(f"  • {doc.get('doctor_name', 'Unknown')} – {doc.get('hospital', '')} | Follow-up: {doc.get('next_follow_up', 'N/A')}")
            if doc.get("reasoning"):
                lines.append(f"    {doc['reasoning']}")
        lines.append("")

    low = result.get("low_priority", [])
    if low:
        lines.append("Low Priority Doctors")
        for doc in low:
            lines.append(f"  • {doc.get('doctor_name', 'Unknown')} – {doc.get('hospital', '')} | Follow-up: {doc.get('next_follow_up', 'N/A')}")
        lines.append("")

    schedule = result.get("recommended_schedule")
    if schedule:
        lines.append("Recommended Schedule")
        lines.append(schedule)
        lines.append("")

    upcoming = result.get("upcoming_followups", [])
    if upcoming:
        lines.append("Upcoming Follow-ups")
        for u in upcoming:
            lines.append(f"  • {u.get('doctor_name', 'Unknown')} – {u.get('follow_up_date', 'N/A')} ({u.get('priority', 'Medium')})")
        lines.append("")

    return "\n".join(lines)


# ─── ENTITY EXTRACTION ────────────────────────────────────────────────────────

def extract_entities_node(state: AgentState) -> AgentState:
    messages = state.get("conversation", [])
    text = messages[-1]["content"] if messages else ""
    try:
        result = entity_extraction_tool.invoke({"text": text})
    except Exception as e:
        logger.error("entity_extraction_tool.invoke failed: %s", str(e), exc_info=True)
        state["response"] = "Sorry, I encountered an error extracting entities. Please try again."
        state["tool_used"] = "entity_extraction"
        return state
    state["entities"] = result
    state["tool_used"] = "entity_extraction"

    lines = ["🔬 Medical Entity Extraction\n"]
    for key, val in result.items():
        if val:
            display = key.replace("_", " ").title()
            if isinstance(val, list):
                lines.append(f"• {display}: {', '.join(val)}")
            else:
                lines.append(f"• {display}: {val}")

    state["response"] = "\n".join(lines) if len(lines) > 1 else "No medical entities found in the provided text."
    return state


# ─── SENTIMENT ────────────────────────────────────────────────────────────────

def sentiment_node(state: AgentState) -> AgentState:
    messages = state.get("conversation", [])
    text = ""
    if messages and isinstance(messages, list) and len(messages) > 0:
        last = messages[-1]
        if isinstance(last, dict):
            text = last.get("content", "")
    try:
        result = sentiment_analysis_tool.invoke({"text": text})
    except Exception as e:
        logger.error("sentiment_analysis_tool.invoke failed: %s", str(e), exc_info=True)
        state["response"] = "Sorry, I encountered an error analyzing sentiment. Please try again."
        state["tool_used"] = "sentiment_analysis"
        return state
    state["database_result"] = result
    state["tool_used"] = "sentiment_analysis"

    lines = []
    lines.append("Sentiment Analysis")
    lines.append("")
    lines.append("Sentiment")
    lines.append(result.get("sentiment", "Neutral"))
    lines.append("")
    lines.append("Confidence")
    lines.append(str(result.get("confidence", "N/A")))
    lines.append("")
    lines.append("Interest Level")
    lines.append(result.get("interest_level", "N/A"))
    lines.append("")
    lines.append("Engagement Score")
    lines.append(str(result.get("engagement_score", "N/A")))
    phrases = result.get("key_phrases", [])
    if phrases:
        lines.append("")
        lines.append("Key Phrases")
        for p in phrases:
            lines.append(f"  • {p}")
    state["response"] = "\n".join(lines)
    return state


# ─── CLASSIFY ────────────────────────────────────────────────────────────────

def classify_node(state: AgentState) -> AgentState:
    messages = state.get("conversation", [])
    text = ""
    if messages and isinstance(messages, list) and len(messages) > 0:
        last = messages[-1]
        if isinstance(last, dict):
            text = last.get("content", "")
    try:
        result = meeting_classifier_tool.invoke({"text": text})
    except Exception as e:
        logger.error("meeting_classifier_tool.invoke failed: %s", str(e), exc_info=True)
        state["response"] = "Sorry, I encountered an error classifying the meeting. Please try again."
        state["tool_used"] = "meeting_classifier"
        return state
    state["database_result"] = result
    state["tool_used"] = "meeting_classifier"

    lines = []
    lines.append("Meeting Classification")
    lines.append("")
    lines.append("Meeting Type")
    lines.append(result.get("meeting_type", "N/A"))
    lines.append("")
    lines.append("Effectiveness")
    lines.append(result.get("effectiveness", "N/A"))
    lines.append("")
    lines.append("Next Action")
    lines.append(result.get("next_action", "N/A"))
    topics = result.get("key_topics", [])
    if topics:
        lines.append("")
        lines.append("Key Topics")
        for t in topics:
            lines.append(f"  • {t}")
    recommendations = result.get("recommendations", [])
    if recommendations:
        lines.append("")
        lines.append("Recommendations")
        for r in recommendations:
            lines.append(f"  • {r}")
    state["response"] = "\n".join(lines)
    return state


# ─── SEARCH ───────────────────────────────────────────────────────────────────

def search_node(state: AgentState) -> AgentState:
    messages = state.get("conversation", [])
    text = messages[-1]["content"] if messages else ""
    try:
        result = search_interactions_tool.invoke({
            "query_text": text,
            "user_id": state.get("user_id"),
        })
    except Exception as e:
        logger.error("search_interactions_tool.invoke failed: %s", str(e), exc_info=True)
        state["response"] = "Sorry, I encountered an error searching interactions. Please try again."
        state["tool_used"] = "search_interactions"
        return state
    state["database_result"] = result
    state["tool_used"] = "search_interactions"

    if not result.get("found"):
        state["response"] = result.get("message", "No matching interactions found.")
        return state

    lines = [f"🔍 Search Results ({result['count']} found)\n"]
    for i, r in enumerate(result.get("results", []), 1):
        lines.append(
            f"{i}. {r['doctor_name']} – {r['hospital']}\n"
            f"   Date: {r['interaction_date']} | Type: {r['interaction_type']}\n"
            f"   Products: {r['products']} | Interest: {r['interest_level']}"
        )
    state["response"] = "\n".join(lines)
    return state


# ─── HISTORY ─────────────────────────────────────────────────────────────────

def history_node(state: AgentState) -> AgentState:
    messages = state.get("conversation", [])
    text = messages[-1]["content"] if messages else ""
    try:
        result = show_history_tool.invoke({
            "query_text": text,
            "user_id": state.get("user_id"),
        })
    except Exception as e:
        logger.error("show_history_tool.invoke failed: %s", str(e), exc_info=True)
        state["response"] = "Sorry, I encountered an error retrieving history. Please try again."
        state["tool_used"] = "show_history"
        return state
    state["database_result"] = result
    state["tool_used"] = "show_history"

    if not result.get("found"):
        state["response"] = result.get("message", "No interactions found in your CRM.")
        return state

    lines = [f"📅 Interaction History ({result['count']} records)\n"]
    for i, r in enumerate(result.get("results", []), 1):
        fu = f" | Follow-up: {r['follow_up_date']}" if r.get("follow_up_date") else ""
        lines.append(
            f"{i}. {r['doctor_name']} – {r['hospital']}\n"
            f"   Date: {r['interaction_date']} | Type: {r['interaction_type']}\n"
            f"   Products: {r['products']} | Interest: {r['interest_level']}{fu}"
        )
    state["response"] = "\n".join(lines)
    return state


# ─── DELETE INTERACTION ───────────────────────────────────────────────────────

def delete_node(state: AgentState) -> AgentState:
    messages = state.get("conversation", [])
    text = messages[-1]["content"] if messages else ""
    try:
        result = delete_interaction_tool.invoke({
            "query_text": text,
            "user_id": state.get("user_id"),
            "confirmed": False,
        })
    except Exception as e:
        logger.error("delete_interaction_tool.invoke failed: %s", str(e), exc_info=True)
        state["response"] = "Sorry, I encountered an error deleting the interaction. Please try again."
        state["tool_used"] = "delete_interaction"
        return state
    state["database_result"] = result
    state["tool_used"] = "delete_interaction"

    if result.get("needs_confirmation"):
        state["pending_deletion"] = result
    state["response"] = result.get("message", "Interaction not found.")
    return state


def confirm_delete_node(state: AgentState) -> AgentState:
    pending = state.get("pending_deletion", {})
    user_id = state.get("user_id")
    try:
        result = delete_interaction_tool.invoke({
            "query_text": pending.get("doctor_name", ""),
            "user_id": user_id,
            "confirmed": True,
        })
    except Exception as e:
        logger.error("delete_interaction_tool.invoke (confirm) failed: %s", str(e), exc_info=True)
        state["response"] = "Sorry, I encountered an error deleting the interaction. Please try again."
        state["tool_used"] = "delete_interaction"
        return state
    state["database_result"] = result
    state["tool_used"] = "delete_interaction"
    state["pending_deletion"] = None
    state["response"] = result.get("message", "Interaction deleted.")
    return state


def cancel_delete_node(state: AgentState) -> AgentState:
    state["pending_deletion"] = None
    state["tool_used"] = "delete_interaction"
    state["response"] = "Deletion cancelled. The interaction has not been modified."
    return state


# ─── DASHBOARD ────────────────────────────────────────────────────────────────

def dashboard_node(state: AgentState) -> AgentState:
    messages = state.get("conversation", [])
    text = messages[-1]["content"] if messages else ""
    try:
        result = dashboard_assistant_tool.invoke({
            "question": text,
            "user_id": state.get("user_id"),
        })
    except Exception as e:
        logger.error("dashboard_assistant_tool.invoke failed: %s", str(e), exc_info=True)
        state["response"] = "Sorry, I encountered an error retrieving dashboard data. Please try again."
        state["tool_used"] = "dashboard_query"
        return state
    state["database_result"] = result
    state["tool_used"] = "dashboard_query"
    state["response"] = result.get("answer", "Could not retrieve dashboard data.")
    return state


# ─── GENERAL ─────────────────────────────────────────────────────────────────

def general_node(state: AgentState) -> AgentState:
    messages = state.get("conversation", [])
    text = messages[-1]["content"] if messages else ""

    if _is_greeting(text):
        state["response"] = (
            "Hello! I'm your AI Sales Assistant.\n\n"
            "I can help you:\n"
            "• Log HCP Interactions\n"
            "• Edit Interactions\n"
            "• Search & View History\n"
            "• Get Dashboard Insights\n"
            "• Summarize Meetings\n"
            "• Recommend Follow-ups\n\n"
            "How can I assist you today?"
        )
        state["tool_used"] = "general"
        return state

    try:
        response = llm.invoke(f"{SYSTEM_PROMPT}\n\nUser: {text}\n\nRespond helpfully and professionally as a CRM assistant.")
        state["response"] = response.content
    except Exception:
        state["response"] = "I encountered a temporary issue. Please try again."
    state["tool_used"] = "general"
    return state


# ─── BUILD GRAPH ──────────────────────────────────────────────────────────────

def build_agent() -> StateGraph:
    workflow = StateGraph(AgentState)

    workflow.add_node("detect_intent", detect_intent)
    workflow.add_node("log_interaction_node", log_interaction_node)
    workflow.add_node("edit_interaction_node", edit_interaction_node)
    workflow.add_node("summarize_node", summarize_node)
    workflow.add_node("followup_node", followup_node)
    workflow.add_node("extract_entities_node", extract_entities_node)
    workflow.add_node("sentiment_node", sentiment_node)
    workflow.add_node("classify_node", classify_node)
    workflow.add_node("search_node", search_node)
    workflow.add_node("history_node", history_node)
    workflow.add_node("delete_node", delete_node)
    workflow.add_node("confirm_delete_node", confirm_delete_node)
    workflow.add_node("cancel_delete_node", cancel_delete_node)
    workflow.add_node("dashboard_node", dashboard_node)
    workflow.add_node("general_node", general_node)

    workflow.set_entry_point("detect_intent")
    workflow.add_conditional_edges("detect_intent", route_intent)

    for node in [
        "log_interaction_node", "edit_interaction_node", "summarize_node",
        "followup_node", "extract_entities_node", "sentiment_node", "classify_node",
        "search_node", "history_node", "delete_node", "confirm_delete_node",
        "cancel_delete_node", "dashboard_node", "general_node",
    ]:
        workflow.add_edge(node, END)

    return workflow.compile()


agent_app = build_agent()
