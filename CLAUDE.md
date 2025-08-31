# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

THEA is a PDF text extraction and analysis system that uses Ollama's vision models to process PDF documents. It converts PDFs to images and sends them to language models for text extraction, character counting, document classification, and content summarization.

## Architecture

The system consists of a single Python script (`thea.py`) that:
1. Converts PDF files to PNG images using pdf2image/poppler (configurable DPI, default: 300)
2. Sends images to Ollama models via the Ollama API endpoint
3. Processes streaming JSON responses with character-by-character output to stdout
4. Implements progressive temperature increase (0.1 → 1.0) during retries
5. Detects and breaks stuck patterns (any 1-3 chunk repetitive sequences)
6. Saves results to timestamped `.thea` files
7. Optionally exports processed images as PNG files

### Core Processing Flow (`process_with_model` function, line 60)
1. Check for existing `.thea` files (skip mode logic, lines 65-74)
2. Build Ollama API payload with temperature (lines 131-140)
3. Stream response and detect stuck patterns (lines 165-228)
4. Save results to `.thea` file (lines 236-241)
5. Display processing statistics (lines 244-263)

### Output File Naming Convention
- **Default**: `<pdf>.<timestamp>.<model>.thea`
- **With suffix**: `<pdf>.<timestamp>.<model>.<suffix>.thea`
- **With prompt file**: `<pdf>.<timestamp>.<model>.<promptname>.thea`
- **Saved images**: `<pdf>.<timestamp>.<model>[.<suffix>].<dpi>p<n>.png`

### Key Technical Details
- **Ollama API Endpoint**: Configurable in code (line 85), defaults to `https://b1s.hey.bahn.business/api/chat`
- **Model Override**: Use `-m/--model` to specify any Ollama model (default: gemma3:27b)
- **Temperature Control**: Initial temperature 0.1 (very precise), increases progressively with retries to approach 1.0
- **Pattern Detection**: Detects any repeating pattern of 1-3 chunks after 50+ repetitions
- **Output Format**: JSON with `extracted_text`, `character_count`, `one_word_description`, `content_summary`
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
```

### Debugging Stuck Patterns
```bash
# Increase retries and watch temperature progression
python3 thea.py --max-retries 10 -t 0.1 "problematic.pdf"
# Temperature will progress: 0.1 → 0.19 → 0.28 → ... → 0.91
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
echo "Extract text and provide detailed analysis..." > detailed.prompt

# Use the custom prompt (creates *.detailed.thea files)
python3 thea.py --prompt detailed.prompt "*.pdf"
```

### Poppler Installation (Required)
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

# Pull required model (default: gemma3:27b, or any model specified with -m)
ollama pull gemma3:27b
# Or pull other models you want to use:
ollama pull gemma:14b
ollama pull llama2:13b
```

### Building Executables
```bash
# Build for current platform
npm run build-windows      # Creates thea-windows.exe on Windows
npm run build-linux        # Creates thea-linux executable on Linux
npm run build-macos        # Creates thea-macos executable on macOS

# Build using spec file (more control)
npm run build-spec         # Linux/macOS
npm run build-spec-windows # Windows

# Clean build artifacts
npm run clean-build        # Linux/macOS
npm run clean-build-windows # Windows
```

Note: PyInstaller can only build executables for the platform it's running on. The executable will be in the `dist/` folder.

## Command-Line Interface

### Synopsis
```bash
python thea.py [OPTIONS] <file_pattern> [file_pattern2] ...
```

### Options
- `--help, -h` - Show comprehensive help message and exit
- `--mode <skip|overwrite>` - Processing mode (default: skip)
  - `skip`: Skip PDFs that already have matching .thea files
  - `overwrite`: Always process PDFs even if .thea files exist
- `-m, --model <name>` - Override default model (e.g., gemma:14b, llama2:13b)
- `-t, --temperature <value>` - Set initial temperature (0.0-2.0, default: 0.1)
- `--prompt <file.prompt>` - Load system prompt from file (filename becomes default suffix)
- `--suffix <text>` - Add custom suffix to output filename (overrides prompt filename)
- `--save-image` - Save extracted images as PNG files with same naming as .thea files
- `--dpi <number>` - Set DPI resolution for PDF to image conversion (50-600, default: 300)
- `--max-retries <n>` - Max retry attempts when model gets stuck (1-10, default: 3)

### File Patterns
- Supports glob patterns: `*.pdf`, `path/*.pdf`, `**/*.pdf`
- Multiple patterns can be specified
- Case-sensitive patterns (use both `*.pdf` and `*.PDF` if needed)

## Project Structure

- `thea.py` - Main application script with PDF processing and model communication
- `requirements.txt` - Python dependencies (pdf2image==1.17.0, Pillow==10.4.0, requests==2.32.3, pyinstaller==6.3.0)
- `thea.spec` - PyInstaller configuration for building executables
- `.gitignore` - Excludes build artifacts and temporary files
- `package.json` - npm scripts for convenient command execution
- `venv/` - Python virtual environment (created during setup)
- `*.thea` - Output files containing extraction results
- `*.prompt` - Custom prompt files (optional)
- `*.png` - Saved images when using --save-image flag

## Key Implementation Details

### Critical Code Locations
- **Main entry point**: Line 273 (`if __name__ == "__main__"`)
- **Argument parsing**: Lines 274-342 (model/temperature at 327-339)
- **Process function**: Line 60 (`process_with_model`)
- **API endpoint**: Line 85 (modify for different Ollama URL)
- **Pattern detection**: Lines 183-228 (stuck pattern logic)
- **Temperature calculation**: Line 125

### Temperature Progression Formula
```python
current_temperature = initial_temperature + (retry_count * (1.0 - initial_temperature) / max_retries)
```
- Default: 0.1 initial, approaches 1.0 with retries
- With 3 retries: 0.10 → 0.40 → 0.70
- With 10 retries: 0.10 → 0.19 → 0.28 → ... → 0.91

### Pattern Detection Logic
The system detects three types of repetitive patterns:
1. **Single chunk**: Same content repeated 50+ times (e.g., `\t\t\t...`)
2. **Two-chunk alternating**: Pattern like `ABABAB...` for 50+ iterations
3. **Three-chunk cycle**: Pattern like `ABCABCABC...` for 50+ iterations

When detected, the connection closes and retries with higher temperature.

### Processing Modes
- `skip` (default): Skip PDFs that already have `.thea` files for the given model
- `overwrite`: Always process PDFs even if `.thea` files already exist

### Suffix Support
- Optional `--suffix` parameter adds a custom suffix before `.thea` extension
- Output format with suffix: `<pdf>.<timestamp>.<model>.<suffix>.thea`
- Skip mode is suffix-specific: only skips files with matching suffix
- Allows parallel processing with different configurations

### Prompt Files
- Load custom prompts from `.prompt` files with `--prompt` parameter
- Prompt filename (without extension) becomes default suffix
- `--suffix` parameter overrides the prompt-based suffix
- Falls back to default prompt if file not found

### Image Export
- Images are saved as PNG format when `--save-image` is used
- Default DPI is 300 (higher quality than pdf2image's default of 200)
- DPI range is validated between 50-600
- Images are saved with DPI in filename: `<dpi>p<page_number>` (e.g., `300p1.png`)

### Streaming Output
- **Always Active**: Content streams directly to stdout character-by-character as received from the model
- Provides real-time visual feedback without buffering or aggregation


### Processing Statistics
After each successful processing, displays:
- **Processing time**: Total duration in seconds
- **Input tokens**: Estimated count (text prompt + images)
- **Output tokens**: Estimated from response length
- **Total tokens**: Sum for cost estimation
- **Output characters**: Exact count
- **Chunks received**: Number of streaming chunks
- **Tokens/second**: Performance metric

## Troubleshooting

### Common Issues

**404 Error: Model not found**
```bash
# Check if model exists
ollama list
# Pull the model if missing
ollama pull gemma3:27b
```

**Poppler not found error**
- Ensure poppler is installed (see installation section)
- On Windows, verify poppler bin folder is in PATH

**Model gets stuck in repetitive output**
- Increase max retries: `--max-retries 10`
- Start with higher temperature: `-t 0.5`
- Check if model is appropriate for vision tasks

**Virtual environment issues**
```bash
# Recreate venv
rm -rf venv
npm run setup
```