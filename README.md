# THEA - PDF Text Extraction & Analysis

A PDF text extraction and analysis system using Ollama's vision models.

## Prerequisites

1. **Node.js** - For running npm scripts
2. **Python 3.8+** - Core runtime
3. **Ollama** - Must be running locally with required models
4. **Poppler** - Required for PDF to image conversion

## Installation

### 1. Install Poppler

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install poppler-utils
```

**macOS:**
```bash
brew install poppler
```

**Windows:**
- Download from: https://github.com/oschwartz10612/poppler-windows/releases/
- Extract the archive
- Add the `bin` folder to your system PATH

### 2. Setup Python Environment

```bash
# Create virtual environment and install dependencies
npm run setup

# Or on Windows:
npm run setup-windows
```

### 3. Install Ollama Models

```bash
# Start Ollama service
ollama serve

# Pull required models
ollama pull gemma3:12b
ollama pull qwen3:14b
ollama pull gpt-oss:20b
```

## Usage

Process all PDF files in the current directory:

```bash
npm run thea
```

Or on Windows:
```bash
npm run thea-windows
```

To process specific files, run directly:
```bash
. venv/bin/activate
python3 thea.py "specific_file.pdf"
python3 thea.py "path/to/*.pdf"
```

## Output

Results are saved as `.thea` files with the format:
```
<original_pdf>.<timestamp>.<model>.thea
```

Each file contains:
- System prompt used (thinking)
- Model's JSON response with:
  - Extracted text
  - Character count
  - One-word description
  - Content summary

## Available Scripts

- `npm run thea` - Process all PDFs in current directory (Linux/macOS)
- `npm run thea-windows` - Process all PDFs in current directory (Windows)
- `npm run setup` - Setup virtual environment and install dependencies
- `npm run install` - Install/update Python dependencies