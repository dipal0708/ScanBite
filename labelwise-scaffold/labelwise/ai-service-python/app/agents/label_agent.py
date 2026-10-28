"""
LLM agent for explaining deterministic label analysis.

Two interchangeable providers, selected with the LLM_PROVIDER env var:

  * "ollama" (default) — a local Ollama server, no API key needed.
  * "openai"           — any OpenAI-compatible chat-completions API
                        (OpenAI, Groq, OpenRouter, DeepSeek, ...),
                        keyed with OPENAI_API_KEY.

The model communicates results; diet-fit and scores remain rule-based.
"""

import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from fastapi import HTTPException

LLM_PROVIDER = (os.getenv("LLM_PROVIDER", "ollama") or "ollama").strip().lower()

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")

OPENAI_BASE_URL = (os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1") or "").rstrip("/")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

SYSTEM_PROMPT = """You are the in-app guide for LabelWise, a food-label scanning app.
You explain already-computed ingredient and nutrition analysis to the user in a warm,
plain-language, non-alarmist way. You are not a doctor: never diagnose, never give
medical advice beyond "consider talking to a doctor or dietitian" for flagged health
conditions. Keep responses concise, specific to the ingredients/flags given, and end
with 2-3 concrete, practical suggestions. Never invent ingredients or numbers that
weren't provided to you."""


def _chat(user_content: str, *, num_predict: int, json_mode: bool = False) -> str:
    """Dispatch to the configured provider (LLM_PROVIDER env var)."""
    if LLM_PROVIDER == "ollama":
        return _ollama_chat(user_content, num_predict=num_predict, json_mode=json_mode)
    if LLM_PROVIDER in ("openai", "openai_compatible"):
        return _openai_chat(user_content, num_predict=num_predict, json_mode=json_mode)
    raise HTTPException(
        status_code=503,
        detail=(
            f"Unknown LLM_PROVIDER '{LLM_PROVIDER}'. "
            "Set it to 'ollama' (local, default) or 'openai' (hosted, OpenAI-compatible)."
        ),
    )


def _ollama_chat(user_content: str, *, num_predict: int, json_mode: bool = False) -> str:
    body = {
        "model": OLLAMA_MODEL,
        "stream": False,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        "options": {"num_predict": num_predict, "temperature": 0.2},
    }
    if json_mode:
        body["format"] = "json"

    request = Request(
        f"{OLLAMA_BASE_URL}/api/chat",
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urlopen(request, timeout=120) as response:
            result = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        if exc.code == 404:
            detail = f"Ollama model '{OLLAMA_MODEL}' was not found. Pull it with: ollama pull {OLLAMA_MODEL}"
        else:
            detail = f"Ollama returned HTTP {exc.code}."
        raise HTTPException(status_code=503, detail=detail) from exc
    except (URLError, TimeoutError) as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Cannot reach Ollama at {OLLAMA_BASE_URL}. Start Ollama and try again.",
        ) from exc
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=502, detail="Ollama returned an invalid response.") from exc

    if not isinstance(result, dict):
        raise HTTPException(status_code=502, detail="Ollama returned an invalid response.")
    content = result.get("message", {}).get("content")
    if not isinstance(content, str) or not content.strip():
        raise HTTPException(status_code=502, detail="Ollama returned no message content.")
    return content.strip()


def _openai_chat(user_content: str, *, num_predict: int, json_mode: bool = False) -> str:
    if not OPENAI_API_KEY:
        raise HTTPException(
            status_code=503,
            detail="OPENAI_API_KEY is not set. Set it in .env, or switch LLM_PROVIDER back to 'ollama'.",
        )
    if not OPENAI_BASE_URL:
        raise HTTPException(
            status_code=503,
            detail="OPENAI_BASE_URL is empty. Set it (e.g. https://api.openai.com/v1) or use LLM_PROVIDER=ollama.",
        )

    body = {
        "model": OPENAI_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        "temperature": 0.2,
        "max_tokens": num_predict,
    }
    if json_mode:
        body["response_format"] = {"type": "json_object"}

    def send(payload: dict) -> dict:
        request = Request(
            f"{OPENAI_BASE_URL}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {OPENAI_API_KEY}",
            },
            method="POST",
        )
        with urlopen(request, timeout=120) as response:
            return json.loads(response.read().decode("utf-8"))

    try:
        try:
            result = send(body)
        except HTTPError as exc:
            # Not every OpenAI-compatible endpoint supports JSON mode;
            # retry once without response_format before giving up.
            if exc.code == 400 and "response_format" in body:
                result = send({k: v for k, v in body.items() if k != "response_format"})
            else:
                raise
    except HTTPError as exc:
        detail = {
            401: "The LLM provider rejected OPENAI_API_KEY (HTTP 401).",
            403: "The LLM provider denied access (HTTP 403). Check OPENAI_API_KEY / OPENAI_BASE_URL.",
            404: f"Model '{OPENAI_MODEL}' was not found at {OPENAI_BASE_URL} (HTTP 404). Check OPENAI_MODEL.",
            429: "The LLM provider rate-limited this request (HTTP 429). Try again shortly.",
        }.get(exc.code, f"The LLM provider returned HTTP {exc.code}.")
        raise HTTPException(status_code=503, detail=detail) from exc
    except (URLError, TimeoutError) as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Cannot reach the LLM provider at {OPENAI_BASE_URL}. Check OPENAI_BASE_URL.",
        ) from exc
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=502, detail="The LLM provider returned an invalid response.") from exc

    if not isinstance(result, dict):
        raise HTTPException(status_code=502, detail="The LLM provider returned an invalid response.")
    try:
        content = result["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        content = None
    if not isinstance(content, str) or not content.strip():
        raise HTTPException(status_code=502, detail="The LLM provider returned no message content.")
    return content.strip()


def _strip_code_fence(text: str) -> str:
    """Models sometimes wrap JSON in ```json fences when JSON mode is unavailable."""
    stripped = text.strip()
    if stripped.startswith("```") and stripped.endswith("```"):
        body = stripped.split("\n", 1)[1] if "\n" in stripped else ""
        body = body.rsplit("```", 1)[0]
        return body.strip()
    return stripped


def explain_scan(structured_result: dict) -> dict:
    user_content = f"""Here is the structured analysis of a scanned food label. Explain it to the
user and give suggestions.

Diet fit: {json.dumps(structured_result.get('diet_fit'))}
Allergen flags: {json.dumps(structured_result.get('allergen_flags'))}
Scores: {json.dumps(structured_result.get('scores'))}
Nutrition: {json.dumps(structured_result.get('nutrition'))}
Classified ingredients: {json.dumps(structured_result.get('classified_ingredients'))}
User health flags: {json.dumps(structured_result.get('health_flags'))}

Respond with JSON only, in this shape:
{{"summary": "...", "suggestions": ["...", "...", "..."]}}"""

    text = _chat(user_content, num_predict=600, json_mode=True)
    try:
        explanation = json.loads(_strip_code_fence(text))
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=502, detail="The LLM returned invalid explanation JSON.") from exc

    if (
        not isinstance(explanation, dict)
        or not isinstance(explanation.get("summary"), str)
        or not isinstance(explanation.get("suggestions"), list)
        or not all(isinstance(item, str) for item in explanation["suggestions"])
    ):
        raise HTTPException(status_code=502, detail="The LLM returned an explanation in an invalid format.")
    return explanation


def answer_followup(scan_result: dict, question: str) -> dict:
    user_content = f"""Scan result context: {json.dumps(scan_result)}

The user is asking a follow-up question about this specific scanned product:
"{question}"

Answer directly and concisely, grounded only in the context above."""

    return {"answer": _chat(user_content, num_predict=400)}
