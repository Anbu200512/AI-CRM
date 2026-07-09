import json
import re
from typing import Literal, Optional
from langgraph.graph import StateGraph, END
from langchain_groq import ChatGroq
from app.config.settings import settings
from app.langgraph.state import AgentState
from app.langgraph.prompts.system_prompts import (
    SYSTEM_PROMPT, INTENT_DETECTION_PROMPT, DOCTOR_NAME_EXTRACT_PROMPT
)
from app.langgraph.tools.log_interaction import log_interaction_tool
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
    return "\n".join([f"{m['role'].upper()}: {m['content']}" for m in messages[-10:]])


def detect_intent(state: AgentState) -> AgentState:
    messages = state.get("conversation", [])
    last_message = messages[-1]["content"] if messages else ""

    # Check if there's a pending deletion and user is confirming/cancelling
    pending = state.get("pending_deletion")
    if pending and pending.get("needs_confirmation"):
        lower = last_message.strip().lower()
        if any(w in lower for w in CONFIRM_WORDS):
            state["intent"] = "confirm_delete"
        elif any(w in lower for w in CANCEL_WORDS):
            state["intent"] = "cancel_delete"
        else:
            state["intent"] = "delete_interaction"
        return state

    response = llm.invoke(f"{INTENT_DETECTION_PROMPT}\n\nMessage: {last_message}")
    intent = response.content.strip().lower()
    state["intent"] = intent
    return state


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
    # Use last user message for extraction, but pass entire state for merging
    text = messages[-1]["content"] if messages else ""
    current_state = state.get("entities", {})

    result = log_interaction_tool.invoke({
        "conversation_text": text,
        "user_id": state.get("user_id"),
        "current_state": current_state,
    })

    state["database_result"] = result
    state["tool_used"] = "log_interaction"

    if "merged_state" in result:
        state["entities"] = result["merged_state"]
    else:
        state["entities"] = {k: v for k, v in result.items() if k not in ("success", "interaction_id", "error")}

    if result.get("success") is False and "missing_fields" in result:
        state["response"] = result.get("response_text", "Please provide the missing information.")
    elif result.get("success"):
        doc = state["entities"].get("doctor_name", "")
        state["entities"] = {}  # Clear form state on success
        state["response"] = (
            f"✅ Interaction Logged Successfully\n\n"
            f"Doctor: {doc}\n"
            f"The interaction has been saved to your CRM. You can view it in Interaction History."
        )
    else:
        state["response"] = f"Failed to log interaction: {result.get('error', 'Unknown error')}"

    return state


# ─── EDIT INTERACTION ────────────────────────────────────────────────────────

def edit_interaction_node(state: AgentState) -> AgentState:
    messages = state.get("conversation", [])
    text = messages[-1]["content"] if messages else ""
    result = edit_interaction_tool.invoke({
        "edit_request": text,
        "interaction_id": state.get("interaction", {}).get("id", 0),
        "user_id": state.get("user_id"),
    })
    state["database_result"] = result
    state["tool_used"] = "edit_interaction"

    if result.get("success"):
        updates = result.get("updates", {})
        field_lines = "\n".join([f"  • {k.replace('_', ' ').title()}: {v}" for k, v in updates.items()])
        state["response"] = (
            f"✅ Interaction Updated Successfully\n\n"
            f"📋 Changes Made:\n{field_lines}"
        )
    else:
        state["response"] = f"Could not update the interaction. {result.get('error', 'Record not found.')}"

    return state


# ─── SUMMARIZE ───────────────────────────────────────────────────────────────

def summarize_node(state: AgentState) -> AgentState:
    messages = state.get("conversation", [])
    text = messages[-1]["content"] if messages else ""
    doctor_name = _extract_doctor_name(text)

    result = summarize_tool.invoke({
        "text": text,
        "user_id": state.get("user_id"),
        "doctor_name": doctor_name,
    })
    state["summary"] = result.get("summary")
    state["tool_used"] = "summarize"

    if result.get("found_in_db"):
        state["response"] = (
            f"📋 Meeting Summary\n\n"
            f"Doctor: {result.get('doctor_name', '')}\n"
            f"Hospital: {result.get('hospital', '')}\n"
            f"Date: {result.get('interaction_date', '')}\n\n"
            f"{result.get('summary', '')}"
        )
    else:
        state["response"] = result.get("summary", "No interaction found.")

    return state


# ─── FOLLOW-UP ────────────────────────────────────────────────────────────────

def followup_node(state: AgentState) -> AgentState:
    messages = state.get("conversation", [])
    text = messages[-1]["content"] if messages else ""
    doctor_name = _extract_doctor_name(text)

    result = followup_tool.invoke({
        "interaction_summary": text,
        "user_id": state.get("user_id"),
        "doctor_name": doctor_name,
    })
    state["database_result"] = result
    state["tool_used"] = "followup"

    if not result.get("found_in_db", True):
        state["response"] = result.get("reasoning", "No previous interaction found.")
        return state

    tp = result.get("talking_points", [])
    sp = result.get("suggested_products", [])
    ce = result.get("clinical_evidence", [])
    agenda = result.get("next_visit_agenda", [])

    response_parts = [f"🎯 Follow-up Recommendation\n"]
    response_parts.append(f"Next Follow-up: {result.get('next_follow_up', 'N/A')}")
    response_parts.append(f"Priority: {result.get('priority', 'N/A')}")
    if tp:
        response_parts.append("\n📌 Talking Points:\n" + "\n".join([f"• {t}" for t in tp]))
    if sp:
        response_parts.append("\n💊 Suggested Products:\n" + "\n".join([f"• {p}" for p in sp]))
    if ce:
        response_parts.append("\n🔬 Clinical Evidence:\n" + "\n".join([f"• {c}" for c in ce]))
    if agenda:
        response_parts.append("\n📅 Next Visit Agenda:\n" + "\n".join([f"• {a}" for a in agenda]))
    if result.get("reasoning"):
        response_parts.append(f"\n💡 {result.get('reasoning')}")

    state["response"] = "\n".join(response_parts)
    return state


# ─── ENTITY EXTRACTION ────────────────────────────────────────────────────────

def extract_entities_node(state: AgentState) -> AgentState:
    messages = state.get("conversation", [])
    text = messages[-1]["content"] if messages else ""
    result = entity_extraction_tool.invoke({"text": text})
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
    text = messages[-1]["content"] if messages else ""
    result = sentiment_analysis_tool.invoke({"text": text})
    state["database_result"] = result
    state["tool_used"] = "sentiment_analysis"
    state["response"] = json.dumps(result, indent=2)
    return state


# ─── CLASSIFY ────────────────────────────────────────────────────────────────

def classify_node(state: AgentState) -> AgentState:
    messages = state.get("conversation", [])
    text = messages[-1]["content"] if messages else ""
    result = meeting_classifier_tool.invoke({"text": text})
    state["database_result"] = result
    state["tool_used"] = "meeting_classifier"
    state["response"] = json.dumps(result, indent=2)
    return state


# ─── SEARCH ───────────────────────────────────────────────────────────────────

def search_node(state: AgentState) -> AgentState:
    messages = state.get("conversation", [])
    text = messages[-1]["content"] if messages else ""
    result = search_interactions_tool.invoke({
        "query_text": text,
        "user_id": state.get("user_id"),
    })
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
    result = show_history_tool.invoke({
        "query_text": text,
        "user_id": state.get("user_id"),
    })
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
    result = delete_interaction_tool.invoke({
        "query_text": text,
        "user_id": state.get("user_id"),
        "confirmed": False,
    })
    state["database_result"] = result
    state["tool_used"] = "delete_interaction"

    if result.get("needs_confirmation"):
        state["pending_deletion"] = result
    state["response"] = result.get("message", "Interaction not found.")
    return state


def confirm_delete_node(state: AgentState) -> AgentState:
    pending = state.get("pending_deletion", {})
    user_id = state.get("user_id")
    result = delete_interaction_tool.invoke({
        "query_text": pending.get("doctor_name", ""),
        "user_id": user_id,
        "confirmed": True,
    })
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
    result = dashboard_assistant_tool.invoke({
        "question": text,
        "user_id": state.get("user_id"),
    })
    state["database_result"] = result
    state["tool_used"] = "dashboard_query"
    state["response"] = result.get("answer", "Could not retrieve dashboard data.")
    return state


# ─── GENERAL ─────────────────────────────────────────────────────────────────

def general_node(state: AgentState) -> AgentState:
    messages = state.get("conversation", [])
    text = messages[-1]["content"] if messages else ""
    response = llm.invoke(f"{SYSTEM_PROMPT}\n\nUser: {text}\n\nRespond helpfully and professionally as a CRM assistant.")
    state["response"] = response.content
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
