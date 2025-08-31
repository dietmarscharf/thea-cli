#!/usr/bin/env python3
"""Test script to verify the new image filename format."""

def test_filename_format():
    """Test the new filename format logic."""
    
    # Simulate the filename generation logic
    pdf_path = "test_document.pdf"
    timestamp = "20250831_120000"
    model_part = "gemma3.27b"
    
    print("Testing new filename format with DPI marking:")
    print("=" * 50)
    
    # Test without suffix
    print("\n1. Without suffix:")
    for dpi in [150, 300, 600]:
        for page in [1, 2, 3]:
            filename = f"{pdf_path}.{timestamp}.{model_part}.{dpi}p{page}.png"
            print(f"   DPI={dpi}, Page={page}: {filename}")
    
    # Test with suffix
    print("\n2. With suffix 'hq':")
    suffix = "hq"
    for dpi in [150, 300, 600]:
        for page in [1, 2]:
            filename = f"{pdf_path}.{timestamp}.{model_part}.{suffix}.{dpi}p{page}.png"
            print(f"   DPI={dpi}, Page={page}: {filename}")
    
    print("\n3. Comparison with old format:")
    print(f"   Old: {pdf_path}.{timestamp}.{model_part}.page_1.png")
    print(f"   New: {pdf_path}.{timestamp}.{model_part}.300p1.png")
    
    print("\nBenefits of new format:")
    print("- DPI value is visible in filename")
    print("- Shorter format (300p1 vs page_1)")
    print("- Easy to identify resolution used for each image")

if __name__ == "__main__":
    test_filename_format()