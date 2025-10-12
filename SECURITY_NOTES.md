
# SECURITY_NOTES.md

## Secrets & API keys
- **Do NOT commit** API keys (OpenRouter, Gemini, or other). Never add them to code or `requirements.txt`.
- Local testing: `.streamlit/secrets.toml` is allowed for convenience **but must never be pushed**.
- Streamlit Cloud: use the App → Secrets UI to set `api_keys.OPENROUTER_API_KEY` (or `GEMINI_API_KEY`) — the value is injected into the running container, not visible in the repo.

## What the code expects
- `config._get_secret("OPENROUTER_API_KEY")` will read from environment or `st.secrets`.
- If an API key is missing, the app falls back to deterministic mock analysis.

## Redacted/removed secrets
- If any code previously had a literal API key string (e.g., `GEMINI_API_KEY = "AIza..."`), it should be removed and replaced with env/secrets access.
- The app uses `utils.cache_*` functions that write to `cache_responses.json`. This file may contain cached outputs (no secrets) — it should be ignored in `.gitignore`.

## Reviewer guidance
- When reviewing the repo, ensure `.streamlit/secrets.toml` is absent.
- If a key must be shared with a reviewer for grading, share via a secure channel (not in GitHub issues/PR comments).
