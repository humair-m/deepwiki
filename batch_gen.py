import os
import logging
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any, Optional
from api_doc import DocumentationAPI
from tqdm import tqdm
import fnmatch

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('batch_doc_generation.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class BatchDocGenerator:
    """Class to generate documentation for the open-swe repository in batches."""
    def __init__(
        self,
        workspace_path: str,
        db_path: str = "llm_docs.db",
        api_base_url: str = "https://text.pollinations.ai/openai/v1/chat/completions",
        api_token: str = "16VFCmZKXdSxDlpU",
        batch_size: int = 100,
        max_workers: int = 30,
        include_patterns: List[str] = ["*.ts", "*.tsx", "*.js"],
        exclude_patterns: List[str] = ["node_modules", "dist", "build", ".git", "*.test.ts", "*.spec.ts"],
        output_format: str = "markdown",
        model: str = "gpt-4o",
        temperature: float = 0.7
    ):
        """
        Initialize the batch documentation generator for the open-swe repository.

        Args:
            workspace_path: Path to the open-swe repository
            db_path: Path to the SQLite database
            api_base_url: Pollination API base URL
            api_token: API token for Pollination API
            batch_size: Number of files to process in a single batch
            max_workers: Maximum number of concurrent workers
            include_patterns: File patterns to include (e.g., ["*.ts", "*.tsx", "*.js"])
            exclude_patterns: Directories or patterns to exclude
            output_format: Output format ("markdown" or "json")
            model: AI model to use
            temperature: Generation temperature
        """
        self.workspace_path = Path(workspace_path)
        self.doc_api = DocumentationAPI(db_path, api_base_url, api_token, retries=15)
        self.batch_size = batch_size
        self.max_workers = max_workers
        self.include_patterns = include_patterns
        self.exclude_patterns = exclude_patterns
        self.output_format = output_format
        self.model = model
        self.temperature = temperature
        if not self.workspace_path.exists():
            raise ValueError(f"Workspace path {workspace_path} does not exist")

    def _get_files(self) -> List[Path]:
        """Recursively find files matching include/exclude patterns."""
        files = []
        for pattern in self.include_patterns:
            for file in self.workspace_path.rglob(pattern):
                if not any(fnmatch.fnmatch(str(file), f"**/{exclude}/**") or fnmatch.fnmatch(str(file), exclude) for exclude in self.exclude_patterns):
                    files.append(file)
        logger.info(f"Found {len(files)} files in {self.workspace_path}")
        return files

    def _process_file(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """Process a single file and generate documentation."""
        try:
            lang = "typescript" if file_path.suffix in [".ts", ".tsx"] else "javascript"
            result = self.doc_api.generate_documentation_from_file(
                file_path=str(file_path),
                model=self.model,
                temperature=self.temperature,
                save_to_db=True,
                output_format=self.output_format,
                lang=lang
            )
            logger.info(f"Successfully generated documentation for {file_path}")
            return {
                "file_path": str(file_path),
                "doc_id": result.get("doc_id"),
                "tokens_used": result["metadata"].tokens_used,
                "generation_time": result["metadata"].generation_time
            }
        except Exception as e:
            logger.error(f"Failed to process {file_path}: {e}")
            return None

    def generate_batch_documentation(self) -> Dict[str, Any]:
        """
        Generate documentation for all files in the open-swe repository in batches.

        Returns:
            Dictionary with statistics and results
        """
        files = self._get_files()
        total_files = len(files)
        processed = 0
        failed = 0
        results = []

        with tqdm(total=total_files, desc="Processing files", unit="file") as pbar:
            for i in range(0, total_files, self.batch_size):
                batch = files[i:i + self.batch_size]
                logger.info(f"Processing batch {i // self.batch_size + 1} ({len(batch)} files)")
                with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                    future_to_file = {executor.submit(self._process_file, file): file for file in batch}
                    for future in as_completed(future_to_file):
                        file = future_to_file[future]
                        processed += 1
                        try:
                            result = future.result()
                            if result:
                                results.append(result)
                            else:
                                failed += 1
                        except Exception as e:
                            logger.error(f"Error processing {file}: {e}")
                            failed += 1
                        pbar.update(1)
                        pbar.set_postfix({"Processed": processed, "Failed": failed})

        self.doc_api.close()
        return {
            "total_files": total_files,
            "processed": processed,
            "failed": failed,
            "results": results
        }

def main():
    """Main function to run the batch documentation generator."""
    workspace_path = "/home/humair/deepwiki/open-swe"  # Path to your open-swe repository
    try:
        batch_generator = BatchDocGenerator(
            workspace_path=workspace_path,
            batch_size=100,
            max_workers=30,
            include_patterns=["*.ts", "*.tsx", "*.js"],
            exclude_patterns=["node_modules", "dist", "build", ".git", "*.test.ts", "*.spec.ts"],
            output_format="markdown",
            model="gpt-4o",
            temperature=0.7
        )
        stats = batch_generator.generate_batch_documentation()
        logger.info(f"Completed: {stats['processed']} processed, {stats['failed']} failed")
        logger.info(f"Results: {len(stats['results'])} documents generated")
    except Exception as e:
        logger.error(f"Batch processing failed: {e}")

if __name__ == "__main__":
    main()
