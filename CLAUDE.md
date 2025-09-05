# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

THEA is a comprehensive PDF processing and financial document analysis system that combines:
1. **Multi-pipeline PDF extraction** with three distinct approaches (image, text, deep learning)
2. **AI-powered document analysis** using Ollama models with retry logic and pattern detection
3. **Financial account analysis system** for processing bank statements and investment documents

The system processes 618+ financial documents across 6 account types, extracting structured data and generating comprehensive markdown reports. Output files use the `.thea_extract` extension with additional sidecar files for metadata.

## Core Architecture

### Pipeline System (`pipelines/`)

The modular pipeline architecture supports three extraction methods:

1. **`pdf-extract-png`** - Vision-based extraction
   - Class: `PdfExtractPngPipeline` in `pipelines/pdf_extract_png.py`
   - Converts PDFs to base64-encoded PNG images using pdf2image/poppler
   - Optimized for Gemma models with thinking tag support
   - Saves PNG sidecar files when `--save-sidecars` is enabled

2. **`pdf-extract-txt`** - Text extraction for non-vision models
   - Class: `PdfExtractTxtPipeline` in `pipelines/pdf_extract_txt.py`
   - Runs PyPDF2, pdfplumber, and pymupdf extractors in parallel
   - Optimized for Qwen models (no thinking tags in JSON)
   - Saves text extraction sidecar files when `--save-sidecars` is enabled

3. **`pdf-extract-docling`** - Deep learning extraction
   - Class: `PdfExtractDoclingPipeline` in `pipelines/pdf_extract_docling.py`
   - Uses IBM Docling ML models for complex layouts with tables/formulas
   - Falls back to gemma3:27b when confidence < 0.7
   - Saves `.docling.txt`, `.docling.json`, and `.docling.md` sidecar files
   - Requires: `pip install docling` (includes torch dependencies, ~3.5GB)

### Financial Document Analysis System

**Base Library (`Konten.py`)**
- `BaseKontoAnalyzer` class provides shared functionality
- `format_date_german()` - Converts ISO dates to DD.MM.YYYY format
- `extract_document_type_from_docling()` - Classifies documents with special handling for MiFID II cost reports
- `generate_document_table()` - Creates markdown tables with German date formatting
- `extract_date_from_filename()` - Handles patterns: YYYYMMDD, vom_DD_MM_YYYY, DD.MM.YYYY

**Depot Account Analysis (`Depotkonto.py`)**
- `DepotkontoAnalyzer` class for investment account processing
- **Critical cost extraction logic (lines 522-636):**
  - Extracts Dienstleistungskosten (service costs) with pipe separator handling
  - Extracts Übergreifende Kosten (depot fees) separately
  - Total costs = Service costs + Depot fees (NOT just one component)
  - All amounts are gross (including 19% VAT)
  - Net calculation: Gross ÷ 1.19
- **Document type detection (lines 114-144):**
  - Special detection for 5 MiFID II cost reports (Ex-Post Reports)
  - Pattern matching for dates: vom_22_04_2021, vom_28_04_2022, vom_15_05_2023, vom_24_04_2024, vom_28_04_2025
- Generates `BLUEITS-Depotkonto.md` and `Ramteid-Depotkonto.md`

**Other Account Types:**
- `Girokonto.py` - Checking account analysis with transaction categorization
- `Geldmarktkonto.py` - Money market account analysis with interest rate tracking

### Core Processing Flow (`thea.py`)

The main `process_with_model()` function (line 348) orchestrates:
1. **Skip Mode Logic** - Different patterns for normal vs sidecar-only mode
2. **Pipeline Processing** - Runs selected pipeline to extract content
3. **Ollama API Streaming** - Chunk-by-chunk processing with https://b1s.hey.bahn.business/api/chat
4. **Pattern Detection** - Monitors for stuck responses (1-100 char repetitions)
5. **Temperature Scaling** - Progressive increase (0.1→1.0) on retries
6. **Thinking Tag Extraction** - `<thinking>` for gemma, `<think>` for qwen
7. **JSON Response Cleaning** (`clean_json_response()` lines 278-390)
8. **Result Persistence** - Saves to `.thea_extract` files with v2.0 metadata

### Critical Model Differences

- **Gemma models**: MUST use `<thinking>` tags BEFORE outputting JSON
- **Qwen models**: MUST NOT use thinking tags when outputting JSON
- **Hardcoded prefix** (thea.py:53): Always adds "Always use <thinking></thinking> tags" to system prompt

## Essential Commands

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
# Process all account documents (618 PDFs in docs/)
npm run thea:konten:docling      # ~2-3 hours for full processing
npm run thea:konten:docling-windows  # Windows version

# Generate account analysis reports
python3 Depotkonto.py    # Analyze depot accounts
python3 Girokonto.py     # Analyze checking accounts
python3 Geldmarktkonto.py # Analyze money market accounts

# Direct execution with pipeline selection
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
```

### Testing and Debugging

```bash
# Test thinking tag extraction
python3 test_thinking.py

# Debug depot extraction issues (if exists)
python3 fix_depot_extraction.py

# Test with sample document
python3 thea.py --mode overwrite --save-sidecars sample_document.pdf

# Process specific account documents
python3 thea.py --prompt prompts/pdf-extract-docling.prompt "docs/BLUEITS-Depotkonto-7274079/*.pdf"
```

### Cleaning Generated Files

```bash
# Clean all THEA files
python3 thea.py --clean                  # With confirmation
python3 thea.py --clean --force          # No confirmation
python3 thea.py --clean --dry-run        # Preview only

# Pipeline-specific cleaning
python3 thea.py --clean --pipeline txt
python3 thea.py --clean --pipeline png
python3 thea.py --clean --pipeline docling
```

## Account Documents Structure

The `docs/` folder contains 618 PDF documents:
- `BLUEITS-Depotkonto-7274079/` - 314 files
- `BLUEITS-Geldmarktkonto-21503990/` - 55 files
- `BLUEITS-Girokonto-200750750/` - 59 files
- `Ramteid-Depotkonto-7274087/` - 88 files
- `Ramteid-Geldmarktkonto-21504006/` - 43 files
- `Ramteid-Girokonto-21377502/` - 59 files

## Critical Implementation Details

### Cost Extraction Pattern Fixes

When extracting financial costs from depot documents:
```python
# Correct patterns for service costs (handles pipe separators)
service_patterns = [
    r'Dienstleistungskosten\s*\|\s*([\d.,]+)\s*€',  # With pipe separator
    r'Dienstleistungskosten[^\d]+([\d.,]+)\s*€'     # General pattern
]

# Total costs calculation (CRITICAL)
total_costs = service_costs + depot_fees  # NOT just service_costs alone!
```

### Document Type Classification

The system uses a priority-based classification in `Konten.py`:
1. Check for specific MiFID II cost report dates (5 known documents)
2. Filename pattern matching (Ex-Post-Rep with specific dates → Kostenaufstellung)
3. Fallback to docling.json metadata
4. Default to "Document" if unclassified

### German Number Formatting

- Input: `1.234,56` (German) → Convert: `.replace('.', '').replace(',', '.')` → Output: `1234.56` (Python)
- Display: Use `format_date_german()` for dates (DD.MM.YYYY format)

### Pattern Detection Thresholds

Stuck response detection in `thea.py`:
- 1-char: 50+ repetitions
- 2-char: 25+ repetitions
- 3-10 char: 10+ repetitions

### File Naming Conventions

- **Main results**: `<pdf>.<timestamp>.<model>.<suffix>.thea_extract`
- **Sidecars**: `<pdf>.<timestamp>.<model>.<suffix>.<type>.<ext>`
- **Timestamp**: `YYYYMMDD_HHMMSS`

## Known Issues and Solutions

### Model outputs thinking tags instead of JSON
- **Root cause**: Hardcoded system prompt prefix
- **Qwen fix**: Add "Do NOT use thinking tags" in prompt
- **Gemma fix**: Ensure "Use thinking THEN output JSON"

### Poppler not found (PNG pipeline)
- Linux: `sudo apt-get install poppler-utils`
- macOS: `brew install poppler`
- Windows: Download from GitHub, add bin to PATH

### Cost extraction showing incorrect totals
- Ensure both Dienstleistungskosten AND Übergreifende Kosten are extracted
- Check for pipe separators in table format
- Verify VAT calculations (19% German USt)

## Processing Performance

- **pdf-extract-png**: ~45-60 seconds per PDF
- **pdf-extract-txt**: ~5-10 seconds per PDF
- **pdf-extract-docling**: ~37 seconds per PDF

## Environment Variables

- `OLLAMA_API_URL`: Override Ollama endpoint (default: https://b1s.hey.bahn.business/api/chat)
- `THEA_DEFAULT_MODEL`: Default model (default: gemma3:27b)
- `THEA_DEFAULT_PIPELINE`: Default pipeline (default: pdf-extract-png)