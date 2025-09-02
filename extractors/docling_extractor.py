from . import BaseExtractor
from typing import Dict, Any
import json

try:
    from docling.document_converter import DocumentConverter
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import PdfPipelineOptions
    HAS_DOCLING = True
    try:
        import docling
        DOCLING_VERSION = docling.__version__ if hasattr(docling, '__version__') else "0.3.0"
    except:
        DOCLING_VERSION = "0.3.0"
except ImportError:
    HAS_DOCLING = False
    DOCLING_VERSION = None
    # Create dummy classes to prevent errors
    DocumentConverter = None
    InputFormat = None
    PdfPipelineOptions = None

class DoclingExtractor(BaseExtractor):
    """Advanced PDF extraction using IBM's Docling with deep learning models."""
    
    def __init__(self):
        super().__init__()
        self.name = "docling"
        self.version = DOCLING_VERSION or "not_installed"
        self.available = HAS_DOCLING
    
    def _do_extraction(self, pdf_path: str) -> tuple[str, Dict[str, Any]]:
        if not self.available:
            raise ImportError("Docling is not installed. Install with: pip install docling")
        
        metadata = {
            "pages": 0,
            "tables": [],
            "sections": [],
            "has_tables": False,
            "has_formulas": False,
            "document_type": None
        }
        
        try:
            # Initialize converter with PDF support
            converter = DocumentConverter(
                allowed_formats=[InputFormat.PDF]
            )
            
            # Convert the document
            result = converter.convert(pdf_path)
            
            # Get the document object
            doc = result.document
            
            # Extract text with structure preservation
            if hasattr(doc, 'export_to_markdown'):
                # Export as markdown to preserve structure
                full_text = doc.export_to_markdown()
                
                # Extract metadata about pages (if available)
                if hasattr(doc, 'pages'):
                    metadata["pages"] = len(doc.pages) if doc.pages else 1
                elif hasattr(result, 'pages'):
                    metadata["pages"] = len(result.pages) if result.pages else 1
                else:
                    # Estimate pages from content
                    metadata["pages"] = max(1, len(full_text) // 3000)
                
                # Check for tables (markdown tables have | and ---)
                if '|' in full_text and '---' in full_text:
                    metadata["has_tables"] = True
                    # Count tables by looking for table headers
                    table_lines = [line for line in full_text.split('\n') if '|---' in line or '| ---' in line]
                    metadata["tables"] = [f"Table {i+1}" for i in range(len(table_lines))]
                
                # Check for formulas (LaTeX-style or markdown math)
                if '$$' in full_text or '$' in full_text or '```math' in full_text:
                    metadata["has_formulas"] = True
                
                # Extract sections from markdown headers
                for line in full_text.split('\n'):
                    if line.startswith('# '):
                        metadata["sections"].append(line[2:].strip())
                    elif line.startswith('## '):
                        metadata["sections"].append(line[3:].strip())
                
            else:
                # Fallback if export_to_markdown is not available
                if hasattr(doc, 'text'):
                    full_text = doc.text
                else:
                    full_text = str(doc)
            
            # Detect document type based on content
            text_lower = full_text.lower()
            if "invoice" in text_lower or "rechnung" in text_lower:
                metadata["document_type"] = "invoice"
            elif "contract" in text_lower or "vertrag" in text_lower:
                metadata["document_type"] = "contract"
            elif "report" in text_lower or "bericht" in text_lower:
                metadata["document_type"] = "report"
            elif "statement" in text_lower or "kontoauszug" in text_lower:
                metadata["document_type"] = "statement"
            else:
                metadata["document_type"] = "document"
            
            return full_text, metadata
            
        except Exception as e:
            # If Docling fails, provide detailed error
            error_msg = f"Docling extraction failed: {str(e)}"
            metadata["error"] = error_msg
            metadata["extraction_method"] = "docling_failed"
            
            # Return empty text with error metadata
            return "", metadata
    
    def _calculate_confidence(self, text: str, extra_data: Dict[str, Any]) -> float:
        """Calculate confidence score for Docling extraction."""
        if not text:
            return 0.0
        
        # Start with base confidence for Docling (higher due to advanced models)
        confidence = 0.7
        
        # Adjust based on text length
        if len(text) > 500:
            confidence += 0.1
        if len(text) > 2000:
            confidence += 0.05
        
        # Bonus for structured content
        if extra_data.get('has_tables'):
            confidence += 0.05
        if extra_data.get('sections'):
            confidence += 0.05
        if extra_data.get('has_formulas'):
            confidence += 0.03
        
        # Penalty for errors
        if extra_data.get('error'):
            confidence -= 0.3
        
        return min(max(confidence, 0.0), 1.0)