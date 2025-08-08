# test.py
import unittest
import tempfile
import os
import sqlite3
import json
from unittest.mock import MagicMock, patch
from pathlib import Path
from docgen import (
    DocumentationGenerator,
    DocDatabase,
    DocMetadata,
    Message,
    ChatCompletionChunk,
    count_tokens,
    read_file
)

class TestDocumentationGenerator(unittest.TestCase):
    @patch('docgen.APIClient')
    def setUp(self, mock_client):
        self.mock_client = mock_client.return_value
        self.mock_client.chat_completion.return_value = [
            ChatCompletionChunk(
                id="test",
                model="gpt-4o",
                choices=[{"delta": {"content": "Test documentation content"}}]
            )
        ]
        self.generator = DocumentationGenerator()
        
        # Create temp file
        self.temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".ts")
        self.temp_file.write(b"function test() { return true; }")
        self.temp_file.close()
    
    def tearDown(self):
        os.unlink(self.temp_file.name)
        if hasattr(self, 'db'):
            self.db.close()
    
    def test_generate_from_file(self):
        result = self.generator.generate_from_file(self.temp_file.name)
        
        self.assertIn("content", result)
        self.assertIn("metadata", result)
        self.assertEqual(result["content"], "Test documentation content")
        self.assertEqual(result["metadata"].file_path, self.temp_file.name)
        
    def test_generate_from_file_missing(self):
        with self.assertRaises(FileNotFoundError):
            self.generator.generate_from_file("/invalid/path/file.ts")
    
    @patch('docgen.read_file')
    def test_file_read_error(self, mock_read):
        mock_read.side_effect = Exception("Read error")
        with self.assertRaises(Exception):
            self.generator.generate_from_file(self.temp_file.name)
    
    def test_count_tokens(self):
        text = "This is a test string"
        self.assertGreater(count_tokens(text, "gpt-4o"), 0)
        self.assertEqual(count_tokens("", "gpt-4o"), 0)

class TestDocDatabase(unittest.TestCase):
    def setUp(self):
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self.db_path = self.temp_db.name
        self.db = DocDatabase()
        
        self.metadata = DocMetadata(
            file_path="test.ts",
            model="gpt-4o",
            tokens_used=100,
            generation_time=2.5
        )
    
    def tearDown(self):
        self.db.close()
        os.unlink(self.db_path)
    
    def test_save_and_retrieve(self):
        doc_id = self.db.save_document("Test content", self.metadata)
        document = self.db.get_document(doc_id)
        
        self.assertIsNotNone(document)
        self.assertEqual(document["content"], "Test content")
        self.assertEqual(document["metadata"]["model"], "gpt-4o")
        self.assertEqual(document["file_path"], "test.ts")
    
    def test_retrieve_nonexistent(self):
        self.assertIsNone(self.db.get_document("invalid_id"))
    
    def test_thread_safety(self):
        from threading import Thread
        results = []
        
        def save_doc(i):
            metadata = DocMetadata(
                file_path=f"file_{i}.ts",
                model="gpt-4o",
                tokens_used=i * 10,
                generation_time=0.5
            )
            doc_id = self.db.save_document(f"Content {i}", metadata)
            results.append(doc_id)
        
        threads = [Thread(target=save_doc, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        self.assertEqual(len(results), 10)
        for doc_id in results:
            self.assertIsNotNone(self.db.get_document(doc_id))

if __name__ == "__main__":
    unittest.main()
