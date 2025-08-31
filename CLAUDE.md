# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

THEA is a PDF text extraction and analysis system that uses Ollama's vision models to process PDF documents. It converts PDFs to images and sends them to language models for text extraction, character counting, document classification, and content summarization.

## Architecture

The system consists of a single Python script (`thea.py`) that:
1. Converts PDF files to PNG images using pdf2image/poppler (configurable DPI, default: 300)
2. Sends images to Ollama models (default: gemma3:27b) via the Ollama API
3. Processes streaming JSON responses with character-by-character output to stdout
4. Automatically retries when model gets stuck in repetitive patterns
5. Saves results to timestamped `.thea` files
6. Optionally saves extracted images as PNG files
7. Displays detailed processing statistics including token usage and performance metrics

### Output File Naming Convention
- **Default**: `<pdf>.<timestamp>.<model>.thea`
- **With suffix**: `<pdf>.<timestamp>.<model>.<suffix>.thea`
- **With prompt file**: `<pdf>.<timestamp>.<model>.<promptname>.thea`
- **Saved images**: `<pdf>.<timestamp>.<model>[.<suffix>].<dpi>p<n>.png`

### Key Components
- **PDF Processing**: Uses pdf2image library (v1.17.0) with poppler backend for PDF-to-image conversion
- **Model Communication**: Makes HTTP requests to Ollama API at `https://b1s.hey.bahn.business/api/chat` with streaming enabled
- **Output Format**: Models respond with JSON containing extracted_text, character_count, one_word_description, and content_summary
- **Error Handling**: Gracefully handles missing poppler installation and provides installation instructions
- **Prompt System**: Supports custom prompts via `.prompt` files with automatic suffix generation
- **Processing Modes**: Skip (default) or overwrite existing files, suffix-specific
- **Image Export**: Optional PNG export with configurable DPI (50-600)
- **Stuck Pattern Detection**: Automatically detects and retries when model gets stuck in repetitive patterns (e.g., endless \n sequences)
- **Streaming Output**: Always streams content character-by-character to stdout in real-time
- **Statistics**: Displays processing time, token usage estimates, and performance metrics

## Development Commands

### Setup and Installation
```bash
# Initial setup (creates venv and installs dependencies)
npm run setup              # Linux/macOS
npm run setup-windows      # Windows

# Install/update dependencies only
npm run install            # Linux/macOS  
npm run install-windows    # Windows
```

### Help and Documentation
```bash
# Show comprehensive help with all options and examples
python3 thea.py --help
python3 thea.py -h
```

### Running the Application
```bash
# Process all PDFs using npm scripts (uses venv automatically)
npm run thea               # Linux/macOS - processes Belege/*.pdf with --save-image (skip mode)
npm run thea-windows       # Windows - processes Belege/*.pdf with --save-image (skip mode)

# Direct Python execution (requires venv activation)
. venv/bin/activate        # Linux/macOS
venv\Scripts\activate      # Windows

# Default mode (skip): Skip PDFs that already have .thea files
python3 thea.py "*.pdf"                                    # Default: aggregate output mode
python3 thea.py "specific_file.pdf"
python3 thea.py "path/to/*.pdf"

# Overwrite mode: Always reprocess PDFs even if .thea files exist
python3 thea.py --mode overwrite "*.pdf"
python3 thea.py --mode overwrite "specific_file.pdf"

# Skip mode (explicit): Skip already processed PDFs
python3 thea.py --mode skip "*.pdf"

# Using suffix for different output versions
python3 thea.py --suffix images "*.pdf"                    # Creates *.images.thea files
python3 thea.py --suffix v2 "*.pdf"                        # Creates *.v2.thea files
python3 thea.py --mode skip --suffix analysis "*.pdf"      # Skip only *.analysis.thea files
python3 thea.py --mode overwrite --suffix final "*.pdf"    # Always create *.final.thea files

# Using custom prompt files
python3 thea.py --prompt extraction.prompt "*.pdf"         # Uses extraction.prompt, suffix: extraction
python3 thea.py --prompt analysis.prompt "*.pdf"           # Uses analysis.prompt, suffix: analysis
python3 thea.py --prompt custom.prompt --suffix v2 "*.pdf" # Uses custom.prompt, suffix: v2 (override)

# Image extraction features
python3 thea.py --save-image "*.pdf"                       # Save images with default DPI (300)
python3 thea.py --save-image --dpi 150 "*.pdf"            # Save images with custom DPI
python3 thea.py --save-image --dpi 600 --suffix hq "*.pdf" # High quality image extraction

# Streaming output (always enabled)
python3 thea.py "*.pdf"                                    # Streams content character-by-character

# Retry configuration for unstable models
python3 thea.py --max-retries 5 "*.pdf"                    # Increase retry attempts to 5
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

# Pull required model (only gemma3:27b is currently used)
ollama pull gemma3:27b
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

## Important Technical Details

- The system requires Ollama to be running locally on port 11434 or at configured endpoint
- Currently only uses gemma3:27b model (other models commented out in code at line 522)
- Output files are saved in the same directory as the input PDF
- The system logs all API communications to stdout for debugging
- JSON format is enforced in model responses via the `format: "json"` parameter
- Virtual environment is required and automatically used by npm scripts
- System prompt instructs models to provide exact character counts and structured JSON output

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

### Stuck Pattern Detection
- Monitors streaming responses for repetitive patterns (e.g., alternating `\` and `n`)
- Automatically terminates and retries when stuck pattern detected (50+ consecutive chunks)
- Configurable retry attempts via `--max-retries` parameter
- Helps handle model instabilities during long-running extractions

### Processing Statistics
After each successful processing, displays:
- **Processing time**: Total duration in seconds
- **Input tokens**: Estimated count (text prompt + images)
- **Output tokens**: Estimated from response length
- **Total tokens**: Sum for cost estimation
- **Output characters**: Exact count
- **Chunks received**: Number of streaming chunks
- **Tokens/second**: Performance metric

## Recent Changes

### Streaming Output (Latest)
- Output now always streams character-by-character to stdout using `sys.stdout.write()`
- Removed all output mode options (--quiet, --verbose, --aggregate)
- Real-time streaming provides immediate visual feedback without buffering

### PyInstaller Support
- Added PyInstaller configuration for building standalone executables
- Created npm scripts for building on Windows, Linux, and macOS
- Executables include all Python dependencies (50-100 MB size)
- Note: Poppler utilities still need to be installed separately

### Pattern Detection & Retry Mechanism
- Flexible detection of any repetitive pattern (1, 2, or 3 chunk sequences)
- Detects patterns like endless tabs (`\t\t\t`), alternating characters, or any repeating sequence
- Retry logic with configurable attempts (default: 3, max: 10)
- Terminates connection and restarts when detecting 50+ repetitions of the same pattern
- Progressive temperature increase during retries (0.3 → ~1.0) helps break stuck patterns

### Image Naming Format
- Uses `<dpi>p<n>` format (e.g., `300p1.png`)
- Makes DPI resolution immediately visible in filename