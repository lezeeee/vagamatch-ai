"""Server-only configuration. No key or secret is returned to the browser."""
import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]
MODEL = 'gpt-4.1-mini-2025-04-14'
LOCAL_MODEL = 'qwen3:4b-instruct-2507-q4_K_M'
LOCAL_API = 'http://127.0.0.1:11434'


@dataclass(frozen=True)
class Settings:
    mode: str = 'ollama'
    api_key: str = field(default='', repr=False)
    allow_paid_api: bool = False

    @property
    def ready(self) -> bool:
        return self.mode in {'demo', 'ollama'} or (self.mode == 'openai' and bool(self.api_key) and self.allow_paid_api)


def get_settings() -> Settings:
    # Read configuration again on each request, so local setup needs no server restart.
    values = {**dotenv_values(ROOT / '.env'), **os.environ}
    return Settings(
        mode=str(values.get('VAGAMATCH_MODE', 'ollama')).strip().lower(),
        api_key=str(values.get('OPENAI_API_KEY') or '').strip(),
        allow_paid_api=str(values.get('VAGAMATCH_ALLOW_PAID_API', 'false')).lower() == 'true',
    )
