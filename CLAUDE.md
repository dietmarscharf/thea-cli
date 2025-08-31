# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

THEA is a PDF text extraction and analysis system that uses Ollama's vision models to process PDF documents. It converts PDFs to images and sends them to language models for text extraction, character counting, document classification, and content summarization.

## Architecture

The system consists of a single Python script (`thea.py`) with three main functions:
1. `pdf_to_base64_images()` - Converts PDF files to base64-encoded PNG images using pdf2image/poppler
2. `process_with_model()` - Core processing logic that handles model communication, retry logic, and result saving
3. `load_prompt_file()` - Loads custom prompts from `.prompt` files

### Processing Flow
1. PDF → PNG conversion at configurable DPI (default: 300)
2. Streaming API communication with Ollama endpoint
3. Progressive temperature increase (0.1 → 1.0) during retries to handle stuck patterns
4. Pattern detection for 1-3 chunk repetitive sequences
5. Results saved as JSON v2.0 format `.thea` files with comprehensive metadata

### Output Format (.thea files v2.0)
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
  "prompt": { "system", "custom_prompt_file", "custom_prompt_content" },
  "response": { "text", "thinking", "json" },
  "statistics": { "tokens", "characters" },
  "errors": [],
  "warnings": []
}
```

## Common Development Commands

### Setup & Dependencies
```bash
# First-time setup (creates venv and installs dependencies)
npm run setup              # Linux/macOS
npm run setup-windows      # Windows

# Install/update dependencies only
npm run install            # Linux/macOS  
npm run install-windows    # Windows

# Activate virtual environment for manual work
. venv/bin/activate        # Linux/macOS
venv\Scripts\activate      # Windows
```

### Running THEA
```bash
# Process PDFs in Belege/ folder with default settings
npm run thea               # Linux/macOS (uses gemma3:27b, saves images)
npm run thea-windows       # Windows

# Direct usage with all options
. venv/bin/activate && python3 thea.py [OPTIONS] <file_pattern> [file_pattern2] ...

# Examples
python3 thea.py sample_document.pdf                    # Basic processing
python3 thea.py -m gemma:14b "*.pdf"                  # Different model
python3 thea.py --mode overwrite "*.pdf"              # Force reprocess
python3 thea.py --save-image --dpi 600 "*.pdf"        # High-res image export
python3 thea.py --prompt custom.prompt "*.pdf"        # Custom prompt
python3 thea.py --max-retries 10 -t 0.5 "*.pdf"       # Adjust retry/temperature
```

### Building Executables
```bash
# Build platform-specific executable
npm run build-windows      # Creates thea.exe
npm run build-linux        # Creates thea-linux
npm run build-macos        # Creates thea-macos

# Build using spec file (more control)
npm run build-spec         # Linux/macOS
npm run build-spec-windows # Windows

# Clean build artifacts
npm run clean-build        # Linux/macOS
npm run clean-build-windows # Windows
```

## Command-Line Options

- `--help, -h` - Show help message
- `--mode <skip|overwrite>` - Processing mode (default: skip)
- `-m, --model <name>` - Override model (default: gemma3:27b)
- `-t, --temperature <value>` - Initial temperature (0.0-2.0, default: 0.1)
- `--prompt <file.prompt>` - Load custom prompt (filename becomes suffix)
- `--suffix <text>` - Add suffix to output filename
- `--save-image` - Export processed images as PNG
- `--dpi <number>` - PDF conversion DPI (50-600, default: 300)
- `--max-retries <n>` - Max retry attempts (1-10, default: 3)

## Key Technical Details

### Ollama Integration
- Default endpoint: `https://b1s.hey.bahn.business/api/chat`
- Streaming JSON responses with `format: "json"` enforced
- Models must support vision capabilities (e.g., gemma3:27b, gemma:14b)
- Temperature progression formula: `initial_temp + (retry_count * (1.0 - initial_temp) / max_retries)`

### Pattern Detection
Detects three types of stuck patterns after 50+ repetitions:
1. Single chunk repetition (e.g., `\t\t\t...`)
2. Two-chunk alternation (e.g., `ABABAB...`)
3. Three-chunk cycle (e.g., `ABCABCABC...`)

### File Naming Convention
- Default: `<pdf>.<timestamp>.<model>.thea`
- With suffix: `<pdf>.<timestamp>.<model>.<suffix>.thea`
- Saved images: `<pdf>.<timestamp>.<model>[.<suffix>].<dpi>p<page>.png`

### Skip Mode Behavior
- Skip mode is suffix-specific: only skips files with matching model AND suffix
- Detects both old plain-text and new JSON format `.thea` files
- Allows parallel processing with different configurations

## Prerequisites

1. **Python 3.8+** with venv support
2. **Poppler** for PDF processing:
   - Ubuntu/Debian: `sudo apt-get install poppler-utils`
   - macOS: `brew install poppler`
   - Windows: Download from GitHub, add bin/ to PATH
3. **Ollama** running with vision models:
   - Start: `ollama serve`
   - Pull model: `ollama pull gemma3:27b`

## Dependencies (requirements.txt)
- pdf2image==1.17.0 - PDF to image conversion
- Pillow==10.4.0 - Image processing
- requests==2.32.3 - API communication
- pyinstaller==6.3.0 - Executable building