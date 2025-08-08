# client.py
import json
import logging
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from urllib.parse import urlencode
from typing import List, Iterator, Optional, Dict, Any
from .models import Message, ChatCompletionChunk
from .config import CONFIG

logger = logging.getLogger(__name__)

class APIClient:
    """Enhanced API client with retry and timeout handling"""
    def __init__(self):
        self.config = CONFIG.api_config
        self.base_url = self.config['base_url'].rstrip('/')
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.config['token']}"
        })
        self._setup_retry()
    
    def _setup_retry(self):
        retry = Retry(
            total=self.config.get('retries', 3),
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["POST"]
        )
        adapter = HTTPAdapter(max_retries=retry)
        self.session.mount("https://", adapter)
    
    def _handle_stream(self, response) -> Iterator[Dict[str, Any]]:
        for line in response.iter_lines():
            if not line:
                continue
            if line.startswith(b'data: '):
                data = line[6:].decode('utf-8')
                if data == '[DONE]':
                    return
                try:
                    yield json.loads(data)
                except json.JSONDecodeError:
                    logger.warning("Failed to parse SSE data")

    def chat_completion(
        self,
        messages: List[Message],
        model: Optional[str] = None,
        stream: bool = True,
        **kwargs
    ) -> Iterator[ChatCompletionChunk]:
        params = {
            "model": model or self.config.get('default_model', 'gpt-4o'),
            "stream": stream,
            "temperature": self.config.get('default_temperature', 0.7),
            "max_tokens": self.config.get('max_tokens', 4000),
            **kwargs
        }
        payload = {
            "messages": [{"role": msg.role, "content": msg.content} for msg in messages],
            **params
        }
        
        try:
            with self.session.post(
                self.base_url,
                json=payload,
                stream=stream,
                timeout=self.config.get('timeout', 30.0)
            ) as response:
                response.raise_for_status()
                for data in self._handle_stream(response):
                    yield ChatCompletionChunk(
                        id=data.get('id', ''),
                        model=data.get('model', ''),
                        choices=data.get('choices', []),
                        created=data.get('created', 0),
                        system_fingerprint=data.get('system_fingerprint')
                    )
        except requests.RequestException as e:
            logger.error(f"API request failed: {e}")
            raise
