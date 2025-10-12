# utils.py - utility functions for caching, hashing, and mock analysis
from dotenv import load_dotenv
load_dotenv()
import os
import json
import hashlib
from datetime import datetime
import random
from typing import Optional

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