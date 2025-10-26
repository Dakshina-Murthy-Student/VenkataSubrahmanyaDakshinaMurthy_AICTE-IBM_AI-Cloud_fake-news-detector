# File: backend.py - LLM integration for fact-checking news articles using OpenRouter API
import json
import traceback
from typing import List, Dict, Any
from config import Config
from utils import mock_analysis, cache_get, cache_set, now_iso, handle_llm_response
import requests
from analyzer import extract_factual_claims
import logging

logger = logging.getLogger(__name__)

OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_MODEL = "meta-llama/llama-3-8b-instruct"


def analyze_text_with_llm(
    full_text: str,
    local_summary: str,
    rep_sentences: List[str],
    metadata: Dict[str, Any],
    use_llm: bool = True,
    token_budget: int = 512
) -> Dict[str, Any]:
    # use a short cache key (hashing large text is recommended; keep simple here)
    cache_key = "analysis_" + (full_text[:2000] or "empty")
    cached = cache_get(cache_key)
    if cached:
        return cached

    # If LLM disabled or no key, return deterministic mock
    if not use_llm or not getattr(Config, "OPENROUTER_API_KEY", None):
        res = mock_analysis(full_text)
        out = {
            "summary": res.get("summary"),
            "llm_flags": res.get("llm_flags", []),
            "suggested_searches": [],
            "confidence": None,
            "mode": "mock",
            "generated_at": now_iso(),
            "error": None
        }
        cache_set(cache_key, out)
        return out

    try:
        factual_claims = extract_factual_claims(full_text) or []
        # Build a compact strict-json prompt (encourage JSON-only output)
        claims_text = "\n".join(f"- {c}" for c in factual_claims[:8])
        prompt = (
            "You are an expert fact-check assistant. For the provided article, return ONLY valid JSON "
            "matching this schema: {\"summary\":string, \"llm_flags\":[{\"sentence\":string,\"reason\":string,\"severity\":\"low|medium|high\"}], "
            "\"suggested_searches\":[string], \"confidence\":number|null}.\n\n"
            "Article summary (local extract):\n"
            f"{local_summary}\n\n"
            "Claims (one per line):\n"
            f"{claims_text}\n\n"
            "For each claim include sentence, reason, and severity. Do not include any commentary or extra fields."
        )

        headers = {
            "Authorization": f"Bearer {Config.OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
        }
        data = {
            "model": OPENROUTER_MODEL,
            "messages": [
                {"role": "system", "content": "You are a JSON-only assistant. Output valid JSON only with fields summary, llm_flags, suggested_searches, confidence."},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": token_budget,
            "temperature": 0.0
        }

        resp = requests.post(OPENROUTER_API_URL, headers=headers, json=data, timeout=60)
        resp.raise_for_status()

        # result may be JSON; capture text robustly
        try:
            # Prefer JSON parse if API returned JSON structure
            result = resp.json()
        except Exception:
            # fallback to raw text
            result = {"raw_text": resp.text}

        # Extract model text content in a safe way
        content = ""
        if isinstance(result, dict) and "choices" in result and result["choices"]:
            try:
                content = result["choices"][0]["message"]["content"]
            except Exception:
                # try safe fallback if structure is different
                content = resp.text
        else:
            content = result.get("raw_text", str(result))

        # Robust parse: use helper which never raises and returns dict or error-indicator
        # Provide a fallback shaped similar to final output (so UI can still display)
        fallback = {
            "summary": local_summary,
            "llm_flags": [],
            "suggested_searches": [],
            "confidence": None,
            "mode": "llm-fallback",
            "generated_at": now_iso(),
            "error": None
        }

        parsed = handle_llm_response(content, fallback=fallback)

        # If parse returned an 'error' key, the handle_llm_response has already returned fallback annotated with _llm_parse_error
        if parsed.get("error"):
            logger.warning("LLM parse error: %s", parsed.get("error"))
            parsed_out = {
                "summary": parsed.get("summary", fallback["summary"]),
                "llm_flags": parsed.get("llm_flags", []),
                "suggested_searches": parsed.get("suggested_searches", []),
                "confidence": parsed.get("confidence", None),
                "mode": parsed.get("mode", "llm-fallback"),
                "generated_at": now_iso(),
                "error": parsed.get("error")
            }
            cache_set(cache_key, parsed_out)
            return parsed_out

        # Ensure required keys, with defaults
        parsed.setdefault("summary", str(parsed.get("summary", local_summary)))
        parsed.setdefault("llm_flags", parsed.get("llm_flags", []))
        parsed.setdefault("suggested_searches", parsed.get("suggested_searches", []))
        parsed.setdefault("confidence", parsed.get("confidence", None))
        parsed.update({"mode": "llm", "generated_at": now_iso(), "error": None})

        cache_set(cache_key, parsed)
        return parsed

    except Exception as e:
        tb = traceback.format_exc()
        msg = (
            "OpenRouter LLM API error. Check your key and quota at https://openrouter.ai/ .\n"
            f"Error detail: {e}\n{tb}"
        )
        logger.exception("LLM call failed: %s", msg)
        fallback = mock_analysis(full_text)
        out = {
            "summary": fallback.get("summary"),
            "llm_flags": fallback.get("llm_flags", []),
            "suggested_searches": [],
            "confidence": None,
            "mode": "llm-error",
            "generated_at": now_iso(),
            "error": msg,
        }
        cache_set(cache_key, out)
        return out


def call_llm(local_summary, rep_sentences, metadata):
    # default to mock to avoid accidental LLM costs; switch to use_llm=True when ready
    return analyze_text_with_llm(local_summary, local_summary, rep_sentences, metadata, use_llm=False)
