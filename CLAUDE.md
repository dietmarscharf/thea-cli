# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

THEA is a comprehensive PDF processing and financial document analysis system that combines:
1. **Multi-pipeline PDF extraction** with three distinct approaches (image, text, deep learning)
2. **AI-powered document analysis** using Ollama models with retry logic and pattern detection
3. **Financial account analysis system** for processing bank statements and investment documents

The system processes 618+ financial documents across 6 account types, extracting structured data and generating comprehensive markdown reports. Output files use the `.thea_extract` extension with additional sidecar files for metadata.

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

### Account Document Analysis System

The repository includes specialized scripts for analyzing financial documents:

- **`Konten.py`** - Base library with shared functionality
  - `BaseKontoAnalyzer` class for document processing
  - Date extraction from various filename patterns
  - Document type classification from docling metadata
  - Markdown report generation utilities

- **`Depotkonto.py`** - Analyzes depot/investment accounts (1084 lines)
  - Processes ISIN codes and transaction types
  - Extracts detailed trading information (shares, execution prices, fees, profit/loss)
  - **Cost information extraction with MiFID II compliance:**
    - Dienstleistungskosten (service/trading costs)
    - Übergreifende Kosten (depot fees)
    - Automatic VAT calculation (19% German USt)
    - Handles pipe-separated table formats
  - Generates `BLUEITS-Depotkonto.md` and `Ramteid-Depotkonto.md`

- **`Girokonto.py`** - Analyzes checking accounts
  - Transaction categorization and balance tracking
  - Generates `BLUEITS-Girokonto.md` and `Ramteid-Girokonto.md`

- **`Geldmarktkonto.py`** - Analyzes money market accounts
  - Interest rate analysis features
  - Generates `BLUEITS-Geldmarktkonto.md` and `Ramteid-Geldmarktkonto.md`

### Core Processing Flow

The main `process_with_model()` function in `thea.py:348` orchestrates:

1. **Skip Mode Logic** - Intelligent file skipping with different patterns
2. **Pipeline Processing** - Runs selected pipeline to extract content
3. **Ollama API Streaming** - Sends to model with chunk-by-chunk processing
4. **Pattern Detection** - Monitors for stuck responses (1-100 char repetitions)
5. **Temperature Scaling** - Progressive increase (0.1→1.0) on retries
6. **Thinking Tag Extraction** - `<thinking>` for gemma, `<think>` for qwen
7. **JSON Response Cleaning** - Handles markdown blocks and validates JSON
8. **Result Persistence** - Saves to `.thea_extract` files with v2.0 metadata format

### Critical Model Differences

- **Gemma models**: MUST use `<thinking>` tags BEFORE outputting JSON to prevent corruption
- **Qwen models**: MUST NOT use thinking tags when outputting JSON (causes parsing failures)
- **Hardcoded prefix** (thea.py:53): Always adds "Always use <thinking></thinking> tags" to system prompt

## Common Development Commands

### Running THEA

```bash
# Using npm scripts with default prompts
npm run thea:pdf-extract-png     # Image extraction with Gemma
npm run thea:pdf-extract-txt     # Text extraction with Qwen
npm run thea:pdf-extract-docling # Docling extraction with gemma3:27b

# Account documents processing (docs/ folder with 618 PDFs)
npm run thea:konten:docling      # Process all account PDFs (~2-3 hours)

# Generate account analysis reports
python3 Depotkonto.py    # Analyze depot accounts
python3 Girokonto.py     # Analyze checking accounts
python3 Geldmarktkonto.py # Analyze money market accounts

# Direct execution with options
python3 thea.py --pipeline pdf-extract-png --model gemma3:27b "*.pdf"
python3 thea.py --pipeline pdf-extract-txt --model qwen3:30b "*.pdf"
python3 thea.py --pipeline pdf-extract-docling --model gemma3:27b "*.pdf"
```

### Testing and Debugging

```bash
# Test thinking tag extraction
python3 test_thinking.py

# Debug depot extraction issues
python3 fix_depot_extraction.py

# Test with sample document
python3 thea.py --mode overwrite --save-sidecars sample_document.pdf
```

### Clean Generated Files

```bash
# Clean all THEA files
python3 thea.py --clean                  # With confirmation
python3 thea.py --clean --force          # No confirmation

# Pipeline-specific cleaning
python3 thea.py --clean --pipeline txt
python3 thea.py --clean --pipeline png
python3 thea.py --clean --pipeline docling
```

## Key Implementation Details

### Critical Functions

**`clean_json_response(response_text)`** (thea.py:278-390)
- Central response parsing function
- Extracts both `<thinking>` and `<think>` tags
- Handles markdown code blocks
- Multiple fallback strategies for JSON extraction

**`extract_cost_information()`** (Depotkonto.py:516-623)
- Extracts MiFID II cost information from depot documents
- Handles both pipe-separated and space-separated formats
- Calculates VAT splits (19% German USt)
- Pattern matching for Dienstleistungskosten and Übergreifende Kosten

**`extract_depot_balance()`** (Depotkonto.py:240-514)
- Extracts depot balances and share counts from statements
- Detects document types (cost_information vs depot_statement)
- Handles German number formatting (1.234,56)
- Multiple fallback patterns for table extraction

### Pattern Detection Thresholds
- 1-char: 50+ repetitions
- 2-char: 25+ repetitions
- 3-10 char: 10+ repetitions
- Longer patterns: fewer repetitions needed

### Temperature Scaling Formula
```python
temperature = initial_temp + (retry_count * (1.0 - initial_temp) / max_attempts)
```

## Account Documents Structure

The `docs/` folder contains 618 PDF documents organized into 6 account folders:
- `BLUEITS-Depotkonto-7274079/` - 314 files (depot/investment account)
- `BLUEITS-Geldmarktkonto-21503990/` - 55 files (money market account)
- `BLUEITS-Girokonto-200750750/` - 59 files (checking account)
- `Ramteid-Depotkonto-7274087/` - 88 files (depot/investment account)
- `Ramteid-Geldmarktkonto-21504006/` - 43 files (money market account)
- `Ramteid-Girokonto-21377502/` - 59 files (checking account)

## Known Issues and Solutions

### Cost Extraction in Financial Documents

When working with depot cost information:
- Service costs (Dienstleistungskosten) and depot fees (Übergreifende Kosten) must be extracted separately
- Total costs = Service costs + Depot fees (not just one component)
- All amounts in documents are gross (including 19% VAT)
- Use patterns that handle pipe separators: `r'Dienstleistungskosten\s*\|\s*([\d.,]+)\s*€'`

### Model outputs thinking tags instead of JSON
- **Root cause**: Hardcoded system prompt prefix encourages thinking tags
- **Qwen fix**: Explicitly add "Do NOT use thinking tags" in prompt file
- **Gemma fix**: Ensure "Use thinking THEN output JSON separately"

### Poppler not found (PNG pipeline)
- Linux/macOS: `sudo apt-get install poppler-utils` or `brew install poppler`
- Windows: Download from GitHub, add bin folder to PATH
- Verify: `pdftoppm -h`

## File Naming Conventions

### Output Files
- **Main results**: `<pdf>.<timestamp>.<model>.<suffix>.thea_extract`
- **PNG sidecars**: `<pdf>.<timestamp>.<model>.<suffix>.<dpi>p<page>.png`
- **Text sidecars**: `<pdf>.<timestamp>.<model>.<suffix>.<extractor>.txt`
- **Docling sidecars**: `<pdf>.<timestamp>.<model>.<suffix>.docling.{txt,json,md}`

Timestamp format: `YYYYMMDD_HHMMSS`

## Processing Rates
- **pdf-extract-png**: ~45-60 seconds per PDF
- **pdf-extract-txt**: ~5-10 seconds per PDF
- **pdf-extract-docling**: ~37 seconds per PDF (1.6 files/minute)

## Environment Variables

- `OLLAMA_API_URL`: Override default Ollama endpoint (default: https://b1s.hey.bahn.business/api/chat)
- `THEA_DEFAULT_MODEL`: Default model if not specified (default: gemma3:27b)
- `THEA_DEFAULT_PIPELINE`: Default pipeline if not auto-detected (default: pdf-extract-png)