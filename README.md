# Fake News Detector — Student Edition

A compact educational tool to help students evaluate article credibility.  
Supports: paste text, URL scraping, PDF / OCR images. Runs local heuristics **and** optionally calls an LLM (OpenRouter / configured provider) for richer fact-checking.

---

## Quick project goals

- Provide a transparent credibility score (0–100).
- Highlight suspicious claims to verify manually.
- Run locally (developer) or on **Streamlit Cloud** (recommended for reviewers / instructors).
- Keep API keys out of the repository (use Streamlit secrets / environment variables).

---

## What to include in the Git repository

**Files you should commit (core project):**
- `app.py`
- `analyzer.py`
- `backend.py`
- `ingest.py`
- `utils.py`
- `config.py`
- `requirements.txt`
- `.gitignore`
- `README.md` (this file)
- `README_RUN.md`
- `SUMMARY.md`
- `SECURITY_NOTES.md`
- `FINAL_CHECKLIST.txt`

**Files you must NOT commit (secrets / local caches):**
- `.streamlit/secrets.toml` (never)
- `cache_responses.json`
- Any file containing your private API key(s) or `.env` with secrets (unless `.env` is in `.gitignore`)

---

## Streamlit Cloud — deploy (recommended for reviewers / instructors)

1. Create a GitHub repo and push the code (see checklist below for exact commands).
2. Open https://streamlit.io/cloud and sign in using your GitHub account.
3. Click **"New app"** → choose the repository and branch, and set the file path to `app.py`.
4. In the Streamlit Cloud app settings, add **secrets** (do **not** paste keys into code or commit them):
   - Navigate to App → Secrets
   - Add under `[api_keys]` the key your app expects (example used in this repo):
     ```
     [api_keys]
     OPENROUTER_API_KEY = "sk-xxxxxxxxxxxxxxxxxxxxxxxx"
     ```
     or, if you use Google Gemini in another branch, set `GEMINI_API_KEY = "..."`.
5. Deploy. Streamlit Cloud will automatically run `pip install -r requirements.txt` and start the app.
6. Use the Streamlit UI to share a link with reviewers. The secret is injected at runtime and is not visible anywhere in the repository or in the UI.

**Important:** If your app uses `OPENROUTER_API_KEY`, set that variable. The code will read it from Streamlit secrets or environment variables via `config._get_secret`.

---

## Reviewer / Professor quick-run instructions

### Option A — Run on Streamlit Cloud (recommended)
- Use the link the student provides. No keys required from reviewer (unless you want to test LLM path; then ask for a test key or student can provide a test guest key in the app's secrets).

### Option B — Run locally (recommended for detailed grading)
1. Clone the repo.
2. Create & activate a virtual environment (or use conda). Example using `venv`:
   ```bash
   python -m venv .venv
   source .venv/bin/activate      # macOS / Linux
   .venv\Scripts\Activate.ps1     # Windows PowerShell
   pip install -r requirements.txt
3. (Optional) If you want LLM tests with OpenRouter, create a local .streamlit/secrets.toml with:
    [api_keys]
    OPENROUTER_API_KEY = "YOUR_OPENROUTER_KEY"
4. Start the app:
    streamlit run app.py
5. Use the UI (paste text, URL, or upload a PDF/image). For LLM-enabled results, ensure the key is present.
## Notes on API keys & privacy

⦁	Never commit keys. Use Streamlit's Secrets Manager (Streamlit Cloud) for production, and local .streamlit/secrets.toml for local testing only (still do not commit).

⦁	The app reads keys via config._get_secret so it supports both environment variables and Streamlit secrets.

⦁	Troubleshooting (common)

⦁	App crashes on start: LookupError: punkt_tab not found — run:

⦁	python -c "import nltk; nltk.download('punkt')" or rely on the app’s fallback (the app will use a regex-based splitter if NLTK tokenizer not available).

⦁	LLM results show MOCK or FALLBACK — check the Streamlit app logs / terminal for messages about missing API key or quota; ensure the secret is set.

⦁	Model import slow / memory heavy — embedding model preloading recommended (see README_RUN.md).

### Licensing & disclaimers

⦁	Educational project — not for production publishing. The tool provides heuristics and (optionally) LLM outputs; human verification required.

⦁	See SECURITY_NOTES.md for secret handling details.

### Contact

⦁	If you are a reviewer or professor and need a demo key or access guidance, contact the submitting student.

---








