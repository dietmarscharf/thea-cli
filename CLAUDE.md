# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

THEA is a comprehensive PDF processing and financial document analysis system that combines:
1. **Multi-pipeline PDF extraction** with three distinct approaches (image, text, deep learning)
2. **AI-powered document analysis** using Ollama models with retry logic and pattern detection
3. **Financial account analysis system** for processing bank statements and investment documents

The system processes 618+ financial documents across 6 account types, extracting structured data and generating comprehensive HTML reports. Output files use the `.thea_extract` extension with additional sidecar files for metadata.

## High-Level Architecture

### Core Processing Flow

The main `process_with_model()` function in `thea.py:348` orchestrates:

1. **Skip Mode Logic** - Intelligent file skipping with different patterns (`thea.py:1536-1568`)
   - Normal mode: Checks for specific `.thea_extract` files
   - Sidecars-only mode: Broader pattern matching for ANY existing sidecar files
2. **Pipeline Processing** - Runs selected pipeline to extract content
3. **Ollama API Streaming** - Sends to model with chunk-by-chunk processing
4. **Pattern Detection** - Monitors for stuck responses (1-100 char repetitions)
5. **Temperature Scaling** - Progressive increase (0.1→1.0) on retries
6. **Thinking Tag Extraction** - `<thinking>` for gemma, `<think>` for qwen
7. **JSON Response Cleaning** - Handles markdown blocks and validates JSON
8. **Result Persistence** - Saves to `.thea_extract` files with v2.0 metadata format

### Pipeline System

The modular pipeline architecture (`pipelines/` directory) consists of:

1. **`pdf-extract-png` Pipeline** - Extracts PDF pages as PNG images for vision models
   - Optimized for Gemma models with thinking tag support
   
2. **`pdf-extract-txt` Pipeline** - Extracts text using multiple methods for text-only models
   - Runs PyPDF2, pdfplumber, and pymupdf extractors in parallel
   - Optimized for Qwen models without thinking tags in JSON output

3. **`pdf-extract-docling` Pipeline** - Advanced extraction using IBM Docling deep learning
   - Uses Docling's ML models for complex documents with tables/formulas
   - Falls back to gemma3:27b when confidence < 0.7
   - Requires: `pip install docling` (includes torch dependencies, ~3.5GB)

### Financial Document Processing System

The repository includes specialized scripts for analyzing financial documents:

- **`Konten.py`** - Base library with shared functionality (320 lines)
  - `BaseKontoAnalyzer` class for document processing
  - German formatting utilities: `format_number_german()`, `format_date_german()`
  
- **`Depotkonto.py`** - Analyzes depot/investment accounts
  - Fallback to docling.txt when THEA extract lacks table data via `parse_docling_table()`
  - Vertical layout detection for Sparkasse documents (lines 190-260)
  - German thousand separator handling in shares extraction (line 100)
  
- **`Girokonto.py`** - Analyzes checking accounts
- **`Geldmarktkonto.py`** - Analyzes money market accounts

## Common Development Commands

### Setup and Dependencies

```bash
# Initial setup
npm run setup                # Linux/macOS
npm run setup-windows        # Windows

# Install Docling (optional, for advanced extraction)
pip install docling
```

### Running THEA

```bash
# Using npm scripts with default prompts
npm run thea:pdf-extract-png     # Image extraction with Gemma
npm run thea:pdf-extract-txt     # Text extraction with Qwen
npm run thea:pdf-extract-docling # Docling extraction with gemma3:27b

# Account documents processing (docs/ folder with 618 PDFs)
npm run thea:konten:docling      # Process all account PDFs (~2-3 hours)
npm run thea:konten:docling-windows  # Windows version

# Generate account analysis reports
python3 Depotkonto.py    # Analyze depot accounts → BLUEITS-Depotkonto.html, Ramteid-Depotkonto.html
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
```

### Clean Generated Files

```bash
# Clean all THEA files
python3 thea.py --clean                  # With confirmation
python3 thea.py --clean --force          # No confirmation

# Pipeline-specific cleaning
npm run thea:clean:txt                   # Clean text pipeline files
npm run thea:clean:png                   # Clean PNG pipeline files
npm run thea:clean:docling              # Clean Docling pipeline files
```

### Testing

```bash
# Test thinking tag extraction
python3 test_thinking.py

# Test with sample document
python3 thea.py --mode overwrite --save-sidecars sample_document.pdf
```

## Critical Model Differences

### Hardcoded System Prompt Issue
**WARNING**: `thea.py:53` contains a hardcoded prefix that always adds thinking tag instructions. This causes conflicts between models:
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
- Handles markdown code blocks
- Critical for Gemma/Qwen model compatibility

**`process_with_model()`** (`thea.py:348`)
- Core processing orchestrator
- Handles retry logic with temperature scaling
- Pattern detection for stuck responses (`thea.py:688-750`)

**`BaseKontoAnalyzer`** (`Konten.py:16`)
- Base class for account analysis scripts
- Handles multiple date formats: YYYYMMDD, vom_DD_MM_YYYY, DD.MM.YYYY

### Pattern Detection Thresholds
- 1-char: 50+ repetitions
- 2-char: 25+ repetitions  
- 3-10 char: 10+ repetitions
- Longer patterns: fewer repetitions needed

### Temperature Scaling Formula
```python
temperature = initial_temp + (retry_count * (1.0 - initial_temp) / max_attempts)
```

### Financial Document Processing

**Cost Extraction** (`Depotkonto.py:586-608`)
```python
# CRITICAL: Total costs = Service costs + Depot fees (NOT just one component!)
cost_info['total_costs'] = cost_info['service_costs'] + cost_info['depot_fees']
```

**Transaction Processing** (`Depotkonto.py`)
- Vertical layout detection for Sparkasse documents (lines 190-260)
- German thousand separator handling in shares extraction (line 100): Pattern `r'Stück\s+([\d.]+)'` with `.replace('.', '')`

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

### Depot statement parsing issues
- Check `Depotkonto.py:673` for `parse_docling_table()` fallback logic
- Debug with: `python3 -c "from Depotkonto import DepotkontoAnalyzer; analyzer = DepotkontoAnalyzer(); result = analyzer.parse_docling_table(Path('path/to/docling.txt')); print(result)"`

### Vertical layout extraction issues (Sparkasse documents)
- Check `Depotkonto.py:190-260` for vertical layout detection logic
- Ensure EUR detection checks up to 2 lines ahead (lines 205-207)

## Recent Critical Fixes

### German Thousand Separator Issue (Fixed)
- **Problem**: Transactions with >1000 shares showed only 1 share
- **Fix**: Changed to `r'Stück\s+([\d.]+)'` and added `.replace('.', '')` at line 100 in `Depotkonto.py`

### Trailing Minus Sign in German Bookkeeping Format (Fixed)
- **Problem**: Sales transactions with losses showed "-" instead of actual loss values
- **Fix**: Added patterns in `Depotkonto.py:272-313` to handle trailing minus

### Vertical Layout Detection for Losses (Fixed)
- **Problem**: Vertical layout detection only worked for "Veräußerungsgewinn" not "Veräußerungsverlust"
- **Fix**: Updated regex at line 193 to handle both gain and loss keywords

## Key Entry Points and Functions

### Main Entry Point
- `thea.py:main()` - CLI entry point, argument parsing
- `thea.py:process_with_model()` (line 348) - Core processing orchestrator

### Pipeline Functions
- `pipelines/manager.py:PipelineManager.get_pipeline()` - Pipeline selection
- `pipelines/base.py:Pipeline.process()` - Abstract pipeline interface

### Prompt Loading
- `thea.py:load_prompt_file()` (line 25) - Load JSON/text prompts
- `thea.py:build_system_prompt()` (line 50) - Build system prompt
- `thea.py:build_user_prompt()` (line 78) - Build user prompt with substitutions

### Utility Functions
- `thea.py:clean_thea_files()` (line 89) - Clean generated files
- `thea.py:extract_thinking_content()` - Extract thinking tags
- `thea.py:clean_json_response()` - Clean and validate JSON