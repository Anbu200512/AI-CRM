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
def sentiment_analysis_tool(text: str) -> Dict[str, Any]:
    """Analyze the sentiment of an HCP interaction text."""
    start = time.time()
    prompt = f"""Analyze the sentiment of this HCP interaction text.
Return JSON with:
- sentiment: Positive/Neutral/Negative
- confidence: 0.0 to 1.0
- key_phrases: list of key phrases that indicate sentiment
- interest_level: High/Medium/Low
- engagement_score: 0 to 100

Text: {text}"""
    response = llm.invoke(prompt)
    elapsed = time.time() - start

    result = {}
    try:
        cleaned = response.content.strip().strip("```json").strip("```").strip()
        result = json.loads(cleaned)
    except:
        result = {"sentiment": "Neutral", "confidence": 0.5, "key_phrases": [], "interest_level": "Medium", "engagement_score": 50}

    db = SessionLocal()
    try:
        log = AILog(prompt=text[:500], response=json.dumps(result), tool="sentiment_analysis", execution_time=elapsed)
        db.add(log)
        db.commit()
    finally:
        db.close()

    return result
