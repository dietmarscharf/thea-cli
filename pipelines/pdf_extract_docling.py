import json
import datetime
import os
from typing import Any, Dict, List, Optional, Tuple
from .base import Pipeline
from extractors.docling_extractor import DoclingExtractor

class PdfExtractDoclingPipeline(Pipeline):
    """Pipeline for advanced PDF extraction using Docling with deep learning models."""
    
    @property
    def pipeline_type(self) -> str:
        return "pdf-extract-docling"
    
    @property
    def requires_vision_model(self) -> bool:
        return False  # Docling handles its own vision/ML processing
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        
        # Initialize Docling extractor
        self.extractor = self._initialize_extractor()
        
        # Get configuration
        self.use_fallback_model = self.config.get('use_fallback_model', True)
        self.fallback_model = self.config.get('fallback_model', 'gemma3:27b')
    
    def _initialize_extractor(self) -> Optional[DoclingExtractor]:
        """Initialize the Docling extractor."""
        try:
            extractor = DoclingExtractor()
            if extractor.available:
                print(f"  Initialized Docling extractor (v{extractor.version})")
                return extractor
            else:
                print(f"  Docling extractor not available (library not installed)")
                print(f"  Install with: pip install docling")
                return None
        except Exception as e:
            print(f"  Failed to initialize Docling: {e}")
            return None
    
    def process(self, pdf_path: str, save_sidecars: bool = False, 
                timestamp: str = None, model_part: str = None, suffix: str = None, **kwargs) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Extract structured content from PDF using Docling's deep learning models.
        
        Args:
            pdf_path: Path to the PDF file
            save_sidecars: Whether to save extraction results as sidecar files
            timestamp: Timestamp for file naming
            model_part: Model name part for file naming
            suffix: Optional suffix for file naming
            
        Returns:
            Tuple of (extraction_results, metadata)
        """
        if not self.extractor:
            print("Error: Docling extractor not available. Please install:")
            print("  pip install docling")
            return {}, {"error": "Docling not available"}
        
        print(f"  Extracting content using Docling deep learning models...")
        
        metadata = {
            "pipeline": self.pipeline_type,
            "timestamp": datetime.datetime.now().isoformat() + "Z",
            "pdf_path": pdf_path,
            "extractor": "docling",
            "fallback_model": self.fallback_model if self.use_fallback_model else None,
            "save_sidecars": save_sidecars,
            "saved_files": []
        }
        
        # Extract using Docling
        extraction_result = self.extractor.extract(pdf_path)
        
        if extraction_result.get("success"):
            text_length = len(extraction_result.get("text", ""))
            confidence = extraction_result.get("confidence", 0)
            
            print(f"    ✓ Docling: {text_length} chars extracted (confidence: {confidence:.2f})")
            
            # Save extraction to file if requested
            if save_sidecars and timestamp and model_part:
                self._save_extraction_file(extraction_result, pdf_path, timestamp, 
                                         model_part, suffix, metadata)
            
            # Update metadata
            metadata["extraction_success"] = True
            metadata["text_length"] = text_length
            metadata["confidence"] = confidence
            metadata["has_tables"] = extraction_result.get("metadata", {}).get("has_tables", False)
            metadata["has_formulas"] = extraction_result.get("metadata", {}).get("has_formulas", False)
            metadata["document_type"] = extraction_result.get("metadata", {}).get("document_type", "unknown")
            metadata["pages"] = extraction_result.get("metadata", {}).get("pages", 0)
            
            # Check if we should use fallback model for enhancement
            if self.use_fallback_model and confidence < 0.7:
                metadata["needs_fallback"] = True
                metadata["fallback_reason"] = f"Low confidence: {confidence:.2f}"
                print(f"    ℹ Low confidence ({confidence:.2f}), recommend using {self.fallback_model} for enhancement")
        else:
            error_msg = extraction_result.get("metadata", {}).get("error", "Unknown error")
            print(f"    ✗ Docling: {error_msg}")
            
            metadata["extraction_success"] = False
            metadata["error"] = error_msg
            metadata["needs_fallback"] = True
            metadata["fallback_reason"] = "Extraction failed"
            
            if self.use_fallback_model:
                print(f"    ℹ Extraction failed, recommend using {self.fallback_model} fallback")
        
        extraction_results = {
            "pdf_path": pdf_path,
            "extraction_metadata": metadata,
            "extraction": extraction_result
        }
        
        return extraction_results, metadata
    
    def format_for_model(self, processed_data: Dict[str, Any], metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format extracted content for model consumption.
        
        Args:
            processed_data: Extraction results from process()
            metadata: Processing metadata
            
        Returns:
            Dictionary with structured data for model message
        """
        extraction = processed_data.get("extraction", {})
        
        # Create instruction based on extraction success
        if metadata.get("extraction_success"):
            if metadata.get("has_tables") or metadata.get("has_formulas"):
                instruction = (
                    "You are receiving structured content extracted from a PDF using Docling's deep learning models. "
                    "The document contains tables and/or formulas that have been preserved in the extraction. "
                    "The content includes document structure, reading order, and layout information. "
                    "Analyze the structured content to understand the document's meaning and context."
                )
            else:
                instruction = (
                    "You are receiving text extracted from a PDF using Docling's advanced document understanding. "
                    "The extraction preserves document structure and reading order. "
                    "Use this structured content to analyze and understand the document."
                )
        else:
            instruction = (
                "PDF extraction using Docling failed. The document may be corrupted, encrypted, or contain "
                "complex layouts that couldn't be processed. Consider using alternative extraction methods "
                "or vision-based models for this document."
            )
        
        # Create structured format for the model
        formatted_data = {
            "extraction_type": "docling-structured",
            "instruction": instruction,
            "pdf_path": processed_data.get("pdf_path"),
            "extraction_summary": {
                "method": "docling",
                "success": metadata.get("extraction_success", False),
                "confidence": round(metadata.get("confidence", 0), 2),
                "document_type": metadata.get("document_type", "unknown"),
                "pages": metadata.get("pages", 0),
                "has_tables": metadata.get("has_tables", False),
                "has_formulas": metadata.get("has_formulas", False)
            }
        }
        
        # Add extracted content if successful
        if metadata.get("extraction_success"):
            formatted_data["content"] = {
                "text": extraction.get("text", ""),
                "text_length": len(extraction.get("text", "")),
                "metadata": extraction.get("metadata", {})
            }
            
            # Add sections if available
            sections = extraction.get("metadata", {}).get("sections", [])
            if sections:
                formatted_data["content"]["sections"] = sections
            
            # Add tables if available
            tables = extraction.get("metadata", {}).get("tables", [])
            if tables:
                formatted_data["content"]["tables"] = tables
        else:
            formatted_data["error"] = metadata.get("error", "Extraction failed")
            formatted_data["fallback_recommended"] = {
                "use_model": metadata.get("fallback_model"),
                "reason": metadata.get("fallback_reason")
            }
        
        return formatted_data
    
    def _save_extraction_file(self, extraction_result: Dict[str, Any], pdf_path: str,
                              timestamp: str, model_part: str, suffix: Optional[str],
                              metadata: Dict[str, Any]) -> None:
        """Save extraction result to files."""
        text_content = extraction_result.get("text", "")
        
        # Build filename
        if suffix:
            text_file = f"{pdf_path}.{timestamp}.{model_part}.{suffix}.docling.txt"
            json_file = f"{pdf_path}.{timestamp}.{model_part}.{suffix}.docling.json"
            md_file = f"{pdf_path}.{timestamp}.{model_part}.{suffix}.docling.md"
        else:
            text_file = f"{pdf_path}.{timestamp}.{model_part}.docling.txt"
            json_file = f"{pdf_path}.{timestamp}.{model_part}.docling.json"
            md_file = f"{pdf_path}.{timestamp}.{model_part}.docling.md"
        
        try:
            # Save plain text content
            with open(text_file, 'w', encoding='utf-8') as f:
                f.write(text_content)
            
            # Save structured metadata
            extraction_metadata = {
                "extractor": "docling",
                "confidence": extraction_result.get("confidence", 0),
                "character_count": len(text_content),
                "extraction_metadata": extraction_result.get("metadata", {}),
                "file_size": os.path.getsize(text_file)
            }
            
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(extraction_metadata, f, indent=2)
            
            # If the content looks like markdown, save as .md too
            if '##' in text_content or '|' in text_content or '```' in text_content:
                with open(md_file, 'w', encoding='utf-8') as f:
                    f.write(text_content)
                print(f"      Saved extraction: {text_file}, {json_file}, {md_file}")
            else:
                print(f"      Saved extraction: {text_file}, {json_file}")
            
            # Track saved files
            file_info = {
                "extractor": "docling",
                "type": "text/plain",
                "text_file": text_file,
                "json_file": json_file,
                "confidence": extraction_result.get("confidence", 0),
                "character_count": len(text_content),
                "file_size": os.path.getsize(text_file)
            }
            
            if os.path.exists(md_file):
                file_info["md_file"] = md_file
            
            metadata["saved_files"].append(file_info)
            
        except Exception as e:
            print(f"      Error saving extraction files: {e}")