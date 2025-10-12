# backend.py - LLM integration for fact-checking news articles using OpenRouter API
import json
import traceback
from typing import List, Dict, Any
from config import Config
from utils import mock_analysis, cache_get, cache_set, now_iso
import requests
from analyzer import extract_factual_claims

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
    cache_key = "analysis_" + (full_text[:2000] or "empty")
    cached = cache_get(cache_key)
    if cached:
        return cached

    if not use_llm or not Config.OPENROUTER_API_KEY:
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
        factual_claims = extract_factual_claims(full_text)
        prompt = (
            "You are an expert fact-check assistant for news articles. For the following news article:\n"
            "1. Summarize it concisely.\n"
            "2. For each claim below, flag if it is questionable, unsupported, or sensational; explain why (use strict JSON: sentence, reason, severity=low|medium|high):\n"
            + "\n".join(f"- {c}" for c in factual_claims[:8]) +
            "\n3. Suggest Google search queries for manual checking.\n"
            "Return result as strict JSON: {summary, llm_flags:[{sentence, reason, severity}], suggested_searches, confidence}."
        )
        headers = {
            "Authorization": f"Bearer {Config.OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
        }
        data = {
            "model": OPENROUTER_MODEL,
            "messages": [
                {"role": "system", "content": "You are a fact-check assistant. Return JSON only (summary, llm_flags, suggested_searches, confidence)."},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": token_budget,
        }
        resp = requests.post(OPENROUTER_API_URL, headers=headers, json=data, timeout=60)
        resp.raise_for_status()
        result = resp.json()
        content = (
            result["choices"][0]["message"]["content"]
            if "choices" in result and result["choices"] and "message" in result["choices"][0]
            else str(result)
        )
        try:
            parsed = json.loads(content)
        except Exception:
            import re
            m = re.search(r"\{.*\}", content, re.DOTALL)
            parsed = json.loads(m.group(0)) if m else {"summary": content, "llm_flags": [], "suggested_searches": [], "confidence": None}
        parsed.setdefault("summary", str(parsed.get("summary", content)))
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
    return analyze_text_with_llm(local_summary, local_summary, rep_sentences, metadata, use_llm=False)