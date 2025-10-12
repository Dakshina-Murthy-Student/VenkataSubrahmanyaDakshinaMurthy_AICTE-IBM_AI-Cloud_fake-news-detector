# analyzer.py
# Core logic for analyzing news articles for factual accuracy and credibility.
# This version is resilient: it uses NLTK's sent_tokenize when available and gracefully
# falls back to a regex-based splitter when NLTK or the punkt data are not installed.

from typing import List, Dict, Any, Optional
import re
from sentence_transformers import SentenceTransformer
import numpy as np
from utils import now_iso

MODEL_NAME = "all-MiniLM-L6-v2"
_model: Optional[SentenceTransformer] = None

# Try to import NLTK's sent_tokenize; if anything fails, keep None and use fallback.
try:
    from nltk.tokenize import sent_tokenize as _nltk_sent_tokenize  # type: ignore
except Exception:
    _nltk_sent_tokenize = None  # will use regex fallback


def get_embedding_model():
    global _model
    if _model is None:
        _model = SentenceTransformer(MODEL_NAME)
    return _model


def better_split_sentences(text: str) -> List[str]:
    """
    Robust splitter:
      - If NLTK's sent_tokenize is available and works, use it.
      - Otherwise use a regex that splits on sentence-ending punctuation
        while attempting to avoid splitting on abbreviations poorly.
    Returns only sentences longer than 10 characters.
    """
    if not text:
        return []

    # Try NLTK tokenizer if available
    if _nltk_sent_tokenize is not None:
        try:
            sents = _nltk_sent_tokenize(text)
            # Filter very short fragments and trim whitespace
            return [s.strip() for s in sents if len(s.strip()) > 10]
        except Exception:
            # If anything goes wrong (missing punkt_tab, lookup error, etc.) fall through
            pass

    # Regex fallback: split after . ! ? followed by whitespace and a capital letter/quote/digit
    # This is conservative and deterministic (no external downloads).
    pieces = re.split(r'(?<=[\.\?\!])\s+(?=[A-Z0-9"\'\u201C])', text.strip())
    sents = [p.strip() for p in pieces if len(p.strip()) > 10]
    return sents


def extractive_summary(text: str, k: int = 6) -> str:
    sentences = better_split_sentences(text)
    if not sentences:
        return "Not enough content to summarize."
    try:
        model = get_embedding_model()
        embeddings = model.encode(sentences, convert_to_numpy=True)
        if embeddings.ndim < 2 or embeddings.shape[0] == 0:
            return "Failed to generate embeddings for summarization."
        norm_embeddings = embeddings / np.linalg.norm(embeddings, axis=1, keepdims=True)
        centroid = norm_embeddings.mean(axis=0)
        norm_centroid = centroid / np.linalg.norm(centroid)
        sims = np.dot(norm_embeddings, norm_centroid)
        top_k = min(k, len(sentences))
        top_idx = np.argsort(-sims)[:top_k]
        selected = [sentences[i] for i in sorted(top_idx)]
        return " ".join(selected)
    except Exception as e:
        return f"Error during extractive summarization: {e}"


def extract_factual_claims(text: str) -> List[str]:
    """Extract sentences with numbers or reporting verbs for LLM checking."""
    sents = better_split_sentences(text)
    claims = []
    for s in sents:
        if any(c.isdigit() for c in s):
            claims.append(s)
        elif any(w in s.lower() for w in [
            "report", "reports", "said", "announced", "launched", "found",
            "published", "revealed", "warned", "study", "research", "survey"
        ]):
            claims.append(s)
    # fallback: top N longest sentences
    if len(claims) < 5:
        claims += sorted(sents, key=len, reverse=True)[:5]
    seen = set()
    out = []
    for c in claims:
        if c not in seen:
            out.append(c)
            seen.add(c)
    return out


def compute_score(document_text: str, metadata: Dict[str, Any], llm_flags: List[Any]=None, cross_checks: Dict=None) -> Dict:
    if llm_flags is None:
        llm_flags = []
    # Normalize llm_flags to list of dicts
    norm_flags = []
    for f in llm_flags:
        if isinstance(f, dict):
            norm_flags.append(f)
        elif isinstance(f, str):
            norm_flags.append({"sentence": f, "reason": "Flagged by LLM (string)", "severity": "medium"})
    llm_flags = norm_flags

    text = document_text or ""
    breakdown = {}

    # Source reputation (30)
    src_score = 5
    src_reason = "No source URL provided"
    url = metadata.get("source_url") if metadata else None
    if url:
        domain = url.lower()
        known_trusted = [
            "nytimes.com", "bbc.co", "theguardian.com",
            "washingtonpost.com", "reuters.com", "apnews.com"
        ]
        for kd in known_trusted:
            if kd in domain:
                src_score = 28
                src_reason = f"Trusted domain matched ({kd})"
                break
        if src_score == 5:
            if ".edu" in domain or ".gov" in domain:
                src_score = 24
                src_reason = "Educational or government domain"
            else:
                src_score = 8
                src_reason = "Unfamiliar domain; check site history"
    breakdown["source_reputation"] = {"score": src_score, "max": 30, "reason": src_reason}

    # Author & date (15)
    ad_score = 0
    ad_reason = ""
    author = metadata.get("authors") if metadata else []
    pubdate = metadata.get("publish_date") if metadata else None
    if author and len(author) > 0:
        ad_score += 8
        ad_reason += "Author present. "
    if pubdate:
        ad_score += 7
        ad_reason += f"Publish date present: {pubdate}. "
    if ad_score == 0:
        ad_reason = "No author or publish date found."
    breakdown["author_date"] = {"score": ad_score, "max": 15, "reason": ad_reason.strip()}

    # Citations & references (15)
    links = re.findall(r"https?://\S+", text)
    if len(links) >= 2:
        cit_score = 12
        cit_reason = f"{len(links)} external links found (possible references)."
    elif len(links) == 1:
        cit_score = 6
        cit_reason = "Single external link found."
    else:
        cit_score = 2
        cit_reason = "No explicit external links found."
    breakdown["citations"] = {"score": cit_score, "max": 15, "reason": cit_reason}

    # Writing style (10)
    sensational_words = ["shocking", "miracle", "proves", "cure", "guarantee",
                         "you won't believe", "unbelievable", "secret", "viral"]
    style_hits = sum(1 for w in sensational_words if w in text.lower())
    if style_hits >= 2:
        style_score = 2
        style_reason = f"Multiple sensational phrases detected: {style_hits}"
    elif style_hits == 1:
        style_score = 6
        style_reason = "One sensational phrase detected."
    else:
        style_score = 10
        style_reason = "Neutral writing style."
    breakdown["writing_style"] = {"score": style_score, "max": 10, "reason": style_reason}

    # Cross-source (20)
    cross_score = 8
    cross_reason = "Cross-check disabled; consider enabling web checks."
    if cross_checks and isinstance(cross_checks, dict):
        corroborations = cross_checks.get("corroboration_count", 0)
        if corroborations >= 3:
            cross_score = 20
            cross_reason = f"Corroborated by {corroborations} sources."
        elif corroborations == 1:
            cross_score = 6
            cross_reason = "Only one corroborating source found."
        else:
            cross_score = 4
            cross_reason = "No corroborating reputable sources found."
    breakdown["cross_source"] = {"score": cross_score, "max": 20, "reason": cross_reason}

    # LLM flags (10)
    if llm_flags:
        sev_map = {"high": 0, "medium": 4, "low": 7}
        worst = min([sev_map.get(f.get("severity", "low").lower(), 7) for f in llm_flags])
        llm_score = worst
        llm_reason = f"LLM returned {len(llm_flags)} flags; worst severity mapped to {llm_score}."
    else:
        llm_score = 8
        llm_reason = "No LLM flags."
    breakdown["llm_flags"] = {"score": llm_score, "max": 10, "reason": llm_reason}

    total = sum(b['score'] for b in breakdown.values())
    total = max(0, min(int(round(total)), 100))

    # Flags & suggestions
    flags = []
    for f in llm_flags:
        flags.append({"sentence": f.get("sentence", ""), "reason": f.get("reason", ""), "severity": f.get("severity", "medium")})
    sentences = better_split_sentences(text)
    for s in sentences:
        if any(w in s.lower() for w in sensational_words):
            if not any(f['sentence'] == s for f in flags):
                flags.append({"sentence": s, "reason": "Sensational wording (local heuristic)", "severity": "medium"})

    suggested = []
    for i, s in enumerate(sentences[:3]):
        if i < len(llm_flags):
            f = llm_flags[i]
            suggested.append({"claim": f.get("sentence", s), "why": f.get("reason", "LLM suggested claim")})
        else:
            suggested.append({"claim": s, "why": "Key factual claim to verify (local heuristic)"})

    report = {
        "summary": extractive_summary(text),
        "score": total,
        "breakdown": breakdown,
        "flags": flags,
        "suggested_facts_to_check": suggested,
        "raw_extracted_text": text[:20000],
        "generated_at": now_iso()
    }
    return report
# End of analyzer.py