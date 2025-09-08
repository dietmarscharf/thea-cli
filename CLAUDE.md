# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

THEA is a comprehensive PDF processing and financial document analysis system that:
1. Extracts structured data from PDFs using three distinct pipelines (vision, text, deep learning)
2. Processes extracted data through Ollama models with retry logic and pattern detection
3. Analyzes German financial documents (bank statements, investment accounts) and generates HTML/Excel reports

The system processes 618+ financial documents across 6 account types with advanced visualizations and dual fiscal/calendar year tracking.

## Architecture

### Core Processing (`thea.py`)

The main `process_with_model()` function (line 392) orchestrates:
- **Skip Mode Logic** - Intelligent file skipping based on existing extracts
- **Pipeline Selection** - Routes to appropriate extraction method
- **Ollama Streaming** - Chunk-by-chunk model processing with pattern detection
- **Temperature Scaling** - Progressive increase (0.1→1.0) on retries
- **Result Persistence** - Saves to `.thea_extract` files with v2.0 metadata

### Pattern Detection (`thea.py:704-717`)

Detects stuck model responses with doubled thresholds:
- Single chunks need 100 repetitions
- 2-chunk patterns need 50 cycles
- Longer patterns scale down progressively

### Pipeline System

Three extraction pipelines managed by `PipelineManager`:
1. **pdf-extract-png** - Vision-based for Gemma models
2. **pdf-extract-txt** - Multi-extractor text for Qwen models  
3. **pdf-extract-docling** - ML-based with IBM Docling

### Financial Analyzers

German document processors inheriting from `BaseKontoAnalyzer` in `Konten.py`:
- **Depotkonto.py** - Investment accounts with dual FY/CY tracking, Excel/HTML generation
- **Girokonto.py** - Checking accounts with transaction categorization
- **Geldmarktkonto.py** - Money market accounts with interest analysis

## Common Commands

### Initial Setup
```bash
# Install dependencies
npm run setup              # Linux/macOS
npm run setup-windows      # Windows

# Install Ollama models
ollama pull gemma3:27b
ollama pull qwen3:14b
```

### Processing Documents
```bash
# Extract all account documents (~2-3 hours for 618 PDFs)
npm run thea:konten:docling

# Generate HTML/Excel reports
python3 Depotkonto.py     # Investment account reports
python3 Girokonto.py      # Checking account reports
python3 Geldmarktkonto.py # Money market reports

# Direct pipeline execution
python3 thea.py --pipeline pdf-extract-docling --model gemma3:27b "docs/**/*.pdf"
```

### Cleaning and Maintenance
```bash
# Clean extraction artifacts
python3 thea.py --clean --force --pipeline docling docs/
npm run thea:clean:docling

# Generate sidecars only (no model processing)
npm run thea:sidecars:docling
```

### Key Parameters
- `--pipeline` - pdf-extract-png, pdf-extract-txt, or pdf-extract-docling
- `--max-attempts` - Retry attempts (1-10, default 5)
- `--temperature` - Initial temperature (0.0-2.0, default 0.1)
- `--mode skip` - Skip existing extractions
- `--mode overwrite` - Force re-extraction
- `--save-sidecars` - Save extraction artifacts

## Report Generation

### HTML Report Structure (`Depotkonto.py`)

#### Dual Year Tracking
- **Fiscal Year (FY)**: April 1 - March 31 for accounting (lines 1714-1723)
- **Calendar Year (CY)**: January 1 - December 31 for tax reporting (lines 1726-1740)
- Cumulative values reset at year boundaries with proper rounding

#### 27-Column Table Layout
- Columns 1-16: Transaction data (date, order#, type, ISIN, shares, price)
- Columns 17-20: FY/CY fees with visual separators
- Columns 21-23: Stock P&L (G/V Aktien)
- Columns 24-26: Non-stock P&L (G/V Nicht-Aktien)
- Column 27: Document link

#### MiFID Section
- Hidden by default (line 2620: `style="display: none;"`)
- Toggle functionality preserved for future use
- Removed from Excel generation (previously lines 4144-4180)

### Excel Generation (`generate_excel()`)

Creates `.xlsx` files with 4 worksheets:
1. **Übersicht** - Account overview and summary
2. **Depotabschlüsse** - Depot statements with balances
3. **Transaktionen** - Full transaction table (27 columns)
4. **Statistik** - Transaction type statistics

### Data Enrichment (`enrich_transactions_with_cumulative_data()`)

Lines 1630-1840: Enriches transactions with:
- Cumulative P&L tracking (stock/non-stock)
- Cumulative fee calculations (gross = net + VAT)
- Fiscal and calendar year resets
- Proper rounding to 2 decimal places

## Critical Implementation Details

### Failed Extraction Handling (lines 604-623)
When extraction fails, the system:
- Creates entry with type `⚠️ EXTRAKTION-FEHLGESCHLAGEN`
- Preserves `original_file` for document link display
- Allows easy identification of failed PDFs for re-processing

### Stock Split Detection (lines 750-762)
Automatically detects splits like "1:2" or "3-for-1" and updates position tracking.

### Vertical Layout Parser (`extract_trading_details()`)
Lines 164-350: Handles Sparkasse's vertical format where values appear on separate lines.

### German Format Handling
- Numbers: 1.234,56 format (handled in `parse_german_number()` in Konten.py)
- Dates: DD.MM.YYYY conversion
- Trailing minus: "199.440,70-" bookkeeping format

### Model-Specific Prompts

**WARNING**: Line 53 in `thea.py` contains hardcoded thinking tag instructions.

For Qwen models: Use `"Output ONLY valid JSON. Do NOT use thinking tags."`
For Gemma models: Use `"Use <thinking> tags for analysis, then output JSON separately."`

## Document Structure

The `docs/` folder contains 618 PDFs across 6 accounts:
- BLUEITS: Depot (314), Geldmarkt (55), Giro (59)
- Ramteid: Depot (88), Geldmarkt (43), Giro (59)

## Performance Metrics

- **pdf-extract-png**: ~45-60 seconds per PDF
- **pdf-extract-txt**: ~5-10 seconds per PDF
- **pdf-extract-docling**: ~37 seconds per PDF
- **Extraction accuracy**: 100% P&L for sales, 72-84% for fees

## Troubleshooting

### Common Issues
1. **Poppler not found**: Install with `apt-get install poppler-utils`
2. **Pattern detection false positives**: Check thresholds in `thea.py:704-717`
3. **Depot parsing failures**: Falls back to `parse_docling_table()` (line 673)
4. **Column misalignment**: Verify 27-column structure in HTML output
5. **Failed extractions**: Look for `⚠️ EXTRAKTION-FEHLGESCHLAGEN` in HTML, check document link for PDF filename
6. **Cumulative value issues**: Check year reset logic (lines 1718-1723, 1735-1740)

### Debug Commands
```bash
# Test specific parser
python3 -c "from Depotkonto import DepotkontoAnalyzer; analyzer = DepotkontoAnalyzer(); result = analyzer.parse_docling_table(Path('path/to/docling.txt')); print(result)"

# Find failed extractions
grep -l '"errors"' docs/**/*.thea_extract

# Re-process specific failed PDF
python3 thea.py --pipeline pdf-extract-docling --model gemma3:27b --temperature 0.3 --mode overwrite "path/to/failed.pdf"

# Check Excel column completeness
python3 -c "import openpyxl; wb = openpyxl.load_workbook('BLUEITS-Depotkonto.xlsx'); ws = wb['Transaktionen']; print(f'Columns: {ws.max_column}, Rows: {ws.max_row}'); wb.close()"
```

## Environment Variables

- `OLLAMA_API_URL`: Override Ollama endpoint (default: http://localhost:11434)
- `THEA_DEFAULT_MODEL`: Default model (gemma3:27b)
- `THEA_DEFAULT_PIPELINE`: Default pipeline (pdf-extract-png)

## File Naming Conventions

- **THEA extracts**: `<pdf>.<timestamp>.<model>.<pipeline>.thea_extract`
- **Sidecars**: `.docling.txt`, `.docling.json`, `.docling.md`
- **Report files**: `<Company>-<AccountType>.html`, `<Company>-<AccountType>.xlsx`

## CSS Features (lines 1700-2400)
- White backgrounds for Nr/Document columns in colored rows
- Visual separators using `fee-block` and `non-stock-block` classes
- Colorblind-friendly profit/loss colors (#28a745/#dc3545)
- Sticky navigation TOC with smooth scrolling
- Hidden MiFID section with toggle functionality