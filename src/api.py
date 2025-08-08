# api.py
import time
import logging
from typing import Dict, Any, Optional
from .client import APIClient
from .database import DocDatabase
from .models import Message, DocMetadata
from .utils import count_tokens, create_prompt, read_file

logger = logging.getLogger(__name__)

class DocumentationGenerator:
    """Core documentation generation API"""
    def __init__(self):
        self.client = APIClient()
        self.db = DocDatabase()
    
    def generate_from_file(
        self,
        file_path: str,
        lang: str = "typescript",
        output_format: str = "markdown",
        **kwargs
    ) -> Dict[str, Any]:
        """Generate docs from source file"""
        try:
            code = read_file(file_path)
            prompt = create_prompt(code, lang, output_format)
            return self._generate_docs(prompt, file_path, **kwargs)
        except Exception as e:
            logger.error(f"File processing failed: {file_path} - {e}")
            raise
    
    def _generate_docs(
        self,
        prompt: str,
        file_path: str,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        save_db: bool = True
    ) -> Dict[str, Any]:
        """Execute documentation generation"""
        start = time.time()
        messages = [Message(role="system", content=prompt)]
        response = ""
        
        # Stream and accumulate response
        for chunk in self.client.chat_completion(messages, model=model):
            response += chunk.get_content()
        
        # Create metadata
        gen_time = time.time() - start
        tokens = count_tokens(response, model or CONFIG.api_config['default_model'])
        metadata = DocMetadata(
            file_path=file_path,
            model=model,
            tokens_used=tokens,
            generation_time=gen_time,
            temperature=temperature or CONFIG.api_config['default_temperature']
        )
        
        # Save to database
        doc_id = self.db.save_document(response, metadata) if save_db else None
        
        logger.info(
            f"Generated docs for {file_path} - "
            f"{tokens} tokens in {gen_time:.2f}s"
        )
        return {
            "content": response,
            "metadata": metadata,
            "doc_id": doc_id
        }
    
    def close(self):
        """Release resources"""
        self.db.close()
