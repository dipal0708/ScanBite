"""
The AI agent layer. It NEVER decides diet-fit or scores itself — those are
deterministic (see services/diet_rules.py, services/scoring.py). It is
given the already-structured results and turns them into a friendly,
personalized explanation, plus 2-3 concrete suggestions.

Keeping the split this way avoids the main failure mode you don't want in
a health app: an LLM silently mis-classifying or missing a health-relevant
ingredient. The LLM's job is empathetic, accurate communication of facts
that were already computed deterministically.
"""

import os
import json
from anthropic import Anthropic

client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

SYSTEM_PROMPT = """You are the in-app guide for LabelWise, a food-label scanning app.
You explain already-computed ingredient and nutrition analysis to the user in a warm,
plain-language, non-alarmist way. You are not a doctor: never diagnose, never give
medical advice beyond "consider talking to a doctor or dietitian" for flagged health
conditions. Keep responses concise, specific to the ingredients/flags given, and end
with 2-3 concrete, practical suggestions. Never invent ingredients or numbers that
weren't provided to you."""


def explain_scan(structured_result: dict) -> dict:
    user_content = f"""Here is the structured analysis of a scanned food label. Explain it to the
user and give suggestions.

Diet fit: {json.dumps(structured_result.get('diet_fit'))}
Allergen flags: {json.dumps(structured_result.get('allergen_flags'))}
Scores: {json.dumps(structured_result.get('scores'))}
Classified ingredients: {json.dumps(structured_result.get('classified_ingredients'))}
User health flags: {json.dumps(structured_result.get('health_flags'))}

Respond with JSON only, in this shape:
{{"summary": "...", "suggestions": ["...", "...", "..."]}}"""

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=600,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_content}],
    )

    text = "".join(block.text for block in response.content if block.type == "text")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"summary": text, "suggestions": []}


def answer_followup(scan_result: dict, question: str) -> dict:
    user_content = f"""Scan result context: {json.dumps(scan_result)}

The user is asking a follow-up question about this specific scanned product:
"{question}"

Answer directly and concisely, grounded only in the context above."""

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=400,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_content}],
    )
    text = "".join(block.text for block in response.content if block.type == "text")
    return {"answer": text}
