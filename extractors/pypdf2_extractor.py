from . import BaseExtractor
from typing import Dict, Any

try:
    import PyPDF2
    HAS_PYPDF2 = True
    PYPDF2_VERSION = PyPDF2.__version__ if hasattr(PyPDF2, '__version__') else "3.0.0"
except ImportError:
    HAS_PYPDF2 = False
    PYPDF2_VERSION = None

class PyPDF2Extractor(BaseExtractor):
    """Basic PDF text extraction using PyPDF2."""
    
    def __init__(self):
        super().__init__()
        self.name = "pypdf2"
        self.version = PYPDF2_VERSION or "not_installed"
        self.available = HAS_PYPDF2
    
    def _do_extraction(self, pdf_path: str) -> tuple[str, Dict[str, Any]]:
        if not self.available:
            raise ImportError("PyPDF2 is not installed")
        
        text_parts = []
        metadata = {"pages": 0}
        
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            metadata["pages"] = len(pdf_reader.pages)
            
            for page_num, page in enumerate(pdf_reader.pages):
                try:
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(f"--- Page {page_num + 1} ---\n{page_text}")
                except Exception as e:
                    text_parts.append(f"--- Page {page_num + 1} ---\n[Error extracting text: {e}]")
        
        full_text = "\n\n".join(text_parts)
        return full_text, metadata