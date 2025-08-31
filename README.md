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

## Available Pipelines

THEA supports three PDF extraction pipelines:

1. **pdf-extract-png** - Vision-based extraction using Ollama models on PDF page images
   - Best for: Complex layouts, scanned documents, documents with images
   - Models: gemma3:27b (default), any vision-capable Ollama model

2. **pdf-extract-txt** - Pure text extraction using multiple libraries 
   - Best for: Text-heavy documents, fast processing, non-vision models
   - Extractors: PyPDF2, pdfplumber, pymupdf (runs all in parallel)

3. **pdf-extract-docling** - Advanced extraction using IBM's Docling deep learning models
   - Best for: Complex documents with tables, formulas, multi-column layouts
   - Features: Structure preservation, table extraction, layout analysis
   - Fallback: Uses gemma3:27b when extraction confidence is low
   - Note: Requires `pip install docling` (large download with torch dependencies)

## Available Scripts

### Pipeline-specific commands:
- `npm run thea:pdf-extract-png` - Process PDFs using vision extraction
- `npm run thea:pdf-extract-txt` - Process PDFs using text extraction  
- `npm run thea:pdf-extract-docling` - Process PDFs using Docling (requires installation)

### General commands:
- `npm run setup` - Setup virtual environment and install dependencies
- `npm run install` - Install/update Python dependencies