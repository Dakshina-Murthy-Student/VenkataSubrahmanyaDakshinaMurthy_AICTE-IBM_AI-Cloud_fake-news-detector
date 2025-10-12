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
- `FIXES.md`
- `SECURITY_NOTES.md`
- `CI_WORKFLOW.yml` (if you want GitHub Actions)
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

Never commit keys. Use Streamlit's Secrets Manager (Streamlit Cloud) for production, and local .streamlit/secrets.toml for local testing only (still do not commit).

The app reads keys via config._get_secret so it supports both environment variables and Streamlit secrets.

Troubleshooting (common)

App crashes on start: LookupError: punkt_tab not found — run:

python -c "import nltk; nltk.download('punkt')"


or rely on the app’s fallback (the app will use a regex-based splitter if NLTK tokenizer not available).

LLM results show MOCK or FALLBACK — check the Streamlit app logs / terminal for messages about missing API key or quota; ensure the secret is set.

Model import slow / memory heavy — embedding model preloading recommended (see README_RUN.md).

Licensing & disclaimers

Educational project — not for production publishing. The tool provides heuristics and (optionally) LLM outputs; human verification required.

See SECURITY_NOTES.md for secret handling details.

Contact

If you are a reviewer or professor and need a demo key or access guidance, contact the submitting student.


---

--- filename: README_RUN.md ---
```markdown
# Developer Quick Run & Troubleshooting

This file contains precise commands to get the app running locally on Windows / macOS / Linux.

## Recommended environment (Python 3.10+; 3.9 OK)

### 1) Create & activate a venv (cross-platform)
Windows PowerShell:
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirements.txt


macOS / Linux:

python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

2) (Optional, recommended) Pre-warm embeddings

To reduce first-run latency:

python - <<'PY'
from sentence_transformers import SentenceTransformer
SentenceTransformer('all-MiniLM-L6-v2').encode("warm up")
print("Model preloaded")
PY

3) (Optional) Install NLTK punkt tokenizer for best sentence splitting

If you want the NLTK tokenizer rather than fallback:

python -c "import nltk; nltk.download('punkt')"

4) Setup secrets locally for LLM testing (do NOT commit)

Create .streamlit/secrets.toml:

[api_keys]
OPENROUTER_API_KEY = "sk-..."

5) Run Streamlit
streamlit run app.py


Open browser at http://localhost:8501.

Running tests / linters

(Provided a pytest test set; add tests under tests/.)

Run tests:

pytest -q


Static checks:

pip install flake8
flake8 .

Troubleshooting hints (summary)

LookupError: punkt_tab not found — run python -c "import nltk; nltk.download('punkt')"

LLM API quota errors — verify key and quota on provider dashboard, or switch to mock mode.

If imports fail for heavy libs (sentence-transformers), follow the README suggestion to use conda (helps with tokenizers & rust build issues).


---

--- filename: SUMMARY.md ---
```markdown
# Summary (one page)

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


--- filename: FIXES.md ---

# FIXES.md — What I changed and why

1. **Crash on startup (NLTK punkt_tab lookup error)**
   - File: `analyzer.py`
   - Fix: Avoid runtime download and fallback to a deterministic regex sentence splitter when NLTK or punkt data are absent.
   - Rationale: Prevent Streamlit from exiting during import; deterministic fallback ensures app always starts.

2. **Session persistence & robust UI guards**
   - File: `app.py`
   - Fix: Use `st.session_state` for `article_text`/`metadata`; wrap sentence-splitting in try/except and show a one-line UI warning if fallback used.
   - Rationale: Improve UX and avoid abrupt crashes.

3. **Secure secrets access**
   - File: `config.py` (no change required if your existing code already reads Streamlit secrets or environment variables)
   - Rationale: Ensure keys are read from `st.secrets` or `os.environ` only.

4. **Backend LLM behavior**
   - Keep mock fallback for when API unavailable or key invalid; the app writes short error excerpts to UI and full trace info into logs (not exposed publicly).


--- filename: SECURITY_NOTES.md ---

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


--- filename: CI_WORKFLOW.yml ---

# .github/workflows/ci.yml
name: CI - Lint & Test

on:
  push:
    branches: [ main, master ]
  pull_request:
    branches: [ main, master ]

jobs:
  lint-test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.10]

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python ${{ matrix.python-version }}
        uses: actions/setup-python@v4
        with:
          python-version: ${{ matrix.python-version }}

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          pip install flake8 pytest

      - name: Run flake8
        run: |
          flake8 .

      - name: Run tests
        run: |
          pytest -q


Note: This CI runs linting & tests only. It does not attempt to start Streamlit or run heavy model downloads.

--- filename: requirements.txt ---

# Conservative, installable dependencies (use conda for heavy C/Rust-backed packages)
streamlit>=1.18,<2.0
requests>=2.28.0
beautifulsoup4>=4.11.0
pdfplumber>=0.7.6
pytesseract>=0.3.10
Pillow>=9.0.0
validators>=0.20.0
langdetect>=1.0.9
python-dotenv>=0.21.0

# Embeddings & NLP
sentence-transformers>=2.2.0
transformers>=4.30.0
numpy>=1.22
pandas>=1.5
tqdm>=4.64.1

# Testing & linting
pytest>=7.0
flake8>=4.0


Notes: For Windows, the sentence-transformers tokenizers and some transformer dependencies are easier to install via conda-forge (conda install -c conda-forge sentence-transformers tokenizers).


--- filename: FINAL_CHECKLIST.txt ---

FINAL CHECKLIST: Push to GitHub & Deploy to Streamlit Cloud

1) Local cleanups
   - Ensure .gitignore includes: .venv/, .streamlit/secrets.toml, cache_responses.json
   - Ensure you removed any hard-coded API keys from config files.

2) Initialize git (if not already)
   git init
   git add .
   git commit -m "Initial stabilized submission - NLTK fallback and Streamlit ready"

3) Create GitHub repo
   - Create on github.com (name: fake-news-detector)
   - Follow instructions to add remote and push:
     git remote add origin git@github.com:<you>/<repo>.git
     git branch -M main
     git push -u origin main

4) Connect Streamlit Cloud
   - On streamlit.io/cloud -> New app -> Select GitHub repo and branch main -> set file path to app.py
   - In App settings -> Secrets, add:
     [api_keys]
     OPENROUTER_API_KEY = "YOUR_OPENROUTER_KEY"

5) Test deployment
   - Use the public URL from Streamlit Cloud.
   - If LLM results read MOCK or FALLBACK, check logs for "key" or "quota" messages.

6) Share link with instructors/reviewers.

Rollback:
- If something breaks, revert local changes (if using git):
  git checkout -- path/to/file
- Or revert commit:
  git reset --hard HEAD~1

Short troubleshooting & FAQ (final)

Q: LLM returns fallback even though I set secrets — A: Ensure secret name matches OPENROUTER_API_KEY (or set environment variable OPENROUTER_API_KEY) and redeploy app in Streamlit Cloud. Check app logs for startup messages.

Q: Streamlit Cloud fails installing dependencies — A: Move heavy packages (tokenizers) to conda. For Cloud, try reducing pinned versions or pre-building a lightweight requirements file (without heavy packages) if you only need mock mode.

Q: Professor asks for non-LLM run — They can run the app without secrets or uncheck Use LLM (in advanced options).