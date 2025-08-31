import json
import datetime
import os
from typing import Any, Dict, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from .base import Pipeline

# Import all extractors
from extractors.pypdf2_extractor import PyPDF2Extractor
from extractors.pdfplumber_extractor import PdfPlumberExtractor
from extractors.pymupdf_extractor import PyMuPDFExtractor

class PdfToTextPipeline(Pipeline):
    """Pipeline for extracting text from PDFs using multiple methods."""
    
    @property
    def pipeline_type(self) -> str:
        return "pdf-extract-txt"
    
    @property
    def requires_vision_model(self) -> bool:
        return False
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        
        # Initialize available extractors
        self.extractors = self._initialize_extractors()
        
        # Get extractor preferences from config
        preferred_extractors = self.config.get('extractors', [])
        if preferred_extractors:
            # Filter to only use specified extractors
            self.extractors = {
                name: ext for name, ext in self.extractors.items()
                if name in preferred_extractors
            }
    
    def _initialize_extractors(self) -> Dict[str, Any]:
        """Initialize all available extractors."""
        extractors = {}
        
        # Try to initialize each extractor
        for ExtractorClass in [PyPDF2Extractor, PdfPlumberExtractor, PyMuPDFExtractor]:
            try:
                extractor = ExtractorClass()
                if extractor.available:
                    extractors[extractor.name] = extractor
                    print(f"  Initialized {extractor.name} extractor (v{extractor.version})")
                else:
                    print(f"  {extractor.name} extractor not available (library not installed)")
            except Exception as e:
                print(f"  Failed to initialize {ExtractorClass.__name__}: {e}")
        
        return extractors
    
    def process(self, pdf_path: str, parallel: bool = True, save_extractions: bool = False, 
                timestamp: str = None, model_part: str = None, suffix: str = None, **kwargs) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Extract text from PDF using multiple methods.
        
        Args:
            pdf_path: Path to the PDF file
            parallel: Whether to run extractors in parallel
            save_extractions: Whether to save extraction results to files
            timestamp: Timestamp for file naming
            model_part: Model name part for file naming
            suffix: Optional suffix for file naming
            
        Returns:
            Tuple of (extraction_results, metadata)
        """
        if not self.extractors:
            print("Error: No text extractors available. Please install at least one:")
            print("  pip install PyPDF2 pdfplumber pymupdf")
            return {}, {"error": "No extractors available"}
        
        print(f"  Extracting text using {len(self.extractors)} method(s)...")
        
        metadata = {
            "pipeline": self.pipeline_type,
            "timestamp": datetime.datetime.now().isoformat() + "Z",
            "pdf_path": pdf_path,
            "extractors_available": list(self.extractors.keys()),
            "extractors_used": [],
            "parallel_extraction": parallel,
            "save_extractions": save_extractions,
            "saved_files": []  # Track saved extraction files
        }
        
        extractions = []
        
        if parallel and len(self.extractors) > 1:
            # Run extractors in parallel
            with ThreadPoolExecutor(max_workers=len(self.extractors)) as executor:
                future_to_extractor = {
                    executor.submit(extractor.extract, pdf_path): name
                    for name, extractor in self.extractors.items()
                }
                
                for future in as_completed(future_to_extractor):
                    extractor_name = future_to_extractor[future]
                    try:
                        result = future.result(timeout=30)
                        if result.get("success"):
                            extractions.append(result)
                            metadata["extractors_used"].append(extractor_name)
                            print(f"    ✓ {extractor_name}: {len(result.get('text', ''))} chars extracted")
                            
                            # Save extraction to file if requested
                            if save_extractions and timestamp and model_part:
                                self._save_extraction_file(result, pdf_path, timestamp, model_part, 
                                                         suffix, metadata)
                        else:
                            print(f"    ✗ {extractor_name}: {result.get('metadata', {}).get('error', 'Unknown error')}")
                    except Exception as e:
                        print(f"    ✗ {extractor_name}: {e}")
        else:
            # Run extractors sequentially
            for name, extractor in self.extractors.items():
                try:
                    result = extractor.extract(pdf_path)
                    if result.get("success"):
                        extractions.append(result)
                        metadata["extractors_used"].append(name)
                        print(f"    ✓ {name}: {len(result.get('text', ''))} chars extracted")
                        
                        # Save extraction to file if requested
                        if save_extractions and timestamp and model_part:
                            self._save_extraction_file(result, pdf_path, timestamp, model_part, 
                                                     suffix, metadata)
                    else:
                        print(f"    ✗ {name}: {result.get('metadata', {}).get('error', 'Unknown error')}")
                except Exception as e:
                    print(f"    ✗ {name}: {e}")
        
        # Calculate overall statistics
        metadata["extraction_count"] = len(extractions)
        metadata["total_characters"] = sum(len(e.get("text", "")) for e in extractions)
        metadata["average_confidence"] = (
            sum(e.get("confidence", 0) for e in extractions) / len(extractions)
            if extractions else 0
        )
        
        extraction_results = {
            "pdf_path": pdf_path,
            "extraction_metadata": metadata,
            "extractions": extractions
        }
        
        return extraction_results, metadata
    
    def format_for_model(self, processed_data: Dict[str, Any], metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format extracted text for model consumption.
        
        Args:
            processed_data: Extraction results from process()
            metadata: Processing metadata
            
        Returns:
            Dictionary with text extraction data for model message
        """
        # Add instruction for the model
        instruction = (
            "You are receiving text extracted from a PDF using multiple methods. "
            "Each extraction method may capture different aspects of the document. "
            "No single extraction is guaranteed to be complete or perfect. "
            "Compare and combine the extractions to understand the full document content. "
            "Higher confidence scores generally indicate better extraction quality."
        )
        
        # Create a structured format for the model
        formatted_data = {
            "extraction_type": "multi-method-text",
            "instruction": instruction,
            "pdf_path": processed_data.get("pdf_path"),
            "extraction_summary": {
                "methods_used": metadata.get("extractors_used", []),
                "extraction_count": metadata.get("extraction_count", 0),
                "average_confidence": round(metadata.get("average_confidence", 0), 2)
            },
            "extractions": []
        }
        
        # Format each extraction for clarity
        for extraction in processed_data.get("extractions", []):
            formatted_extraction = {
                "method": extraction.get("method"),
                "confidence": round(extraction.get("confidence", 0), 2),
                "text_length": len(extraction.get("text", "")),
                "text": extraction.get("text", ""),
                "metadata": extraction.get("metadata", {})
            }
            formatted_data["extractions"].append(formatted_extraction)
        
        # Sort by confidence (highest first)
        formatted_data["extractions"].sort(key=lambda x: x["confidence"], reverse=True)
        
        return formatted_data
    
    def _save_extraction_file(self, extraction_result: Dict[str, Any], pdf_path: str, 
                              timestamp: str, model_part: str, suffix: Optional[str], 
                              metadata: Dict[str, Any]) -> None:
        """Save extraction result to a text file."""
        import os
        
        extractor_name = extraction_result.get("method", "unknown")
        text_content = extraction_result.get("text", "")
        
        # Build filename
        if suffix:
            text_file = f"{pdf_path}.{timestamp}.{model_part}.{suffix}.{extractor_name}.txt"
            meta_file = f"{pdf_path}.{timestamp}.{model_part}.{suffix}.{extractor_name}.json"
        else:
            text_file = f"{pdf_path}.{timestamp}.{model_part}.{extractor_name}.txt"
            meta_file = f"{pdf_path}.{timestamp}.{model_part}.{extractor_name}.json"
        
        try:
            # Save text content
            with open(text_file, 'w', encoding='utf-8') as f:
                f.write(text_content)
            
            # Save metadata
            extraction_metadata = {
                "extractor": extractor_name,
                "confidence": extraction_result.get("confidence", 0),
                "character_count": len(text_content),
                "extraction_metadata": extraction_result.get("metadata", {}),
                "file_size": os.path.getsize(text_file)
            }
            
            with open(meta_file, 'w', encoding='utf-8') as f:
                json.dump(extraction_metadata, f, indent=2)
            
            print(f"      Saved extraction: {text_file}")
            
            # Track saved file
            file_info = {
                "extractor": extractor_name,
                "type": "text/plain",
                "text_file": text_file,
                "meta_file": meta_file,
                "confidence": extraction_result.get("confidence", 0),
                "character_count": len(text_content),
                "file_size": os.path.getsize(text_file)
            }
            metadata["saved_files"].append(file_info)
            
        except Exception as e:
            print(f"      Error saving extraction file: {e}")