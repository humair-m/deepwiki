# AI-Powered Documentation Generator

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

Automatically generate professional documentation for your codebase using AI. This tool connects to the Pollination AI API to create comprehensive documentation in Markdown or JSON format for various programming languages.

## Key Features ✨

- **AI-Powered Documentation**: Generate docs using GPT-4o or other LLMs
- **Multi-Language Support**: TypeScript, JavaScript, Python, Java, and more
- **Batch Processing**: Document entire codebases in parallel
- **SQLite Storage**: Efficient document storage with metadata tracking
- **Cost Estimation**: Predict API usage costs before execution
- **Custom Templates**: Configure documentation formats via YAML

## Installation 📦

```bash
# Clone repository
git clone https://github.com/yourusername/ai-docgen.git
cd ai-docgen

# Install dependencies
pip install -r requirements.txt

# Set up configuration
cp config.example.yaml configs.yaml

# Configuration
```yaml
# configs.yaml
api:
  base_url: "https://text.pollinations.ai/openai/v1/chat/completions"
  token: "your-api-token-here"  # Replace with your actual token
  retries: 30
  default_model: "gpt-4o"
  default_temperature: 0.7
  max_tokens: 12000
  timeout: 30.0

database:
  path: "docs.db"
  
logging:
  level: "INFO"
  
prompts:
  markdown:
    typescript: |
      Generate documentation for:
      ```typescript
      {code_content}
      ```

```
---
#Usage 🚀
Single File Processing
```python

from src  import DocumentationGenerator

# Initialize generator
generator = DocumentationGenerator()

# Generate documentation for a file
result = generator.generate_from_file(
    "src/utils.ts",
    lang="typescript",
    output_format="markdown"
)```


Batch Processing (CLI)
```bash

# Process entire codebase
python batch_cli.py /path/to/project \
  --workers 12 \
  --batch 100 \
  --include "*.ts" "*.tsx" \
  --exclude "node_modules" "dist"
```
Example output:
```text

Processing files: 100%|██████████| 452/452 [12:45<00:00, 1.69s/file]
Batch processing complete:
  Files processed: 452
  Succeeded: 438
  Failed: 8
  Skipped: 6
  Total tokens: 1,234,567
  Estimated cost: $37.04
  Total time: 765.32 seconds

```
#Retrieving Documentation
```python
from src import DocDatabase

# Access stored documents
db = DocDatabase()
document = db.get_document("doc_abc123def456")

print(f"Document content:\n{document['content']}")
print(f"Metadata:\n{document['metadata']}")
```
#Customization 🎨

Modify Documentation Templates

Edit the prompts section in configs.yaml:
yaml

prompts:
  markdown:
    python: |
      Generate Python documentation with:
      ```python
      {code_content}
      ```
      
      ## Custom Section
      {custom_content}
      
      ...

#Add New Languages

    Add language detection in batch.py:
```
python

lang_map = {
    ".rs": "rust",
    ".go": "golang",
    # Add new mappings here
}
```

    Create a template in configs.yaml:

```yaml

prompts:
  markdown:
    rust: |
      Generate Rust documentation:
      ```rust
      {code_content}
      ```
      ...
```







