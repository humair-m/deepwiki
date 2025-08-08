from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, List, Optional

@dataclass
class Message:
    """Represents a chat message with role and content."""
    role: str
    content: str

    def __post_init__(self):
        valid_roles = {"user", "assistant", "system"}
        if self.role not in valid_roles:
            raise ValueError(f"Invalid role: {self.role}. Must be one of {valid_roles}")

@dataclass
class ChatCompletionChunk:
    """Represents a streaming chunk from the API response."""
    id: str
    object: str
    created: int
    model: str
    choices: List[Dict[str, Any]]
    system_fingerprint: Optional[str] = None
    prompt_filter_results: Optional[List[Dict[str, Any]]] = None

    def get_content(self) -> str:
        """Extract content from the first choice's delta."""
        if self.choices and len(self.choices) > 0:
            delta = self.choices[0].get('delta', {})
            return delta.get('content', '')
        return ''

    def is_finished(self) -> bool:
        """Check if the chunk indicates completion."""
        return bool(self.choices and len(self.choices) > 0 and self.choices[0].get('finish_reason'))

@dataclass
class DocMetadata:
    """Metadata for generated documentation."""
    file_path: str
    model: str
    tokens_used: int
    generation_time: float
    prompt_hash: str
    temperature: float = 0.7
    llm_config: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    created_at: Optional[datetime] = field(default_factory=datetime.now)
