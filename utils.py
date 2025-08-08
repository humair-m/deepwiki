import logging
from typing import Any
import tiktoken

# Configure logging with structured format
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler('doc_api.log'), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

def count_tokens(text: Any, model: str = "gpt-4o") -> int:
    """Count tokens in text with robust error handling."""
    if text is None:
        return 0
    if hasattr(text, '__iter__') and not isinstance(text, (str, bytes)):
        try:
            text = ''.join(str(chunk) for chunk in text)
        except Exception as e:
            logger.warning(f"Failed to convert iterable to string: {str(e)}")
            return 0
    try:
        encoding = tiktoken.encoding_for_model(model)
        return len(encoding.encode(str(text)))
    except Exception as e:
        logger.warning(f"Token counting failed for model {model}: {str(e)}")
        try:
            return len(str(text).split())
        except Exception:
            logger.error(f"Fallback token counting failed: {str(e)}")
            return 0

def create_documentation_prompt(code_content: str, output_format: str = "markdown", lang: str = "typescript") -> str:
    """Generate a documentation prompt based on output format and language."""
    lang = lang.lower()
    if output_format.lower() == "markdown":
        if lang in ["typescript", "javascript"]:
            return f"""
Generate **comprehensive and professional documentation** in **GitHub-flavored Markdown** for the following {lang} code:
```lang
{code_content}
```
The documentation must include:

## 📄 1. Module Overview
- **Purpose**: Describe the script/module's purpose.
- **Category**: e.g., API Client, Database Manager, Utility.
- **Key Features**: List major capabilities.

## 🧠 2. Function and Class Documentation
For each function, class, and interface, provide:
### 🧾 Signature
```lang
function functionName(param1: Type, ...): ReturnType
```
### 📥 Parameters
| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| param1 | string | Yes | — | Parameter description |
### 📤 Returns
| Type | Description |
|------|-------------|
| boolean | Description of return value |
### ⚠️ Raises
| Exception | Condition |
|-----------|-----------|
| Error | Description of error condition |
### 💻 Example Usage
```lang
const result = functionName("example");
```
## 🧪 3. Edge Cases & Error Handling
| Edge Case | Expected Behavior |
|-----------|-------------------|
| Invalid input | Throw TypeError |
## 💡 4. Notes, Dependencies & Best Practices
- **Dependencies**: List required packages.
- **Limitations**: Describe assumptions or bottlenecks.
- **Best Practices**: Usage recommendations.
## 📊 5. Mermaid Flowchart
```mermaid
flowchart TD
    A[Start] --> B[Function Call]
    B --> C{{Condition}}
    C -->|Yes| D[Success Path]
    C -->|No| E[Error Path]
    D --> F[End]
    E --> F
```
Replace with actual logic flow from the code.
"""
        else:
            return f"""
Generate **comprehensive and professional documentation** in **GitHub-flavored Markdown** for the following {lang} code:
```lang
{code_content}
```
The documentation must include:

## 📄 1. Module Overview
- **Purpose**: Describe the script/module's purpose.
- **Category**: e.g., Data Processing, Utility.
- **Key Features**: List major capabilities.

## 🧠 2. Function and Class Documentation
For each function and class, provide:
### 🧾 Signature
```lang
def function_name(param1: Type, ...) -> ReturnType:
```
### 📥 Parameters
| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| param1 | str | Yes | — | Parameter description |
### 📤 Returns
| Type | Description |
|------|-------------|
| bool | Description of return value |
### ⚠️ Raises
| Exception | Condition |
|-----------|-----------|
| ValueError | Invalid input |
### 💻 Example Usage
```lang
result = function_name("example")
```
## 🧪 3. Edge Cases & Error Handling
| Edge Case | Expected Behavior |
|-----------|-------------------|
| Invalid input | Raise ValueError |
## 💡 4. Notes, Dependencies & Best Practices
- **Dependencies**: List required packages.
- **Limitations**: Describe assumptions or bottlenecks.
- **Best Practices**: Usage recommendations.
## 📊 5. Mermaid Flowchart
```mermaid
flowchart TD
    A[Start] --> B[Function Call]
    B --> C{{Condition}}
    C -->|Yes| D[Success Path]
    C -->|No| E[Error Path]
    D --> F[End]
    E --> F
```
Replace with actual logic flow from the code.
"""
    elif output_format.lower() == "json":
        return f"""
Generate structured JSON documentation for the following {lang} code:
```lang
{code_content}
```
The JSON must include:
- "module": {"purpose": str, "category": str, "key_features": list[str]}
- "functions": list[dict] with keys: "signature", "parameters", "returns", "raises", "example"
- "edge_cases": list[dict] with keys: "case", "behavior"
- "notes": {"dependencies": list[str], "limitations": list[str], "best_practices": list[str]}
- "flowchart": str (Mermaid.js syntax)
"""
    else:
        raise ValueError(f"Unsupported output format: {output_format}")
