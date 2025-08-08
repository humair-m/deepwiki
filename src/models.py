# models.py
from dataclasses import dataclass
from datetime import datetime
from typing import List, Dict, Optional

@dataclass
class Message:
    role: str
    content: str

@dataclass
class ChatCompletionChunk:
    id: str
    model: str
    choices: List[Dict[str, Any]]
    created: int = 0
    system_fingerprint: Optional[str] = None

    def get_content(self) -> str:
        return self.choices[0].get('delta', {}).get('content', '') if self.choices else ''

@dataclass
class DocMetadata:
    file_path: str
    model: str
    tokens_used: int
    generation_time: float
    temperature: float = 0.7
    created_at: datetime = datetime.now()
