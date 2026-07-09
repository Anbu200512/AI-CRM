import json
import time
from typing import Any, Dict
from langchain_groq import ChatGroq
from langchain_core.tools import tool
from app.config.settings import settings
from app.database.connection import SessionLocal
from app.models.ai_log import AILog

llm = ChatGroq(api_key=settings.GROQ_API_KEY, model="llama-3.1-8b-instant")


@tool
def meeting_classifier_tool(text: str) -> Dict[str, Any]:
    """Classify the type and quality of an HCP meeting."""
    start = time.time()
    prompt = f"""Classify this HCP meeting interaction.
Return JSON with:
- meeting_type: Initial Visit/Follow-up/Product Launch/Clinical Discussion/Routine Check
- effectiveness: Effective/Moderate/Ineffective
- next_action: Sample Drop/Prescription Request/Clinical Data Share/Follow-up Visit/No Action
- key_topics: list of key topics discussed
- recommendations: list of recommendations

Text: {text}"""
    response = llm.invoke(prompt)
    elapsed = time.time() - start

    result = {}
    try:
        cleaned = response.content.strip().strip("```json").strip("```").strip()
        result = json.loads(cleaned)
    except:
        result = {"meeting_type": "Unknown", "effectiveness": "Moderate", "next_action": "Follow-up Visit", "key_topics": [], "recommendations": []}

    db = SessionLocal()
    try:
        log = AILog(prompt=text[:500], response=json.dumps(result), tool="meeting_classifier", execution_time=elapsed)
        db.add(log)
        db.commit()
    finally:
        db.close()

    return result
