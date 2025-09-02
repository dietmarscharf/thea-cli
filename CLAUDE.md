# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

THEA is a multi-pipeline PDF processing system that extracts content from PDFs using three distinct approaches:
1. **Image extraction** for vision models (pdf-extract-png)
2. **Text extraction** for text-only models (pdf-extract-txt)
3. **Deep learning extraction** using IBM Docling (pdf-extract-docling)

It processes documents through Ollama models with sophisticated retry logic, pattern detection, and streaming response handling. Output files use the `.thea_extract` extension.

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
   - Requires: `pip install docling` (includes torch dependencies)

4. **Pipeline Manager** (`pipelines/manager.py`)
   - Dynamically selects pipeline based on model capabilities
   - Auto-detects: qwen→text pipeline, gemma→image pipeline
   - Can be overridden via `--pipeline` parameter or prompt file settings

### Text Extractors

The text pipeline uses multiple extractors (`extractors/` directory):
- **PyPDF2Extractor**: Basic text extraction, confidence ~0.8
- **PdfPlumberExtractor**: Advanced extraction with table support, confidence ~0.9
- **PyMuPDFExtractor**: Fast extraction with formatting, confidence ~1.0
- **DoclingExtractor**: ML-based extraction for complex layouts

### Core Processing Flow

The main `process_with_model()` function in `thea.py:348` orchestrates:

1. **Skip Mode Logic** - Checks for existing files based on mode (`thea.py:1536-1568`)
   - Normal mode: Checks for `.thea_extract` files matching `*.{model}.{suffix}.thea_extract`
   - Sidecars-only mode: Checks for ANY existing pipeline-specific sidecar files:
     - Docling: `*.docling.*` (catches all variations regardless of model/suffix)
     - Text: `*.pypdf2.txt`, `*.pdfplumber.txt`, `*.pymupdf.txt`
     - PNG: `*.png`
2. **Pipeline Processing** - Runs selected pipeline to extract content
3. **Ollama API Streaming** - Sends to model with chunk-by-chunk processing
4. **Pattern Detection** - Monitors for stuck responses (1-100 char repetitions)
5. **Temperature Scaling** - Progressive increase (0.1→1.0) on retries
6. **Thinking Tag Extraction** - `<thinking>` for gemma, `<think>` for qwen
7. **JSON Response Cleaning** - Handles markdown blocks and validates JSON
8. **Result Persistence** - Saves to `.thea_extract` files with v2.0 metadata format

### Prompt Configuration System

JSON prompt files in `prompts/` directory control model behavior:

**Critical Model Differences:**
- **Gemma models**: Must use `<thinking>` tags BEFORE outputting JSON
- **Qwen models**: Must NOT use thinking tags when outputting JSON

Prompt structure:
- `system_prompt.suffix` - Model-specific instructions
- `user_prompt.template` - Template with `{{pdf_path}}` placeholder
- `settings` - Pipeline, model, temperature, format enforcement
- `output_format.schema` - Expected JSON structure

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
npm run thea:sidecars            # Auto-detect pipeline (skip existing)

# Force regeneration of sidecars
npm run thea:sidecars:png-force     # Force PNG extraction
npm run thea:sidecars:txt-force     # Force text extraction
npm run thea:sidecars:docling-force # Force Docling extraction
npm run thea:sidecars-force         # Force auto-detect pipeline

# Bank statement processing
npm run thea:kontoauszug:gemma   # Gemma for bank statements
npm run thea:kontoauszug:qwen    # Qwen for bank statements

# Direct execution with options
python3 thea.py --pipeline pdf-extract-png --model gemma3:27b "*.pdf"
python3 thea.py --pipeline pdf-extract-txt --model qwen3:30b "*.pdf"
python3 thea.py --pipeline pdf-extract-docling --model gemma3:27b "*.pdf"
python3 thea.py --prompt prompts/bank_gemma.prompt --save-sidecars "document.pdf"

# Key parameters
--pipeline <type>      # pdf-extract-png, pdf-extract-txt, or pdf-extract-docling
--save-sidecars        # Save PNG images or text extractions
--sidecars-only        # Generate sidecars without model processing
--max-attempts <n>     # Retry attempts for stuck patterns (1-10)
--temperature <value>  # Initial temperature (0.0-2.0, default: 0.1)
--mode <skip|overwrite> # Skip existing or overwrite
--dpi <number>         # Image resolution (50-600, default: 300)
--format <json|none>   # JSON enforcement or allow thinking tags
--clean                # Clean THEA-generated files
--force                # Skip confirmation prompts
--dry-run              # Preview actions without executing
```

### Testing

```bash
# Test thinking tag extraction
python3 test_thinking.py

# Test with sample document
python3 thea.py --mode overwrite --save-sidecars sample_document.pdf

# Test specific pipeline
python3 thea.py --pipeline pdf-extract-txt --save-sidecars sample_document.pdf

# Process financial documents
python3 thea.py --prompt prompts/pdf-extract-txt.prompt "Belege/*.pdf"
```

### Clean Generated Files

```bash
# Clean all THEA files
python3 thea.py --clean                  # With confirmation
python3 thea.py --clean --force          # No confirmation
python3 thea.py --clean --dry-run        # Preview only

# Pipeline-specific cleaning
python3 thea.py --clean --pipeline txt          # Clean only text extraction files
python3 thea.py --clean --pipeline png          # Clean only PNG/image files
python3 thea.py --clean --pipeline docling      # Clean only Docling files

# NPM scripts for pipeline-specific cleaning
npm run thea:clean:txt                   # Clean text pipeline files
npm run thea:clean:txt-dry              # Dry run for text pipeline
npm run thea:clean:txt-force            # Force clean text pipeline

npm run thea:clean:png                   # Clean PNG pipeline files
npm run thea:clean:png-dry              # Dry run for PNG pipeline
npm run thea:clean:png-force            # Force clean PNG pipeline

npm run thea:clean:docling              # Clean Docling pipeline files
npm run thea:clean:docling-dry          # Dry run for Docling pipeline
npm run thea:clean:docling-force        # Force clean Docling pipeline

# Windows variants available for all commands (append -windows)
npm run thea:clean:txt-windows
npm run thea:clean:png-force-windows
# etc.

# Cleans: *.thea_extract, *.thea (legacy), *.png, extraction files (*.txt, *.json, *.md)
```

### File Transfer and Sync

```bash
# Transfer extraction results to another project
npm run thea:sync-sidecars         # Linux/macOS rsync
npm run thea:sync-sidecars-windows # Windows robocopy
npm run thea:sync-sidecars-dry     # Dry run to preview

# Syncs: *.thea_extract, *.docling.*, *.pypdf2.txt, *.pdfplumber.txt, *.pymupdf.txt, *.png
# Target: ../Sparkasse/docs/
```

### Building Executables

```bash
npm run build-windows    # Creates thea-windows.exe
npm run build-linux      # Creates thea-linux
npm run build-macos      # Creates thea-macos
```

## File Naming Conventions

### Output Files
- **Main results**: `<pdf>.<timestamp>.<model>.<suffix>.thea_extract`
- **PNG sidecars**: `<pdf>.<timestamp>.<model>.<suffix>.<dpi>p<page>.png`
- **Text sidecars**: `<pdf>.<timestamp>.<model>.<suffix>.<extractor>.txt`
- **Docling sidecars**: `<pdf>.<timestamp>.<model>.<suffix>.docling.{txt,json,md}`
- **Metadata**: `<pdf>.<timestamp>.<model>.<suffix>.<extractor>.json`

Timestamp format: `YYYYMMDD_HHMMSS`
Extractors: `pypdf2`, `pdfplumber`, `pymupdf`, `docling`

## Key Implementation Details

### Pattern Detection Thresholds
- 1-char patterns: 100+ repetitions
- 2-char patterns: 75+ repetitions  
- 3-char patterns: 50+ repetitions
- 4-99 char patterns: 25+ repetitions
- 100+ char patterns: 10+ repetitions

### Temperature Progression Formula
```python
temperature = initial_temp + (retry_count * (1.0 - initial_temp) / max_attempts)
```
Example with 3 retries: 0.10 → 0.40 → 0.70

### Pipeline Selection Logic
1. Check prompt file `settings.pipeline`
2. Check `--pipeline` command-line override
3. Auto-detect based on model name (qwen→txt, gemma→png)
4. Default to `pdf-extract-png`

### Ollama API Configuration
- Default endpoint: `https://b1s.hey.bahn.business/api/chat`
- Streaming enabled with chunk-by-chunk processing
- Token limit controlled via `num_predict` parameter
- Timeout configurable (default: 100-200 seconds)

## Pipeline-Specific Details

### Sidecar-Only Mode

The `--sidecars-only` flag enables extraction-only mode without sending data to Ollama models:

**Use cases:**
- Pre-process PDFs for later analysis
- Quick text/image extraction without AI processing
- Batch extraction for archival purposes
- Testing extraction quality before AI analysis
- Offline extraction when Ollama is unavailable

**Behavior by pipeline:**

**pdf-extract-png:**
- Extracts PDF pages as PNG images
- Saves: `*.{timestamp}.{model}.{suffix}.{dpi}p{page}.png`
- Example: `python3 thea.py --sidecars-only --pipeline pdf-extract-png --dpi 150 "*.pdf"`

**pdf-extract-txt:**
- Runs PyPDF2, pdfplumber, pymupdf extractors
- Saves: `*.pypdf2.txt`, `*.pdfplumber.txt`, `*.pymupdf.txt`
- Example: `python3 thea.py --sidecars-only --pipeline pdf-extract-txt "documents/*.pdf"`

**pdf-extract-docling:**
- Uses Docling deep learning extraction
- Saves: `*.docling.txt`, `*.docling.json`, `*.docling.md`
- Example: `python3 thea.py --sidecars-only --pipeline pdf-extract-docling "complex/*.pdf"`

**Notes:**
- Automatically enables `--save-sidecars`
- Skips all model processing
- Much faster than full processing (no API calls)
- Files use same naming convention as full processing
- Skip mode in sidecars-only checks for ANY existing sidecar files regardless of model or suffix used
- This prevents duplicate processing even when switching between models or using different suffixes

### Docling Pipeline (pdf-extract-docling)

The Docling pipeline uses IBM's advanced document understanding models for complex PDFs:

**When to use:**
- Documents with complex tables or multi-column layouts
- Scientific papers with formulas and equations
- Financial statements with structured data
- Documents where text extraction fails

**Features:**
- Preserves document structure and reading order
- Extracts tables with cell relationships intact
- Handles mathematical formulas and equations
- Confidence scoring for extraction quality
- Automatic fallback to gemma3:27b when confidence < 0.7

**Installation:**
```bash
pip install docling  # Large download (~2GB with torch dependencies)
```

**Configuration in prompt files:**
```json
{
  "settings": {
    "pipeline": "pdf-extract-docling",
    "model": "gemma3:27b",
    "pipeline_config": {
      "use_fallback_model": true,
      "fallback_model": "gemma3:27b"
    }
  }
}
```

**Output files:**
- `.docling.txt` - Plain text extraction
- `.docling.json` - Metadata with confidence scores
- `.docling.md` - Markdown format (if applicable)

## Critical Prompt Settings

### For Qwen Models (pdf-extract-txt)
```json
{
  "system_prompt": {
    "suffix": "...Output ONLY valid JSON. Do NOT use thinking tags..."
  },
  "settings": {
    "format": "json",  // Enforces JSON-only output
    "temperature": 0.2  // Slightly higher to prevent overthinking
  }
}
```

### For Gemma Models (pdf-extract-png)
```json
{
  "system_prompt": {
    "suffix": "...Use <thinking> tags for analysis, then output JSON..."
  },
  "settings": {
    "format": "json",  // Still enforces JSON after thinking
    "temperature": 0.15 // Balanced for vision analysis
  }
}
```

## Error Handling

### Stuck Pattern Recovery
When repetitive patterns are detected:
1. Close streaming connection
2. Save partial response
3. Increment retry counter
4. Increase temperature
5. Retry with new temperature

### Missing Dependencies
- Image pipeline requires: pdf2image, poppler binaries
- Text pipeline requires: At least one of PyPDF2, pdfplumber, pymupdf
- Graceful degradation when extractors unavailable

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

## Performance and Processing

### Processing Rates

Typical processing speeds (may vary based on PDF complexity and system resources):

- **pdf-extract-png**: ~45-60 seconds per PDF (vision processing)
- **pdf-extract-txt**: ~5-10 seconds per PDF (text extraction only)
- **pdf-extract-docling**: ~37 seconds per PDF (1.6 files/minute)

### Batch Processing

For large batches (1000+ PDFs):
```bash
# Estimate completion time
# Files: 1420 PDFs
# Rate: 1.6 files/minute (Docling)
# Time: ~15 hours

# Run overnight with logging
nohup python3 thea.py --pipeline pdf-extract-docling "Belege/*.pdf" > processing.log 2>&1 &

# Monitor progress
tail -f processing.log
find Belege -name "*.thea_extract" | wc -l  # Count completed
```

### Resource Usage

- **Memory**: ~2-4GB for standard PDFs, up to 8GB for complex documents
- **Disk Space**: 
  - Main `.thea_extract` files: ~5-50KB per PDF
  - PNG sidecars: ~100-500KB per page
  - Docling sidecars: ~10-100KB per PDF
  - Text sidecars: ~5-50KB per PDF

### Optimization Tips

1. **Skip Mode**: Default behavior - skips already processed files
2. **Pipeline Selection**: Use text pipeline for simple documents (5-10x faster)
3. **DPI Settings**: Lower DPI (150) for faster processing, higher (300+) for accuracy
4. **Parallel Processing**: Run multiple instances on different directories
5. **Clean Regularly**: Use pipeline-specific clean commands to manage disk space

## Common Issues and Solutions

### Model outputs thinking tags instead of JSON
- **Qwen**: Add "Do NOT use thinking tags" to system prompt
- **Gemma**: Clarify "Use thinking THEN output JSON separately"
- Always set `"format": "json"` in settings

### Inconsistent extraction quality
- Check extractor confidence scores in metadata
- PyMuPDF typically has highest confidence (1.0)
- Consider adjusting `extractors` list in prompt settings

### Pattern detection triggers too early
- Increase initial temperature slightly (0.1 → 0.15)
- Reduce max_attempts if model consistently gets stuck
- Check for actual repetitive content in source PDF

### Poppler not found errors
- Ensure poppler-utils is installed (Linux/macOS)
- On Windows, verify poppler bin directory is in PATH
- Test with: `pdftoppm -h` in terminal

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
│   └── thinking_test.prompt
├── docs/                  # Project documentation and output
├── test_thinking.py       # Test suite for thinking tag extraction
├── requirements.txt       # Python dependencies
└── package.json          # NPM scripts and project metadata
```

## Available Prompt Files

- **pdf-extract-png.prompt**: Vision-based extraction with Gemma models
- **pdf-extract-txt.prompt**: Text extraction for Qwen models  
- **pdf-extract-docling.prompt**: Docling ML extraction
- **bank_gemma.prompt**: Bank statement processing (Gemma)
- **bank_qwen.prompt**: Bank statement processing (Qwen)
- **bank_konto_kontoauszuege.prompt**: German bank account statements
- **thinking_test.prompt**: Testing thinking tag behavior

## Key Functions and Entry Points

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

## Environment Variables

- `OLLAMA_API_URL`: Override default Ollama endpoint (default: https://b1s.hey.bahn.business/api/chat)
- `THEA_DEFAULT_MODEL`: Default model if not specified (default: gemma3:27b)
- `THEA_DEFAULT_PIPELINE`: Default pipeline if not auto-detected (default: pdf-extract-png)

## Linting and Testing

### Running Tests
```bash
# Test thinking tag extraction logic
python3 test_thinking.py

# Test with sample PDF document (included in repo)
python3 thea.py --mode overwrite --save-sidecars sample_document.pdf
```

### Code Quality Checks
No formal linting configured. When adding linting:
- Consider adding ruff or pylint for Python code
- Add configuration to pyproject.toml or setup.cfg
- Create npm script aliases for consistency

## Troubleshooting Guide

### Common Issues

1. **"Poppler not found" errors**
   - Linux/macOS: `sudo apt-get install poppler-utils` or `brew install poppler`
   - Windows: Download from GitHub, add bin folder to PATH
   - Verify: `pdftoppm -h`

2. **Model stuck in repetitive patterns**
   - Automatic retry with temperature scaling (0.1→1.0)
   - Check pattern detection thresholds in thea.py
   - Consider adjusting initial temperature in prompt file

3. **Wrong pipeline auto-selected**
   - Override with `--pipeline` parameter
   - Set in prompt file's `settings.pipeline`
   - Model name patterns: qwen→txt, gemma→png

4. **Docling installation issues**
   - Large download (~2GB with torch)
   - Install separately: `pip install docling`
   - Falls back to text extraction if unavailable

5. **Thinking tags in JSON output**
   - Qwen models: Must NOT use thinking tags with JSON
   - Gemma models: Use thinking tags THEN output JSON
   - Check prompt file's `system_prompt.suffix`