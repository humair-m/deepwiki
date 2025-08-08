# batch.py
import logging
import fnmatch
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
from docgen import DocumentationGenerator, CONFIG

logger = logging.getLogger(__name__)

class BatchProcessor:
    """Parallel documentation generator for large codebases"""
    def __init__(
        self,
        workspace: str,
        include: List[str] = None,
        exclude: List[str] = None
    ):
        """
        Initialize batch processor
        
        Args:
            workspace: Path to codebase root
            include: File patterns to include (default: all code files)
            exclude: Patterns to exclude (default: common excluded dirs)
        """
        self.workspace = Path(workspace).resolve()
        self.include = include or ["*.ts", "*.tsx", "*.js", "*.py", "*.java"]
        self.exclude = exclude or ["node_modules", "dist", "build", ".git", "__pycache__"]
        self.generator = DocumentationGenerator()
        
        if not self.workspace.exists():
            raise ValueError(f"Workspace not found: {workspace}")
    
    def find_files(self) -> List[Path]:
        """Discover files matching inclusion patterns"""
        logger.info(f"Scanning {self.workspace} for files...")
        files = []
        
        for pattern in self.include:
            for file in self.workspace.rglob(pattern):
                if not any(
                    fnmatch.fnmatch(str(file), f"**/{exclude_pattern}") or
                    fnmatch.fnmatch(file.name, exclude_pattern)
                    for exclude_pattern in self.exclude
                ):
                    files.append(file)
        
        logger.info(f"Found {len(files)} files to process")
        return files
    
    def process_file(self, file_path: Path) -> Dict[str, Any]:
        """Process a single file with error handling"""
        start_time = time.time()
        file_str = str(file_path)
        
        try:
            # Determine language from extension
            ext = file_path.suffix.lower()
            lang_map = {
                ".ts": "typescript",
                ".tsx": "typescript",
                ".js": "javascript",
                ".py": "python",
                ".java": "java"
            }
            lang = lang_map.get(ext, "unknown")
            
            # Skip unknown languages
            if lang == "unknown":
                return {
                    "file": file_str,
                    "status": "skipped",
                    "reason": "Unsupported language"
                }
            
            result = self.generator.generate_from_file(
                file_str,
                lang=lang,
                output_format="markdown"
            )
            
            return {
                "file": file_str,
                "status": "success",
                "doc_id": result["doc_id"],
                "tokens": result["metadata"].tokens_used,
                "time": time.time() - start_time
            }
        except Exception as e:
            logger.error(f"Failed to process {file_str}: {str(e)}")
            return {
                "file": file_str,
                "status": "failed",
                "error": str(e)
            }
    
    def run(self, max_workers: int = 8, batch_size: int = 50) -> Dict[str, Any]:
        """
        Execute batch processing
        
        Args:
            max_workers: Max concurrent threads
            batch_size: Files per processing batch
            
        Returns:
            Processing report with statistics
        """
        files = self.find_files()
        total_files = len(files)
        results = []
        
        logger.info(f"Starting batch processing with {max_workers} workers...")
        start_time = time.time()
        
        with tqdm(total=total_files, desc="Processing files") as pbar:
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # Process in batches to manage memory
                for i in range(0, total_files, batch_size):
                    batch = files[i:i + batch_size]
                    futures = {executor.submit(self.process_file, file): file for file in batch}
                    
                    for future in as_completed(futures):
                        result = future.result()
                        results.append(result)
                        pbar.update(1)
                        pbar.set_postfix({
                            "Succeeded": len([r for r in results if r["status"] == "success"]),
                            "Failed": len([r for r in results if r["status"] == "failed"])
                        })
        
        # Generate report
        success = len([r for r in results if r["status"] == "success"])
        failed = len([r for r in results if r["status"] == "failed"])
        skipped = len([r for r in results if r["status"] == "skipped"])
        total_time = time.time() - start_time
        
        logger.info(
            f"Processed {total_files} files in {total_time:.2f} seconds: "
            f"{success} succeeded, {failed} failed, {skipped} skipped"
        )
        
        # Estimate costs
        total_tokens = sum(r["tokens"] for r in results if "tokens" in r)
        token_cost = (total_tokens / 1000) * CONFIG.api_config.get("token_price", 0.03)
        
        return {
            "total_files": total_files,
            "succeeded": success,
            "failed": failed,
            "skipped": skipped,
            "total_time": total_time,
            "total_tokens": total_tokens,
            "estimated_cost": token_cost,
            "results": results
        }
    
    def close(self):
        """Release resources"""
        self.generator.close()

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Batch documentation generator")
    parser.add_argument("workspace", help="Path to codebase")
    parser.add_argument("-w", "--workers", type=int, default=8, 
                        help="Max concurrent workers")
    parser.add_argument("-b", "--batch", type=int, default=50,
                        help="Files per batch")
    parser.add_argument("-i", "--include", nargs="+", default=["*.ts", "*.tsx"],
                        help="File patterns to include")
    parser.add_argument("-e", "--exclude", nargs="+", 
                        default=["node_modules", "dist", ".git"],
                        help="Patterns to exclude")
    args = parser.parse_args()
    
    processor = BatchProcessor(
        workspace=args.workspace,
        include=args.include,
        exclude=args.exclude
    )
    
    try:
        report = processor.run(
            max_workers=args.workers,
            batch_size=args.batch
        )
        print("\nBatch processing complete:")
        print(f"  Files processed: {report['total_files']}")
        print(f"  Succeeded: {report['succeeded']}")
        print(f"  Failed: {report['failed']}")
        print(f"  Skipped: {report['skipped']}")
        print(f"  Total tokens: {report['total_tokens']}")
        print(f"  Estimated cost: ${report['estimated_cost']:.2f}")
        print(f"  Total time: {report['total_time']:.2f} seconds")
    finally:
        processor.close()

if __name__ == "__main__":
    main()
