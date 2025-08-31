# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

THEA is a PDF text extraction and analysis system that uses Ollama's vision models to process PDF documents. It converts PDFs to images and sends them to language models for text extraction, character counting, document classification, and content summarization.

## Architecture

### Core Components

The system (`thea.py`) consists of five main functions:

1. **`load_prompt_file(prompt_path)`** - Loads JSON or plain text prompt configurations. Returns a dict with prompt config or None.

2. **`build_system_prompt(prompt_config)`** - Constructs the complete system prompt by combining:
   - Hardcoded prefix: "You are a vision-based text extractor and analyzer. "
   - Configurable suffix from prompt config
   - Output format instructions from schema

3. **`build_user_prompt(prompt_config, pdf_path)`** - Creates user prompts from templates with `{{variable}}` substitution.

4. **`pdf_to_base64_images(pdf_path, dpi)`** - Converts PDFs to base64-encoded PNG images using pdf2image/poppler. Returns tuple of (base64_images, pil_images).

5. **`process_with_model(...)`** - Main processing orchestrator that:
   - Manages retry logic with progressive temperature increases
   - Detects and handles stuck pattern repetitions
   - Streams responses from Ollama API
   - Saves results as JSON v2.0 format

### Processing Pipeline

1. **Configuration Loading**
   - Priority: Command-line args > `.prompt` file > hardcoded defaults
   - Auto-loads `.prompt` from root if present
   - Supports both JSON and legacy plain text formats

2. **PDF Processing**
   - Converts each page to PNG at specified DPI
   - Encodes images as base64 for API transmission
   - Optionally saves images with pattern: `<pdf>.<timestamp>.<model>.<dpi>p<page>.png`

3. **Model Communication**
   - Streams responses character-by-character to stdout
   - Implements retry logic with temperature progression: `initial_temp + (retry_count * (1.0 - initial_temp) / max_retries)`
   - Detects stuck patterns (single chunk, two-chunk alternating, three-chunk cycle)

4. **Result Storage**
   - Saves as `.thea` files in JSON v2.0 format
   - Contains complete metadata, settings, prompts, response, and statistics
   - Backward compatible with legacy text format detection

## Commands

### Development Setup
```bash
# Initial setup
npm run setup              # Linux/macOS
npm run setup-windows      # Windows

# Activate virtual environment
. venv/bin/activate        # Linux/macOS
venv\Scripts\activate      # Windows
```

### Running THEA
```bash
# Default processing (Belege/ folder, gemma3:27b, --max-retries 10)
npm run thea               # Linux/macOS
npm run thea-windows       # Windows

# Direct execution with options
python3 thea.py [OPTIONS] <file_pattern> [file_pattern2] ...

# Common patterns
python3 thea.py sample_document.pdf                    # Single file
python3 thea.py --mode overwrite "*.pdf"              # Force reprocess
python3 thea.py --prompt invoice.prompt "*.pdf"       # Custom prompt
python3 thea.py -m gemma:14b -t 0.5 "*.pdf"          # Different model/temp
```

### Building Executables
```bash
npm run build-windows      # Creates thea.exe
npm run build-linux        # Creates thea-linux
npm run build-macos        # Creates thea-macos
npm run build-spec         # Build using thea.spec
```

## Prompt File Format

### Structure (`.prompt` or `<name>.prompt`)
```json
{
  "version": "1.0",
  "system_prompt": {
    "suffix": "Extraction instructions...",
    "output_format": {
      "type": "json",
      "schema": { "field": "type" },
      "instructions": "Format guidance"
    }
  },
  "user_prompt": {
    "template": "Process {{pdf_path}}"
  },
  "settings": {
    "model": "gemma3:27b",
    "temperature": 0.1,
    "max_retries": 3,
    "mode": "skip",
    "save_image": false,
    "dpi": 300,
    "endpoint_url": "https://b1s.hey.bahn.business/api/chat"
  }
}
```

### Parameter Priority
1. Command-line arguments (highest)
2. Prompt file settings
3. Hardcoded defaults (lowest)

## Output Format (.thea v2.0)

```json
{
  "version": "2.0",
  "metadata": {
    "file": { "pdf_path", "pdf_size_bytes", "pdf_pages", "output_file" },
    "processing": { "timestamp", "start_time", "end_time", "processing_time_seconds", "hostname", "platform" },
    "model": { "name", "endpoint", "stream", "format" }
  },
  "settings": { "mode", "suffix", "prompt_file", "save_image", "dpi", "max_retries", "initial_temperature", "temperature_progression" },
  "execution": { "retry_count", "final_temperature", "stuck_pattern_detected", "pattern_type", "chunks_received", "images_processed" },
  "prompt": { "system", "user", "prompt_file", "prompt_config" },
  "response": { "text", "thinking", "json" },
  "statistics": { "tokens", "characters" },
  "errors": [],
  "warnings": []
}
```

## Key Technical Details

### Ollama Configuration
- Default endpoint: `https://b1s.hey.bahn.business/api/chat`
- Requires vision-capable models (gemma3:27b, gemma:14b, etc.)
- Enforces JSON output with `format: "json"`
- Streaming enabled for real-time output

### Pattern Detection
Monitors for repetitive output patterns (50+ repetitions):
- Single chunk: Same content repeated
- Two-chunk: Alternating between two values  
- Three-chunk: Cycling through three values

### File Naming
- Output: `<pdf>.<timestamp>.<model>[.<suffix>].thea`
- Images: `<pdf>.<timestamp>.<model>[.<suffix>].<dpi>p<page>.png`
- Suffix auto-derived from prompt filename unless overridden

### Skip Mode Logic
- Only skips files matching both model AND suffix
- Detects both JSON v2.0 and legacy text formats
- Enables parallel processing with different configurations

## Prerequisites

1. **Python 3.8+** with venv module
2. **Poppler** (PDF processing):
   - Ubuntu/Debian: `sudo apt-get install poppler-utils`
   - macOS: `brew install poppler`
   - Windows: Download from GitHub, add bin/ to PATH
3. **Ollama** with vision models:
   ```bash
   ollama serve
   ollama pull gemma3:27b
   ```

## Dependencies
- pdf2image==1.17.0
- Pillow==10.4.0
- requests==2.32.3
- pyinstaller==6.3.0