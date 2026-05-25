"""Centralized configuration loaded from environment variables.

Loading order (first non-empty wins):
  1. Shell environment variable (e.g. `$env:GOOGLE_API_KEY=...`)
  2. Values in `gradeops/.env` (loaded via python-dotenv from an ABSOLUTE
     path resolved from this file's location — robust to whatever CWD
     uvicorn was launched with)
  3. Class-level defaults below
"""
from pathlib import Path

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict


# backend/config.py → ../ → gradeops/ → .env  (absolute path, CWD-independent)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_ENV_FILE = _PROJECT_ROOT / ".env"

if _ENV_FILE.exists():
    load_dotenv(_ENV_FILE, override=False)


class Settings(BaseSettings):
    # --- LLM provider selection ----------------------------------------
    # 'google'    : Gemini via langchain-google-genai (FREE tier)
    # 'anthropic' : Claude via langchain-anthropic   (paid)
    llm_provider: str = "google"

    # --- Google Gemini -------------------------------------------------
    # 2.5-flash-lite has the highest free-tier quota of any vision-capable
    # Gemini (15 RPM / 1000 RPD) — picked for reliability over peak quality.
    google_api_key: str = ""
    grader_model_google: str = "gemini-2.5-flash-lite"

    # --- Anthropic Claude (paid; used only if LLM_PROVIDER=anthropic) --
    anthropic_api_key: str = ""
    grader_model_anthropic: str = "claude-sonnet-4-20250514"

    # --- Database ------------------------------------------------------
    database_url: str = "sqlite:///./gradeops.db"

    # --- OCR routing ---------------------------------------------------
    ocr_backend: str = "hosted"

    # --- Storage -------------------------------------------------------
    storage_root: str = "./storage"

    # --- Grader behavior -----------------------------------------------
    grader_num_passes: int = 1            # 1 keeps free-tier-friendly; 5 matches the multi-pass design
    grader_critic_retry: int = 0          # set to 1 to enable critic→scorer retry

    # --- Rate-limit throttling -----------------------------------------
    # Seconds between successive LLM calls. Gemini free tier = 15 RPM,
    # so the safe floor is 4s. We default to 4.5s with a small jitter
    # cushion so even rapid back-to-back uploads stay under quota.
    llm_min_gap_seconds: float = 4.5

    # --- Plagiarism ----------------------------------------------------
    plagiarism_threshold: float = 0.82
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"

    # --- Versioning ----------------------------------------------------
    prompt_version: str = "v1.0"
    schema_version: str = "v1.0"

    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE) if _ENV_FILE.exists() else None,
        env_file_encoding="utf-8-sig",
        extra="ignore",
        case_sensitive=False,
    )

    @property
    def storage_path(self) -> Path:
        p = Path(self.storage_root)
        (p / "pdfs").mkdir(parents=True, exist_ok=True)
        (p / "pages").mkdir(parents=True, exist_ok=True)
        (p / "crops").mkdir(parents=True, exist_ok=True)
        return p

    @property
    def grader_model(self) -> str:
        if (self.llm_provider or "google").lower() == "anthropic":
            return self.grader_model_anthropic
        return self.grader_model_google


settings = Settings()
