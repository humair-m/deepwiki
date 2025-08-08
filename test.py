# batch.py
import logging
import fnmatch
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
from .api import DocumentationGenerator
from .config import CONFIG

logger = logging.getLogger(__name__)

class BatchProcessor:
    """Parallel documentation generator"""
    def __init__(
        self,
        workspace: str,
        include: List[str] = ("*.ts", "*.tsx"),
        exclude: List[str] = ("node_modules", "dist", ".git")
    ):
        self.workspace = Path(workspace)
        self.include = include
        self.exclude = exclude
        self.generator = DocumentationGenerator()
    
    def find_files(self) -> List[Path]:
        """Discover files matching patterns"""
        files = []
        for pattern in self.include:
            for file in self.workspace.rglob(pattern):
                if not any(fnmatch.fnmatch(file, f"**/{e}/**") for e in self.exclude):
                    files.append(file)
        logger.info(f"Found {len(files)} files to process")
        return files
    
    def process_file(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """Process single file handler"""
        try:
            lang = "typescript" if file_path.suffix in (".ts", ".tsx") else "javascript"
            result = self.generator.generate_from_file(
                str(file_path),
                lang=lang,
                output_format="markdown"
            )
            return {
                "file": str(file_path),
                "doc_id": result["doc_id"],
                "tokens": result["metadata"].tokens_used,
                "time": result["metadata"].generation_time
            }
        except Exception as e:
            logger.error(f"Failed {file_path}: {e}")
            return None
    
    def run(self, workers: int = 8, batch_size: int = 50) -> Dict[str, Any]:
        """Execute batch processing"""
        files = self.find_files()
        results = []
        failed = 0
        
        with tqdm(total=len(files), ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {}
            for batch in [files[i:i+batch_size] for i in range(0, len(files), batch_size)]:
                for file in batch:
                    futures[executor.submit(self.process_file, file)] = file
            
            for future in as_completed(futures):
                file = futures[future]
                if result := future.result():
                    results.append(result)
                else:
                    failed += 1
                tqdm.update(1)
        
        self.generator.close()
        return {
            "total": len(files),
            "succeeded": len(results),
            "failed": failed,
            "results": results
        }

def main():
    processor = BatchProcessor(
        workspace="/path/to/project",
        include=["*.ts", "*.tsx"],
        exclude=["node_modules", "dist"]
    )
    report = processor.run(workers=16)
    logger.info(
        f"Processed {report['total']} files: "
        f"{report['succeeded']} succeeded, "
        f"{report['failed']} failed"
    )

if __name__ == "__main__":
    main()
