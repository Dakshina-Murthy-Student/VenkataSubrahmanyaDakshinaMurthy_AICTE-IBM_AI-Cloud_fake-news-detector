# app.py - Main Streamlit app for Fake News Detector
import streamlit as st
from ingest import extract_text_from_url, extract_text_from_pdf, extract_text_from_image, create_metadata_from_text
from analyzer import extractive_summary, better_split_sentences, compute_score
from backend import analyze_text_with_llm
from config import Config
import json
from urllib.parse import quote_plus

# --- Modern, accessible, professional color palette ---
PRIMARY = "#2563eb"
BACKGROUND = "#5c5c88"
SURFACE = "#040404"
BORDER = "#4f72c2"
TEXT_DARK = "#23272f"
TEXT_MEDIUM = "#495057"
SUCCESS_BG = "#e8f5e9"
WARNING_BG = "#fff3cd"
ERROR_BG = "#fdeaea"
INFO_BG = "#e3f2fd"
FLAG_ACCENT = "#ffc107"
SCORE_GOOD = "#43a047"
SCORE_MID = "#ffc107"
SCORE_BAD = "#e53935"

st.set_page_config(page_title="🕵️ Fake News Detector", layout="wide")

# --- Style block for human-friendly appearance ---
st.markdown(f"""
<style>
/* (same styles as before) */
</style>
""", unsafe_allow_html=True)

# --- Header and Help ---
st.title("🕵️ Fake News Detector — Student Edition")
st.caption("Check news credibility instantly with AI & transparent scoring.")

with st.expander("ℹ️ How to use this tool (click to expand)", expanded=False):
    st.markdown("""
- **Step 1:** Paste, upload, or link to an article.
- **Step 2:** Click **Analyze Article**.
- **Step 3:** See the credibility score and flagged claims.
- **Step 4:** Click 'Search this claim' to check any suspicious statements.
- For advanced options and full breakdown, use 'Show Advanced Results'.
""")

# --- Step 1: Article Input ---
st.markdown('<div style="font-size: 1.25em; font-weight: 700; color: #2563eb; margin-top: 1em;">Step 1: Enter Article</div>', unsafe_allow_html=True)
tab_text, tab_url, tab_file = st.tabs(["📝 Paste Text", "🌐 From URL", "📄 Upload File"])

# Use session_state to preserve inputs across reruns
if 'article_text' not in st.session_state:
    st.session_state.article_text = ""
if 'metadata' not in st.session_state:
    st.session_state.metadata = {}

with tab_text:
    pasted_text = st.text_area("Paste the full article text here", height=200, key="article_text_area")
    if pasted_text:
        st.session_state.article_text = pasted_text
        st.session_state.metadata = create_metadata_from_text(pasted_text, source_type="text_paste")
with tab_url:
    url_input = st.text_input("Enter article URL", key="url_input")
    if url_input:
        with st.spinner("Fetching article..."):
            text, meta = extract_text_from_url(url_input)
            if text:
                st.session_state.article_text = text
                st.session_state.metadata = meta
            else:
                st.error("❌ Could not extract article text from this URL.")
with tab_file:
    uploaded_file = st.file_uploader("Upload PDF or Image", type=['pdf','png','jpg','jpeg'])
    if uploaded_file:
        file_bytes = uploaded_file.getvalue()
        with st.spinner("Extracting text..."):
            if uploaded_file.type == "application/pdf" or uploaded_file.name.lower().endswith(".pdf"):
                text, meta = extract_text_from_pdf(file_bytes)
                meta["source_type"] = "pdf_upload"
            else:
                text, meta = extract_text_from_image(file_bytes)
                meta["source_type"] = "image_upload"
            if text:
                st.session_state.article_text = text
                st.session_state.metadata = meta
            elif "Tesseract OCR not installed" in text:
                st.error("Tesseract OCR not installed or not in PATH.")
            else:
                st.error("Extraction failed. File may be unsupported or corrupted.")

# --- Input quality feedback ---
article_text = st.session_state.article_text or ""
metadata = st.session_state.metadata or {}

# Sentence splitting can fail if a tokenizer is not available. Use try/except to avoid crash.
try:
    sents = better_split_sentences(article_text) if article_text else []
except Exception:
    sents = []
    # Show a one-line warning so the user knows we fell back to a simpler splitter.
    st.warning("Sentence splitting used a simple fallback (NLTK tokenizer not available). For better sentence splitting install/download NLTK 'punkt' data.")

if article_text:
    if len(article_text) < 200:
        st.warning("⚠️ This article is very short. Paste a full news article for best results.")
    elif len(sents) < 3:
        st.warning("⚠️ Too few sentences. Paste a full article, not a headline.")
    else:
        st.success(f"✅ Article loaded! Detected {len(sents)} sentences.")

# --- Step 2: Analyze Options (progressive disclosure) ---
st.markdown('<div style="font-size: 1.25em; font-weight: 700; color: #2563eb; margin-top: 1.5em;">Step 2: Analyze</div>', unsafe_allow_html=True)
show_advanced = st.checkbox("Show advanced options", value=False)
if show_advanced:
    st.caption("For power users: tune the analysis for more thorough or faster checks.")
    use_llm = st.checkbox("Use AI Fact-Checking (LLM)", value=True)
    max_rep = st.slider("Number of key sentences for AI", 4, 12, 8)
    token_budget = st.slider("AI token budget", 256, 2048, 768, step=64)
    show_raw = st.checkbox("Show full extracted text in results", value=False)
else:
    use_llm = True
    max_rep = 8
    token_budget = 768
    show_raw = False

# --- Step 3: Analyze Button ---
if article_text:
    st.markdown("")
    if st.button("🔎 Analyze Article", type="primary", use_container_width=True):
        with st.spinner("Summarizing article..."):
            local_summary = extractive_summary(article_text, k=max_rep)
            rep_sentences = sorted(sents, key=len, reverse=True)[:max_rep] if sents else []

        with st.spinner("Fact-checking (may take 10-20s with AI)..."):
            backend_resp = analyze_text_with_llm(
                full_text=article_text,
                local_summary=local_summary,
                rep_sentences=rep_sentences,
                metadata=metadata,
                use_llm=use_llm,
                token_budget=token_budget
            )

        # --- Mode Banner ---
        if backend_resp.get("mode") == "llm":
            st.markdown(f'<div class="mode-banner" style="background:{INFO_BG};color:{TEXT_DARK};">💡 <b>AI Fact-Checking ACTIVE:</b> Advanced AI analyzed this article.</div>', unsafe_allow_html=True)
        elif backend_resp.get("mode") == "llm-error":
            st.markdown(f'<div class="mode-banner" style="background:{WARNING_BG};color:{TEXT_DARK};">⚠️ <b>AI/API error:</b> Only heuristics used. See below for details.</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="mode-banner" style="background:{SURFACE};color:{TEXT_DARK};">🤖 <b>Offline Mode:</b> Only local heuristics are used.</div>', unsafe_allow_html=True)

        # --- Error banner (brief) ---
        if backend_resp.get("error"):
            # show short safe excerpt only
            st.error(f"AI/API error: {str(backend_resp.get('error'))[:800]}")

        # --- Score computation ---
        final_report = compute_score(article_text, metadata, llm_flags=backend_resp.get("llm_flags", []), cross_checks=backend_resp.get("cross_check"))
        if backend_resp.get("summary"):
            final_report["summary"] = backend_resp["summary"]
        final_report["mode"] = backend_resp.get("mode", "mock")
        final_report["llm_confidence"] = backend_resp.get("confidence", None)
        final_report["suggested_searches"] = backend_resp.get("suggested_searches", [])

        # --- Score & summary rendering (unchanged) ---
        score = final_report['score']
        if score >= 70:
            color_class = "score-good"
            emoji = "🟢"
            verdict = "Likely credible"
        elif score >= 40:
            color_class = "score-mid"
            emoji = "🟡"
            verdict = "Somewhat questionable"
        else:
            color_class = "score-bad"
            emoji = "🔴"
            verdict = "Potentially unreliable"

        st.markdown(
            f"""
            <div class="{color_class}" style="padding:14px 18px;border-radius:8px;margin-bottom:8px;">
            <span style="font-size:2.2em;vertical-align:middle">{emoji}</span>
            <span style="font-size:1.35em;font-weight:bold;padding-left:9px;"> Score: {score}/100 — {verdict}</span>
            </div>
            """, unsafe_allow_html=True
        )
        st.markdown('<div style="font-size: 1.1em; font-weight: 700; color: #2563eb; margin-top: 1.2em;">📝 Concise summary</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="summary-box">{final_report.get("summary", "(no summary available)")}</div>', unsafe_allow_html=True)

        # --- Flags & suggested searches (unchanged) ---
        st.markdown('<div style="font-size: 1.1em; font-weight: 700; color: #d7263d;">🚩 Flagged Claims & Fact Checks</div>', unsafe_allow_html=True)
        if final_report["flags"]:
            for f in final_report["flags"]:
                sev = f.get("severity", "medium").capitalize()
                sent = f.get("sentence", "")
                reason = f.get("reason", "")
                search_url = "https://www.google.com/search?q=" + quote_plus(sent[:200])
                st.markdown(
                    f"""
                    <div class="flag-box">
                      <span style="color:#b26a00;font-weight:600">{sev}</span>
                      <span style="font-weight:500;"> {sent}</span>
                      <div style="font-size:0.97em;color:{TEXT_MEDIUM};margin-top:0.3em;">
                        Reason: {reason} <br>
                        <a href="{search_url}" target="_blank" style="color:{PRIMARY};text-decoration:underline;">🔎 Search this claim</a>
                      </div>
                    </div>
                    """, unsafe_allow_html=True
                )
        else:
            st.success("No suspicious claims detected in this article.")

        if final_report.get("suggested_searches"):
            st.markdown('<div style="font-size: 1.1em; font-weight: 700; color: #2563eb;">🔍 Suggested searches for manual verification</div>', unsafe_allow_html=True)
            for q in final_report["suggested_searches"]:
                url = "https://www.google.com/search?q=" + quote_plus(q)
                st.write(f"- [{q}]({url})", unsafe_allow_html=True)

        # --- Advanced/Transparency Panel ---
        if st.checkbox("Show Advanced Results", value=False):
            with st.expander("🧪 Full Scoring & AI Details", expanded=True):
                st.markdown("#### Score breakdown")
                st.json(final_report.get("breakdown", {}))
                if final_report.get("llm_confidence") is not None:
                    conf = final_report["llm_confidence"]
                    st.caption(f"AI confidence (0-1 scale): {conf:.2f}")
                if show_raw:
                    st.markdown("#### Full extracted text")
                    st.text_area("Raw text", value=article_text[:20000], height=300)
                st.download_button("Download JSON report", json.dumps({
                        "report": final_report,
                        "backend_response": backend_resp,
                        "metadata": metadata
                    }, ensure_ascii=False, indent=2),
                    file_name="fake_news_report.json", mime="application/json")
else:
    st.info("Paste article text, enter a URL, or upload a file to begin.")

st.markdown("---")
st.caption("Made for students. No guarantee of accuracy. Use responsibly.")
# End of app.py