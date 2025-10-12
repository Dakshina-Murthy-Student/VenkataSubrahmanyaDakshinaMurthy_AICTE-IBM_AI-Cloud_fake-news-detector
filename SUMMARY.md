# Summary
Project: Fake News Detector — Student Edition

Purpose:
- Provide a simple educational tool to evaluate article credibility with transparent heuristics and optional LLM assistance.

Key changes made during stabilization:
- Fixed crash caused by NLTK `punkt_tab` missing by adding a deterministic fallback sentence-splitter.
- Added robust session_state usage and guarded calls to avoid startup crashes.
- Reorganized config secret access to prefer environment or Streamlit secrets.
- Added documentation and deployment instructions for Streamlit Cloud.

Deployment path:
- Recommended: Streamlit Cloud.
- Local: venv + `pip install -r requirements.txt`. Optional conda for heavy dependencies.

Security:
- API keys must be injected via Streamlit Secrets or environment variables. See `SECURITY_NOTES.md`.
