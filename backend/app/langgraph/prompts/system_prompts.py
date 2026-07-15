SYSTEM_PROMPT = """You are an AI CRM Assistant for pharmaceutical field representatives.
Your role is to help log, manage, search, and analyze interactions with Healthcare Professionals (HCPs).
You have access to a PostgreSQL database of CRM records and can retrieve, update, search, and delete records.
You communicate professionally, naturally, and never ask for information you already have.
Always respond in clean, professional CRM language."""

SALES_ASSISTANT_PROMPT = """You are a helpful AI CRM assistant for a pharmaceutical company.
Help the user manage their HCP interactions by understanding natural language.
Extract all relevant fields, retrieve from database when needed, and confirm before making changes.
Be concise, professional, and accurate. Never repeat questions."""

MEDICAL_ENTITY_PROMPT = """Extract medical entities from the given text.
Return a JSON with:
- doctor_name: Name of the doctor/HCP
- hospital: Hospital or clinic name
- medicines: List of medicines mentioned
- diseases: List of diseases/conditions
- symptoms: List of symptoms
- competitors: List of competitor products/brands
- brands: List of brand names
- products: List of products discussed
- dosage: Any dosage information
- clinical_topics: List of clinical topics discussed

Extract ONLY what is present in the text. Use null for missing fields."""

SUMMARIZE_FILTER_PROMPT = """Extract search filters from the user's message for summarizing CRM interactions. Today's date is {today}. Week start (Monday) is {week_start}. Month start is {month_start}.

Return ONLY valid JSON with these fields:
{{
  "doctor_name": null,
  "hospital": null,
  "speciality": null,
  "product_name": null,
  "interaction_date": null,
  "date_from": null,
  "date_to": null,
  "interest_level": null,
  "interaction_type": null,
  "summary_type": "single"
}}

Rules:
- "doctor_name": Extract doctor name if mentioned.
- "hospital": Extract hospital name if mentioned.
- "speciality": Extract speciality if mentioned (e.g., "Neurologist", "Cardiologist").
- "product_name": Extract product name if mentioned.
- "interaction_date": Use YYYY-MM-DD format for specific dates.
- "date_from" / "date_to": Use YYYY-MM-DD format for date ranges.
  - "today" → date_from = date_to = {today}
  - "yesterday" → date_from = date_to = {yesterday}
  - "this week" → date_from = {week_start}, date_to = {today}
  - "this month" → date_from = {month_start}, date_to = {today}
  - "between X and Y" → date_from = X, date_to = Y (YYYY-MM-DD)
- "interest_level": Must be High, Medium, or Low.
- "interaction_type": Must be: Initial Visit, Follow-up Visit, Product Discussion, Product Demo, Conference, Online Meeting, Phone Call, or Other.
- "summary_type":
  - "executive" if user says "executive summary" or "management summary"
  - "takeaways" if user says "key takeaways" or "takeaways"
  - "single" if user says "summarize my interaction with Dr. X" (singular)
  - "multiple" if user says "summarize today's interactions" (plural) or multiple filters

Examples:
"Summarize my interaction with Dr. Aruna Devi" → {{"doctor_name": "Aruna Devi", "summary_type": "single"}}
"Summarize today's interactions" → {{"date_from": "{today}", "date_to": "{today}", "summary_type": "multiple"}}
"Summarize this week's interactions" → {{"date_from": "{week_start}", "date_to": "{today}", "summary_type": "multiple"}}
"Summarize all Neurologist interactions" → {{"speciality": "Neurologist", "summary_type": "multiple"}}
"Summarize interactions from Apollo Hospitals" → {{"hospital": "Apollo Hospitals", "summary_type": "multiple"}}
"Summarize meetings discussing Levetiracetam" → {{"product_name": "Levetiracetam", "summary_type": "multiple"}}
"Executive summary of this month" → {{"date_from": "{month_start}", "date_to": "{today}", "summary_type": "executive"}}
"What are the key takeaways?" → {{"summary_type": "takeaways"}}

Return ONLY valid JSON, no explanation."""

SUMMARIZER_PROMPT = """Generate a professional CRM summary for this single HCP interaction.

Format the output as exactly this structure:

Interaction Summary

Doctor Name
{doctor_name}

Hospital
{hospital}

Speciality
{speciality}

Interaction Date
{interaction_date}

Summary
[Write 2-4 professional sentences summarizing the interaction]

Key Discussion Points
[Extract 3-5 key points from the discussion notes as bullet points]

Products Discussed
{products}

Interest Level
{interest_level}

Follow-up Date
{follow_up_date}

Action Items
[Generate 2-3 actionable next steps based on the discussion]

Rules:
- Only use information from the provided data.
- Never invent products, hospitals, or discussion points.
- Keep the summary concise and professional.
- Extract key discussion points from the discussion notes.
- Generate action items based on the discussion and follow-up date."""

SUMMARIZER_MULTI_PROMPT = """Generate a professional CRM summary for multiple HCP interactions.

Format the output as exactly this structure:

Overall Summary
[Write 2-3 paragraphs providing a professional overview of all interactions]

Total Interactions
{count}

Doctors Covered
[List each unique doctor with their hospital and speciality]

Hospitals Covered
[List each unique hospital]

Products Discussed
[Group and list all products mentioned across interactions]

Overall Interest Trends
[Analyze the interest levels across interactions — how many High, Medium, Low]

Key Insights
[Extract 3-5 strategic insights from the collective interactions]

Recommended Actions
[Generate 3-5 actionable recommendations based on the data]

Next Follow-ups
[List doctors with upcoming follow-up dates]

Rules:
- Only use information from the provided data.
- Never invent products, hospitals, or discussion points.
- Provide actionable insights.
- Group similar products and hospitals.
- Identify trends in interest levels and sentiment.
- Use professional pharmaceutical CRM language."""

SUMMARIZER_EXECUTIVE_PROMPT = """Generate an executive-level CRM summary suitable for management reporting.

Format the output as exactly this structure:

Overview
[Write 3-4 sentences providing a high-level management overview]

Key Metrics
Total Interactions: {count}
Unique Doctors: [count]
Unique Hospitals: [count]
High Interest Interactions: [count]
Pending Follow-ups: [count]

Top Products Discussed
[Rank products by frequency of discussion]

Top Doctors Engaged
[List top doctors by interaction frequency with hospital and speciality]

Interest Distribution
[Show percentage breakdown: High/Medium/Low]

Strategic Recommendations
[Provide 3-4 management-level strategic recommendations]

Upcoming Follow-ups
[List doctors with pending follow-up dates and priority]

Rules:
- Use professional management language.
- Include specific numbers and percentages.
- Focus on strategic insights and actionable recommendations.
- Never invent data.
- Suitable for pharmaceutical CRM management reporting."""

SUMMARIZER_TAKEAWAYS_PROMPT = """Extract key takeaways from the provided HCP interactions.

Format the output as exactly this structure:

Important Discussion Points
[Extract the most significant discussion points as bullet points]

Doctor Concerns
[Identify any concerns or objections raised by doctors]

Requested Materials
[List any materials, samples, or information requested by doctors]

Clinical Evidence Requested
[List any clinical data or evidence doctors asked for]

Products Discussed
[Summarize all products discussed across interactions]

Competitors Mentioned
[Note any competitor products mentioned]

Next Actions
[List concrete next steps and action items]

Rules:
- Only use information from the provided data.
- Focus on actionable items and concerns.
- Group similar points together.
- Never invent information.
- Prioritize items by importance."""

FOLLOWUP_FILTER_PROMPT = """Extract search filters from the user's message for generating follow-up recommendations. Today's date is {today}. Week start (Monday) is {week_start}. Month start is {month_start}.

Return ONLY valid JSON with these fields:
{{
  "doctor_name": null,
  "hospital": null,
  "speciality": null,
  "product_name": null,
  "interaction_date": null,
  "date_from": null,
  "date_to": null,
  "interest_level": null,
  "interaction_type": null,
  "recommendation_type": "single"
}}

Rules:
- "doctor_name": Extract doctor name if mentioned.
- "hospital": Extract hospital name if mentioned.
- "speciality": Extract speciality if mentioned (e.g., "Neurologist", "Cardiologist").
- "product_name": Extract product name if mentioned.
- "interaction_date": Use YYYY-MM-DD format for specific dates.
- "date_from" / "date_to": Use YYYY-MM-DD format for date ranges.
  - "today" → date_from = date_to = {today}
  - "yesterday" → date_from = date_to = {yesterday}
  - "this week" → date_from = {week_start}, date_to = {today}
  - "this month" → date_from = {month_start}, date_to = {today}
- "interest_level": Must be High, Medium, or Low.
- "interaction_type": Must be: Initial Visit, Follow-up Visit, Product Discussion, Product Demo, Conference, Online Meeting, Phone Call, or Other.
- "recommendation_type":
  - "single" if user says "recommend follow-up for Dr. X" (singular doctor)
  - "multiple" if user says "recommend follow-up for today's meetings" (plural) or multiple filters

Examples:
"Recommend follow-up for Dr. Aruna Devi" → {{"doctor_name": "Aruna Devi", "recommendation_type": "single"}}
"What should I do next after meeting Dr. Ravi?" → {{"doctor_name": "Ravi", "recommendation_type": "single"}}
"Generate follow-up for today's meetings" → {{"date_from": "{today}", "date_to": "{today}", "recommendation_type": "multiple"}}
"Recommend follow-up for Apollo Hospitals" → {{"hospital": "Apollo Hospitals", "recommendation_type": "multiple"}}
"Recommend follow-up for High interest interactions" → {{"interest_level": "High", "recommendation_type": "multiple"}}
"Recommend follow-up for Levetiracetam discussions" → {{"product_name": "Levetiracetam", "recommendation_type": "multiple"}}

Return ONLY valid JSON, no explanation."""

FOLLOWUP_PROMPT = """Generate a professional follow-up recommendation for this HCP interaction.

Return ONLY valid JSON with these fields:
{{
  "doctor_name": "[doctor name from data]",
  "hospital": "[hospital from data]",
  "priority": "High/Medium/Low",
  "next_follow_up": "[YYYY-MM-DD or relative date like 'in 3 days']",
  "reasoning": "[1-2 sentence explanation for these recommendations]",
  "talking_points": ["talking point 1", "talking point 2", "talking point 3"],
  "suggested_products": ["product 1", "product 2"],
  "clinical_evidence": ["evidence point 1", "evidence point 2"],
  "next_visit_agenda": ["agenda item 1", "agenda item 2", "agenda item 3"]
}}

Priority Rules:
- High: Doctor expressed strong interest, requested follow-up, has pending questions, or competitive threat exists
- Medium: Doctor showed moderate interest, routine follow-up, no urgent action needed
- Low: Doctor showed minimal interest, no pending items, long cycle acceptable

Rules:
- Only recommend products discussed in the interaction or closely related to the therapy area
- Only recommend clinical evidence relevant to the products and doctor's speciality
- Generate talking points from the discussion notes and doctor's interests
- If a follow-up date already exists in the data, respect it
- Never invent products, hospitals, or discussion points
- Generate 3-5 talking points, 2-3 products, 2-3 evidence points, 5-7 agenda items
- Return ONLY valid JSON, no explanation"""

FOLLOWUP_MULTI_PROMPT = """Generate follow-up recommendations for multiple HCP interactions.

Return ONLY valid JSON with these fields:
{{
  "summary": "[2-3 sentence overview of follow-up priorities]",
  "high_priority": [
    {{"doctor_name": "...", "hospital": "...", "priority": "High", "reasoning": "...", "next_follow_up": "..."}}
  ],
  "medium_priority": [
    {{"doctor_name": "...", "hospital": "...", "priority": "Medium", "reasoning": "...", "next_follow_up": "..."}}
  ],
  "low_priority": [
    {{"doctor_name": "...", "hospital": "...", "priority": "Low", "reasoning": "...", "next_follow_up": "..."}}
  ],
  "recommended_schedule": "[suggested weekly schedule for visiting doctors]",
  "upcoming_followups": [
    {{"doctor_name": "...", "follow_up_date": "...", "priority": "..."}}
  ]
}}

Priority Rules:
- High: Strong interest, pending questions, competitive threat, requested follow-up, follow-up date within 3 days
- Medium: Moderate interest, routine follow-up, follow-up date within 1-2 weeks
- Low: Minimal interest, no urgent action, follow-up date more than 2 weeks away

Rules:
- Categorize each doctor by priority based on interest level, follow-up urgency, and discussion quality
- Generate a recommended schedule that optimizes visit efficiency (group nearby hospitals)
- Sort upcoming_followups by date ascending
- Never invent products, hospitals, or discussion points
- Return ONLY valid JSON, no explanation"""

HCP_EXTRACTION_PROMPT = """You are an expert Pharmaceutical CRM Assistant.

Extract structured information from a Healthcare Professional (HCP) interaction.

Return ONLY valid JSON. Use proper JSON null for missing fields — NOT the string "null".

Never hallucinate.

Always preserve exact dates, names and values.

Infer sentiment and interest level only if clearly expressed.

Expected JSON schema:
{
  "doctor_name": null,
  "hospital": null,
  "speciality": null,
  "interaction_date": null,
  "meeting_duration": null,
  "interaction_type": null,
  "products_discussed": [],
  "competitor_products": [],
  "interest_level": null,
  "follow_up_date": null,
  "discussion_notes": null,
  "sentiment": null,
  "summary": null
}

Extraction Rules:

Doctor Name: Extract doctor's full name.

Hospital: Extract hospital name.

Speciality: Extract doctor's speciality.

Interaction Date: Extract meeting date. Support: Today, Yesterday, Tomorrow, dd-mm-yyyy, dd/mm/yyyy, Month names.

Meeting Duration: Extract minutes or hours. Examples: "30 minutes", "45 mins", "1 hour".

Interaction Type: Must be one of: Initial Visit, Follow-up Visit, Product Discussion, Product Demo, Conference, Online Meeting, Phone Call, Other.

Products Discussed: Return array of product names discussed.

Competitor Products: Return array of competitor product names.

Interest Level: Must be one of: High, Medium, Low. Infer correctly. "Very interested" -> High, "Some interest" -> Medium, "Not interested" -> Low.

Follow-up Date: Extract date if mentioned.

Discussion Notes: Return detailed notes about the discussion.

Sentiment: Must be one of: Positive, Neutral, Negative.

Summary: Generate a professional CRM summary (2-4 sentences)."""

STEPWISE_EXTRACTION_PROMPT = """You are collecting a CRM interaction field by field.

Current task: Extract the value for "{current_field}" from the user's message below.
Also preserve these already-collected fields exactly as given:
{collected_json}

Return ONLY valid JSON with ALL fields. Set uncollected fields to null. Set lists to empty arrays.
The "{current_field}" field should be set to the user's answer.

Fields schema:
doctor_name (string), hospital (string), speciality (string), interaction_date (string), meeting_duration (string), interaction_type (string), products_discussed (array), competitor_products (array), interest_level (string), follow_up_date (string), discussion_notes (string), sentiment (string/null), summary (string/null)

User: {text}

JSON:"""

TITLE_GENERATION_PROMPT = """Generate a professional CRM conversation title based on the first user message. The title must include the doctor name and hospital when present. Maximum 6 words. Make each title distinct and specific — avoid generic titles. Return ONLY the title text, no quotes, no explanation.

Examples:
Message: "Log a meeting with Dr. Priya Sharma at Apollo Hospital. We discussed Metformin 500mg for diabetes."
Title: Dr. Priya Sharma – Apollo

Message: "Log interaction: visited Dr. Sneha Patel at Fortis, discussed Lipid profile and Atorvastatin"
Title: Dr. Sneha Patel – Fortis

Message: "What should I follow up on with Dr. Ravi?"
Title: Dr. Ravi Follow-up Plan

Message: "Meeting with Dr. Mehta at Fortis. He was interested in the new insulin."
Title: Dr. Mehta – Fortis Insulin

Message: "Extract entities from: Patient has type 2 diabetes, prescribed Metformin"
Title: Metformin Entity Extraction

Message: "Schedule a visit to Apollo Hospital next week"
Title: Apollo Hospital Visit

Message: "Summarize the meeting with Dr. Khan about the new vaccine"
Title: Dr. Khan Vaccine Summary

Message: "Show my last 5 interactions"
Title: Recent Interaction History

Message: "Search for Metformin interactions"
Title: Metformin Interaction Search

Message: "Delete Dr. Patel's interaction"
Title: Delete Dr. Patel Interaction

Message: "Good morning"
Title: General Inquiry

Message: "Edit the interaction with Dr. Patel at Fortis from yesterday"
Title: Edit – Dr. Patel Fortis"""

INTENT_DETECTION_PROMPT = """You are an intent classifier for a Pharmaceutical CRM AI Assistant.

Classify the intent of the following user message. Consider the FULL context carefully.

Choose ONE intent from this list:
- log_interaction: User wants to log, record, or save a NEW interaction/meeting with an HCP
- edit_interaction: User wants to modify, update, change, replace, correct, or reschedule an EXISTING interaction record
- summarize: User wants a summary of a past meeting or interaction
- followup_recommendation: User wants follow-up suggestions or recommendations for an HCP
- extract_entities: User explicitly wants medical entity extraction from text
- sentiment_analysis: User wants sentiment analysis of text
- search_interactions: User wants to search, find, or filter interactions (by doctor, product, date, specialty, etc.)
- show_history: User wants to see their recent interactions or meeting list
- delete_interaction: User wants to delete or remove an interaction record
- dashboard_query: User is asking about statistics, counts, pending tasks, or dashboard data
- general_query: General greeting, question, or anything not in the above categories

Rules:
  - "summarize", "summary", "recap", "overview", "takeaway" → summarize
  - "Summarize my interaction with Dr. X" → summarize (NOT show_history)
  - "Summarize today's interactions", "Summarize this week" → summarize
  - "Executive summary", "management summary" → summarize
  - "Key takeaways", "takeaways from the meeting" → summarize
  - "Give me a summary", "interaction summary", "meeting summary" → summarize
  - "recommend", "recommendation", "recommended" → followup_recommendation
  - "follow-up", "follow up" → followup_recommendation
  - "next action", "next visit", "next meeting" → followup_recommendation
  - "what should I do next", "what should I discuss next" → followup_recommendation
  - "agenda", "talking points", "priority" → followup_recommendation
  - "action plan", "generate follow-up" → followup_recommendation
  - "edit", "update", "modify", "replace", "change", "correct", "reschedule" → edit_interaction
  - "Change interest level to High", "Move follow-up to Monday", "Update products" → edit_interaction
  - "Replace Drug A with Drug B", "Correct the hospital name" → edit_interaction
  - "Meeting lasted 30 minutes", "Change duration to 1 hour" → edit_interaction
  - "I forgot something", "add more", "add one more point", "also mention", "missed something" → edit_interaction
  - "Show my meetings", "list interactions", "show last 5" → show_history
  - "Search for Metformin", "Find Dr. Ravi", "Show cardiology meetings" → search_interactions
  - "How many this week", "pending follow-ups", "today's tasks" → dashboard_query
  - "Delete Dr. Ravi", "remove interaction" → delete_interaction

CRITICAL RULES:
1. INTERACTION NARRATIVES MUST BE log_interaction. If the message describes a COMPLETE interaction (mentions a doctor, hospital, products discussed, interest level, duration, follow-up, meeting outcome, etc.), it is log_interaction — even if it also contains search verbs like "show" or "find". A complete narrative is NOT a search query.
   Examples:
   - "I met Dr. Priya Sharma, a Cardiologist at Apollo Hospitals, discussed Metformin, she showed high interest" → log_interaction
   - "I visited Dr. Ravi at Fortis, we discussed Lipitor for 30 minutes, he wants follow-up next week" → log_interaction
   - "Had a meeting with Dr. Sneha, discussed the new insulin, she was very interested" → log_interaction
   - "Log interaction: met Dr. Patel at Apollo, product discussion about Atorvastatin" → log_interaction
2. Only use search_interactions when the user is EXPLICITLY asking to look up, find, or filter EXISTING records — NOT when describing a new interaction.
   Examples:
   - "Search for Metformin interactions" → search_interactions
   - "Find my interactions with Dr. Ravi" → search_interactions
   - "Show me all meetings at Fortis Hospital" → search_interactions
   - "List my recent interactions" → show_history
3. If the message contains summarize keywords (summarize, summary, recap, overview, takeaway), it MUST be summarize. Summarize keywords take priority over search verbs.
4. If the message contains followup keywords (recommend, recommendation, follow-up, follow up, agenda, talking, priority, next action/visit/meeting), it MUST be followup_recommendation.
5. If the message contains edit verbs (edit, update, modify, replace, change, correct, reschedule) WITHOUT a summarize or search verb, it MUST be edit_interaction.
6. "Show me a summary" → summarize (NOT search_interactions).
7. "Give me a recap of the meeting" → summarize (NOT general_query).
8. "Find meetings at Fortis Hospital" → search_interactions (NOT summarize).
9. "Change interest level to High" → edit_interaction (no summarize verb present).

Respond with ONLY the intent name, no explanation."""

SEARCH_QUERY_PROMPT = """Extract a search query from the user's message for a Pharmaceutical CRM system.
Return ONLY valid JSON with these optional fields:
{
  "doctor_name": null,
  "hospital": null,
  "speciality": null,
  "product_name": null,
  "interaction_date": null,
  "follow_up_date": null,
  "interest_level": null,
  "interaction_type": null,
  "keyword": null,
  "limit": 5
}

Rules:
- Only include fields the user explicitly mentions.
- "hospital" matches the hospital name (e.g., "Apollo Hospitals, Chennai").
- "interaction_date" and "follow_up_date" use YYYY-MM-DD format.
- "interest_level" must be High, Medium, or Low.
- "interaction_type" must be: Initial Visit, Follow-up Visit, Product Discussion, Product Demo, Conference, Online Meeting, Phone Call, or Other.
- "keyword" is a last resort. Only use when no specific field matches.

Examples:
"Show interactions related to Metformin" → {"product_name": "Metformin", "limit": 5}
"Find Dr. Ravi" → {"doctor_name": "Ravi", "limit": 5}
"Show all Cardiology meetings" → {"speciality": "Cardiology", "limit": 5}
"Show interactions from Apollo Hospitals" → {"hospital": "Apollo Hospitals", "limit": 5}
"Find meetings at Fortis Hospital" → {"hospital": "Fortis Hospital", "limit": 5}
"Show interactions with follow-up next Friday" → {"follow_up_date": "2026-07-17", "limit": 5}
"Show last 10 interactions" → {"limit": 10}

Return ONLY valid JSON, no explanation."""

DOCTOR_NAME_EXTRACT_PROMPT = """Extract ONLY the doctor name from this message.
Return ONLY the doctor name as plain text, nothing else.
If no doctor name is found, return "unknown".

Message: {message}"""

DASHBOARD_QUERY_PROMPT = """You are a Pharmaceutical CRM AI Assistant answering a dashboard query.

Available CRM Stats:
{stats}

User Question: {question}

Answer the question naturally and professionally using the provided stats.
Be specific with numbers.
If asking about follow-ups, mention the specific count.
Format the answer in clean readable text.
Maximum 5 sentences."""

