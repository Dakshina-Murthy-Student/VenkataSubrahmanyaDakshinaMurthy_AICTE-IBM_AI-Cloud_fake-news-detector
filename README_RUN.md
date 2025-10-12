 ---

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
