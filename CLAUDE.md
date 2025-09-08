# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

THEA is a comprehensive PDF processing and financial document analysis system that combines:
1. **Multi-pipeline PDF extraction** with three distinct approaches (image, text, deep learning)
2. **AI-powered document analysis** using Ollama models with retry logic and pattern detection
3. **Financial account analysis system** for processing bank statements and investment documents

The system processes 618+ financial documents across 6 account types, extracting structured data and generating comprehensive HTML reports with advanced visualizations.

## Architecture

### Core Processing Flow

The main `process_with_model()` function in `thea.py:392` orchestrates:

1. **Skip Mode Logic** - Intelligent file skipping with different patterns
2. **Pipeline Processing** - Runs selected pipeline to extract content
3. **Ollama API Streaming** - Sends to model with chunk-by-chunk processing
4. **Pattern Detection** - Monitors for stuck responses (1-100 char repetitions)
5. **Temperature Scaling** - Progressive increase (0.1→1.0) on retries
6. **Thinking Tag Extraction** - `<thinking>` for gemma, `<think>` for qwen
7. **JSON Response Cleaning** - Handles markdown blocks and validates JSON
8. **Result Persistence** - Saves to `.thea_extract` files with v2.0 metadata format

### Pipeline System

Three distinct pipelines in `pipelines/` directory:

1. **`pdf-extract-png`** - Vision-based extraction for Gemma models
2. **`pdf-extract-txt`** - Multi-extractor text for Qwen models  
3. **`pdf-extract-docling`** - ML-based extraction with IBM Docling

### Financial Document Analysis

Specialized analyzers for German financial documents:

- **`Konten.py`** - Base analyzer class with German formatting utilities
- **`Depotkonto.py`** - Depot/investment accounts with dual FY/CY tracking (lines 2400-3600)
- **`Girokonto.py`** - Checking accounts with transaction categorization
- **`Geldmarktkonto.py`** - Money market accounts with interest analysis

## Common Commands

### Running THEA

```bash
# Process account documents
npm run thea:konten:docling      # Process all 618 PDFs (~2-3 hours)

# Generate HTML reports
python3 Depotkonto.py    # Creates BLUEITS-Depotkonto.html and Ramteid-Depotkonto.html
python3 Girokonto.py     # Creates checking account reports
python3 Geldmarktkonto.py # Creates money market reports

# Direct pipeline execution
python3 thea.py --pipeline pdf-extract-docling --model gemma3:27b "docs/**/*.pdf"
```

### Key Parameters
- `--pipeline <type>` - pdf-extract-png, pdf-extract-txt, or pdf-extract-docling
- `--save-sidecars` - Save extraction artifacts
- `--max-attempts <n>` - Retry attempts (1-10, default 5)
- `--temperature <value>` - Initial temperature (0.0-2.0, default 0.1)

## Critical Implementation Details

### HTML Report Generation (Depotkonto.py)

#### Dual Tracking System (lines 2400-3600)
- **Fiscal Year (FY)** vs **Calendar Year (CY)** tracking for tax purposes
- Yellow rows for FY transitions, blue rows for CY transitions
- Automatic detection when FY ≠ CY (lines 2498-2510)

#### Column Structure (27 columns total)
Regular transaction rows with dual tracking:
- Columns 1-16: Basic transaction data
- Columns 17-20: FY and CY fees (with visual separators)
- Columns 21-23: Stock P&L (G/V Aktien)
- Columns 24-26: Non-stock P&L (G/V Nicht-Aktien) 
- Column 27: Document link

#### CSS Styling Features (lines 1700-2000)
- White background for Nr. and Document columns in colored rows
- Black text for all document links
- Visual separators using `fee-block` and `non-stock-block` classes
- Colorblind-friendly colors: Green profit (#28a745), Red loss (#dc3545)

#### Recent Fixes in Column Alignment
- **Line 3134**: Fixed non-stock column in FY summary rows
- **Line 3178**: Fixed non-stock column in FY start rows
- **Lines 2843-2844**: Added fees storage in transactions for CY calculations
- **Lines 2866-2867**: Store zero fees when no fees exist

### Stock Split Detection (lines 850-950)

Automatically detects and tracks stock splits:
```python
# Detects splits like "1:2" or "3-for-1"
# Calculates multiplier and new shares added
# Updates running totals for accurate position tracking
```

### Vertical Layout Parser (lines 190-260)

Handles Sparkasse's unique vertical format where values appear on separate lines:
- Detects pattern "Veräußerungs(gewinn|verlust) Ausmachender Betrag"
- Extracts values from up to 2 lines ahead
- Uses Kurswert proximity for value assignment

### German Format Handling

- **Numbers**: 1.234,56 format with thousand separators (line 100)
- **Dates**: DD.MM.YYYY format conversion
- **Trailing minus**: Handles "199.440,70-" bookkeeping format

## Model-Specific Configuration

### Critical System Prompt Issue
**WARNING**: `thea.py:53` contains hardcoded thinking tag instructions causing model conflicts.

### For Qwen Models
```json
{
  "system_prompt": {
    "suffix": "Output ONLY valid JSON. Do NOT use thinking tags."
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
    "suffix": "Use <thinking> tags for analysis, then output JSON separately."
  },
  "settings": {
    "format": "json",
    "temperature": 0.15
  }
}
```

## Account Document Structure

The `docs/` folder contains 618 PDFs across 6 accounts:
- BLUEITS: Depot (314), Geldmarkt (55), Giro (59)
- Ramteid: Depot (88), Geldmarkt (43), Giro (59)

## Processing Performance

- **pdf-extract-png**: ~45-60 seconds per PDF
- **pdf-extract-txt**: ~5-10 seconds per PDF
- **pdf-extract-docling**: ~37 seconds per PDF

## Data Quality Achievements

- **BLUEITS Depot**: 100% profit/loss extraction (112/112 sales)
- **Ramteid Depot**: 100% profit/loss extraction (23/23 sales)
- **Fee extraction**: 72.6% BLUEITS, 84.1% Ramteid
- **Stock split tracking**: Automatic 3:1 Tesla split detection

## Troubleshooting

### Common Issues

1. **Poppler not found**: Install with `apt-get install poppler-utils`
2. **Thinking tags in JSON**: Check model-specific prompt configuration
3. **Depot parsing failures**: Falls back to `parse_docling_table()` (line 673)
4. **Column misalignment**: Check `non-stock-block` classes in HTML output

### Debug Commands

```bash
# Test docling parser
python3 -c "from Depotkonto import DepotkontoAnalyzer; analyzer = DepotkontoAnalyzer(); result = analyzer.parse_docling_table(Path('path/to/docling.txt')); print(result)"

# Clean generated files
python3 thea.py --clean --force
npm run thea:clean:docling
```

## Environment Variables

- `OLLAMA_API_URL`: Override Ollama endpoint
- `THEA_DEFAULT_MODEL`: Default model (gemma3:27b)
- `THEA_DEFAULT_PIPELINE`: Default pipeline (pdf-extract-png)

## Recent Enhancements (2024-2025)

### Dual FY/CY Tracking System
- Fiscal Year (FY): April 1 - March 31 accounting period
- Calendar Year (CY): January 1 - December 31 for tax reporting
- Yellow rows: FY transitions with cumulative P&L and fee totals
- Blue rows: CY transitions (only when FY != CY)
- 27-column table structure with visual separators for fee/P&L blocks
- Automatic fee propagation from transactions to CY calculations

### Column Alignment Fixes
- Fixed non-stock values in yellow FY rows (lines 3134-3136, 3177-3179)
- Added fee storage in transactions for CY calculations (lines 2843-2844)
- Corrected visual separator positions
- Removed extra `<td></td>` elements causing 28 vs 27 column mismatches

### CSS Border Fixes
- Removed `year-separator` class from FY summary rows (line 3108)
- Removed `calendar-year-separator` class from CY summary rows (line 3262)
- Added `border-bottom: none !important` to depot-statement-year-end (line 1840)
- Eliminated black borders between fiscal/calendar year transition rows

### Enhanced Visualizations
- White background for Nr. and Document columns in colored rows (lines 1812-1831)
- Black text with underlines for all document links (lines 1882-1885)
- Purple background for capital action rows (Kapitalmaßnahme)
- Improved CSS for print and screen display

## File Naming Conventions

- **THEA extracts**: `<pdf>.<timestamp>.<model>.<suffix>.thea_extract`
- **Sidecars**: `.docling.txt`, `.docling.json`, `.docling.md`
- **HTML reports**: `<Company>-<AccountType>.html`

## Backup Directory

The `/backup/` directory contains archived test scripts, temporary files, and development artifacts.
These files should only be consulted when explicitly asked about:
- Old test scripts and their results
- Previous development iterations
- Backup versions of modified files

Current backup structure:
- `/backup/20250908/` - Test scripts, HTML generation utilities, and documentation from initial development