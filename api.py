import time
import logging
from typing import Dict, Any, Optional, List
from pathlib import Path
from .client import PollinationClient
from .database import DocDatabase
from .models import Message, DocMetadata
from .utils import count_tokens, create_documentation_prompt

# Configure logging with structured format
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler('doc_api.log'), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

class DocumentationAPI:
    """API for generating and managing AI-powered documentation."""
    def __init__(
        self,
        db_path: str = "llm_docs.db",
        api_base_url: str = "https://text.pollinations.ai/openai/v1/chat/completions",
        api_token: str = "16VFCmZKXdSxDlpU",
        retries: int = 30
    ):
        """Initialize the Documentation API with configurable parameters."""
        self.client = PollinationClient(api_base_url, api_token, retries)
        self.database = DocDatabase(db_path)
        self.api_token = api_token
        self.prompt_cache: Dict[str, str] = {}

    def _read_file(self, file_path: str) -> str:
        """Read file content with error handling."""
        try:
            file_path = Path(file_path)
            if not file_path.exists():
                raise FileNotFoundError(f"File not found: {file_path}")
            with file_path.open('r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            logger.error(f"Failed to read file {file_path}: {str(e)}")
            raise

    def generate_documentation_from_file(
        self,
        file_path: str,
        model: str = "gpt-4o",
        temperature: float = 0.7,
        save_to_db: bool = True,
        output_format: str = "markdown",
        lang: str = "typescript"
    ) -> Dict[str, Any]:
        """
        Generate documentation from a source file.

        Args:
            file_path: Path to the source file.
            model: AI model to use for generation.
            temperature: Sampling temperature for generation.
            save_to_db: Whether to save the result to the database.
            output_format: Desired output format ("markdown" or "json").
            lang: Programming language of the source file.

        Returns:
            Dictionary with generated content, metadata, and optional doc_id.
        """
        try:
            code_content = self._read_file(file_path)
            prompt = create_documentation_prompt(code_content, output_format, lang)
            return self.generate_documentation(
                prompt=prompt,
                file_path=file_path,
                model=model,
                temperature=temperature,
                save_to_db=save_to_db,
                output_format=output_format
            )
        except Exception as e:
            logger.error(f"Error generating documentation from file {file_path}: {str(e)}")
            raise

    def generate_documentation(
        self,
        prompt: str,
        file_path: str,
        model: str = "gpt-4o",
        temperature: float = 0.7,
        save_to_db: bool = True,
        output_format: str = "markdown"
    ) -> Dict[str, Any]:
        """
        Generate documentation using the AI API.

        Args:
            prompt: Prompt for documentation generation.
            file_path: Path to the file being documented.
            model: AI model to use.
            temperature: Sampling temperature.
            save_to_db: Whether to save to database.
            output_format: Output format ("markdown" or "json").

        Returns:
            Dictionary with generated content, metadata, and optional doc_id.
        """
        logger.info(f"Starting documentation generation for {file_path}")
        start_time = time.time()
        try:
            messages = [Message(role="system", content=prompt)]
            response_chunks = []
            for chunk in self.client.chat_completion(
                messages=messages,
                model=model,
                temperature=temperature,
                token=self.api_token
            ):
                response_chunks.append(chunk.get_content())
            response_text = ''.join(response_chunks)
            generation_time = time.time() - start_time
            tokens_used = count_tokens(response_text, model)
            metadata = DocMetadata(
                file_path=file_path,
                model=model,
                tokens_used=tokens_used,
                generation_time=generation_time,
                prompt_hash="",
                temperature=temperature,
                llm_config={"max_tokens": 12000, "token": self.api_token}
            )
            result = {'content': response_text, 'metadata': metadata}
            if save_to_db:
                doc_id = self.database.save_document(
                    content=response_text,
                    metadata=metadata,
                    prompt=prompt
                )
                result['doc_id'] = doc_id
            logger.info(f"Documentation generated for {file_path} ({tokens_used} tokens, {generation_time:.2f}s)")
            return result
        except Exception as e:
            logger.error(f"Failed to generate documentation for {file_path}: {str(e)}")
            raise

    def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a document by its ID."""
        try:
            return self.database.get_document(doc_id)
        except Exception as e:
            logger.error(f"Error retrieving document {doc_id}: {str(e)}")
            return None

    def list_documents(self, file_path: str) -> List[Dict[str, Any]]:
        """List all documents for a given file path."""
        try:
            return self.database.get_documents_by_path(file_path)
        except Exception as e:
            logger.error(f"Error listing documents for {file_path}: {str(e)}")
            return []

    def delete_document(self, doc_id: str) -> bool:
        """Delete a document by its ID."""
        try:
            return self.database.delete_document(doc_id)
        except Exception as e:
            logger.error(f"Error deleting document {doc_id}: {str(e)}")
            return False

    def close(self) -> None:
        """Close the database connection."""
        try:
            self.database.close()
            logger.info("DocumentationAPI closed")
        except Exception as e:
            logger.error(f"Error closing DocumentationAPI: {str(e)}")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
