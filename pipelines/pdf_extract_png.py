import base64
import io
from typing import Any, Dict, List, Optional, Tuple
from .base import Pipeline

try:
    from pdf2image import convert_from_path
    from PIL import Image
except ImportError:
    print("pdf2image not available")
    convert_from_path = None
    Image = None

class PdfExtractPngPipeline(Pipeline):
    """Pipeline for extracting PDF pages as PNG images."""
    
    @property
    def pipeline_type(self) -> str:
        return "pdf-extract-png"
    
    @property
    def requires_vision_model(self) -> bool:
        return True
    
    def process(self, pdf_path: str, dpi: int = 300, save_sidecars: bool = False, **kwargs) -> Tuple[Tuple[List[str], List[Any]], Dict[str, Any]]:
        """
        Convert PDF to base64-encoded PNG images.
        
        Args:
            pdf_path: Path to the PDF file
            dpi: Resolution for image conversion
            save_sidecars: Whether to save PNG images as sidecar files
            
        Returns:
            Tuple of ((base64_images, pil_images), metadata)
        """
        if convert_from_path is None:
            print("Error: pdf2image with poppler is required but not available")
            print("Please install poppler binaries for Windows:")
            print("1. Download from: https://github.com/oschwartz10612/poppler-windows/releases/")
            print("2. Extract and add to PATH")
            print("3. Or use conda: conda install -c conda-forge poppler")
            return ([], []), {"error": "pdf2image not available"}
        
        metadata = {
            "pipeline": self.pipeline_type,
            "dpi": dpi,
            "pages_processed": 0,
            "save_sidecars": save_sidecars,
            "saved_files": []  # Track saved image files
        }
        
        try:
            images = convert_from_path(pdf_path, dpi=dpi)
            base64_images: List[str] = []
            pil_images: List[Any] = []
            
            for i, image in enumerate(images, 1):
                # Keep PIL image for potential saving
                if save_sidecars:
                    pil_images.append(image)
                
                # Track image information
                image_info = {
                    "page": i,
                    "width": image.width,
                    "height": image.height,
                    "resolution": f"{image.width}x{image.height}",
                    "dpi": dpi
                }
                
                # Convert to base64
                img_byte_arr = io.BytesIO()
                image.save(img_byte_arr, format='PNG')
                base64_image = base64.b64encode(img_byte_arr.getvalue()).decode('utf-8')
                base64_images.append(base64_image)
                
                # Add base64 size to image info
                image_info["base64_size"] = len(base64_image)
                metadata["saved_files"].append(image_info)
            
            metadata["pages_processed"] = len(images)
            metadata["total_image_size"] = sum(len(img) for img in base64_images)
            
            return (base64_images, pil_images), metadata
            
        except Exception as e:
            print(f"Error processing PDF {pdf_path}: {e}")
            metadata["error"] = str(e)
            return ([], []), metadata
    
    def format_for_model(self, processed_data: Tuple[List[str], List[Any]], metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format base64 images for model consumption.
        
        Args:
            processed_data: Tuple of (base64_images, pil_images)
            metadata: Processing metadata
            
        Returns:
            Dictionary with images field for model message
        """
        base64_images, _ = processed_data
        return {
            "images": base64_images,
            "pipeline_metadata": {
                "type": self.pipeline_type,
                "pages": metadata.get("pages_processed", 0),
                "dpi": metadata.get("dpi", 300)
            }
        }