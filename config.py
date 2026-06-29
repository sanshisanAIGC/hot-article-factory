"""热搜文章工厂 - 配置"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

def _env(k, d=""): return os.getenv(k, d).strip()

DEEPSEEK_API_KEY = _env("DEEPSEEK_API_KEY")
DEEPSEEK_BASE_URL = _env("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
DEEPSEEK_MODEL = _env("DEEPSEEK_MODEL", "deepseek-v4-pro")

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"

# 发布时段
PUBLISH_TIMES = ["07:30", "12:00", "18:30"]

def validate_config() -> list[str]:
    missing = []
    if not DEEPSEEK_API_KEY:
        missing.append("DEEPSEEK_API_KEY")
    return missing
