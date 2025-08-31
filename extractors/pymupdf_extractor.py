from . import BaseExtractor
from typing import Dict, Any

try:
    import fitz  # PyMuPDF
    HAS_PYMUPDF = True
    PYMUPDF_VERSION = fitz.version[0] if hasattr(fitz, 'version') else "1.23.0"
except ImportError:
    HAS_PYMUPDF = False
    PYMUPDF_VERSION = None

class PyMuPDFExtractor(BaseExtractor):
    """Fast PDF text extraction with formatting using PyMuPDF."""
    
    def __init__(self):
        super().__init__()
        self.name = "pymupdf"
        self.version = PYMUPDF_VERSION or "not_installed"
        self.available = HAS_PYMUPDF
    
    def _do_extraction(self, pdf_path: str) -> tuple[str, Dict[str, Any]]:
        if not self.available:
            raise ImportError("PyMuPDF (fitz) is not installed")
        
        text_parts = []
        metadata = {
            "pages": 0,
            "has_images": False,
            "has_annotations": False
        }
        
        doc = fitz.open(pdf_path)
        metadata["pages"] = doc.page_count
        
        for page_num, page in enumerate(doc):
            page_text_parts = [f"--- Page {page_num + 1} ---"]
            
            # Extract text with layout preservation
            try:
                # Get text with better layout preservation
                text = page.get_text("text")
                if text:
                    page_text_parts.append(text)
                
                # Check for images
                image_list = page.get_images()
                if image_list:
                    metadata["has_images"] = True
                    page_text_parts.append(f"[Page contains {len(image_list)} image(s)]")
                
                # Check for annotations
                annot_list = page.annots()
                if annot_list:
                    metadata["has_annotations"] = True
                    for annot in annot_list:
                        if annot.info.get("content"):
                            page_text_parts.append(f"[Annotation: {annot.info['content']}]")
                
            except Exception as e:
                page_text_parts.append(f"[Error extracting content: {e}]")
            
            text_parts.append("\n".join(page_text_parts))
        
        doc.close()
        
        full_text = "\n\n".join(text_parts)
        return full_text, metadata
    
    def _calculate_confidence(self, text: str, extra_data: Dict[str, Any]) -> float:
        """Enhanced confidence calculation for PyMuPDF."""
        base_confidence = super()._calculate_confidence(text, extra_data)
        
        # PyMuPDF generally provides good extraction
        base_confidence += 0.1
        
        # Adjust for document complexity
        if extra_data.get('has_images'):
            base_confidence += 0.05
        if extra_data.get('has_annotations'):
            base_confidence += 0.05
        
        return min(base_confidence, 1.0)