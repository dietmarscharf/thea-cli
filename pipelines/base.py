from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple

class Pipeline(ABC):
    """Abstract base class for PDF processing pipelines."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the pipeline with optional configuration.
        
        Args:
            config: Pipeline-specific configuration from prompt file
        """
        self.config = config or {}
    
    @abstractmethod
    def process(self, pdf_path: str, **kwargs) -> Tuple[Any, Dict[str, Any]]:
        """
        Process a PDF file through the pipeline.
        
        Args:
            pdf_path: Path to the PDF file
            **kwargs: Additional pipeline-specific parameters
            
        Returns:
            Tuple of (processed_data, metadata)
            - processed_data: The main output (images, text, etc.)
            - metadata: Processing metadata and statistics
        """
        pass
    
    @abstractmethod
    def format_for_model(self, processed_data: Any, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format the processed data for sending to the model.
        
        Args:
            processed_data: Output from process() method
            metadata: Metadata from process() method
            
        Returns:
            Dictionary ready to be included in the model message
        """
        pass
    
    @property
    @abstractmethod
    def pipeline_type(self) -> str:
        """Return the pipeline type identifier."""
        pass
    
    @property
    def requires_vision_model(self) -> bool:
        """Return whether this pipeline requires a vision-capable model."""
        return False