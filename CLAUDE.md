# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

THEA is a comprehensive PDF processing and financial document analysis system that combines:
1. **Multi-pipeline PDF extraction** with three distinct approaches (image, text, deep learning)
2. **AI-powered document analysis** using Ollama models with retry logic and pattern detection
3. **Financial account analysis system** for processing bank statements and investment documents

The system processes 618+ financial documents across 6 account types, extracting structured data and generating comprehensive markdown reports with German formatting standards.

## Architecture

### Pipeline System

The modular pipeline architecture (`pipelines/` directory) consists of:

1. **`pdf-extract-png` Pipeline** - Extracts PDF pages as PNG images for vision models
   - Class: `PdfExtractPngPipeline` in `pipelines/pdf_extract_png.py`
   - Converts PDFs to base64-encoded PNG images using pdf2image/poppler
   - Saves PNG sidecar files when `--save-sidecars` is enabled
   - Optimized for Gemma models with thinking tag support

2. **`pdf-extract-txt` Pipeline** - Extracts text using multiple methods for text-only models
   - Class: `PdfExtractTxtPipeline` in `pipelines/pdf_extract_txt.py`
   - Runs PyPDF2, pdfplumber, and pymupdf extractors in parallel
   - Saves text extraction sidecar files when `--save-sidecars` is enabled
   - Optimized for Qwen models without thinking tags in JSON output

3. **`pdf-extract-docling` Pipeline** - Advanced extraction using IBM Docling deep learning
   - Class: `PdfExtractDoclingPipeline` in `pipelines/pdf_extract_docling.py`
   - Uses Docling's ML models for complex documents with tables/formulas
   - Saves `.docling.txt`, `.docling.json`, and `.docling.md` sidecar files
   - Falls back to gemma3:27b when confidence < 0.7
   - Requires: `pip install docling` (includes torch dependencies, ~3.5GB)

### Core Processing Flow

The main `process_with_model()` function in `thea.py:348` orchestrates:

1. **Skip Mode Logic** - Intelligent file skipping with different patterns (`thea.py:1536-1568`)
   - Normal mode: Checks for specific `.thea_extract` files
   - Sidecars-only mode: Broader pattern matching for ANY existing sidecar files
2. **Pipeline Processing** - Runs selected pipeline to extract content
3. **Ollama API Streaming** - Sends to model with chunk-by-chunk processing (endpoint: `https://b1s.hey.bahn.business/api/chat`)
4. **Pattern Detection** - Monitors for stuck responses (1-100 char repetitions, `thea.py:688-750`)
5. **Temperature Scaling** - Progressive increase (0.1→1.0) on retries
6. **Thinking Tag Extraction** - `<thinking>` for gemma, `<think>` for qwen
7. **JSON Response Cleaning** - Handles markdown blocks and validates JSON
8. **Result Persistence** - Saves to `.thea_extract` files with v2.0 metadata format

### Financial Account Analysis System

Specialized scripts for analyzing financial documents:

- **`Konten.py`** - Base library with shared functionality (320 lines)
  - `BaseKontoAnalyzer` class for document processing
  - German date/number formatting utilities
  - Document type classification from docling metadata
  - Markdown report generation

- **`Depotkonto.py`** - Analyzes depot/investment accounts
  - MiFID II cost extraction logic (lines 586-608)
  - ISIN code processing and transaction categorization
  - Color-coded sales transactions in markdown

- **`Girokonto.py`** - Analyzes checking accounts
  - Transaction categorization and balance tracking
  - Monthly/yearly aggregation functions

- **`Geldmarktkonto.py`** - Analyzes money market accounts
  - Interest rate extraction and analysis

## Common Development Commands

### Setup and Dependencies

```bash
# Initial setup
npm run setup                # Linux/macOS
npm run setup-windows        # Windows

# Activate virtual environment
. venv/bin/activate          # Linux/macOS
venv\Scripts\activate        # Windows

# Install/update dependencies
pip install -r requirements.txt

# Install Docling (optional, for advanced extraction)
pip install docling
```

### Running THEA

```bash
# Using npm scripts with default prompts
npm run thea:pdf-extract-png     # Image extraction with Gemma
npm run thea:pdf-extract-txt     # Text extraction with Qwen
npm run thea:pdf-extract-docling # Docling extraction with gemma3:27b

# Sidecar-only mode (extraction without AI analysis)
npm run thea:sidecars:png        # Extract PNG images only (skip existing)
npm run thea:sidecars:txt        # Extract text only (skip existing)
npm run thea:sidecars:docling    # Docling extraction only (skip existing)

# Force regeneration of sidecars
npm run thea:sidecars:png-force     # Force PNG extraction
npm run thea:sidecars:txt-force     # Force text extraction
npm run thea:sidecars:docling-force # Force Docling extraction

# Account documents processing (docs/ folder with 618 PDFs)
npm run thea:konten:docling      # Process all account PDFs (~2-3 hours)
npm run thea:konten:docling-windows  # Windows version

# Generate account analysis reports
python3 Depotkonto.py    # Analyze depot accounts
python3 Girokonto.py     # Analyze checking accounts
python3 Geldmarktkonto.py # Analyze money market accounts

# Direct execution with options
python3 thea.py --pipeline pdf-extract-png --model gemma3:27b "*.pdf"
python3 thea.py --pipeline pdf-extract-txt --model qwen3:30b "*.pdf"
python3 thea.py --pipeline pdf-extract-docling --model gemma3:27b "*.pdf"

# Key parameters
--pipeline <type>      # pdf-extract-png, pdf-extract-txt, or pdf-extract-docling
--save-sidecars        # Save PNG images or text extractions
--sidecars-only        # Generate sidecars without model processing
--max-attempts <n>     # Retry attempts for stuck patterns (1-10)
--temperature <value>  # Initial temperature (0.0-2.0, default: 0.1)
--mode <skip|overwrite> # Skip existing or overwrite
--dpi <number>         # Image resolution (50-600, default: 300)
--format <json|none>   # JSON enforcement or allow thinking tags
```

### Clean Generated Files

```bash
# Clean all THEA files
python3 thea.py --clean                  # With confirmation
python3 thea.py --clean --force          # No confirmation
python3 thea.py --clean --dry-run        # Preview only

# Pipeline-specific cleaning
npm run thea:clean:txt                   # Clean text pipeline files
npm run thea:clean:png                   # Clean PNG pipeline files
npm run thea:clean:docling              # Clean Docling pipeline files

# With dry-run option
npm run thea:clean:txt-dry              # Preview text cleanup
npm run thea:clean:png-dry              # Preview PNG cleanup
npm run thea:clean:docling-dry          # Preview Docling cleanup

# Force clean (no confirmation)
npm run thea:clean:txt-force            # Force clean text files
npm run thea:clean:png-force            # Force clean PNG files
npm run thea:clean:docling-force        # Force clean Docling files
```

### Testing

```bash
# Test thinking tag extraction
python3 test_thinking.py

# Test with sample document
python3 thea.py --mode overwrite --save-sidecars sample_document.pdf

# Process financial documents with specific prompts
python3 thea.py --prompt prompts/bank_konto_kontoauszuege_v2.prompt "Belege/*.pdf"
```

## Critical Model Differences

### Hardcoded System Prompt Issue
**WARNING**: `thea.py:53` contains a hardcoded prefix that always adds thinking tag instructions:
```python
prefix = "You are a vision-based text extractor and analyzer. Always use <thinking></thinking> tags..."
```

This causes conflicts between models:
- **Gemma models**: MUST use `<thinking>` tags BEFORE outputting JSON to prevent corruption
- **Qwen models**: MUST NOT use thinking tags when outputting JSON (causes parsing failures)

### Model-Specific Prompt Configuration

**For Qwen Models** (`prompts/pdf-extract-txt.prompt`):
```json
{
  "system_prompt": {
    "suffix": "...Output ONLY valid JSON. Do NOT use thinking tags..."
  },
  "settings": {
    "format": "json",
    "temperature": 0.2
  }
}
```

**For Gemma Models** (`prompts/pdf-extract-png.prompt`):
```json
{
  "system_prompt": {
    "suffix": "...Use <thinking> tags for analysis, then output JSON..."
  },
  "settings": {
    "format": "json",
    "temperature": 0.15
  }
}
```

## Key Implementation Details

### Critical Functions

**`clean_json_response(response_text)`** (`thea.py:278-390`)
- Central response parsing function
- Extracts both `<thinking>` and `<think>` tags
- Handles markdown code blocks (`\`\`\`json`)
- Multiple fallback strategies for JSON extraction
- Critical for Gemma/Qwen model compatibility

**`process_with_model()`** (`thea.py:348`)
- Core processing orchestrator
- Handles retry logic with temperature scaling
- Pattern detection for stuck responses (`thea.py:688-750`)
- Streaming response handling

**Pattern Detection Thresholds** (`thea.py:688-750`)
- 1-char: 50+ repetitions
- 2-char: 25+ repetitions
- 3-10 char: 10+ repetitions
- Longer patterns: fewer repetitions needed

**Temperature Scaling Formula**
```python
temperature = initial_temp + (retry_count * (1.0 - initial_temp) / max_attempts)
```

### Financial Document Processing

**Cost Extraction** (`Depotkonto.py:586-608`)
```python
# CRITICAL: Total costs = Service costs + Depot fees (NOT just one component!)
cost_info['total_costs'] = cost_info['service_costs'] + cost_info['depot_fees']
```

**German Formatting** (`Konten.py`)
- `format_number_german()`: Converts 1,234.56 to 1.234,56
- `format_date_german()`: Converts YYYY-MM-DD to DD.MM.YYYY
- Currency/percentage symbols only in table headers, never in cells

### Pipeline Selection Priority
1. Prompt file `settings.pipeline`
2. CLI `--pipeline` override
3. Auto-detect: qwen→txt, gemma→png
4. Default: `pdf-extract-png`

## File Naming Conventions

### Output Files
- **Main results**: `<pdf>.<timestamp>.<model>.<suffix>.thea_extract`
- **PNG sidecars**: `<pdf>.<timestamp>.<model>.<suffix>.<dpi>p<page>.png`
- **Text sidecars**: `<pdf>.<timestamp>.<model>.<suffix>.<extractor>.txt`
- **Docling sidecars**: `<pdf>.<timestamp>.<model>.<suffix>.docling.{txt,json,md}`

Timestamp format: `YYYYMMDD_HHMMSS`
Extractors: `pypdf2`, `pdfplumber`, `pymupdf`, `docling`

## Account Documents Structure

The `docs/` folder contains 618 PDF documents organized into 6 account folders:
- `BLUEITS-Depotkonto-7274079/` - 314 files (depot/investment account)
- `BLUEITS-Geldmarktkonto-21503990/` - 55 files (money market account)
- `BLUEITS-Girokonto-200750750/` - 59 files (checking account)
- `Ramteid-Depotkonto-7274087/` - 88 files (depot/investment account)
- `Ramteid-Geldmarktkonto-21504006/` - 43 files (money market account)
- `Ramteid-Girokonto-21377502/` - 59 files (checking account)

## Processing Rates and Performance
- **pdf-extract-png**: ~45-60 seconds per PDF
- **pdf-extract-txt**: ~5-10 seconds per PDF
- **pdf-extract-docling**: ~37 seconds per PDF (1.6 files/minute)

## Environment Variables
- `OLLAMA_API_URL`: Override default Ollama endpoint (default: https://b1s.hey.bahn.business/api/chat)
- `THEA_DEFAULT_MODEL`: Default model if not specified (default: gemma3:27b)
- `THEA_DEFAULT_PIPELINE`: Default pipeline if not auto-detected (default: pdf-extract-png)

## Troubleshooting

### Model outputs thinking tags instead of JSON
- **Root cause**: Hardcoded system prompt prefix encourages thinking tags
- **Qwen fix**: Explicitly add "Do NOT use thinking tags" in prompt file
- **Gemma fix**: Ensure "Use thinking THEN output JSON separately"

### Poppler not found (PNG pipeline)
- Linux/macOS: `sudo apt-get install poppler-utils` or `brew install poppler`
- Windows: Download from GitHub, add bin folder to PATH
- Verify: `pdftoppm -h`

### Case sensitivity in file patterns
- Windows filesystems may have uppercase extensions (.PDF)
- Scripts handle both .pdf and .PDF patterns
- Glob patterns include both cases: `*.pdf`, `*.PDF`