# utils.py
import tiktoken
import logging
from pathlib import Path
from .config import CONFIG

logger = logging.getLogger(__name__)

def count_tokens(text: str, model: str) -> int:
    """Accurately count tokens for a given model"""
    try:
        encoder = tiktoken.encoding_for_model(model)
        return len(encoder.encode(text))
    except KeyError:
        logger.warning(f"Using fallback token counter for {model}")
        return len(text.split())  # Fallback

def read_file(file_path: str) -> str:
    """Safe file reader with validation"""
    path = Path(file_path)
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(f"Invalid file: {file_path}")
    return path.read_text(encoding='utf-8')

def create_prompt(code: str, lang: str, output_format: str) -> str:
    """Generate prompt using configured templates"""
    template = CONFIG.get_prompt(output_format, lang)
    return template.format(code_content=code) if template else ""
