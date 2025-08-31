from typing import Dict, Any, Optional
from .base import Pipeline
from .pdf_to_png import PdfToPngPipeline
from .pdf_to_text import PdfToTextPipeline

class PipelineManager:
    """Manages pipeline selection and execution."""
    
    # Available pipeline types
    PIPELINES = {
        "pdf-convert-png": PdfToPngPipeline,
        "pdf-extract-txt": PdfToTextPipeline
    }
    
    @classmethod
    def get_pipeline(cls, pipeline_type: str, config: Optional[Dict[str, Any]] = None) -> Pipeline:
        """
        Get a pipeline instance by type.
        
        Args:
            pipeline_type: Type of pipeline to create
            config: Optional configuration for the pipeline
            
        Returns:
            Pipeline instance
            
        Raises:
            ValueError: If pipeline type is not recognized
        """
        if pipeline_type not in cls.PIPELINES:
            raise ValueError(
                f"Unknown pipeline type: {pipeline_type}. "
                f"Available types: {', '.join(cls.PIPELINES.keys())}"
            )
        
        pipeline_class = cls.PIPELINES[pipeline_type]
        return pipeline_class(config)
    
    @classmethod
    def get_pipeline_from_prompt(cls, prompt_config: Dict[str, Any]) -> Pipeline:
        """
        Get a pipeline based on prompt configuration.
        
        Args:
            prompt_config: Prompt configuration dictionary
            
        Returns:
            Pipeline instance (defaults to pdf-convert-png if not specified)
        """
        # Get pipeline type from settings
        settings = prompt_config.get("settings", {})
        pipeline_type = settings.get("pipeline", "pdf-convert-png")
        
        # Get pipeline-specific configuration
        pipeline_config = settings.get("pipeline_config", {})
        
        # Add extractor preferences if specified
        if "extractors" in settings:
            pipeline_config["extractors"] = settings["extractors"]
        
        print(f"  Using pipeline: {pipeline_type}")
        
        return cls.get_pipeline(pipeline_type, pipeline_config)
    
    @classmethod
    def determine_pipeline_for_model(cls, model_name: str, override: Optional[str] = None) -> str:
        """
        Determine the best pipeline for a given model.
        
        Args:
            model_name: Name of the model
            override: Optional pipeline override
            
        Returns:
            Pipeline type string
        """
        if override:
            return override
        
        # Text-only models should use text extraction
        text_only_models = ["qwen", "mixtral", "phi", "vicuna", "alpaca"]
        model_lower = model_name.lower()
        
        for text_model in text_only_models:
            if text_model in model_lower:
                return "pdf-extract-txt"
        
        # Default to image pipeline for vision models
        return "pdf-convert-png"