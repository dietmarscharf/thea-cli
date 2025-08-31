import base64
import io
import json
import sys
from typing import Any, List, Optional, Dict
import requests
import glob
import os
import datetime
import time
import platform
import socket
try:
    from pdf2image import convert_from_path
except ImportError:
    print("pdf2image not available")
    convert_from_path = None
from PIL import Image
import os

def load_prompt_file(prompt_path):
    """Load system prompt from a .prompt file."""
    try:
        with open(prompt_path, 'r', encoding='utf-8') as f:
            return f.read().strip()
    except FileNotFoundError:
        print(f"Warning: Prompt file '{prompt_path}' not found. Using default prompt.")
        return None
    except Exception as e:
        print(f"Error reading prompt file '{prompt_path}': {e}")
        return None

def pdf_to_base64_images(pdf_path, dpi=300) -> tuple[list[Any], list[Any]]:
    # Convert PDF to list of PIL images (one per page)
    # Returns tuple of (base64_images, pil_images)
    if convert_from_path is None:
        print("Error: pdf2image with poppler is required but not available")
        print("Please install poppler binaries for Windows:")
        print("1. Download from: https://github.com/oschwartz10612/poppler-windows/releases/")
        print("2. Extract and add to PATH")
        print("3. Or use conda: conda install -c conda-forge poppler")
        return [], []
    
    try:
        images = convert_from_path(pdf_path, dpi=dpi)
        base64_images: list[Any] = []
        pil_images: list[Any] = []
        for image in images:
            # Keep PIL image for potential saving
            pil_images.append(image)
            # Convert to base64
            img_byte_arr = io.BytesIO()
            image.save(img_byte_arr, format='PNG')
            base64_image = base64.b64encode(img_byte_arr.getvalue()).decode('utf-8')
            base64_images.append(base64_image)
        return base64_images, pil_images
    except Exception as e:
        print(f"Error processing PDF {pdf_path}: {e}")
        return [], []


def process_with_model(model_name, base64_images, pdf_path, system_prompt, user_prompt, mode='skip', suffix='', save_image=False, pil_images=None, max_retries=3, dpi=300, initial_temperature=0.1, prompt_file=None, custom_prompt_content=None, endpoint_url="https://b1s.hey.bahn.business/api/chat"):
    # Track all execution details for the new JSON format
    execution_data = {
        "version": "2.0",
        "metadata": {},
        "settings": {},
        "execution": {},
        "prompt": {},
        "response": {},
        "statistics": {},
        "errors": [],
        "warnings": []
    }
    
    # Generate model part (e.g., gemma3.12b)
    model_part: Any = model_name.replace(":", ".")
    
    # Check if a .thea file already exists for this PDF and model with the same suffix
    if mode == 'skip':
        if suffix:
            existing_pattern = f"{pdf_path}.*.{model_part}.{suffix}.thea"
        else:
            existing_pattern = f"{pdf_path}.*.{model_part}.thea"
        existing_files = glob.glob(existing_pattern)
        if existing_files:
            suffix_msg = f" with suffix '{suffix}'" if suffix else ""
            # Check if any are in new JSON format (for info)
            json_format_count = 0
            for existing_file in existing_files:
                try:
                    with open(existing_file, 'r', encoding='utf-8') as f:
                        first_char = f.read(1)
                        if first_char == '{':
                            json_format_count += 1
                except:
                    pass
            format_info = f" ({json_format_count} JSON format)" if json_format_count > 0 else ""
            print(f"Skipping {pdf_path} with model {model_name}{suffix_msg} - already processed ({len(existing_files)} existing file(s){format_info})")
            return
    
    # Messages: Combine system and user, with images in the user message
    user_message = {"role": "user", "content": user_prompt, "images": base64_images}
    
    messages = [
        {"role": "system", "content": system_prompt},
        user_message
    ]
    
    # Ollama API endpoint
    url = endpoint_url
    
    # Generate timestamp and datetime objects
    now = datetime.datetime.now()
    timestamp = now.strftime("%Y%m%d_%H%M%S")
    iso_start_time = now.isoformat() + "Z"
    
    # Output filename: append to the original filename with optional suffix
    if suffix:
        output_file: Any = pdf_path + "." + timestamp + "." + model_part + "." + suffix + ".thea"
    else:
        output_file: Any = pdf_path + "." + timestamp + "." + model_part + ".thea"
    
    # Populate metadata
    execution_data["metadata"]["file"] = {
        "pdf_path": pdf_path,
        "pdf_absolute_path": os.path.abspath(pdf_path),
        "pdf_size_bytes": os.path.getsize(pdf_path) if os.path.exists(pdf_path) else 0,
        "pdf_pages": len(base64_images),
        "output_file": output_file
    }
    
    execution_data["metadata"]["processing"] = {
        "timestamp": timestamp,
        "start_time": iso_start_time,
        "end_time": None,  # Will be set later
        "processing_time_seconds": None,  # Will be set later
        "hostname": socket.gethostname(),
        "platform": platform.system().lower()
    }
    
    execution_data["metadata"]["model"] = {
        "name": model_name,
        "endpoint": url,
        "stream": True,
        "format": "json"
    }
    
    # Populate settings
    execution_data["settings"] = {
        "mode": mode,
        "suffix": suffix,
        "prompt_file": prompt_file,
        "save_image": save_image,
        "dpi": dpi,
        "max_retries": max_retries,
        "initial_temperature": initial_temperature,
        "temperature_progression": []  # Will be populated during retries
    }
    
    # Populate prompt information
    execution_data["prompt"] = {
        "system": system_prompt,
        "custom_prompt_file": prompt_file,
        "custom_prompt_content": custom_prompt_content
    }
    
    # Initialize execution images data
    images_processed = []
    for i in range(len(base64_images)):
        images_processed.append({
            "page": i + 1,
            "resolution": None,  # Will be set if we have PIL images
            "dpi": dpi,
            "saved_as": None
        })
    
    # Save images if requested
    if save_image and pil_images:
        for i, image in enumerate(pil_images, 1):
            if suffix:
                image_file = f"{pdf_path}.{timestamp}.{model_part}.{suffix}.{dpi}p{i}.png"
            else:
                image_file = f"{pdf_path}.{timestamp}.{model_part}.{dpi}p{i}.png"
            try:
                image.save(image_file, format='PNG')
                print(f"Saved image: {image_file}")
                # Update images_processed
                images_processed[i-1]["saved_as"] = image_file
                images_processed[i-1]["resolution"] = f"{image.width}x{image.height}"
            except Exception as e:
                print(f"Error saving image {image_file}: {e}")
                execution_data["errors"].append(f"Failed to save image {i}: {str(e)}")
    elif pil_images:
        # Still populate resolution even if not saving
        for i, image in enumerate(pil_images):
            images_processed[i]["resolution"] = f"{image.width}x{image.height}"
    
    # Statistics tracking
    start_time = time.time()
    total_input_tokens = 0
    total_output_tokens = 0
    
    # Estimate input tokens (rough approximation: 1 token ≈ 4 chars)
    # Count prompt tokens
    input_text = system_prompt + user_prompt
    total_input_tokens = len(input_text) // 4
    # Add image tokens (estimate: 1 image ≈ 1000 tokens per page)
    total_input_tokens += len(base64_images) * 1000
    
    # Variables to track across retries
    final_retry_count = 0
    final_temperature = initial_temperature
    stuck_pattern_detected = False
    pattern_type = None
    
    # Retry loop for handling stuck model responses
    for retry_count in range(max_retries):
        # Calculate progressive temperature: starts at initial_temperature, increases to approach 1.0
        # Formula: temperature = initial_temp + (retry_count * (1.0 - initial_temp) / max_retries)
        current_temperature = initial_temperature + (retry_count * (1.0 - initial_temperature) / max_retries)
        execution_data["settings"]["temperature_progression"].append(current_temperature)
        final_retry_count = retry_count
        final_temperature = current_temperature
        
        if retry_count > 0:
            print(f"\n=== RETRY {retry_count}/{max_retries - 1} for Model: {model_name} for File: {pdf_path} ===")
            print(f"Temperature adjusted to: {current_temperature:.2f}")
        
        # Build payload with current temperature
        payload = {
            "model": model_name,
            "messages": messages,
            "stream": True,  # Enable streaming for chunked responses
            "format": "json",  # Force JSON output
            "options": {
                "temperature": current_temperature
            }
        }
        
        # Log outgoing communication to stdout
        print(f"\n=== Outgoing Request to Model: {model_name} for File: {pdf_path} ===")
        print(f"Temperature: {current_temperature:.2f}")
        
        try:
            # Track request time
            request_start = time.time()
            
            # Send request with streaming
            response = requests.post(url, json=payload, stream=True)
            response.raise_for_status()  # Raise error if request fails
            
            # Collect full response for final JSON parsing and file saving
            full_response = ""
            
            # Pattern detection variables
            repetitive_pattern_count = 0
            last_contents = []  # Store last few content values for pattern detection
            stuck_detected = False
            local_pattern_type = None
            
            chunk_count = 0
            request_time = time.time() - request_start
            
            # Log incoming streaming chunks to stdout
            print(f"\n=== Incoming Streaming Response from Model: {model_name} for File: {pdf_path} ===")
            
            for chunk in response.iter_lines():
                if chunk:
                    decoded_chunk = chunk.decode('utf-8')
                    chunk_count += 1
                    
                    try:
                        # Ollama streams as JSON lines; extract 'message' content if present
                        chunk_data = json.loads(decoded_chunk)
                        if 'message' in chunk_data and 'content' in chunk_data['message']:
                            content = chunk_data['message']['content']
                            full_response += content
                            
                            # Stream content directly to stdout character by character
                            sys.stdout.write(content)
                            sys.stdout.flush()
                            
                            # Check for any repetitive pattern (1, 2, or 3 chunk patterns)
                            last_contents.append(content)
                            if len(last_contents) > 150:  # Keep last 150 chunks for pattern detection
                                last_contents.pop(0)
                            
                            # Check if we're stuck in a repeating pattern
                            if len(last_contents) >= 50:
                                stuck_detected = False
                                pattern_description = ""
                                
                                # Check for 1-chunk pattern (same content repeated)
                                if len(set(last_contents[-50:])) == 1:
                                    stuck_detected = True
                                    local_pattern_type = "single_chunk"
                                    pattern_description = f"single chunk '{last_contents[-1]}' repeated"
                                
                                # Check for 2-chunk pattern (alternating between two values)
                                elif len(last_contents) >= 50:
                                    # Get potential 2-chunk pattern
                                    potential_pattern = last_contents[-2:]
                                    is_pattern = True
                                    for i in range(50):
                                        if last_contents[-(50-i)] != potential_pattern[i % 2]:
                                            is_pattern = False
                                            break
                                    if is_pattern:
                                        stuck_detected = True
                                        local_pattern_type = "two_chunk_alternating"
                                        pattern_description = f"alternating pattern '{potential_pattern[0]}', '{potential_pattern[1]}'"
                                
                                # Check for 3-chunk pattern
                                if not stuck_detected and len(last_contents) >= 51:
                                    # Get potential 3-chunk pattern
                                    potential_pattern = last_contents[-3:]
                                    is_pattern = True
                                    for i in range(51):
                                        if last_contents[-(51-i)] != potential_pattern[i % 3]:
                                            is_pattern = False
                                            break
                                    if is_pattern:
                                        stuck_detected = True
                                        local_pattern_type = "three_chunk_cycle"
                                        pattern_description = f"3-chunk pattern '{potential_pattern[0]}', '{potential_pattern[1]}', '{potential_pattern[2]}'"
                                
                                if stuck_detected:
                                    print(f"\n!!! STUCK PATTERN DETECTED after {len(last_contents)} chunks !!!")
                                    print(f"Model appears to be stuck generating repetitive pattern: {pattern_description}")
                                    response.close()  # Close the connection
                                    break
                    except json.JSONDecodeError:
                        print("Error decoding chunk:", decoded_chunk)
            
            # If stuck was detected, retry
            if stuck_detected:
                stuck_pattern_detected = True
                pattern_type = local_pattern_type
                print(f"Terminating connection and retrying... (Attempt {retry_count + 1}/{max_retries})")
                continue  # Go to next retry iteration
            
            # After streaming, parse the collected response as JSON
            print(f"\n=== Final Collected Response for File: {pdf_path} with Model: {model_name} ===")
            try:
                json_response = json.loads(full_response.strip())
                
                # Calculate and collect statistics
                end_time = time.time()
                processing_time = end_time - start_time
                iso_end_time = datetime.datetime.now().isoformat() + "Z"
                total_output_tokens = len(full_response) // 4  # Rough estimate
                
                # Update execution data
                execution_data["metadata"]["processing"]["end_time"] = iso_end_time
                execution_data["metadata"]["processing"]["processing_time_seconds"] = processing_time
                
                execution_data["execution"] = {
                    "retry_count": final_retry_count,
                    "final_temperature": final_temperature,
                    "stuck_pattern_detected": stuck_pattern_detected,
                    "pattern_type": pattern_type,
                    "chunks_received": chunk_count,
                    "request_time_seconds": request_time,
                    "images_processed": images_processed
                }
                
                execution_data["response"] = {
                    "text": full_response,
                    "thinking": None,  # Future enhancement
                    "json": json_response
                }
                
                execution_data["statistics"] = {
                    "tokens": {
                        "input_estimated": total_input_tokens,
                        "output_estimated": total_output_tokens,
                        "total_estimated": total_input_tokens + total_output_tokens,
                        "tokens_per_second": total_output_tokens / processing_time if processing_time > 0 else 0
                    },
                    "characters": {
                        "response_total": len(full_response),
                        "extracted_text": len(json_response.get("extracted_text", "")),
                        "json_formatted": len(json.dumps(json_response, indent=2))
                    }
                }
                
                # Save to file in new JSON format
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(execution_data, f, indent=2, ensure_ascii=False)
                
                print(f"Successfully saved response to: {output_file}")
                
                # Display statistics
                print("\n=== Processing Statistics ===")
                print(f"Processing time: {processing_time:.2f} seconds")
                print(f"Input tokens (estimated): ~{total_input_tokens:,}")
                print(f"  - Text prompt: ~{len(input_text) // 4:,} tokens")
                print(f"  - Images: ~{len(base64_images) * 1000:,} tokens ({len(base64_images)} pages)")
                print(f"Output tokens (estimated): ~{total_output_tokens:,}")
                print(f"Total tokens: ~{total_input_tokens + total_output_tokens:,}")
                print(f"Output characters: {len(full_response):,}")
                print(f"Chunks received: {chunk_count}")
                if processing_time > 0:
                    print(f"Tokens/second: ~{total_output_tokens / processing_time:.1f}")
                print("=" * 30)
                
                return  # Success, exit the function
                
            except json.JSONDecodeError as e:
                print("Failed to parse JSON from response:", full_response)
                execution_data["errors"].append(f"JSON parse error: {str(e)}")
                
                # Calculate and collect statistics even on failure
                end_time = time.time()
                processing_time = end_time - start_time
                iso_end_time = datetime.datetime.now().isoformat() + "Z"
                total_output_tokens = len(full_response) // 4
                
                # Update execution data with error state
                execution_data["metadata"]["processing"]["end_time"] = iso_end_time
                execution_data["metadata"]["processing"]["processing_time_seconds"] = processing_time
                
                execution_data["execution"] = {
                    "retry_count": final_retry_count,
                    "final_temperature": final_temperature,
                    "stuck_pattern_detected": stuck_pattern_detected,
                    "pattern_type": pattern_type,
                    "chunks_received": chunk_count,
                    "request_time_seconds": request_time,
                    "images_processed": images_processed
                }
                
                execution_data["response"] = {
                    "text": full_response,
                    "thinking": None,
                    "json": None  # Failed to parse
                }
                
                execution_data["statistics"] = {
                    "tokens": {
                        "input_estimated": total_input_tokens,
                        "output_estimated": total_output_tokens,
                        "total_estimated": total_input_tokens + total_output_tokens,
                        "tokens_per_second": total_output_tokens / processing_time if processing_time > 0 else 0
                    },
                    "characters": {
                        "response_total": len(full_response),
                        "extracted_text": 0,
                        "json_formatted": 0
                    }
                }
                
                # Still save the response in new JSON format
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(execution_data, f, indent=2, ensure_ascii=False)
                
                print(f"Successfully saved response to: {output_file} (with JSON parse error)")
                
                # Display statistics even on JSON parse failure
                print("\n=== Processing Statistics (JSON parse failed) ===")
                print(f"Processing time: {processing_time:.2f} seconds")
                print(f"Input tokens (estimated): ~{total_input_tokens:,}")
                print(f"Output tokens (estimated): ~{total_output_tokens:,}")
                print(f"Output characters: {len(full_response):,}")
                print(f"Chunks received: {chunk_count}")
                print("=" * 30)
                
                return  # Exit even with JSON parse failure
                
        except Exception as e:
            print(f"Error during request (attempt {retry_count + 1}/{max_retries}): {e}")
            execution_data["errors"].append(f"Request error (attempt {retry_count + 1}): {str(e)}")
            if retry_count == max_retries - 1:
                print(f"Failed after {max_retries} attempts. Giving up on {pdf_path} with model {model_name}")
                # Save error state to file
                end_time = time.time()
                processing_time = end_time - start_time
                iso_end_time = datetime.datetime.now().isoformat() + "Z"
                
                execution_data["metadata"]["processing"]["end_time"] = iso_end_time
                execution_data["metadata"]["processing"]["processing_time_seconds"] = processing_time
                
                execution_data["execution"] = {
                    "retry_count": final_retry_count,
                    "final_temperature": final_temperature,
                    "stuck_pattern_detected": stuck_pattern_detected,
                    "pattern_type": pattern_type,
                    "chunks_received": 0,
                    "request_time_seconds": 0,
                    "images_processed": images_processed
                }
                
                execution_data["response"] = {
                    "text": None,
                    "thinking": None,
                    "json": None
                }
                
                execution_data["statistics"] = {
                    "tokens": {
                        "input_estimated": total_input_tokens,
                        "output_estimated": 0,
                        "total_estimated": total_input_tokens,
                        "tokens_per_second": 0
                    },
                    "characters": {
                        "response_total": 0,
                        "extracted_text": 0,
                        "json_formatted": 0
                    }
                }
                
                # Save error state
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(execution_data, f, indent=2, ensure_ascii=False)
                
                print(f"Saved error state to: {output_file}")
                return

if __name__ == "__main__":
    # Parse command-line arguments
    mode = 'skip'  # Default mode
    suffix = ''  # Default no suffix
    prompt_file = None  # Default no prompt file
    save_image = False  # Default don't save images
    dpi = 300  # Default DPI for PDF to image conversion
    max_retries = 3  # Default max retries for stuck model responses
    model_override = None  # Default: use built-in model list
    temperature = 0.1  # Default temperature (very low for precision)
    args = sys.argv[1:]
    
    # Check for help flag first
    if len(args) >= 1 and args[0] in ['--help', '-h', 'help']:
        args = []
    
    # Parse optional arguments
    while len(args) >= 1 and args[0].startswith('-'):
        if args[0] == '--mode' and len(args) >= 2:
            if args[1] in ['skip', 'overwrite']:
                mode = args[1]
                args = args[2:]  # Remove mode arguments from args
            else:
                print(f"Error: Invalid mode '{args[1]}'. Use 'skip' or 'overwrite'.")
                sys.exit(1)
        elif args[0] == '--suffix' and len(args) >= 2:
            suffix = args[1]
            args = args[2:]  # Remove suffix arguments from args
        elif args[0] == '--prompt' and len(args) >= 2:
            prompt_file = args[1]
            args = args[2:]  # Remove prompt arguments from args
        elif args[0] == '--save-image':
            save_image = True
            args = args[1:]  # Remove save-image flag from args
        elif args[0] == '--dpi' and len(args) >= 2:
            try:
                dpi = int(args[1])
                if dpi < 50 or dpi > 600:
                    print(f"Error: DPI must be between 50 and 600. Got: {dpi}")
                    sys.exit(1)
                args = args[2:]  # Remove dpi arguments from args
            except ValueError:
                print(f"Error: Invalid DPI value '{args[1]}'. Must be an integer.")
                sys.exit(1)
        elif args[0] == '--max-retries' and len(args) >= 2:
            try:
                max_retries = int(args[1])
                if max_retries < 1 or max_retries > 10:
                    print(f"Error: Max retries must be between 1 and 10. Got: {max_retries}")
                    sys.exit(1)
                args = args[2:]  # Remove max-retries arguments from args
            except ValueError:
                print(f"Error: Invalid max-retries value '{args[1]}'. Must be an integer.")
                sys.exit(1)
        elif args[0] in ['--model', '-m'] and len(args) >= 2:
            model_override = args[1]
            args = args[2:]  # Remove model arguments from args
        elif args[0] in ['--temperature', '-t'] and len(args) >= 2:
            try:
                temperature = float(args[1])
                if temperature < 0.0 or temperature > 2.0:
                    print(f"Error: Temperature must be between 0.0 and 2.0. Got: {temperature}")
                    sys.exit(1)
                args = args[2:]  # Remove temperature arguments from args
            except ValueError:
                print(f"Error: Invalid temperature value '{args[1]}'. Must be a float.")
                sys.exit(1)
        else:
            print(f"Error: Unknown option '{args[0]}'")
            sys.exit(1)
    
    if len(args) < 1:
        print("THEA - PDF Text Extraction and Analysis System")
        print("=" * 50)
        print("\nUsage:")
        print("  python thea.py [OPTIONS] <file_pattern> [file_pattern2] ...")
        print("  python thea.py --help")
        print("\nOptions:")
        print("  --help, -h        Show this help message and exit")
        print("  --mode <mode>     Processing mode:")
        print("                    - skip:      Skip PDFs that already have matching .thea files (default)")
        print("                    - overwrite: Always process PDFs even if .thea files exist")
        print("  --prompt <file>   Load system prompt from a .prompt file")
        print("                    The filename (without .prompt) becomes the default suffix")
        print("  --suffix <text>   Add custom suffix to output filename before .thea extension")
        print("                    Overrides the automatic suffix from prompt filename")
        print("  --save-image      Save extracted images as PNG files with same naming as .thea files")
        print("  --dpi <number>    Set DPI resolution for PDF to image conversion (50-600, default: 300)")
        print("  --max-retries <n> Max retry attempts when model gets stuck (1-10, default: 3)")
        print("  -m, --model <name> Override default model (e.g., gemma:14b, llama2:13b)")
        print("  -t, --temperature <value> Set initial temperature (0.0-2.0, default: 0.1)")
        print("                    Temperature increases progressively with retries to reach ~1.0")
        print("\nOutput File Format:")
        print("  Default:          <pdf>.<timestamp>.<model>.thea")
        print("  With suffix:      <pdf>.<timestamp>.<model>.<suffix>.thea")
        print("  With prompt:      <pdf>.<timestamp>.<model>.<promptname>.thea")
        print("  Saved images:     <pdf>.<timestamp>.<model>[.<suffix>].<dpi>p<n>.png")
        print("\nExamples:")
        print("  # Basic usage - process all PDFs, skip existing")
        print("  python thea.py '*.pdf'")
        print("\n  # Force reprocessing of all PDFs")
        print("  python thea.py --mode overwrite '*.pdf'")
        print("\n  # Process with custom suffix (for versioning)")
        print("  python thea.py --suffix v2 'documents/*.pdf'")
        print("\n  # Use custom prompt file (auto-suffix: extraction)")
        print("  python thea.py --prompt extraction.prompt '*.pdf'")
        print("\n  # Custom prompt with explicit suffix override")
        print("  python thea.py --prompt detailed.prompt --suffix final 'reports/*.pdf'")
        print("\n  # Process multiple patterns")
        print("  python thea.py 'invoices/*.pdf' 'receipts/*.PDF' 'documents/scan_*.pdf'")
        print("\n  # Skip only files with specific suffix")
        print("  python thea.py --mode skip --suffix images '*.pdf'")
        print("\n  # Save images with custom DPI")
        print("  python thea.py --save-image --dpi 150 '*.pdf'")
        print("\n  # High quality image extraction")
        print("  python thea.py --save-image --dpi 600 --suffix hq 'important.pdf'")
        print("\n  # Increase retry attempts for unstable model")
        print("  python thea.py --max-retries 5 '*.pdf'")
        print("\n  # Use a different model")
        print("  python thea.py -m gemma:14b '*.pdf'")
        print("\n  # Set higher initial temperature for more creative output")
        print("  python thea.py -t 0.7 '*.pdf'")
        print("\n  # Combine options: custom model with higher temperature")
        print("  python thea.py -m llama2:13b -t 0.5 --max-retries 10 '*.pdf'")
        print("\nNotes:")
        print("  - Requires Ollama running on localhost:11434")
        print("  - Requires poppler-utils for PDF processing")
        print("  - Default model: gemma3:27b (override with -m/--model)")
        print("  - Skip mode is suffix-specific: only skips files with matching suffix")
        print("  - Prompt files should contain the system prompt in plain text")
        print("  - Default DPI: 300 (higher = better quality but larger files)")
        print("  - Images saved as PNG when --save-image is used")
        print("  - Automatically retries if model gets stuck in repetitive patterns")
        print("\nEnvironment:")
        print("  - Python 3.x with virtual environment")
        print("  - Dependencies: pdf2image, Pillow, requests")
        print("  - Run 'npm run setup' for initial setup")
        sys.exit(1)
    
    # Load prompt file if specified
    custom_prompt = None  # Initialize variable
    if prompt_file:
        custom_prompt = load_prompt_file(prompt_file)
        if custom_prompt:
            system_prompt = custom_prompt
            # Extract prompt name for suffix if no explicit suffix given
            if not suffix:
                # Remove .prompt extension and use as suffix
                prompt_name = os.path.splitext(os.path.basename(prompt_file))[0]
                suffix = prompt_name
                print(f"Using prompt file: {prompt_file} (suffix: {suffix})")
            else:
                print(f"Using prompt file: {prompt_file} (suffix override: {suffix})")
        else:
            # Fall back to default prompt
            system_prompt = (
                "You are a vision-based text extractor and analyzer. Extract all text from the provided PDF image(s) accurately. "
                "Then, count the total number of characters in the extracted text directly (do not count step-by-step or iteratively; "
                "just compute and output the exact count). Provide a one-word description of the document type. "
                "Also, briefly summarize what the document is about content-wise in 1-2 sentences. "
                "Respond ONLY in this exact JSON format, nothing else: "
                "{\"extracted_text\": \"the full extracted text here\", \"character_count\": 123, "
                "\"one_word_description\": \"example\", \"content_summary\": \"Brief content description here.\"}"
            )
    else:
        # Default system prompt
        system_prompt = (
            "You are a vision-based text extractor and analyzer. Extract all text from the provided PDF image(s) accurately. "
            "Then, count the total number of characters in the extracted text directly (do not count step-by-step or iteratively; "
            "just compute and output the exact count). Provide a one-word description of the document type. "
            "Also, briefly summarize what the document is about content-wise in 1-2 sentences. "
            "Respond ONLY in this exact JSON format, nothing else: "
            "{\"extracted_text\": \"the full extracted text here\", \"character_count\": 123, "
            "\"one_word_description\": \"example\", \"content_summary\": \"Brief content description here.\"}"
        )
    
    print(f"Mode: {mode}")
    if suffix:
        print(f"Suffix: {suffix}")
    if save_image:
        print(f"Save images: enabled")
    print(f"DPI: {dpi}")
    print(f"Max retries: {max_retries}")
    print(f"Initial temperature: {temperature}")
    if model_override:
        print(f"Model: {model_override}")
    else:
        print(f"Model: gemma3:27b (default)")
    
    # Collect all PDF files from all provided patterns
    pdf_paths = []
    for pattern in args:
        matching_files = glob.glob(pattern)
        if matching_files:
            pdf_paths.extend(matching_files)
            print(f"Found {len(matching_files)} files matching pattern: {pattern}")
        else:
            print(f"No files found matching pattern: {pattern}")
    
    # Remove duplicates while preserving order
    pdf_paths = list(dict.fromkeys(pdf_paths))
    
    if not pdf_paths:
        print("No PDF files found in any of the provided patterns")
        sys.exit(1)
    
    print(f"\nTotal unique PDF files to process: {len(pdf_paths)}")
    
    # Note: system_prompt is now defined earlier based on --prompt parameter
    
    # Use model override if provided, otherwise use default
    if model_override:
        models: list[str] = [model_override]
    else:
        models: list[str] = ["gemma3:27b"]  # Default model
    
    for pdf_path in pdf_paths:
        print(f"\nProcessing file: {pdf_path}")
        base64_images, pil_images = pdf_to_base64_images(pdf_path, dpi=dpi)
        
        if not base64_images:
            print(f"Skipping {pdf_path} - no images available")
            continue
        
        for model in models:
            # User prompt per file
            user_prompt: str = f"Extract the text from this PDF document '{pdf_path}', count its characters, describe it with one word, and summarize its content as instructed."
            
            # Pass additional parameters for the new JSON format
            process_with_model(
                model, base64_images, pdf_path, system_prompt, user_prompt, 
                mode, suffix, save_image, pil_images, max_retries, dpi, temperature,
                prompt_file=prompt_file,
                custom_prompt_content=custom_prompt if prompt_file else None,
                endpoint_url="https://b1s.hey.bahn.business/api/chat"
            )