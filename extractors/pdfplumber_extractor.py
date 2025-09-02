from . import BaseExtractor
from typing import Dict, Any
import json

try:
    import pdfplumber
    HAS_PDFPLUMBER = True
    PDFPLUMBER_VERSION = pdfplumber.__version__ if hasattr(pdfplumber, '__version__') else "0.10.3"
except ImportError:
    HAS_PDFPLUMBER = False
    PDFPLUMBER_VERSION = None

class PdfPlumberExtractor(BaseExtractor):
    """Advanced PDF text extraction with table support using pdfplumber."""
    
    def __init__(self):
        super().__init__()
        self.name = "pdfplumber"
        self.version = PDFPLUMBER_VERSION or "not_installed"
        self.available = HAS_PDFPLUMBER
    
    def _do_extraction(self, pdf_path: str) -> tuple[str, Dict[str, Any]]:
        if not self.available:
            raise ImportError("pdfplumber is not installed")
        
        text_parts = []
        tables_data = []
        metadata = {"pages": 0, "tables": []}
        
        with pdfplumber.open(pdf_path) as pdf:
            metadata["pages"] = len(pdf.pages)
            
            for page_num, page in enumerate(pdf.pages):
                page_text_parts = [f"--- Page {page_num + 1} ---"]
                
                # Extract regular text
                try:
                    text = page.extract_text()
                    if text:
                        page_text_parts.append(text)
                except Exception as e:
                    page_text_parts.append(f"[Error extracting text: {e}]")
                
                # Extract tables
                try:
                    tables = page.extract_tables()
                    if tables:
                        for table_idx, table in enumerate(tables):
                            table_text = f"\n[Table {table_idx + 1}]\n"
                            for row in table:
                                # Convert None values to empty strings
                                row = [str(cell) if cell is not None else "" for cell in row]
                                table_text += " | ".join(row) + "\n"
                            page_text_parts.append(table_text)
                            
                            # Store table data for metadata
                            tables_data.append({
                                "page": page_num + 1,
                                "table_index": table_idx + 1,
                                "rows": len(table),
                                "columns": len(table[0]) if table else 0
                            })
                except Exception as e:
                    page_text_parts.append(f"[Error extracting tables: {e}]")
                
                text_parts.append("\n".join(page_text_parts))
        
        metadata["tables"] = tables_data
        metadata["table_count"] = len(tables_data)
        
        full_text = "\n\n".join(text_parts)
        return full_text, metadata
    
    def _calculate_confidence(self, text: str, extra_data: Dict[str, Any]) -> float:
        """Enhanced confidence calculation for pdfplumber."""
        base_confidence = super()._calculate_confidence(text, extra_data)
        
        # Boost confidence if tables were found
        if extra_data.get('table_count', 0) > 0:
            base_confidence += 0.15
        
        return min(base_confidence, 1.0)