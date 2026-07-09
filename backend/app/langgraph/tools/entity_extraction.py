import json
import re
import time
from typing import Any, Dict
from langchain_groq import ChatGroq
from langchain_core.tools import tool
from app.config.settings import settings
from app.langgraph.prompts.system_prompts import HCP_EXTRACTION_PROMPT
from app.database.connection import SessionLocal
from app.models.ai_log import AILog

llm = ChatGroq(api_key=settings.GROQ_API_KEY, model="llama-3.1-8b-instant")


@tool
def entity_extraction_tool(text: str) -> Dict[str, Any]:
    """Extract structured HCP interaction fields from natural language text."""
    start = time.time()
    response = llm.invoke(f"{HCP_EXTRACTION_PROMPT}\n\nText: {text}")
    elapsed = time.time() - start

    result = {}
    try:
        cleaned = response.content.strip()
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
        cleaned = cleaned.strip()
        result = json.loads(cleaned)
    except:
        result = {"error": "Could not parse extraction", "raw": response.content}

    db = SessionLocal()
    try:
        log = AILog(prompt=text[:500], response=json.dumps(result), tool="entity_extraction", execution_time=elapsed)
        db.add(log)
        db.commit()
    finally:
        db.close()

    return result
