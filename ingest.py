# ingest.py - Module for ingesting and processing text from various sources
import io
from typing import Tuple, Dict
from langdetect import detect, LangDetectException
from PIL import Image
import pytesseract
import pdfplumber
import validators
from bs4 import BeautifulSoup
import requests
import re
from utils import hash_text

USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
HEADERS = {'User-Agent': USER_AGENT}

def normalize_whitespace(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r'\r\n?', "\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Remove hyphenation at line breaks (common in PDFs/OCR)
    text = re.sub(r'-\n(\w)', r'\1', text)
    # Remove excessive spaces before punctuation
    text = re.sub(r' ([,.!?;:])', r'\1', text)
    return text.strip()

def detect_language(text: str):
    try:
        if not text or len(text.strip()) < 10:
            return None
        return detect(text)
    except LangDetectException:
        return None

def create_metadata_from_text(text: str, source_type="paste") -> Dict:
    meta = {"source_type": source_type}
    meta["hash"] = hash_text(text[:5000])
    meta["lang"] = detect_language(text)
    return meta

def extract_text_from_url(url: str) -> Tuple[str, Dict]:
    meta = {"source_url": url}
    if not validators.url(url):
        return "", meta
    try:
        r = requests.get(url, timeout=12, headers=HEADERS)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        # Try to extract the main content block, not just all <p> tags
        # Use <article>, then fallback to <main>, then <div id="content">, then <p>
        content = None
        for selector in ["article", "main", "div#content"]:
            block = soup.select_one(selector)
            if block:
                content = block.get_text(separator=" ", strip=True)
                break
        if not content:
            # fallback: join all <p> tags
            paragraphs = [p.get_text() for p in soup.find_all("p")]
            content = (soup.title.string + "\n\n" if soup.title and soup.title.string else "") + " ".join(paragraphs)
        meta.update({"title": soup.title.string if soup.title else None, "authors": [], "publish_date": None})
    except Exception:
        return "", meta
    text = normalize_whitespace(content)
    meta["hash"] = hash_text(text[:5000])
    meta["lang"] = detect_language(text)
    return text, meta

def extract_text_from_pdf(file_bytes: bytes) -> Tuple[str, Dict]:
    meta = {"source_type": "pdf"}
    try:
        text_pages = []
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            for page in pdf.pages:
                txt = page.extract_text() or ""
                text_pages.append(txt)
        text = "\n\n".join(text_pages)
    except Exception as e:
        text = f"PDF extraction failed: {e}"
    text = normalize_whitespace(text)
    meta["hash"] = hash_text(text[:5000])
    meta["lang"] = detect_language(text)
    return text, meta

def extract_text_from_image(file_bytes: bytes) -> Tuple[str, Dict]:
    meta = {"source_type": "image"}
    txt = ""
    try:
        pytesseract.get_tesseract_version()
        img = Image.open(io.BytesIO(file_bytes)).convert("RGB")
        txt = pytesseract.image_to_string(img)
        # Second OCR pass with different config for better results (optional)
        if len(txt.strip()) < 50:
            txt2 = pytesseract.image_to_string(img, config='--psm 6')
            if len(txt2) > len(txt):
                txt = txt2
    except pytesseract.TesseractNotFoundError:
        txt = "Tesseract OCR not installed or configured in PATH."
    except Exception as e:
        txt = f"Image extraction failed: {e}"
    txt = normalize_whitespace(txt)
    meta["hash"] = hash_text(txt[:5000])
    meta["lang"] = detect_language(txt)
    return txt, meta