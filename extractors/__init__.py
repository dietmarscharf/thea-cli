from typing import Dict, Any, Optional, List
import time

class BaseExtractor:
    """Base class for PDF text extractors."""
    
    def __init__(self):
        self.name = self.__class__.__name__.replace('Extractor', '').lower()
        self.version = "unknown"
    
    def extract(self, pdf_path: str) -> Dict[str, Any]:
        """
        Extract text from PDF.
        
        Returns:
            Dictionary with extraction results including:
            - method: Extractor name
            - version: Library version
            - text: Extracted text
            - confidence: Confidence score (0-1)
            - metadata: Additional extraction metadata
        """
        start_time = time.time()
        
        try:
            text, extra_data = self._do_extraction(pdf_path)
            extraction_time = time.time() - start_time
            
            return {
                "method": self.name,
                "version": self.version,
                "text": text,
                "confidence": self._calculate_confidence(text, extra_data),
                "metadata": {
                    "extraction_time": extraction_time,
                    **extra_data
                },
                "success": True
            }
        except Exception as e:
            return {
                "method": self.name,
                "version": self.version,
                "text": "",
                "confidence": 0.0,
                "metadata": {
                    "extraction_time": time.time() - start_time,
                    "error": str(e)
                },
                "success": False
            }
    
    def _do_extraction(self, pdf_path: str) -> tuple[str, Dict[str, Any]]:
        """Override this method in subclasses."""
        raise NotImplementedError
    
    def _calculate_confidence(self, text: str, extra_data: Dict[str, Any]) -> float:
        """Calculate confidence score based on extraction quality."""
        if not text:
            return 0.0
        
        # Basic confidence calculation
        confidence = 0.5
        
        # Adjust based on text length
        if len(text) > 100:
            confidence += 0.2
        if len(text) > 1000:
            confidence += 0.1
        
        # Adjust based on structure
        if '\n' in text:
            confidence += 0.1
        if extra_data.get('tables'):
            confidence += 0.1
        
        return min(confidence, 1.0)