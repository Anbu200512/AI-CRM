import re
import sys
from typing import Dict, Optional

sys.path.insert(0, '.')

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


def _detect_explicit_action_intent(text: str) -> Optional[str]:
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


SUMMARIZE_PATTERNS = ["summarize", "summary", "recap", "overview", "takeaway"]
FOLLOWUP_PATTERNS = ["recommend", "recommendation", "recommended", "followup", "follow-up", "follow up", "agenda", "talking", "priority"]
FOLLOWUP_PHRASES = [r"next\s+(?:action|visit|meeting)", r"what\s+should\s+I\s+(?:do|discuss)\s+next", r"action\s+plan", r"(?:generate|give|provide|create)\s+(?:me\s+)?(?:a\s+)?(?:follow.?up|recommendation|suggestion|talking\s+points|clinical\s+evidence|visit\s+agenda)"]
EDIT_PATTERNS = ["edit", "update", "modify", "replace", "change", "correct", "reschedule"]
FORGOT_PATTERNS = ["forgot", "add more", "add one more", "missed something", "also want", "also need"]
SEARCH_PATTERNS = ["show", "search", "find", "list", "display", "get", "retrieve"]


def classify(msg):
    lower = msg.strip().lower()

    if not lower:
        return "general_query", {"reason": "empty message"}

    explicit = _detect_explicit_action_intent(msg)
    if explicit:
        return explicit, {"reason": "explicit action verb at message start"}

    narr = _detect_interaction_narrative(msg)
    if narr["is_narrative"]:
        return "log_interaction", narr

    if any(p in lower for p in FORGOT_PATTERNS):
        return "edit_interaction", {"reason": "forgot pattern"}

    if any(re.search(r'\b' + p + r'\b', lower) for p in EDIT_PATTERNS):
        return "edit_interaction", {"reason": "edit verb"}

    if any(re.search(r'\b' + p + r'\b', lower) for p in SEARCH_PATTERNS):
        return "search_interactions", {"reason": "search verb"}

    if any(re.search(r'\b' + p + r'\b', lower) for p in SUMMARIZE_PATTERNS):
        return "summarize", {"reason": "summarize keyword"}

    if any(re.search(r'\b' + p + r'\b', lower) for p in FOLLOWUP_PATTERNS) or \
       any(re.search(p, lower) for p in FOLLOWUP_PHRASES):
        return "followup_recommendation", {"reason": "followup keyword"}

    return "general_query", {"reason": "no match"}


test_cases = [
    # === REQUIRED EXAMPLES ===
    ("I met Dr. Priya Sharma, a Cardiologist at Apollo Hospitals, we discussed Metformin for diabetes", "log_interaction"),
    ("Add a new log I met Dr. Priya Sharma at Apollo Hospitals, discussed the new drug", "log_interaction"),
    ("I met Dr. Priya Sharma, she was interested in the product, add this as a log", "log_interaction"),
    ("Show interactions with Dr. Priya Sharma.", "search_interactions"),
    ("Summarize my interaction with Dr. Priya Sharma.", "summarize"),
    ("Recommend a follow-up for Dr. Priya Sharma.", "followup_recommendation"),
    ("Edit the interaction for Dr. Priya Sharma.", "edit_interaction"),

    # === FOLLOW-UP RECOMMENDATION (required examples) ===
    ("Generate a follow-up recommendation for Dr. Priya Sharma.", "followup_recommendation"),
    ("Recommend products for Dr. Priya Sharma.", "followup_recommendation"),
    ("Suggest talking points for Dr. Priya Sharma.", "followup_recommendation"),
    ("What should I do next after meeting Dr. Priya Sharma?", "followup_recommendation"),
    ("Generate a follow-up plan for Dr. Priya Sharma", "followup_recommendation"),
    ("Recommend next visit for Dr. Priya Sharma", "followup_recommendation"),
    ("Suggest clinical evidence for Dr. Priya Sharma", "followup_recommendation"),
    ("What is the recommended follow-up for Dr. Priya Sharma?", "followup_recommendation"),
    ("Generate recommended products for Dr. Priya Sharma", "followup_recommendation"),

    # === GIVE/PROVIDE follow-up requests ===
    ("give a follow-up recommendation for Dr. Priya Sharma.", "followup_recommendation"),
    ("Give me talking points for Dr. Khan", "followup_recommendation"),
    ("provide a follow-up recommendation for Dr. Priya Sharma", "followup_recommendation"),
    ("give me a recommendation for Dr. Ravi", "followup_recommendation"),
    ("give me clinical evidence for Dr. Mehta", "followup_recommendation"),

    # === LOG INTERACTION (must NOT catch follow-up requests) ===
    ("I met Dr. Priya Sharma yesterday...", "log_interaction"),
    ("I visited Dr. Ravi at Fortis Hospital, discussed Lipitor for 30 minutes, he wants follow-up next week", "log_interaction"),
    ("We discussed Cardiology products with Dr. Khan, he was very interested", "log_interaction"),
    ("Had a meeting with Dr. Sneha Patel, discussed the new insulin, she was enthusiastic", "log_interaction"),
    ("Log interaction: met Dr. Patel at Apollo, product discussion about Atorvastatin", "log_interaction"),
    ("Log my meeting with Dr. Mehta at Fortis", "log_interaction"),
    ("Record interaction with Dr. Shah, discussed diabetes medications", "log_interaction"),
    ("Save this meeting with Dr. Ravi as a log", "log_interaction"),
    ("Product discussion with Dr. Patel about Metformin, high interest", "log_interaction"),
    ("Add a new log I met Dr. Priya Sharma at Apollo Hospitals, discussed the new drug", "log_interaction"),
    ("I met Dr. Priya Sharma, she was interested in the product, add this as a log", "log_interaction"),

    # === EDIT INTERACTION ===
    ("Edit the interaction for Dr. Priya Sharma.", "edit_interaction"),
    ("update the interaction with Dr. Patel", "edit_interaction"),
    ("change interest level to High", "edit_interaction"),

    # === SUMMARIZE INTERACTION ===
    ("Summarize my interaction with Dr. Priya Sharma.", "summarize"),
    ("summarize my meeting with Dr. Patel", "summarize"),
    ("give me a summary of today's interactions", "summarize"),

    # === SEARCH INTERACTION ===
    ("Show interactions with Dr. Priya Sharma.", "search_interactions"),
    ("show me interactions with Dr. Priya", "search_interactions"),
    ("search for Metformin interactions", "search_interactions"),
    ("find Dr. Ravi", "search_interactions"),
    ("list all meetings at Fortis Hospital", "search_interactions"),
    ("show my recent interactions", "search_interactions"),

    # === FOLLOWUP edge cases ===
    ("what should I recommend for Dr. Ravi", "followup_recommendation"),
    ("suggest follow-up actions for Dr. Patel", "followup_recommendation"),
    ("What are the priority items for Dr. Mehta?", "followup_recommendation"),
]

passed = 0
failed = 0
print("=" * 100)
print("INTENT ROUTING TEST RESULTS")
print("=" * 100)

for msg, expected in test_cases:
    actual, info = classify(msg)
    status = "PASS" if actual == expected else "FAIL"
    if actual == expected:
        passed += 1
    else:
        failed += 1

    marker = "  OK" if status == "PASS" else "FAIL"
    print(f"  {marker} | {actual:25s} | expected: {expected:25s} | {msg[:60]}")

print("=" * 100)
print(f"Results: {passed} passed, {failed} failed out of {len(test_cases)}")
print("=" * 100)
