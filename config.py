# config.py - Configuration helper for API keys and settings
import os
from datetime import datetime, timedelta

try:
    import streamlit as st
except Exception:
    st = None

def _get_secret(key: str, default=None):
    val = os.environ.get(key)
    if val:
        return val
    try:
        if st is not None and hasattr(st, "secrets"):
            s = st.secrets.to_dict()
            if "api_keys" in s and key in s["api_keys"]:
                return s["api_keys"][key]
            if key in s:
                return s[key]
            if "metadata" in s and key in s["metadata"]:
                return s["metadata"][key]
    except Exception:
        pass
    return default

class Config:
    """
    Configuration helper:
    - OPENROUTER_API_KEY: from env or Streamlit secrets
    """
    OPENROUTER_API_KEY = _get_secret("OPENROUTER_API_KEY", _get_secret("OPENROUTER_API_KEY", ""))

    @classmethod
    def is_key_present(cls) -> bool:
        return bool(cls.OPENROUTER_API_KEY)

    @classmethod
    def is_key_valid(cls) -> bool:
        return cls.is_key_present()