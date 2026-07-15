import json
import logging
import traceback
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.models.user import User
from app.models.conversation import Conversation, Message
from app.schemas.chat import ChatMessage, ChatResponse, ExtractRequest, ExtractResponse, FollowUpRequest, FollowUpResponse
from app.langgraph.agent import agent_app
from app.langgraph.tools.entity_extraction import entity_extraction_tool
from app.langgraph.tools.followup import followup_tool
from app.langgraph.tools.summarize import summarize_tool
from app.langgraph.tools.edit_interaction import edit_interaction_tool
from app.langgraph.tools.sentiment import sentiment_analysis_tool
from app.langgraph.prompts.system_prompts import TITLE_GENERATION_PROMPT
from app.config.settings import settings
from langchain_groq import ChatGroq
from app.utils.auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/ai", tags=["AI"])

llm = ChatGroq(api_key=settings.GROQ_API_KEY, model="llama-3.1-8b-instant")


def generate_title(user_message: str) -> str:
    try:
        response = llm.invoke(f"{TITLE_GENERATION_PROMPT}\n\nMessage: {user_message}")
        title = response.content.strip().strip('"').strip("'")
        if len(title) > 100:
            title = title[:97] + "..."
        return title if title else "New Chat"
    except Exception:
        return "New Chat"


@router.post("/chat", response_model=ChatResponse)
def chat(data: ChatMessage, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    conv = None
    if data.conversation_id:
        conv = (
            db.query(Conversation)
            .filter(Conversation.id == data.conversation_id, Conversation.user_id == current_user.id)
            .first()
        )

    is_new = conv is None
    if is_new:
        conv = Conversation(
            id=str(uuid.uuid4()),
            user_id=current_user.id,
            title="New Chat",
        )
        db.add(conv)
        db.commit()
        db.refresh(conv)

    user_msg = Message(
        conversation_id=conv.id,
        role="user",
        content=data.message,
    )
    db.add(user_msg)
    db.commit()

    history = (
        db.query(Message)
        .filter(Message.conversation_id == conv.id)
        .order_by(Message.created_at)
        .all()
    )
    conversation_history = [{"role": m.role, "content": m.content} for m in history]

    parsed_entities = {}
    parsed_pending_deletion = None
    if conv.extracted_data:
        try:
            stored = json.loads(conv.extracted_data)
            if isinstance(stored, dict):
                if "entities" in stored:
                    raw = stored["entities"]
                    parsed_entities = raw if isinstance(raw, dict) else {}
                    if not isinstance(raw, dict):
                        logger.warning("stored entities is not a dict, type=%s, resetting", type(raw).__name__)
                else:
                    parsed_entities = stored
                parsed_pending_deletion = stored.get("pending_deletion")
            else:
                logger.warning("conv.extracted_data JSON is not a dict, type=%s, resetting", type(stored).__name__)
        except json.JSONDecodeError as e:
            logger.error("Failed to parse conv.extracted_data JSON: %s", e)
        except Exception as e:
            logger.error("Unexpected error restoring entities: %s", e)

    logger.info("Restored entities keys: %s", list(parsed_entities.keys()))

    initial_state = {
        "conversation": conversation_history,
        "doctor": None,
        "hospital": None,
        "entities": parsed_entities,
        "summary": None,
        "intent": None,
        "interaction": {},
        "database_result": {},
        "tool_used": None,
        "response": None,
        "user_id": current_user.id,
        "pending_deletion": parsed_pending_deletion,
    }
    try:
        result = agent_app.invoke(initial_state)
        ai_response = result.get("response", "I couldn't process that request.")
    except Exception as e:
        logger.error("Agent invoke failed: %s", str(e), exc_info=True)
        tb = traceback.format_exc()
        logger.error("Full traceback:\n%s", tb)
        ai_msg = Message(
            conversation_id=conv.id,
            role="assistant",
            content=f"Sorry, I encountered an error processing your request. Please try again. ({str(e)})",
        )
        db.add(ai_msg)
        db.commit()
        return ChatResponse(
            response=ai_msg.content,
            extracted={},
            tool_used="general",
            conversation_id=conv.id,
            title=conv.title,
        )

    ai_msg = Message(
        conversation_id=conv.id,
        role="assistant",
        content=ai_response,
    )
    db.add(ai_msg)

    if is_new or conv.title == "New Chat":
        generated = generate_title(data.message)
        conv.title = generated

    new_entities = result.get("entities")
    if not isinstance(new_entities, dict):
        logger.warning("result entities is not a dict, type=%s, defaulting to {}", type(new_entities).__name__)
        new_entities = {}
    new_pending = result.get("pending_deletion")
    tool_used = result.get("tool_used", "general")

    if tool_used == "log_interaction" and not new_entities:
        conv.extracted_data = None
    elif new_entities or new_pending:
        conv.extracted_data = json.dumps({"entities": new_entities, "pending_deletion": new_pending})
    elif tool_used in ("delete_interaction",) and not new_pending:
        conv.extracted_data = None

    db.commit()

    return ChatResponse(
        response=ai_response,
        extracted=result.get("entities", {}),
        tool_used=result.get("tool_used", "general"),
        conversation_id=conv.id,
        title=conv.title,
    )


@router.post("/extract", response_model=ExtractResponse)
def extract(data: ExtractRequest, current_user: User = Depends(get_current_user)):
    result = entity_extraction_tool.invoke({"text": data.text})
    return ExtractResponse(
        doctor_name=result.get("doctor_name"),
        hospital=result.get("hospital"),
        speciality=result.get("speciality"),
        interaction_date=result.get("interaction_date"),
        meeting_duration=result.get("meeting_duration"),
        interaction_type=result.get("interaction_type"),
        products_discussed=result.get("products_discussed"),
        competitor_products=result.get("competitor_products"),
        interest_level=result.get("interest_level"),
        follow_up_date=result.get("follow_up_date"),
        discussion_notes=result.get("discussion_notes"),
        sentiment=result.get("sentiment"),
        summary=result.get("summary"),
    )


@router.post("/summarize")
def summarize(data: ExtractRequest, current_user: User = Depends(get_current_user)):
    result = summarize_tool.invoke({"text": data.text})
    return result


@router.post("/followup", response_model=FollowUpResponse)
def followup(data: FollowUpRequest, current_user: User = Depends(get_current_user)):
    result = followup_tool.invoke({"interaction_summary": data.summary})
    return FollowUpResponse(
        next_follow_up=result.get("next_follow_up", "1 week"),
        priority=result.get("priority", "Medium"),
        talking_points=result.get("talking_points", []),
        suggested_products=result.get("suggested_products", []),
        reasoning=result.get("reasoning", ""),
    )


@router.post("/edit")
def edit(data: dict, current_user: User = Depends(get_current_user)):
    result = edit_interaction_tool.invoke({
        "edit_request": data.get("message", ""),
        "interaction_id": data.get("interaction_id", 0),
        "user_id": current_user.id,
        "edit_context": data.get("edit_context", {}),
        "conversation_history": data.get("conversation_history", []),
    })
    return result


@router.post("/entities")
def entities(data: ExtractRequest, current_user: User = Depends(get_current_user)):
    result = entity_extraction_tool.invoke({"text": data.text})
    return result


@router.post("/sentiment")
def sentiment(data: ExtractRequest, current_user: User = Depends(get_current_user)):
    result = sentiment_analysis_tool.invoke({"text": data.text})
    return result
