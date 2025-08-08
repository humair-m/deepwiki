import json
import logging
from typing import List, Iterator, Optional, Dict, Any
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from urllib.parse import urlencode
from .models import Message, ChatCompletionChunk

# Configure logging with structured format
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler('doc_api.log'), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

class PollinationClient:
    """Client for interacting with the Pollination AI API with retry support."""
    def __init__(
        self,
        base_url: str = "https://text.pollinations.ai/openai/v1/chat/completions",
        api_token: str = "16VFCmZKXdSxDlpU",
        retries: int = 30
    ):
        self.base_url = base_url.rstrip('/')
        self.api_token = api_token
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "Accept": "text/event-stream"
        })
        retry_strategy = Retry(
            total=retries,
            backoff_factor=2,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["POST"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("https://", adapter)

    def _parse_sse_line(self, line: str) -> Optional[Dict[str, Any]]:
        """Parse a Server-Sent Events line."""
        line = line.strip()
        if not line or line.startswith(':'):
            return None
        if line.startswith('data: '):
            data_str = line[6:]
            if data_str.strip() == '[DONE]':
                return {'done': True}
            try:
                return json.loads(data_str)
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse JSON: {str(e)}")
                return None
        return None

    def chat_completion(
        self,
        messages: List[Message],
        model: str = "gpt-4o",
        stream: bool = True,
        temperature: float = 0.7,
        max_tokens: Optional[int] = 12000,
        **kwargs
    ) -> Iterator[ChatCompletionChunk]:
        """Create a chat completion with streaming support."""
        formatted_messages = [{"role": msg.role, "content": msg.content} for msg in messages]
        params = {
            "model": model,
            "stream": str(stream).lower(),
            "token": self.api_token,
            "nofeed": "false",
            "temperature": temperature
        }
        if max_tokens is not None:
            params["max_tokens"] = max_tokens
        params.update({k: v for k, v in kwargs.items() if v is not None})
        query_string = urlencode(params, doseq=True)
        url = f"{self.base_url}?{query_string}"
        payload = {"messages": formatted_messages}
        try:
            with self.session.post(url, json=payload, stream=True, timeout=30) as response:
                response.raise_for_status()
                for line in response.iter_lines(decode_unicode=True):
                    if not line:
                        continue
                    parsed = self._parse_sse_line(line)
                    if parsed is None:
                        continue
                    if parsed.get('done'):
                        break
                    yield ChatCompletionChunk(
                        id=parsed.get('id', ''),
                        object=parsed.get('object', ''),
                        created=parsed.get('created', 0),
                        model=parsed.get('model', ''),
                        choices=parsed.get('choices', []),
                        system_fingerprint=parsed.get('system_fingerprint'),
                        prompt_filter_results=parsed.get('prompt_filter_results')
                    )
        except requests.RequestException as e:
            logger.error(f"API request failed: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error processing API response: {str(e)}")
            raise

    def chat_completion_simple(
        self,
        prompt: str,
        model: str = "gpt-4o",
        temperature: float = 0.7,
        **kwargs
    ) -> str:
        """Simple chat completion returning a single string response."""
        messages = [Message(role="system", content=prompt)]
        try:
            return ''.join(chunk.get_content() for chunk in self.chat_completion(messages, model, True, temperature, **kwargs)).strip()
        except Exception as e:
            logger.error(f"Simple chat completion failed: {str(e)}")
            raise
