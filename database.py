import sqlite3
import hashlib
import json
import time
import logging
from pathlib import Path
from threading import Lock
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
from .models import DocMetadata

# Configure logging with structured format
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler('doc_api.log'), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

class DocDatabase:
    """SQLite database for storing AI-generated documentation."""
    def __init__(self, db_path: str = "llm_docs.db"):
        self.db_path = Path(db_path)
        try:
            self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
            self.conn.row_factory = sqlite3.Row
            self.lock = Lock()
            self._create_tables()
            self.conn.execute("PRAGMA cache_size = -20000")
            self.conn.execute("PRAGMA synchronous = NORMAL")
            self.conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Failed to initialize database {db_path}: {str(e)}")
            raise

    def _create_tables(self) -> None:
        """Create database schema with indexes."""
        with self.lock:
            try:
                self.conn.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    id TEXT PRIMARY KEY,
                    file_path TEXT NOT NULL,
                    content TEXT NOT NULL,
                    model TEXT NOT NULL,
                    tokens_used INTEGER NOT NULL,
                    generation_time REAL NOT NULL,
                    created_at REAL NOT NULL,
                    temperature REAL DEFAULT 0.7,
                    prompt_hash TEXT NOT NULL,
                    llm_config TEXT DEFAULT '{}',
                    dependencies TEXT DEFAULT '[]'
                )""")
                self.conn.execute("""
                CREATE TABLE IF NOT EXISTS prompts (
                    hash TEXT PRIMARY KEY,
                    prompt TEXT NOT NULL,
                    last_used REAL NOT NULL
                )""")
                self.conn.execute("""
                CREATE TABLE IF NOT EXISTS embeddings (
                    doc_id TEXT PRIMARY KEY,
                    vector BLOB NOT NULL,
                    FOREIGN KEY(doc_id) REFERENCES documents(id) ON DELETE CASCADE
                )""")
                self.conn.execute("CREATE INDEX IF NOT EXISTS idx_file_path ON documents(file_path)")
                self.conn.execute("CREATE INDEX IF NOT EXISTS idx_prompt_hash ON documents(prompt_hash)")
                self.conn.execute("CREATE INDEX IF NOT EXISTS idx_created_at ON documents(created_at)")
                self.conn.commit()
            except sqlite3.Error as e:
                logger.error(f"Failed to create tables: {str(e)}")
                raise

    @staticmethod
    def _generate_doc_id(file_path: str, prompt_hash: str) -> str:
        """Generate a unique document ID."""
        return hashlib.sha256(f"{file_path}:{prompt_hash}".encode()).hexdigest()[:20]

    @staticmethod
    def _hash_prompt(prompt: str) -> str:
        """Generate a hash for the prompt."""
        return hashlib.sha256(prompt.encode()).hexdigest()

    def save_document(
        self,
        content: Union[str, bytes],
        metadata: DocMetadata,
        prompt: str,
        vector: Optional[bytes] = None
    ) -> str:
        """Save documentation to the database."""
        with self.lock:
            try:
                if isinstance(content, bytes):
                    content = content.decode('utf-8')
                elif not isinstance(content, str):
                    content = str(content)
                prompt_hash = self._hash_prompt(prompt)
                metadata.prompt_hash = prompt_hash
                doc_id = self._generate_doc_id(metadata.file_path, prompt_hash)
                self.conn.execute("""
                INSERT OR REPLACE INTO prompts (hash, prompt, last_used)
                VALUES (?, ?, ?)
                """, (prompt_hash, prompt, time.time()))
                self.conn.execute("""
                INSERT OR REPLACE INTO documents (
                    id, file_path, content, model, tokens_used,
                    generation_time, created_at, temperature,
                    prompt_hash, llm_config, dependencies
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    doc_id,
                    metadata.file_path,
                    content,
                    metadata.model,
                    metadata.tokens_used,
                    metadata.generation_time,
                    metadata.created_at.timestamp() if metadata.created_at else time.time(),
                    metadata.temperature,
                    prompt_hash,
                    json.dumps(metadata.llm_config),
                    json.dumps(metadata.dependencies)
                ))
                if vector:
                    self.conn.execute("""
                    INSERT OR REPLACE INTO embeddings (doc_id, vector)
                    VALUES (?, ?)
                    """, (doc_id, vector))
                self.conn.commit()
                logger.info(f"Saved document with ID: {doc_id}")
                return doc_id
            except sqlite3.Error as e:
                logger.error(f"Failed to save document: {str(e)}")
                self.conn.rollback()
                raise

    def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a document by its ID."""
        with self.lock:
            try:
                row = self.conn.execute("""
                SELECT d.*, p.prompt
                FROM documents d
                JOIN prompts p ON d.prompt_hash = p.hash
                WHERE d.id = ?
                """, (doc_id,)).fetchone()
                if not row:
                    logger.warning(f"Document not found: {doc_id}")
                    return None
                return {
                    'id': row['id'],
                    'file_path': row['file_path'],
                    'content': row['content'],
                    'model': row['model'],
                    'tokens_used': row['tokens_used'],
                    'generation_time': row['generation_time'],
                    'created_at': datetime.fromtimestamp(row['created_at']),
                    'temperature': row['temperature'],
                    'prompt_hash': row['prompt_hash'],
                    'llm_config': json.loads(row['llm_config']),
                    'dependencies': json.loads(row['dependencies']),
                    'prompt': row['prompt']
                }
            except sqlite3.Error as e:
                logger.error(f"Failed to retrieve document {doc_id}: {str(e)}")
                return None

    def get_documents_by_path(self, file_path: str) -> List[Dict[str, Any]]:
        """Retrieve all documents for a file path."""
        with self.lock:
            try:
                rows = self.conn.execute("""
                SELECT d.*, p.prompt
                FROM documents d
                JOIN prompts p ON d.prompt_hash = p.hash
                WHERE d.file_path = ?
                ORDER BY d.created_at DESC
                """, (file_path,)).fetchall()
                return [
                    {
                        'id': row['id'],
                        'file_path': row['file_path'],
                        'content': row['content'],
                        'model': row['model'],
                        'tokens_used': row['tokens_used'],
                        'generation_time': row['generation_time'],
                        'created_at': datetime.fromtimestamp(row['created_at']),
                        'temperature': row['temperature'],
                        'prompt_hash': row['prompt_hash'],
                        'llm_config': json.loads(row['llm_config']),
                        'dependencies': json.loads(row['dependencies']),
                        'prompt': row['prompt']
                    }
                    for row in rows
                ]
            except sqlite3.Error as e:
                logger.error(f"Failed to retrieve documents for {file_path}: {str(e)}")
                return []

    def delete_document(self, doc_id: str) -> bool:
        """Delete a document by its ID."""
        with self.lock:
            try:
                cursor = self.conn.cursor()
                cursor.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
                deleted = cursor.rowcount > 0
                self.conn.commit()
                if deleted:
                    logger.info(f"Deleted document: {doc_id}")
                else:
                    logger.warning(f"Document not found for deletion: {doc_id}")
                return deleted
            except sqlite3.Error as e:
                logger.error(f"Failed to delete document {doc_id}: {str(e)}")
                return False

    def close(self) -> None:
        """Close the database connection."""
        with self.lock:
            try:
                if hasattr(self, 'conn'):
                    self.conn.execute("VACUUM")
                    self.conn.close()
                    logger.info("Database connection closed")
            except sqlite3.Error as e:
                logger.error(f"Failed to close database: {str(e)}")
