"""
Centralized configuration for the Page Pass AI Agent.

All magic numbers, model names, thresholds, and environment-driven settings
live here so they can be tuned in one place without touching business logic.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ──────────────────────────────────────────────
# Gemini / LLM Settings
# ──────────────────────────────────────────────
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL_NAME: str = os.getenv("GEMINI_MODEL", "gemma-4-31b-it")
BATCH_SIZE: int = int(os.getenv("BATCH_SIZE", "20"))

# ──────────────────────────────────────────────
# PDF Extraction Settings
# ──────────────────────────────────────────────
TFIDF_THRESHOLD: float = float(os.getenv("TFIDF_THRESHOLD", "0.05"))
PDF_WINDOW_BEFORE: int = 500   # characters before the matched spec
PDF_WINDOW_AFTER: int = 1000   # characters after the matched spec
TFIDF_WINDOW_SIZE: int = 1500  # characters extracted on a Tier-2 match

# ──────────────────────────────────────────────
# API / Networking
# ──────────────────────────────────────────────
API_HOST: str = os.getenv("API_HOST", "http://localhost:8000")
API_AUDIT_ENDPOINT: str = f"{API_HOST}/api/v1/audit"
API_REQUEST_TIMEOUT: int = int(os.getenv("API_TIMEOUT", "300"))  # seconds
