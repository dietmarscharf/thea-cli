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

### Text Extractors

The text pipeline uses multiple extractors (`extractors/` directory):
- **PyPDF2Extractor**: Basic text extraction, confidence ~0.8
- **PdfPlumberExtractor**: Advanced extraction with table support, confidence ~0.9
- **PyMuPDFExtractor**: Fast extraction with formatting, confidence ~1.0
- **DoclingExtractor**: ML-based extraction for complex layouts

### Account Document Analysis System

The repository includes specialized scripts for analyzing financial documents:

- **`Konten.py`** - Base library with shared functionality (320 lines)
  - `BaseKontoAnalyzer` class for document processing
  - Date extraction from various filename patterns
  - Document type classification from docling metadata
  - Markdown report generation utilities

- **`Depotkonto.py`** - Analyzes depot/investment accounts
  - Processes ISIN codes and transaction types
  - Generates `BLUEITS-Depotkonto.md` and `Ramteid-Depotkonto.md`

- **`Girokonto.py`** - Analyzes checking accounts
  - Transaction categorization and balance tracking
  - Generates `BLUEITS-Girokonto.md` and `Ramteid-Girokonto.md`

- **`Geldmarktkonto.py`** - Analyzes money market accounts
  - Interest rate analysis features
  - Generates `BLUEITS-Geldmarktkonto.md` and `Ramteid-Geldmarktkonto.md`

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

### Financial Document Processing

#### Vertical Layout Detection (Sparkasse Format)
Recent improvements in `Depotkonto.py:190-260` handle Sparkasse's vertical format where values appear on separate lines:
```
Ermittlung steuerrelevante Erträge Veräußerungsgewinn Ausmachender Betrag
3.204,55 EUR
52.354,50
EUR
```

The extraction logic (`Depotkonto.py:195-260`):
1. Detects vertical layout pattern
2. Extracts numbers from subsequent lines (checks up to 2 lines ahead for EUR)
3. Uses proximity to Kurswert (gross amount) to determine which value is profit/loss vs net amount
4. Debug logging for BLUEITS transactions to track extraction accuracy

#### Base Account Analysis System

- **`Konten.py`** - Base library with shared functionality (320 lines)
  - `BaseKontoAnalyzer` class for document processing
  - German formatting utilities: `format_number_german()`, `format_date_german()`
  - Document type classification from docling metadata
  - Markdown report generation

- **`Depotkonto.py`** - Analyzes depot/investment accounts
  - MiFID II cost extraction logic (lines 586-608)
  - ISIN code processing and transaction categorization
  - Color-coded sales transactions with profit/loss tracking
  - Cumulative profit/loss columns for tax reporting

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
# NOTE: Now uses --temperature 0.1 --max-attempts 10 for better reliability
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

**`extract_thinking_content(text)`** (thea.py:240-276)
- Extracts thinking tags from model responses
- Supports both `<thinking>` and `<think>` formats
- Handles multiple thinking blocks with separation

**`process_with_model()`** (`thea.py:348`)
- Core processing orchestrator
- Handles retry logic with temperature scaling
- Pattern detection for stuck responses (`thea.py:688-750`)
- Streaming response handling

**`BaseKontoAnalyzer`** (Konten.py:16)
- Base class for account analysis scripts
- Methods: `extract_date_from_filename()`, `extract_document_type_from_docling()`
- Handles multiple date formats: YYYYMMDD, vom_DD_MM_YYYY, DD.MM.YYYY
- Document type classification with fallback patterns

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

**German Formatting** (`Konten.py`)
- `format_number_german()`: Converts 1,234.56 to 1.234,56
- `format_date_german()`: Converts YYYY-MM-DD to DD.MM.YYYY
- Currency/percentage symbols only in table headers, never in cells

**Transaction Processing** (`Depotkonto.py`)
- Vertical layout detection for Sparkasse documents (lines 190-260)
- Kurswert extraction with multiple patterns (lines 125-143)
- Intelligent value assignment using proximity to gross amount
- Debug logging for BLUEITS transactions
- German thousand separator handling in shares extraction (line 100): Pattern `r'Stück\s+([\d.]+)'` with `.replace('.', '')`
- Transaction type detection including:
  - `Limit-Order-Vormerkung`: Limit order confirmations with reservation fees
  - `Orderabrechnung-Stornierung`: Order cancellations  
  - `Orderabrechnung-Verkauf/Kauf`: Executed buy/sell orders

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

## Data Quality Achievements
- **BLUEITS Depot**: 100% G/V extraction for 72 sales transactions
- **Ramteid Depot**: 100% G/V extraction for 17 sales transactions (excluding 1 Ausführungsanzeige)
- **Total Documents**: 618 PDFs across 6 account types successfully processed
- **Transaction Types**: 9+ distinct types properly classified
- **German Format Support**: Full support for DD.MM.YYYY dates, 1.234,56 numbers, trailing minus

## Visual Design Choices

### Colorblind-Friendly Transaction Marking
Sales transactions in depot reports use accessible colors (lines 1384-1397 in `Depotkonto.py`):
- **Profit (Gewinn)**: Blue background (#0173B2) with white text
- **Loss (Verlust)**: Orange background (#DE8F05) with white text  
- **Neutral (0 EUR)**: Light gray background (#e9ecef)
- **No coloring**: Ausführungsanzeige and other non-final transactions

This color scheme is distinguishable for most types of color blindness (deuteranopia, protanopia).

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

### Vertical layout extraction issues (Sparkasse documents)
- Check `Depotkonto.py:190-260` for vertical layout detection logic
- Ensure EUR detection checks up to 2 lines ahead (lines 205-207)
- Use debug output to verify value assignment (lines 223-226, 244-249)

### Case sensitivity in file patterns
- Windows filesystems may have uppercase extensions (.PDF)
- Scripts handle both .pdf and .PDF patterns
- Glob patterns include both cases: `*.pdf`, `*.PDF`

## Sidecar-Only Mode

The `--sidecars-only` flag enables extraction-only mode without sending data to Ollama models:

**Use cases:**
- Pre-process PDFs for later analysis
- Quick text/image extraction without AI processing
- Testing extraction quality before AI analysis

**Behavior:**
- Automatically enables `--save-sidecars`
- Skips all model processing
- Much faster than full processing (no API calls)
- Skip mode checks for ANY existing sidecar files regardless of model/suffix

## Docling Pipeline Details

**When to use:**
- Documents with complex tables or multi-column layouts
- Scientific papers with formulas and equations
- Financial statements with structured data

**Features:**
- Preserves document structure and reading order
- Extracts tables with cell relationships intact
- Confidence scoring for extraction quality
- Automatic fallback to gemma3:27b when confidence < 0.7

## Critical Prompt Settings

### For Qwen Models
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

### For Gemma Models
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

## Processing Rates
- **pdf-extract-png**: ~45-60 seconds per PDF
- **pdf-extract-txt**: ~5-10 seconds per PDF
- **pdf-extract-docling**: ~37 seconds per PDF (1.6 files/minute)

## Recent Critical Fixes

### German Thousand Separator Issue (Fixed)
- **Problem**: Transactions with >1000 shares showed only 1 share (e.g., "Stück 1.565" parsed as 1)
- **Root Cause**: Regex pattern `r'Stück\s+(\d+)'` didn't handle German thousand separators (dots)
- **Fix**: Changed to `r'Stück\s+([\d.]+)'` and added `.replace('.', '')` at line 100 in `Depotkonto.py`
- **Impact**: Transaction 34 now correctly shows 1565 shares instead of 1

### Trailing Minus Sign in German Bookkeeping Format (Fixed)
- **Problem**: Sales transactions with losses showed "-" instead of actual loss values
- **Root Cause**: German bookkeeping format uses trailing minus (e.g., "199.440,70-") not matched by regex expecting leading minus
- **Fix**: Added new patterns in `Depotkonto.py:272-313` to handle trailing minus:
  ```python
  (r'Veräußerungsverlust\s+([\d.,]+)-\s*EUR', -1.0),  # Trailing minus
  ```
- **Impact**: G/V extraction rate improved from 57.5% to 100% for BLUEITS sales (after excluding Kapitalmaßnahme)

### Vertical Layout Detection for Losses (Fixed)
- **Problem**: Vertical layout detection only worked for "Veräußerungsgewinn" not "Veräußerungsverlust"
- **Fix**: Updated regex at line 193 to `r'Ermittlung steuerrelevante Erträge\s+Veräußerungs(?:gewinn|verlust)\s+Ausmachender Betrag'`
- **Additional Fix**: Lines 204-234 now handle trailing minus in vertical layouts with proper sign detection
- **Impact**: Transaction 38 now correctly shows -12.150,00 EUR loss

### Transaction Type Classification (Enhanced)
- **New Types Added** in `Depotkonto.py`:
  - `Ausführungsanzeige`: Preliminary execution notices without final costs (line 427-434)
  - `Kapitalmaßnahme`: For stock splits and other corporate actions (line 435-440)
  - `Limit-Order-Vormerkung`: For limit order confirmations with "Vormerkungsentgelt" 
  - `Stornierung`: For order cancellations with "Streichungsbestätigung"
- **Detection Priority**: Execution notices → Capital measures → Limit orders → Cancellations → Regular orders
- **Statistics Exclusion**: Kapitalmaßnahme and Ausführungsanzeige excluded from G/V extraction rate (line 1049)
- **Solution** (`Depotkonto.py:100`):
  ```python
  shares_match = re.search(r'Stück\s+([\d.]+)', text)
  if shares_match:
      shares_str = shares_match.group(1).replace('.', '')
      details['shares'] = int(shares_str)
  ```

### Complete Transaction Type System
- **Ausführungsanzeige-Verkauf/Kauf**: Preliminary execution notices (line 427-434)
- **Kapitalmaßnahme**: Stock splits, corporate actions (e.g., Tesla 3:1 split Aug 2022)
- **Limit-Order-Vormerkung**: Limit order confirmations with "Vormerkungsentgelt"
- **Orderabrechnung-Stornierung**: Order cancellations with "Streichungsbestätigung"
- **Orderabrechnung-Verkauf/Kauf**: Executed buy/sell orders
- **Kostenaufstellung**: MiFID II cost reports (Ex-Post)
- **Depotabschluss**: Depot statements (annual/quarterly)
- **Dividende**: Dividend payments
- **Zinsen**: Interest payments

### Line Ending Issues (Windows/WSL)
- Create `.gitattributes` file with proper line ending configuration
- Use `git checkout -- <path>` to reset files to repository state

## Available Prompt Files

- **`pdf-extract-png.prompt`** - Vision-based extraction with Gemma models
- **`pdf-extract-txt.prompt`** - Text extraction for Qwen models  
- **`pdf-extract-docling.prompt`** - Docling ML extraction
- **`bank_gemma.prompt`** - Bank statement processing (Gemma)
- **`bank_qwen.prompt`** - Bank statement processing (Qwen)
- **`bank_konto_kontoauszuege.prompt`** - German bank account statements
- **`bank_konto_kontoauszuege_v2.prompt`** - Enhanced with validation and cross-references
- **`thinking_test.prompt`** - Testing thinking tag behavior

## Key Processing Information

### Processing Rates
- **pdf-extract-png**: ~45-60 seconds per PDF
- **pdf-extract-txt**: ~5-10 seconds per PDF
- **pdf-extract-docling**: ~37 seconds per PDF (1.6 files/minute)

### Batch Processing
For overnight runs:
```bash
nohup python3 thea.py --pipeline pdf-extract-docling "Belege/*.pdf" > processing.log 2>&1 &
tail -f processing.log  # Monitor progress
```

## Critical Issues and Solutions

### Model outputs thinking tags instead of JSON
- **Root cause**: Hardcoded system prompt prefix encourages thinking tags
- **Qwen fix**: Explicitly add "Do NOT use thinking tags" in prompt file
- **Gemma fix**: Ensure "Use thinking THEN output JSON separately"
- **Always**: Set `"format": "json"` in settings

### Poppler not found (required for PNG pipeline)
- Linux/macOS: `sudo apt-get install poppler-utils` or `brew install poppler`
- Windows: Download from GitHub, add bin folder to PATH
- Verify: `pdftoppm -h`

## Prompt File Development

When creating new prompt files:
1. Use existing prompts as templates (`prompts/pdf-extract-*.prompt`)
2. For Qwen: Explicitly forbid thinking tags in JSON output
3. For Gemma: Instruct to use thinking tags THEN output JSON
4. Always include `format: "json"` in settings for JSON enforcement
5. Use consistent schema field names (e.g., `three_word_description_*`)
6. Include `document_type` field for classification
7. Set appropriate temperature (0.15-0.2 recommended)
8. Use `{{pdf_path}}` placeholder in user_prompt.template

## Building Executables

```bash
npm run build-windows    # Creates thea-windows.exe
npm run build-linux      # Creates thea-linux
npm run build-macos      # Creates thea-macos
```

## Directory Structure

```
THEA/
├── thea.py                 # Main entry point, CLI argument handling
├── pipelines/              # Pipeline implementations
│   ├── __init__.py
│   ├── base.py            # BasePipeline abstract class
│   ├── manager.py         # Pipeline selection and management
│   ├── pdf_extract_png.py # Image extraction pipeline
│   ├── pdf_extract_txt.py # Text extraction pipeline
│   └── pdf_extract_docling.py # Docling ML pipeline
├── extractors/            # Text extraction implementations
│   ├── __init__.py
│   ├── pypdf2_extractor.py
│   ├── pdfplumber_extractor.py
│   ├── pymupdf_extractor.py
│   └── docling_extractor.py
├── prompts/               # Prompt configuration files
│   ├── pdf-extract-png.prompt
│   ├── pdf-extract-txt.prompt
│   ├── pdf-extract-docling.prompt
│   ├── bank_gemma.prompt
│   ├── bank_qwen.prompt
│   ├── bank_konto_kontoauszuege.prompt
│   ├── bank_konto_kontoauszuege_v2.prompt
│   └── thinking_test.prompt
├── docs/                  # Financial documents (618 PDFs)
│   ├── BLUEITS-Depotkonto-7274079/     # 314 files
│   ├── BLUEITS-Geldmarktkonto-21503990/ # 55 files
│   ├── BLUEITS-Girokonto-200750750/    # 59 files
│   ├── Ramteid-Depotkonto-7274087/     # 88 files
│   ├── Ramteid-Geldmarktkonto-21504006/ # 43 files
│   └── Ramteid-Girokonto-21377502/     # 59 files
├── Konten.py              # Base account analyzer class
├── Depotkonto.py          # Depot account analysis
├── Girokonto.py           # Checking account analysis
├── Geldmarktkonto.py      # Money market analysis
├── test_thinking.py       # Test suite for thinking tags
├── requirements.txt       # Python dependencies
├── package.json          # NPM scripts and project metadata
└── CLAUDE.md             # This documentation file
```

## Key Entry Points and Functions

### Main Entry Point
- `thea.py:main()` - CLI entry point, argument parsing
- `thea.py:process_with_model()` (line 348) - Core processing orchestrator

### Pipeline Functions
- `pipelines/manager.py:PipelineManager.get_pipeline()` - Pipeline selection
- `pipelines/base.py:Pipeline.process()` - Abstract pipeline interface
- `pipelines/base.py:Pipeline.format_for_model()` - Model formatting

### Prompt Loading
- `thea.py:load_prompt_file()` (line 25) - Load JSON/text prompts
- `thea.py:build_system_prompt()` (line 50) - Build system prompt
- `thea.py:build_user_prompt()` (line 78) - Build user prompt with substitutions

### Utility Functions
- `thea.py:clean_thea_files()` (line 89) - Clean generated files
- `thea.py:extract_thinking_content()` - Extract thinking tags
- `thea.py:clean_json_response()` - Clean and validate JSON