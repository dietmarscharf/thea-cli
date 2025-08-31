# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

THEA is a PDF text extraction and analysis system that uses Ollama's vision models to process PDF documents. It converts PDFs to images and sends them to language models for text extraction, character counting, document classification, and content summarization with bilingual German/English output.

## Architecture

The system consists of a single Python script (`thea.py`) that:
1. Converts PDF files to PNG images using pdf2image/poppler (configurable DPI, default: 300)
2. Sends images to Ollama models via the Ollama API endpoint
3. Processes streaming JSON responses with character-by-character output to stdout
4. Implements progressive temperature increase (0.1 → 1.0) during retries
5. Detects and breaks stuck patterns (1-100 character repetitive sequences)
6. Saves results to timestamped `.thea` files in JSON v2.0 format
7. Optionally exports processed images as PNG files

### Core Processing Flow (`process_with_model` function, line 227)
1. Check for existing `.thea` files (skip mode logic)
2. Build Ollama API payload with temperature and token limits
3. Stream response and detect stuck patterns (up to 100 char patterns)
4. Handle timeouts (default: 100s) and token limits (default: 50000)
5. Save results to `.thea` file with comprehensive metadata
6. Display processing statistics

### Safety Features (Recent Enhancements)
- **Pattern Detection**: Detects 1-100 character repetitive patterns with adaptive thresholds
- **Timeout Protection**: Overall request timeout (configurable via `--timeout`)
- **Token Limiting**: Max token generation via Ollama's `num_predict` parameter
- **Proper Error Handling**: Saves partial responses even on failure

### Output File Naming Convention
- **Default**: `<pdf>.<timestamp>.<model>.thea`
- **With suffix**: `<pdf>.<timestamp>.<model>.<suffix>.thea`
- **With prompt file**: `<pdf>.<timestamp>.<model>.<promptname>.thea`
- **Saved images**: `<pdf>.<timestamp>.<model>[.<suffix>].<dpi>p<n>.png`

### Key Technical Details
- **Ollama API Endpoint**: Configurable, defaults to `https://b1s.hey.bahn.business/api/chat`
- **Model Override**: Use `-m/--model` to specify any Ollama model (default: gemma3:27b)
- **Temperature Control**: Initial temperature 0.1, increases progressively with retries
- **Pattern Detection**: 3000-chunk buffer for detecting patterns up to 100 characters
- **Output Format**: JSON v2.0 with `extracted_text`, `character_count`, bilingual descriptions
- **Processing Modes**: `skip` (default) or `overwrite`, suffix-specific
- **Custom Prompts**: Load via `.prompt` files, filename becomes suffix
- **Retry Logic**: Configurable 1-10 attempts with progressive temperature increase

## Quick Start

```bash
# First-time setup
npm run setup              # Linux/macOS
npm run setup-windows      # Windows

# Process PDFs (default: Belege/ folder)
npm run thea               # Linux/macOS
npm run thea-windows       # Windows

# Process specific files
. venv/bin/activate && python3 thea.py "sample_document.pdf"
```

## Common Development Tasks

### Testing with Sample Document
```bash
. venv/bin/activate
python3 thea.py sample_document.pdf                    # Basic test
python3 thea.py -m gemma:14b sample_document.pdf      # Test with different model
python3 thea.py --mode overwrite sample_document.pdf  # Force reprocess
python3 thea.py --timeout 200 --max-tokens 10000 "*.pdf"  # Custom limits
```

### Debugging Stuck Patterns
```bash
# Increase retries and watch temperature progression
python3 thea.py --max-retries 10 -t 0.1 "problematic.pdf"
# Temperature will progress: 0.1 → 0.2 → 0.3 → ... → 1.0
```

### Working with Different Models
```bash
# Check available models
ollama list

# Use a specific model
python3 thea.py -m gemma3:27b "*.pdf"    # Default
python3 thea.py -m gemma:14b "*.pdf"     # Smaller, faster
python3 thea.py -m llama2:13b "*.pdf"    # Alternative model
```

### Custom Prompts
```bash
# Create a custom prompt file
echo '{"version": "1.0", "system_prompt": {"suffix": "..."}}' > custom.prompt

# Use the custom prompt (creates *.custom.thea files)
python3 thea.py --prompt custom.prompt "*.pdf"
```

### Cleaning THEA Files
```bash
# Clean with confirmation
python3 thea.py --clean Belege/

# Force clean without confirmation
python3 thea.py --clean --force Belege/

# Preview what would be deleted
python3 thea.py --clean --dry-run Belege/

# Or use npm scripts
npm run thea:clean
npm run thea:clean-force
npm run thea:clean-dry
```

### Building Executables
```bash
npm run build-windows      # Creates thea-windows.exe
npm run build-linux        # Creates thea-linux
npm run build-macos        # Creates thea-macos
npm run clean-build        # Clean build artifacts
```

## Command-Line Interface

### Synopsis
```bash
python thea.py [OPTIONS] <file_pattern> [file_pattern2] ...
python thea.py --clean [--force] [--dry-run] [directory]
```

### Key Options
- `--mode <skip|overwrite>` - Processing mode (default: skip)
- `-m, --model <name>` - Override model (e.g., gemma:14b)
- `-t, --temperature <value>` - Initial temperature (0.0-2.0, default: 0.1)
- `--timeout <secs>` - Overall timeout (1-3600, default: 100)
- `--max-tokens <n>` - Max tokens to generate (100-100000, default: 50000)
- `--prompt <file.prompt>` - Load custom prompt configuration
- `--suffix <text>` - Add custom suffix to output filename
- `--save-image` - Save extracted images as PNG files
- `--dpi <number>` - Set DPI for PDF conversion (50-600, default: 300)
- `--max-retries <n>` - Max retry attempts (1-10, default: 3)

## Project Structure

- `thea.py` - Main application with all processing logic
- `requirements.txt` - Python dependencies (pdf2image, Pillow, requests, pyinstaller)
- `.prompt` - Default JSON prompt configuration with bilingual output schema
- `package.json` - npm scripts for convenient command execution
- `*.thea` - Output files containing extraction results (JSON v2.0)
- `*.prompt` - Custom prompt files (optional)

## Critical Code Locations

- **Main entry point**: Line 731 (`if __name__ == "__main__"`)
- **Process function**: Line 227 (`process_with_model`)
- **Pattern detection**: Lines 484-540 (stuck pattern logic with 1-100 char support)
- **Temperature calculation**: Line 397 (progressive increase formula)
- **Timeout/token monitoring**: Lines 447-473 (safety limits)
- **Clean function**: Line 86 (`clean_thea_files`)

## Temperature Progression Formula
```python
current_temperature = initial_temperature + (retry_count * (1.0 - initial_temperature) / (max_retries - 1))
```
- Default: 0.1 initial, reaches 1.0 on final retry
- With 3 retries: 0.10 → 0.55 → 1.00
- With 10 retries: 0.10 → 0.20 → 0.30 → ... → 1.00

## Pattern Detection Enhancement
The system now detects patterns from 1 to 100 characters:
- **Buffer size**: 3000 chunks (increased from 300)
- **Adaptive thresholds**:
  - 1-char patterns: 50 repetitions required
  - 2-char patterns: 25 repetitions
  - 3-10 char patterns: 10 repetitions or 60/length
  - 11-30 char patterns: 8 repetitions
  - 31-60 char patterns: 5 repetitions
  - 61-100 char patterns: 3 repetitions

## JSON Prompt File Format
```json
{
  "version": "1.0",
  "system_prompt": {
    "suffix": "Extract all text... provide bilingual output...",
    "output_format": {
      "type": "json",
      "schema": {
        "extracted_text": "string",
        "character_count": "number",
        "one_word_description_german": "string",
        "one_word_description_english": "string",
        "content_summary_german": "string",
        "content_summary_english": "string"
      }
    }
  },
  "user_prompt": {
    "template": "Process {{pdf_path}}"
  },
  "settings": {
    "model": "gemma3:27b",
    "temperature": 0.1,
    "max_retries": 3,
    "timeout": 100,
    "max_tokens": 50000
  }
}
```

## Prerequisites Installation

### Poppler (Required for PDF Processing)
```bash
# Ubuntu/Debian
sudo apt-get update && sudo apt-get install poppler-utils

# macOS
brew install poppler

# Windows
# Download from https://github.com/oschwartz10612/poppler-windows/releases/
# Extract and add bin folder to PATH
```

### Ollama Setup
```bash
# Start Ollama service
ollama serve

# Pull required model (default: gemma3:27b)
ollama pull gemma3:27b
```

## Recent Bug Fixes
- Fixed request_time calculation to occur after streaming completes
- Removed unused repetitive_pattern_count variable
- Initialize chunk_count and request_time at start of each retry
- Added proper data saving when timeout/token limits are hit
- Improved error handling for stuck pattern detection on final retry