# File: utils.py - utility functions for caching, hashing, and robust LLM parsing
from dotenv import load_dotenv
load_dotenv()
import os
import json
import hashlib
from datetime import datetime
import random
from typing import Optional, Any, Dict
import re
import logging

# --- existing cache/hash utilities ---
CACHE_FILE = "cache_responses.json"

def hash_text(text: str) -> str:
    """16-char hex hash for short display and cache keys."""
    if not text:
        return "empty"
    h = hashlib.sha256()
    h.update(text.encode("utf-8"))
    return h.hexdigest()[:16]

def load_cache() -> dict:
    if not os.path.exists(CACHE_FILE):
        return {}
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_cache(cache: dict):
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)

def cache_get(key: str):
    cache = load_cache()
    return cache.get(key)

def cache_set(key: str, value):
    cache = load_cache()
    cache[key] = value
    save_cache(cache)

def now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"

def mock_analysis(text: str) -> dict:
    """
    Deterministic mock analysis that produces stable output for the same text.
    """
    text_hash = hash_text(text)
    random.seed(text_hash)  # deterministic per content
    length = len(text or "")
    credibility_score = 50 + (length % 31) - (length % 5)
    credibility_score = max(25, min(80, credibility_score))

    llm_flags = []
    if length > 300:
        s = (text.split(".")[0] + ".") if "." in text else (text[:200] + "...")
        llm_flags.append({
            "sentence": s,
            "reason": "Mock: statement may require verification (no primary source found).",
            "severity": "medium"
        })

    return {
        "credibility": int(credibility_score),
        "summary": (
            "Mock analysis: this summary was generated locally. "
            "For authoritative checking, enable OpenRouter API in secrets."
        ),
        "mode": "mock",
        "llm_flags": llm_flags,
        "generated_at": now_iso()
    }

# --- new: robust JSON parsing utilities for LLM responses ---

logger = logging.getLogger(__name__)

# regex to remove C0 control characters except newline (\n), carriage return (\r) and tab (\t)
_control_char_re = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f]')

def sanitize_text_for_json(s: str) -> str:
    """
    Remove control characters that break json.loads while keeping \n and \t.
    Normalize Windows CRLF to LF.
    """
    if s is None:
        return ""
    if isinstance(s, bytes):
        s = s.decode("utf-8", errors="replace")
    # remove problematic control chars
    s = _control_char_re.sub(' ', s)
    # normalize CRLF -> LF
    s = s.replace("\r\n", "\n").replace("\r", "\n")
    return s

def extract_json_substring(s: str) -> str:
    """
    Try to find a balanced {...} or [...] JSON substring inside a larger text.
    Returns the substring if found, else original string.
    """
    if not s:
        return s
    # find first opening brace or bracket
    first_obj = s.find('{')
    first_arr = s.find('[')
    # choose the earliest non-negative index (or -1 if none)
    starts = [i for i in (first_obj, first_arr) if i != -1]
    if not starts:
        return s
    start = min(starts)
    stack = []
    for i in range(start, len(s)):
        ch = s[i]
        if ch == '{' or ch == '[':
            stack.append(ch)
        elif ch == '}' or ch == ']':
            if not stack:
                continue
            open_ch = stack.pop()
            if len(stack) == 0:
                # balanced top-level JSON found
                return s[start:i+1]
    # failed to find balanced substring; return original
    return s

def parse_llm_json(raw_text: Any) -> Dict[str, Any]:
    """
    Robustly parse an LLM response that should be JSON.
    Steps:
      1) coerce to str, sanitize control chars
      2) try direct json.loads
      3) try extracting the first {...} or [...] block and parse that
      4) on failure, return a safe dict with 'error' and 'raw' (truncated)
    Always returns a dict (never raises).
    """
    try:
        if raw_text is None:
            return {"error": "empty_response", "raw": ""}
        # coerce to string safely
        if isinstance(raw_text, bytes):
            text = raw_text.decode("utf-8", errors="replace")
        else:
            text = str(raw_text)
    except Exception as e:
        logger.exception("Failed to coerce raw_text to str: %s", e)
        return {"error": "coercion_failed", "raw": ""}

    cleaned = sanitize_text_for_json(text)

    # 1) direct parse
    try:
        parsed = json.loads(cleaned)
        return parsed if isinstance(parsed, dict) else {"result": parsed}
    except Exception as e:
        logger.debug("Direct json.loads failed: %s", e)

    # 2) try extracting json substring
    candidate = extract_json_substring(cleaned)
    if candidate and candidate != cleaned:
        try:
            parsed = json.loads(candidate)
            return parsed if isinstance(parsed, dict) else {"result": parsed}
        except Exception as e:
            logger.debug("json.loads on extracted substring failed: %s", e)

    # 3) try removing leading non-json chars and re-attempt
    try:
        m = re.search(r'[\{\[]', cleaned)
        if m:
            idx = m.start()
            candidate2 = cleaned[idx:].strip(" \n`")
            try:
                parsed = json.loads(candidate2)
                return parsed if isinstance(parsed, dict) else {"result": parsed}
            except Exception as e:
                logger.debug("json.loads after trimming failed: %s", e)
    except Exception:
        pass

    # final fallback: return structured error dict (truncate raw to 5000 chars)
    raw_preview = cleaned[:5000] if len(cleaned) > 5000 else cleaned
    logger.error("LLM response could not be parsed as JSON. Returning fallback. Raw preview: %s", raw_preview[:1000])
    return {"error": "invalid_json_from_llm", "raw": raw_preview}

def handle_llm_response(raw_text: Any, fallback: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Helper wrapper that parses LLM response and returns either the parsed dict
    or a safe fallback (if provided) or a structured error dict.
    Use this in backend before using parsed fields.
    """
    parsed = parse_llm_json(raw_text)
    if parsed is None:
        parsed = {"error": "null_parsed"}
    if isinstance(parsed, dict) and parsed.get("error"):
        # If caller provided a fallback, return it (annotated)
        if fallback:
            out = dict(fallback)
            out["_llm_parse_error"] = parsed.get("error")
            out["_llm_raw_preview"] = parsed.get("raw", "")[:1000]
            return out
        else:
            return parsed
    return parsed

# End of utils.py
