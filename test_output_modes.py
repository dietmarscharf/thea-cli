#!/usr/bin/env python3
"""Test script to demonstrate the different output modes."""

def simulate_output_modes():
    """Simulate how different output modes would display content."""
    
    # Simulate streaming content
    sample_chunks = [
        "This ", "is ", "a ", "sample ", "text ", "that ", "would ", "be ", 
        "streamed ", "from ", "the ", "Ollama ", "API ", "in ", "multiple ", 
        "chunks. ", "Each ", "chunk ", "contains ", "a ", "few ", "tokens ", 
        "of ", "the ", "response. ", "In ", "real ", "usage, ", "this ", 
        "would ", "be ", "JSON ", "formatted ", "data ", "with ", "extracted ", 
        "text ", "from ", "PDF ", "documents."
    ]
    
    print("=" * 60)
    print("DEMONSTRATION OF OUTPUT MODES")
    print("=" * 60)
    
    # 1. Verbose mode (default)
    print("\n1. VERBOSE MODE (default - shows every chunk):")
    print("-" * 50)
    for i, chunk in enumerate(sample_chunks[:10], 1):
        print(f"Chunk {i}: {{'message': {{'content': '{chunk}'}}}}")
    print("... (continues for all chunks)")
    
    # 2. Aggregate mode
    print("\n2. AGGREGATE MODE (50 characters at a time):")
    print("-" * 50)
    buffer = ""
    total_chars = 0
    for chunk in sample_chunks:
        buffer += chunk
        total_chars += len(chunk)
        if len(buffer) >= 50:
            print(f"[{total_chars} chars] {buffer[:50]}", end="")
            buffer = buffer[50:]
    if buffer:
        print(f"[{total_chars} chars] {buffer}")
    
    # 3. Quiet mode
    print("\n3. QUIET MODE (minimal output):")
    print("-" * 50)
    print("Processing file: document.pdf")
    print("Successfully saved response to: document.20250831_120000.gemma3.27b.thea")
    
    print("\n" + "=" * 60)
    print("BENEFITS:")
    print("- Verbose: Full debugging information")
    print("- Aggregate: Reduced clutter, still see progress")
    print("- Quiet: Only essential information")

if __name__ == "__main__":
    simulate_output_modes()