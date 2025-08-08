# database.py
import sqlite3
import json
import hashlib
import logging
from pathlib import Path
from threading import Lock
from typing import Dict, Any, List, Optional
from datetime import datetime
from .config import CONFIG
from .models import DocMetadata

logger = logging.getLogger(__name__)

class DocDatabase:
    """Thread-safe SQLite database handler"""
    def __init__(self):
        self.config = CONFIG.db_config
        self.db_path = Path(self.config.get('path', 'llm_docs.db'))
        self.lock = Lock()
        self.conn = self._initialize_db()
    
    def _initialize_db(self) -> sqlite3.Connection:
        """Initialize database with schema"""
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA cache_size = -20000")
        conn.execute("PRAGMA synchronous = NORMAL")
        
        with conn:
            conn.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY,
                file_path TEXT NOT NULL,
                content TEXT NOT NULL,
                metadata TEXT NOT NULL,
                created_at REAL DEFAULT (datetime('now'))
            )""")
            conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_file_path 
            ON documents(file_path)
            """)
        return conn

    def save_document(self, content: str, metadata: DocMetadata) -> str:
        """Save document with metadata"""
        doc_id = hashlib.sha256(
            f"{metadata.file_path}:{metadata.model}".encode()
        ).hexdigest()[:20]
        
        with self.lock, self.conn:
            self.conn.execute("""
            INSERT OR REPLACE INTO documents (id, file_path, content, metadata)
            VALUES (?, ?, ?, ?)
            """, (
                doc_id,
                metadata.file_path,
                content,
                json.dumps({
                    "model": metadata.model,
                    "tokens_used": metadata.tokens_used,
                    "generation_time": metadata.generation_time,
                    "temperature": metadata.temperature
                })
            ))
        logger.info(f"Saved document: {doc_id}")
        return doc_id

    def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve document by ID"""
        with self.lock:
            row = self.conn.execute(
                "SELECT * FROM documents WHERE id = ?",
                (doc_id,)
            ).fetchone()
            if not row:
                return None
            return {
                "id": row["id"],
                "content": row["content"],
                "metadata": json.loads(row["metadata"]),
                "file_path": row["file_path"],
                "created_at": datetime.fromtimestamp(row["created_at"])
            }

    def close(self):
        """Cleanup database resources"""
        with self.lock:
            self.conn.close()
            logger.info("Database connection closed")
