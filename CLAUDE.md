# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

THEA is a dual-pipeline PDF processing system that can either convert PDFs to images for vision models or extract text using multiple methods for text-only models. It streams responses from Ollama models and implements sophisticated retry logic with pattern detection.

## Architecture

### Dual Pipeline System

The system dynamically selects between two processing pipelines based on model capabilities:

1. **Image Pipeline (`pdf-extract-png`)**: Extracts PDFs as base64 PNG images for vision models
2. **Text Pipeline (`pdf-extract-txt`)**: Extracts text using PyPDF2, pdfplumber, and pymupdf in parallel

Pipeline selection is determined by:
- Prompt file `settings.pipeline` configuration
- Command-line `--pipeline` override
- Auto-detection based on model type (qwen→text, gemma→image)

### Core Processing Flow

The main `process_with_model()` function (line 316) orchestrates:
1. Pipeline data preparation (images or extracted text JSON)
2. Ollama API streaming with chunk-by-chunk processing
3. Pattern detection for stuck responses (1-100 char repetitions)
4. Progressive temperature scaling on retries (0.1→1.0)
5. Thinking tag extraction (`<thinking>` for gemma, `<think>` for qwen)
6. JSON response cleaning and validation
7. Comprehensive metadata tracking in v2.0 JSON format

### Prompt System

Prompts are JSON files with:
- `system_prompt.suffix`: Model-specific instructions
- `user_prompt.template`: Template with `{{pdf_path}}` placeholder
- `settings`: Model, pipeline, temperature, and processing configuration

### Key Architectural Decisions

- **Streaming Response Handling**: Character-by-character output for real-time feedback
- **Pattern Detection**: Adaptive thresholds based on pattern length (1-100 chars)
- **Token Management**: Ollama's `num_predict` parameter limits generation
- **Error Recovery**: Partial responses saved even on failure
- **Pipeline Modularity**: Abstract `Pipeline` base class for extensibility

## Essential Commands

### Development

```bash
# Setup environment (first time)
npm run setup                    # Linux/macOS
npm run setup-windows            # Windows

# Activate virtual environment
. venv/bin/activate              # Linux/macOS
venv\Scripts\activate            # Windows

# Install/update dependencies
pip install -r requirements.txt

# Run tests
python3 test_thinking.py         # Test thinking tag extraction
```

### Processing PDFs

```bash
# Model-specific processing
npm run thea:gemma               # Gemma with image pipeline
npm run thea:qwen                # Qwen with text extraction

# Bank statement analysis
npm run thea:kontoauszug:gemma   # Gemma for bank statements
npm run thea:kontoauszug:qwen    # Qwen for bank statements

# Direct execution with options
python3 thea.py --pipeline pdf-extract-txt --model qwen3:14b "*.pdf"
python3 thea.py --prompt prompts/bank_gemma.prompt --save-sidecars "document.pdf"
```

### Building Executables

```bash
# Platform-specific builds
npm run build-windows            # Creates thea-windows.exe
npm run build-linux              # Creates thea-linux
npm run build-macos              # Creates thea-macos

# Build using spec file
pyinstaller thea.spec            # Uses platform detection
```

### Maintenance

```bash
# Clean generated files
python3 thea.py --clean Belege/          # With confirmation
python3 thea.py --clean --force Belege/  # No confirmation
python3 thea.py --clean --dry-run        # Preview only
```

## Key Parameters

- `--pipeline <type>`: Force `pdf-extract-png` or `pdf-extract-txt`
- `--prompt <file>`: Load prompt configuration (determines pipeline)
- `--model <name>`: Override model (default: gemma3:12b)
- `--max-attempts <n>`: Retries for stuck patterns (1-10, default: 3)
- `--temperature <value>`: Initial temperature (0.0-2.0, default: 0.1)
- `--format <json|none>`: Control thinking output (none allows thinking tags)
- `--save-sidecars`: Save sidecar files (PNG for image pipeline, TXT for text pipeline)
- `--dpi <number>`: PDF conversion resolution (50-600, default: 300)

## File Structure

```
├── thea.py                      # Main entry point
├── pipelines/                   # Pipeline implementations
│   ├── manager.py              # Pipeline selection logic
│   ├── pdf_to_png.py          # Image conversion
│   └── pdf_to_text.py         # Multi-method text extraction
├── extractors/                  # Text extraction methods
│   ├── pypdf2_extractor.py    # Basic extraction
│   ├── pdfplumber_extractor.py # Table-aware extraction
│   └── pymupdf_extractor.py   # Fast extraction with formatting
└── prompts/                     # Model-specific configurations
    ├── bank_gemma.prompt       # Gemma with images
    └── bank_qwen.prompt        # Qwen with text extraction
```

## Model Configuration

Default models (smaller for faster switching):
- **gemma3:12b**: Vision model, uses image pipeline
- **qwen3:14b**: Text-only model, uses extraction pipeline

Models auto-detect appropriate pipeline unless overridden.

## Ollama Integration

- Default endpoint: `https://b1s.hey.bahn.business/api/chat`
- Streaming enabled for real-time output
- Timeout: 100s default (configurable)
- Max tokens: 50,000 default (configurable)

## Output Format

`.thea` files contain v2.0 JSON with:
- `metadata`: File, processing, model information
- `execution`: Retry count, temperature, pattern detection
- `response`: Raw text, extracted thinking, parsed JSON
- `statistics`: Token counts, processing time, throughput

Filename: `<pdf>.<timestamp>.<model>[.<suffix>].thea`