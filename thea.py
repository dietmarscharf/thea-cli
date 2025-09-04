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
import re

# Import pipeline system
from pipelines.manager import PipelineManager
from pipelines.pdf_extract_png import PdfExtractPngPipeline

try:
    from PIL import Image
except ImportError:
    print("PIL not available")
    Image = None

def load_prompt_file(prompt_path):
    """Load prompt configuration from a .prompt file (JSON or plain text)."""
    try:
        with open(prompt_path, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            
        # Check if it's JSON format
        if content.startswith('{'):
            try:
                prompt_config = json.loads(content)
                return prompt_config
            except json.JSONDecodeError as e:
                print(f"Error parsing JSON in prompt file '{prompt_path}': {e}")
                return None
        else:
            # Legacy plain text format - return as system prompt only
            return {"legacy": True, "system_prompt": {"suffix": content}}
            
    except FileNotFoundError:
        print(f"Warning: Prompt file '{prompt_path}' not found. Using default prompt.")
        return None
    except Exception as e:
        print(f"Error reading prompt file '{prompt_path}': {e}")
        return None

def build_system_prompt(prompt_config):
    """Build the complete system prompt from configuration."""
    # Hardcoded prefix - encourage thinking
    prefix = "You are a vision-based text extractor and analyzer. Always use <thinking></thinking> tags to show your analysis process. "
    
    # Get suffix from config
    suffix = prompt_config.get("system_prompt", {}).get("suffix", "")
    
    # Get output format instructions
    output_format = prompt_config.get("system_prompt", {}).get("output_format", {})
    format_instructions = ""
    
    if output_format:
        instructions = output_format.get("instructions", "")
        if output_format.get("type") == "json" and output_format.get("schema"):
            # Build JSON format example from schema
            schema_example = {}
            for key, value in output_format["schema"].items():
                if isinstance(value, dict):
                    schema_example[key] = f"<{value.get('type', 'string')}>"
                else:
                    schema_example[key] = f"<{value}>"
            format_instructions = f" {instructions}: {json.dumps(schema_example)}"
        elif instructions:
            format_instructions = f" {instructions}"
    
    return prefix + suffix + format_instructions

def build_user_prompt(prompt_config, pdf_path):
    """Build user prompt from template with variable substitution."""
    template = prompt_config.get("user_prompt", {}).get("template", "")
    if not template:
        # Fallback to default
        return f"Extract the text from this PDF document '{pdf_path}', count its characters, describe it with one word in both German and English, and summarize its content in both German and English as instructed."
    
    # Simple variable substitution
    result = template.replace("{{pdf_path}}", pdf_path)
    return result

def clean_thea_files(directory=".", force=False, dry_run=False, pipeline=None):
    """Clean THEA-generated files from directory.
    
    Args:
        directory: Directory to clean
        force: Skip confirmation prompt
        dry_run: Show what would be deleted without deleting
        pipeline: Optional - clean only files from specific pipeline ('txt', 'png', 'docling', or None for all)
    """
    # Patterns for THEA files (with timestamp pattern YYYYMMDD_HHMMSS)
    # Format: <original>.<timestamp>.<model>.<suffix>.thea_extract or .thea (legacy)
    # Model names can contain dots (e.g., gemma3.27b)
    if pipeline:
        # Filter by specific pipeline
        if pipeline == 'txt':
            thea_patterns = [r'^.*\.\d{8}_\d{6}\..*\.pdf-extract-txt\.thea_extract$']
        elif pipeline == 'png':
            thea_patterns = [r'^.*\.\d{8}_\d{6}\..*\.pdf-extract-png\.thea_extract$']
        elif pipeline == 'docling':
            thea_patterns = [r'^.*\.\d{8}_\d{6}\..*\.pdf-extract-docling\.thea_extract$']
        else:
            print(f"Unknown pipeline type: {pipeline}. Use 'txt', 'png', 'docling', or None for all.")
            return 0, 0, 0
    else:
        # All THEA files
        thea_patterns = [
            r'^.*\.\d{8}_\d{6}\..*\.thea_extract$',  # New THEA extract files
            r'^.*\.\d{8}_\d{6}\..*\.thea$'  # Legacy THEA files
        ]
    
    # Patterns for THEA-generated PNG files (must have DPI+page pattern)
    # Format: <original>.<timestamp>.<model>.<suffix>.<dpi>p<page>.png or without suffix
    if pipeline == 'png' or pipeline is None:
        png_patterns = [
            r'^.*\.\d{8}_\d{6}\..*\.\d+p\d+\.png$'  # Any PNG with timestamp and DPI pattern
        ]
    else:
        png_patterns = []  # Don't clean PNG files if specific other pipeline requested
    
    # Patterns for pipeline-specific extraction files
    # pdf-extract-txt: <original>.<timestamp>.<model>.pdf-extract-txt.<extractor>.(txt|json)
    # pdf-extract-docling: <original>.<timestamp>.<model>.pdf-extract-docling.docling.(txt|json|md)
    # pdf-extract-png: PNG files are handled above with png_patterns
    if pipeline == 'txt':
        extraction_patterns = [
            r'^.*\.\d{8}_\d{6}\..*\.pdf-extract-txt\.(pypdf2|pdfplumber|pymupdf)\.(txt|json)$'
        ]
    elif pipeline == 'docling':
        extraction_patterns = [
            r'^.*\.\d{8}_\d{6}\..*\.pdf-extract-docling\.docling\.(txt|json|md)$'
        ]
    elif pipeline == 'png':
        extraction_patterns = []  # PNG files are handled by png_patterns
    elif pipeline is None:
        extraction_patterns = [
            # pdf-extract-txt pipeline files
            r'^.*\.\d{8}_\d{6}\..*\.pdf-extract-txt\.(pypdf2|pdfplumber|pymupdf)\.(txt|json)$',
            # pdf-extract-docling pipeline files
            r'^.*\.\d{8}_\d{6}\..*\.pdf-extract-docling\.docling\.(txt|json|md)$',
            # Legacy extraction files (older format)
            r'^.*\.\d{8}_\d{6}\..*\.(pypdf2|pdfplumber|pymupdf)\.(txt|json)$'
        ]
    else:
        extraction_patterns = []
    
    thea_files = []
    png_files = []
    extraction_files = []
    
    # Find matching files
    try:
        for file in os.listdir(directory):
            file_path = os.path.join(directory, file)
            if os.path.isfile(file_path):
                # Check THEA files
                for pattern in thea_patterns:
                    if re.match(pattern, file):
                        thea_files.append(file_path)
                        break
                # Check PNG files
                for pattern in png_patterns:
                    if re.match(pattern, file):
                        png_files.append(file_path)
                        break
                # Check extraction files
                for pattern in extraction_patterns:
                    if re.match(pattern, file):
                        extraction_files.append(file_path)
                        break
    except FileNotFoundError:
        print(f"Error: Directory '{directory}' not found.")
        return 0, 0
    except PermissionError:
        print(f"Error: Permission denied accessing directory '{directory}'.")
        return 0, 0
    
    # Sort files for consistent display
    thea_files.sort()
    png_files.sort()
    extraction_files.sort()
    
    total_thea = len(thea_files)
    total_png = len(png_files)
    total_extraction = len(extraction_files)
    
    if total_thea == 0 and total_png == 0 and total_extraction == 0:
        print(f"No THEA-generated files found in '{directory}'")
        return 0, 0, 0
    
    # Display files to be deleted
    pipeline_msg = f" (pipeline: {pipeline})" if pipeline else " (all pipelines)"
    print(f"\n=== THEA Files to Clean in '{directory}'{pipeline_msg} ===")
    print(f"Found {total_thea} .thea_extract file(s), {total_png} .png file(s), and {total_extraction} extraction file(s)")
    
    if dry_run:
        print("\n--- DRY RUN MODE - No files will be deleted ---")
    
    if thea_files:
        print(f"\n.thea files ({total_thea}):")
        for f in thea_files[:10]:  # Show first 10
            print(f"  - {os.path.basename(f)}")
        if total_thea > 10:
            print(f"  ... and {total_thea - 10} more")
    
    if png_files:
        print(f"\n.png files ({total_png}):")
        for f in png_files[:10]:  # Show first 10
            print(f"  - {os.path.basename(f)}")
        if total_png > 10:
            print(f"  ... and {total_png - 10} more")
    
    if extraction_files:
        print(f"\nExtraction files ({total_extraction}):")
        for f in extraction_files[:10]:  # Show first 10
            print(f"  - {os.path.basename(f)}")
        if total_extraction > 10:
            print(f"  ... and {total_extraction - 10} more")
    
    if dry_run:
        print(f"\nDry run complete. Would delete {total_thea} .thea, {total_png} .png, and {total_extraction} extraction files.")
        return 0, 0, 0
    
    # Confirmation prompt
    if not force:
        print(f"\nAbout to delete {total_thea} .thea file(s), {total_png} .png file(s), and {total_extraction} extraction file(s)")
        response = input("Are you sure? (y/N): ").strip().lower()
        if response != 'y':
            print("Cancelled.")
            return 0, 0, 0
    
    # Delete files
    deleted_thea = 0
    deleted_png = 0
    deleted_extraction = 0
    
    print("\nDeleting files...")
    
    for f in thea_files:
        try:
            os.remove(f)
            deleted_thea += 1
            if deleted_thea <= 5 or deleted_thea % 10 == 0:  # Progress indicator
                print(f"  Deleted: {os.path.basename(f)}")
        except Exception as e:
            print(f"  Error deleting {f}: {e}")
    
    for f in png_files:
        try:
            os.remove(f)
            deleted_png += 1
            if deleted_png <= 5 or deleted_png % 10 == 0:  # Progress indicator
                print(f"  Deleted: {os.path.basename(f)}")
        except Exception as e:
            print(f"  Error deleting {f}: {e}")
    
    for f in extraction_files:
        try:
            os.remove(f)
            deleted_extraction += 1
            if deleted_extraction <= 5 or deleted_extraction % 10 == 0:  # Progress indicator
                print(f"  Deleted: {os.path.basename(f)}")
        except Exception as e:
            print(f"  Error deleting {f}: {e}")
    
    print(f"\n=== Clean Complete ===")
    print(f"Deleted {deleted_thea} .thea file(s), {deleted_png} .png file(s), and {deleted_extraction} extraction file(s)")
    
    return deleted_thea, deleted_png, deleted_extraction

def clean_json_response(response_text):
    """Extract JSON and thinking from response, handling markdown blocks and thinking tags."""
    if not response_text:
        return "", None
    
    cleaned_json = response_text.strip()
    thinking_text = None
    
    # Check for <thinking> or <think> tags - handle multiple occurrences and nested content
    thinking_start_tag = None
    thinking_end_tag = None
    
    if '<thinking>' in cleaned_json and '</thinking>' in cleaned_json:
        thinking_start_tag = '<thinking>'
        thinking_end_tag = '</thinking>'
    elif '<think>' in cleaned_json and '</think>' in cleaned_json:
        thinking_start_tag = '<think>'
        thinking_end_tag = '</think>'
    
    if thinking_start_tag and thinking_end_tag:
        # Find all thinking blocks (there might be multiple)
        thinking_blocks = []
        search_pos = 0
        
        while True:
            start = cleaned_json.find(thinking_start_tag, search_pos)
            if start == -1:
                break
            
            # Find the matching end tag (handle nested tags if any)
            end = cleaned_json.find(thinking_end_tag, start)
            if end == -1:
                break
            
            end += len(thinking_end_tag)
            
            # Extract thinking content without tags
            thinking_content = cleaned_json[start + len(thinking_start_tag):end - len(thinking_end_tag)].strip()
            if thinking_content:
                thinking_blocks.append(thinking_content)
            
            # Remove this thinking section from response
            cleaned_json = cleaned_json[:start] + ' ' + cleaned_json[end:]
            
            # Don't update search_pos since we modified the string
        
        # Combine all thinking blocks
        if thinking_blocks:
            thinking_text = "\n\n---\n\n".join(thinking_blocks)
        
        cleaned_json = cleaned_json.strip()
    
    # Check for markdown code blocks
    if '```json' in cleaned_json:
        # Find the LAST occurrence of ```json (in case there are multiple)
        last_json_start = cleaned_json.rfind('```json')
        
        # Everything before last ```json could be additional thinking/explanation
        if last_json_start > 0:
            pre_json = cleaned_json[:last_json_start].strip()
            if pre_json and not thinking_text:
                thinking_text = pre_json
            elif pre_json and thinking_text:
                thinking_text = thinking_text + "\n\n" + pre_json
        
        # Extract JSON content after ```json
        json_part = cleaned_json[last_json_start + 7:]  # Skip '```json'
        
        # Remove closing ``` if present
        if '```' in json_part:
            json_part = json_part[:json_part.find('```')]
        
        cleaned_json = json_part.strip()
    
    # If no JSON found yet, try to find JSON structure directly
    if not cleaned_json or (cleaned_json and not cleaned_json.startswith('{')):
        # Look for JSON object starting with {
        json_start = cleaned_json.find('{')
        if json_start != -1:
            # Find the matching closing brace
            brace_count = 0
            json_end = -1
            for i in range(json_start, len(cleaned_json)):
                if cleaned_json[i] == '{':
                    brace_count += 1
                elif cleaned_json[i] == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        json_end = i + 1
                        break
            
            if json_end != -1:
                # Extract JSON and add any prefix to thinking
                if json_start > 0:
                    pre_json = cleaned_json[:json_start].strip()
                    if pre_json:
                        if thinking_text:
                            thinking_text = thinking_text + "\n\n" + pre_json
                        else:
                            thinking_text = pre_json
                
                cleaned_json = cleaned_json[json_start:json_end]
    
    return cleaned_json, thinking_text


# Legacy function for backward compatibility - now handled by pipeline
def pdf_to_base64_images(pdf_path, dpi=300) -> tuple[list[Any], list[Any]]:
    """Legacy wrapper for image pipeline."""
    pipeline = PdfExtractPngPipeline()
    result, metadata = pipeline.process(pdf_path, dpi=dpi, save_sidecars=True)
    return result


def process_with_model(model_name, pipeline_data, pdf_path, system_prompt, user_prompt, mode='skip', suffix='', save_image=False, pil_images=None, max_attempts=3, dpi=300, initial_temperature=0.1, prompt_file=None, prompt_config=None, endpoint_url="https://b1s.hey.bahn.business/api/chat", timeout=100, max_tokens=50000, format_mode=None, pipeline_type="pdf-convert-png", pipeline_metadata=None):
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
    
    # Skip check has been moved to before pipeline processing to avoid creating duplicate sidecar files
    # The check now happens in the main loop before calling pipeline.process()
    
    # Messages: Combine system and user, with pipeline data
    if pipeline_type == "pdf-extract-png":
        # Image pipeline - use base64 images
        base64_images, _ = pipeline_data if isinstance(pipeline_data, tuple) else (pipeline_data, [])
        user_message = {"role": "user", "content": user_prompt, "images": base64_images}
    else:
        # Text pipeline - include extraction data in content
        extraction_json = json.dumps(pipeline_data, indent=2, ensure_ascii=False)
        combined_content = f"{user_prompt}\n\n[PDF TEXT EXTRACTIONS]\n{extraction_json}"
        user_message = {"role": "user", "content": combined_content}
    
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
        output_file: Any = pdf_path + "." + timestamp + "." + model_part + "." + suffix + ".thea_extract"
    else:
        output_file: Any = pdf_path + "." + timestamp + "." + model_part + ".thea_extract"
    
    # Populate metadata
    # Determine page count based on pipeline
    if pipeline_type == "pdf-extract-png":
        base64_images, _ = pipeline_data if isinstance(pipeline_data, tuple) else (pipeline_data, [])
        page_count = len(base64_images)
    else:
        # For text pipeline, get page count from metadata if available
        page_count = pipeline_metadata.get("pages_processed", 0) if pipeline_metadata else 0
    
    execution_data["metadata"]["file"] = {
        "pdf_path": pdf_path,
        "pdf_absolute_path": os.path.abspath(pdf_path),
        "pdf_size_bytes": os.path.getsize(pdf_path) if os.path.exists(pdf_path) else 0,
        "pdf_pages": page_count,
        "output_file": output_file
    }
    
    execution_data["metadata"]["processing"] = {
        "timestamp": timestamp,
        "start_time": iso_start_time,
        "end_time": None,  # Will be set later
        "processing_time_seconds": None,  # Will be set later
        "hostname": socket.gethostname(),
        "platform": platform.system().lower(),
        "pipeline": pipeline_type,
        "pipeline_metadata": pipeline_metadata
    }
    
    execution_data["metadata"]["model"] = {
        "name": model_name,
        "endpoint": url,
        "stream": True,
        "format": "json" if format_mode == "json" else None
    }
    
    # Populate settings
    execution_data["settings"] = {
        "mode": mode,
        "suffix": suffix,
        "prompt_file": prompt_file,
        "save_sidecars": save_sidecars,
        "dpi": dpi,
        "max_attempts": max_attempts,
        "initial_temperature": initial_temperature,
        "temperature_progression": [],  # Will be populated during retries
        "timeout": timeout,
        "max_tokens": max_tokens
    }
    
    # Populate prompt information
    execution_data["prompt"] = {
        "system": system_prompt,
        "user": user_prompt,
        "prompt_file": prompt_file,
        "prompt_config": prompt_config if prompt_config and not prompt_config.get("legacy") else None
    }
    
    # Initialize execution data based on pipeline type
    if pipeline_type == "pdf-extract-png":
        base64_images, _ = pipeline_data if isinstance(pipeline_data, tuple) else (pipeline_data, [])
        files_processed = []
        
        # Get saved file info from pipeline metadata if available
        if pipeline_metadata and "saved_files" in pipeline_metadata:
            for file_info in pipeline_metadata["saved_files"]:
                files_processed.append({
                    "page": file_info.get("page"),
                    "type": "image/png",
                    "resolution": file_info.get("resolution"),
                    "width": file_info.get("width"),
                    "height": file_info.get("height"),
                    "dpi": file_info.get("dpi"),
                    "base64_size": file_info.get("base64_size"),
                    "saved_as": None  # Will be updated if saved
                })
        else:
            # Fallback for compatibility
            for i in range(len(base64_images)):
                files_processed.append({
                    "page": i + 1,
                    "type": "image/png",
                    "resolution": None,
                    "dpi": dpi,
                    "saved_as": None
                })
    else:
        # For text pipeline, track extraction files
        files_processed = []
        base64_images = []  # For compatibility with existing code
        
        # Get saved extraction file info from pipeline metadata
        if pipeline_metadata and "saved_files" in pipeline_metadata:
            files_processed = pipeline_metadata["saved_files"]
    
    # Save images if requested
    if save_sidecars and pil_images:
        for i, image in enumerate(pil_images, 1):
            if suffix:
                image_file = f"{pdf_path}.{timestamp}.{model_part}.{suffix}.{dpi}p{i}.png"
            else:
                image_file = f"{pdf_path}.{timestamp}.{model_part}.{dpi}p{i}.png"
            try:
                image.save(image_file, format='PNG')
                print(f"Saved image: {image_file}")
                # Update files_processed
                if i-1 < len(files_processed):
                    files_processed[i-1]["saved_as"] = image_file
                    files_processed[i-1]["file_size"] = os.path.getsize(image_file)
                    if not files_processed[i-1].get("resolution"):
                        files_processed[i-1]["resolution"] = f"{image.width}x{image.height}"
            except Exception as e:
                print(f"Error saving image {image_file}: {e}")
                execution_data["errors"].append(f"Failed to save image {i}: {str(e)}")
    elif pil_images:
        # Still populate resolution even if not saving
        for i, image in enumerate(pil_images):
            if i < len(files_processed) and not files_processed[i].get("resolution"):
                files_processed[i]["resolution"] = f"{image.width}x{image.height}"
    
    # Statistics tracking
    start_time = time.time()
    total_input_tokens = 0
    total_output_tokens = 0
    
    # Estimate input tokens (rough approximation: 1 token ≈ 4 chars)
    if pipeline_type == "pdf-extract-png":
        # Count prompt tokens for image pipeline
        input_text = system_prompt + user_prompt
        total_input_tokens = len(input_text) // 4
        # Add image tokens (estimate: 1 image ≈ 1000 tokens per page)
        total_input_tokens += len(base64_images) * 1000
    else:
        # For text pipeline, include the extraction JSON in token count
        extraction_json = json.dumps(pipeline_data, ensure_ascii=False) if isinstance(pipeline_data, dict) else str(pipeline_data)
        input_text = system_prompt + user_prompt + extraction_json
        total_input_tokens = len(input_text) // 4
    
    # Variables to track across retries
    final_retry_count = 0
    final_temperature = initial_temperature
    stuck_pattern_detected = False
    pattern_type = None
    
    # Retry loop for handling stuck model responses
    for retry_count in range(max_attempts):
        # Initialize per-retry variables
        chunk_count = 0
        request_time = 0
        
        # Calculate progressive temperature: starts at initial_temperature, increases to 1.0
        # Formula: temperature = initial_temp + (retry_count * (1.0 - initial_temp) / (max_attempts - 1))
        # Handle edge case where max_attempts = 1
        if max_attempts == 1:
            current_temperature = initial_temperature
        else:
            current_temperature = initial_temperature + (retry_count * (1.0 - initial_temperature) / (max_attempts - 1))
        execution_data["settings"]["temperature_progression"].append(current_temperature)
        final_retry_count = retry_count
        final_temperature = current_temperature
        
        if retry_count > 0:
            print(f"\n=== RETRY {retry_count + 1}/{max_attempts} for Model: {model_name} for File: {pdf_path} ===")
            print(f"Temperature adjusted to: {current_temperature:.2f}")
        
        # Build payload with current temperature
        payload = {
            "model": model_name,
            "messages": messages,
            "stream": True,  # Enable streaming for chunked responses
            "options": {
                "temperature": current_temperature,
                "num_predict": max_tokens  # Maximum tokens to generate
            }
        }
        
        # Only add format if explicitly set to 'json'
        if format_mode == 'json':
            payload["format"] = "json"  # Force JSON output (disables thinking)
        
        # Log outgoing communication to stdout
        print(f"\n=== Outgoing Request to Model: {model_name} for File: {pdf_path} ===")
        print(f"Temperature: {current_temperature:.2f}")
        
        try:
            # Track request time
            request_start = time.time()
            
            # Send request with streaming (with timeout for initial connection)
            response = requests.post(url, json=payload, stream=True, timeout=(10, None))  # 10s connect timeout, no read timeout
            response.raise_for_status()  # Raise error if request fails
            
            # Collect full response for final JSON parsing and file saving
            full_response = ""
            
            # Pattern detection variables
            last_contents = []  # Store last few content values for pattern detection
            stuck_detected = False
            local_pattern_type = None
            
            # Log incoming streaming chunks to stdout
            print(f"\n=== Incoming Streaming Response from Model: {model_name} for File: {pdf_path} ===")
            
            for chunk in response.iter_lines():
                if chunk:
                    decoded_chunk = chunk.decode('utf-8')
                    chunk_count += 1
                    
                    # Check overall timeout
                    elapsed_time = time.time() - request_start
                    if elapsed_time > timeout:
                        print(f"\n!!! TIMEOUT: Response exceeded {timeout} seconds (elapsed: {elapsed_time:.1f}s) !!!")
                        response.close()
                        stuck_detected = True
                        local_pattern_type = "timeout"
                        pattern_description = f"Response timed out after {elapsed_time:.1f} seconds"
                        break
                    
                    try:
                        # Debug: Log ALL chunks to understand Ollama response structure
                        if chunk_count <= 20:  # Log first 20 chunks for debugging
                            print(f"\nDEBUG Chunk {chunk_count}: {decoded_chunk[:300]}...")
                        
                        # Ollama streams as JSON lines; extract 'message' content if present
                        chunk_data = json.loads(decoded_chunk)
                        if 'message' in chunk_data and 'content' in chunk_data['message']:
                            content = chunk_data['message']['content']
                            full_response += content
                            
                            # Additional debug for thinking detection
                            if '<thinking>' in content or '</thinking>' in content:
                                print(f"\nDEBUG: Found thinking tag in chunk {chunk_count}: {content[:100]}...")
                            
                            # Stream content directly to stdout character by character
                            sys.stdout.write(content)
                            sys.stdout.flush()
                            
                            # Check token limit (rough estimate: 1 token ≈ 4 chars)
                            approx_tokens = len(full_response) // 4
                            if approx_tokens > max_tokens:
                                print(f"\n!!! TOKEN LIMIT: Exceeded {max_tokens} tokens (approx {approx_tokens}) !!!")
                                response.close()
                                stuck_detected = True
                                local_pattern_type = "token_limit"
                                pattern_description = f"Exceeded token limit of {max_tokens}"
                                break
                            
                            # Check for any repetitive pattern (1 to 100 chunk patterns)
                            last_contents.append(content)
                            if len(last_contents) > 3000:  # Keep last 3000 chunks for pattern detection (increased for much longer patterns)
                                last_contents.pop(0)
                            
                            # Check if we're stuck in a repeating pattern
                            # We need enough chunks to detect patterns
                            if len(last_contents) >= 20:  # Minimum chunks to start checking
                                stuck_detected = False
                                pattern_description = ""
                                
                                # Check for patterns from 1 to 100 chunks in length
                                for pattern_length in range(1, 101):
                                    # Calculate minimum repetitions needed for confidence
                                    # For shorter patterns, require more repetitions
                                    # For longer patterns, require fewer repetitions but at least 10
                                    if pattern_length == 1:
                                        min_repetitions = 50  # Single chunk needs 50 repetitions
                                    elif pattern_length == 2:
                                        min_repetitions = 25  # 2-chunk pattern needs 25 cycles (50 chunks)
                                    elif pattern_length <= 10:
                                        # For 3-10 chunk patterns, require at least 10 repetitions
                                        # or enough to fill 60 chunks, whichever is less
                                        min_repetitions = max(10, 60 // pattern_length)
                                    elif pattern_length <= 30:
                                        min_repetitions = 8  # Medium patterns need 8 repetitions
                                    elif pattern_length <= 60:
                                        min_repetitions = 5  # Longer patterns need 5 repetitions
                                    else:  # pattern_length <= 100
                                        min_repetitions = 3  # Very long patterns need only 3 repetitions
                                    
                                    required_chunks = pattern_length * min_repetitions
                                    
                                    # Check if we have enough chunks to test this pattern
                                    if len(last_contents) >= required_chunks:
                                        # Get the potential pattern (last pattern_length chunks)
                                        potential_pattern = last_contents[-pattern_length:]
                                        
                                        # Check if this pattern repeats for the required number of chunks
                                        is_pattern = True
                                        for i in range(required_chunks):
                                            chunk_index = -(required_chunks - i)
                                            pattern_index = i % pattern_length
                                            if last_contents[chunk_index] != potential_pattern[pattern_index]:
                                                is_pattern = False
                                                break
                                        
                                        if is_pattern:
                                            stuck_detected = True
                                            if pattern_length == 1:
                                                local_pattern_type = "single_chunk"
                                                pattern_description = f"single chunk '{potential_pattern[0][:50]}' repeated {min_repetitions} times"
                                            elif pattern_length == 2:
                                                local_pattern_type = "two_chunk_alternating"
                                                pattern_description = f"2-chunk alternating pattern repeated {min_repetitions} times"
                                            elif pattern_length <= 10:
                                                local_pattern_type = f"{pattern_length}_chunk_pattern"
                                                pattern_description = f"{pattern_length}-chunk cyclic pattern repeated {min_repetitions} times"
                                            else:
                                                local_pattern_type = f"{pattern_length}_chunk_long_pattern"
                                                pattern_description = f"{pattern_length}-character pattern repeated {min_repetitions} times"
                                            break  # Found a pattern, stop checking
                                
                                if stuck_detected:
                                    print(f"\n!!! STUCK PATTERN DETECTED after {len(last_contents)} chunks !!!")
                                    print(f"Model appears to be stuck generating repetitive pattern: {pattern_description}")
                                    response.close()  # Close the connection
                                    break
                    except json.JSONDecodeError:
                        print("Error decoding chunk:", decoded_chunk)
            
            # Calculate actual request time after streaming completes
            request_time = time.time() - request_start
            
            # If stuck was detected, retry
            if stuck_detected:
                stuck_pattern_detected = True
                pattern_type = local_pattern_type
                
                # Check if this is the last retry
                if retry_count == max_attempts - 1:
                    # Last attempt failed - save what we have
                    print(f"\nFinal attempt failed due to: {local_pattern_type}")
                    
                    # Calculate statistics
                    end_time = time.time()
                    processing_time = end_time - start_time
                    iso_end_time = datetime.datetime.now().isoformat() + "Z"
                    total_output_tokens = len(full_response) // 4
                    
                    # Update execution data
                    execution_data["metadata"]["processing"]["end_time"] = iso_end_time
                    execution_data["metadata"]["processing"]["processing_time_seconds"] = processing_time
                    
                    execution_data["execution"] = {
                        "retry_count": retry_count,
                        "final_temperature": current_temperature,
                        "stuck_pattern_detected": True,
                        "pattern_type": pattern_type,
                        "chunks_received": chunk_count,
                        "request_time_seconds": request_time,
                        "files_processed": files_processed
                    }
                    
                    execution_data["response"] = {
                        "text": full_response if full_response else None,
                        "thinking": None,
                        "json": None
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
                    
                    execution_data["errors"].append(f"Processing terminated due to: {pattern_type}")
                    
                    # Save the partial/failed response
                    with open(output_file, 'w', encoding='utf-8') as f:
                        json.dump(execution_data, f, indent=2, ensure_ascii=False)
                    
                    print(f"Saved partial response to: {output_file}")
                    return  # Exit the function
                
                print(f"Terminating connection and retrying... (Attempt {retry_count + 1}/{max_attempts})")
                continue  # Go to next retry iteration
            
            # After streaming, parse the collected response as JSON
            print(f"\n=== Final Collected Response for File: {pdf_path} with Model: {model_name} ===")
            
            # Debug: Show raw response structure
            print(f"\n=== Response Analysis ===")
            print(f"Total response length: {len(full_response):,} characters")
            
            # Check for thinking tags
            has_thinking = '<thinking>' in full_response or '<think>' in full_response
            has_json_block = '```json' in full_response
            
            print(f"Contains thinking tags: {has_thinking}")
            if has_thinking:
                thinking_count = full_response.count('<thinking>') + full_response.count('<think>')
                print(f"  Number of thinking blocks: {thinking_count}")
            
            print(f"Contains JSON markdown block: {has_json_block}")
            
            # Show preview of response structure
            if len(full_response) > 200:
                print(f"\nResponse preview (first 200 chars):")
                print(f"  {full_response[:200]}...")
            else:
                print(f"\nFull response:")
                print(f"  {full_response}")
            
            try:
                # Clean the response and extract JSON/thinking
                cleaned_json, thinking_text = clean_json_response(full_response)
                
                print(f"\n=== Extraction Results ===")
                print(f"Extracted thinking: {'Yes' if thinking_text else 'No'}")
                if thinking_text:
                    thinking_lines = thinking_text.split('\n')
                    print(f"  Thinking length: {len(thinking_text):,} chars, {len(thinking_lines)} lines")
                    if len(thinking_lines) > 3:
                        print(f"  First 3 lines:")
                        for i, line in enumerate(thinking_lines[:3]):
                            print(f"    {i+1}. {line[:100]}{'...' if len(line) > 100 else ''}")
                    else:
                        for i, line in enumerate(thinking_lines):
                            print(f"    {i+1}. {line[:100]}{'...' if len(line) > 100 else ''}")
                
                print(f"Cleaned JSON length: {len(cleaned_json):,} characters")
                json_response = json.loads(cleaned_json)
                
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
                    "files_processed": files_processed
                }
                
                execution_data["response"] = {
                    "text": full_response,
                    "thinking": thinking_text,  # Extracted thinking content
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
                print(f"Initial JSON parse failed: {str(e)}")
                print("Attempting to clean and parse response...")
                
                # Try to clean and parse the response
                try:
                    cleaned_json, thinking_text = clean_json_response(full_response)
                    json_response = json.loads(cleaned_json)
                    print("Successfully parsed JSON after cleaning!")
                    
                    # Continue with normal flow since we successfully parsed
                    end_time = time.time()
                    processing_time = end_time - start_time
                    iso_end_time = datetime.datetime.now().isoformat() + "Z"
                    total_output_tokens = len(full_response) // 4
                    
                    execution_data["metadata"]["processing"]["end_time"] = iso_end_time
                    execution_data["metadata"]["processing"]["processing_time_seconds"] = processing_time
                    
                    execution_data["execution"] = {
                        "retry_count": final_retry_count,
                        "final_temperature": final_temperature,
                        "stuck_pattern_detected": stuck_pattern_detected,
                        "pattern_type": pattern_type,
                        "chunks_received": chunk_count,
                        "request_time_seconds": request_time,
                        "files_processed": files_processed
                    }
                    
                    execution_data["response"] = {
                        "text": full_response,
                        "thinking": thinking_text,
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
                    
                    # Save successfully cleaned response
                    with open(output_file, 'w', encoding='utf-8') as f:
                        json.dump(execution_data, f, indent=2, ensure_ascii=False)
                    
                    print(f"Successfully saved response to: {output_file}")
                    
                    # Display statistics
                    print("\n=== Processing Statistics ===")
                    print(f"Processing time: {processing_time:.2f} seconds")
                    print(f"Input tokens (estimated): ~{total_input_tokens:,}")
                    print(f"Output tokens (estimated): ~{total_output_tokens:,}")
                    print(f"Output characters: {len(full_response):,}")
                    print(f"Chunks received: {chunk_count}")
                    if processing_time > 0:
                        print(f"Tokens/second: ~{total_output_tokens / processing_time:.1f}")
                    print("=" * 30)
                    
                    return  # Success after cleaning
                    
                except Exception as cleaning_error:
                    # Cleaning also failed, continue with original error handling
                    print(f"JSON cleaning also failed: {str(cleaning_error)}")
                    print("Failed to parse JSON from response:", full_response[:500] if len(full_response) > 500 else full_response)
                    execution_data["errors"].append(f"JSON parse error: {str(e)}; Cleaning error: {str(cleaning_error)}")
                
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
                    "files_processed": files_processed
                }
                
                # Even if JSON parsing failed, try to extract thinking
                _, thinking_text = clean_json_response(full_response)
                
                execution_data["response"] = {
                    "text": full_response,
                    "thinking": thinking_text,
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
            print(f"Error during request (attempt {retry_count + 1}/{max_attempts}): {e}")
            execution_data["errors"].append(f"Request error (attempt {retry_count + 1}): {str(e)}")
            if retry_count == max_attempts - 1:
                print(f"Failed after {max_attempts} attempts. Giving up on {pdf_path} with model {model_name}")
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
                    "files_processed": files_processed
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
    save_sidecars = False  # Default don't save sidecar files (images or text extractions)
    sidecars_only = False  # Default: run model processing after extraction
    dpi = 300  # Default DPI for PDF to image conversion
    max_attempts = 3  # Default max attempts for stuck model responses
    model_override = None  # Default: use built-in model list
    temperature = 0.1  # Default temperature (very low for precision)
    timeout = 100  # Default timeout in seconds for overall response
    max_tokens = 50000  # Default max tokens to generate
    format_mode = None  # Default: no format restriction (allows thinking)
    pipeline_override = None  # Default: use prompt settings or auto-detect
    args = sys.argv[1:]
    
    # Check for help flag first
    if len(args) >= 1 and args[0] in ['--help', '-h', 'help']:
        args = []
    
    # Check for clean mode
    if len(args) >= 1 and args[0] == '--clean':
        # Handle clean command
        directory = "."
        force = False
        dry_run = False
        pipeline = None
        
        # Parse clean-specific options
        args = args[1:]  # Remove --clean
        while len(args) > 0:
            if args[0] == '--force':
                force = True
                args = args[1:]
            elif args[0] == '--dry-run':
                dry_run = True
                args = args[1:]
            elif args[0] == '--pipeline' and len(args) >= 2:
                pipeline = args[1]
                if pipeline not in ['txt', 'png', 'docling']:
                    print(f"Invalid pipeline: {pipeline}. Use 'txt', 'png', or 'docling'")
                    sys.exit(1)
                args = args[2:]
            elif not args[0].startswith('-'):
                # This is the directory
                directory = args[0]
                args = args[1:]
            else:
                print(f"Unknown clean option: {args[0]}")
                print("Usage: python thea.py --clean [--force] [--dry-run] [--pipeline <txt|png|docling>] [directory]")
                sys.exit(1)
        
        # Execute clean and exit
        deleted_thea, deleted_png, deleted_extraction = clean_thea_files(directory, force, dry_run, pipeline)
        sys.exit(0)
    
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
        elif args[0] == '--save-sidecars':
            save_sidecars = True
            args = args[1:]  # Remove save-sidecars flag from args
        elif args[0] == '--sidecars-only':
            sidecars_only = True
            save_sidecars = True  # Automatically enable sidecar saving
            args = args[1:]  # Remove sidecars-only flag from args
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
        elif args[0] == '--max-attempts' and len(args) >= 2:
            try:
                max_attempts = int(args[1])
                if max_attempts < 1 or max_attempts > 10:
                    print(f"Error: Max attempts must be between 1 and 10. Got: {max_attempts}")
                    sys.exit(1)
                args = args[2:]  # Remove max-attempts arguments from args
            except ValueError:
                print(f"Error: Invalid max-attempts value '{args[1]}'. Must be an integer.")
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
        elif args[0] == '--timeout' and len(args) >= 2:
            try:
                timeout = int(args[1])
                if timeout < 1 or timeout > 3600:
                    print(f"Error: Timeout must be between 1 and 3600 seconds. Got: {timeout}")
                    sys.exit(1)
                args = args[2:]  # Remove timeout arguments from args
            except ValueError:
                print(f"Error: Invalid timeout value '{args[1]}'. Must be an integer.")
                sys.exit(1)
        elif args[0] == '--max-tokens' and len(args) >= 2:
            try:
                max_tokens = int(args[1])
                if max_tokens < 100 or max_tokens > 100000:
                    print(f"Error: Max tokens must be between 100 and 100000. Got: {max_tokens}")
                    sys.exit(1)
                args = args[2:]  # Remove max-tokens arguments from args
            except ValueError:
                print(f"Error: Invalid max-tokens value '{args[1]}'. Must be an integer.")
                sys.exit(1)
        elif args[0] == '--format' and len(args) >= 2:
            if args[1].lower() in ['json', 'none', 'null', '']:
                format_mode = 'json' if args[1].lower() == 'json' else None
                args = args[2:]  # Remove format arguments from args
            else:
                print(f"Error: Format must be 'json' or 'none'. Got: {args[1]}")
                sys.exit(1)
        elif args[0] == '--pipeline' and len(args) >= 2:
            pipeline_override = args[1]
            if pipeline_override not in ['pdf-convert-png', 'pdf-extract-txt', 'pdf-extract-png', 'pdf-extract-docling']:
                print(f"Error: Unknown pipeline type '{pipeline_override}'")
                print("Available pipelines: pdf-extract-png, pdf-extract-txt, pdf-extract-docling")
                # Support legacy name
                if pipeline_override == 'pdf-convert-png':
                    pipeline_override = 'pdf-extract-png'
                else:
                    sys.exit(1)
            args = args[2:]  # Remove pipeline arguments from args
        else:
            print(f"Error: Unknown option '{args[0]}'")
            sys.exit(1)
    
    if len(args) < 1:
        print("THEA - PDF Text Extraction and Analysis System")
        print("=" * 50)
        print("\nUsage:")
        print("  python thea.py [OPTIONS] <file_pattern> [file_pattern2] ...")
        print("  python thea.py --clean [--force] [--dry-run] [--pipeline <type>] [directory]")
        print("  python thea.py --help")
        print("\nOptions:")
        print("  --help, -h        Show this help message and exit")
        print("  --clean           Clean THEA-generated files (.thea_extract, .png, extraction files)")
        print("                    Options: --force (skip confirmation)")
        print("                            --dry-run (show what would be deleted)")
        print("                            --pipeline <txt|png|docling> (clean specific pipeline only)")
        print("  --mode <mode>     Processing mode:")
        print("                    - skip:      Skip PDFs that already have matching .thea files (default)")
        print("                    - overwrite: Always process PDFs even if .thea files exist")
        print("  --prompt <file>   Load system prompt from a .prompt file")
        print("                    The filename (without .prompt) becomes the default suffix")
        print("  --suffix <text>   Add custom suffix to output filename before .thea extension")
        print("                    Overrides the automatic suffix from prompt filename")
        print("  --save-sidecars   Save sidecar files (PNG images for image pipeline, text files for text pipeline)")
        print("  --sidecars-only   Generate sidecar files only without model processing (implies --save-sidecars)")
        print("  --dpi <number>    Set DPI resolution for PDF to image conversion (50-600, default: 300)")
        print("  --max-attempts <n> Max attempts when model gets stuck (1-10, default: 3)")
        print("  -m, --model <name> Override default model (e.g., gemma:14b, llama2:13b)")
        print("  -t, --temperature <value> Set initial temperature (0.0-2.0, default: 0.1)")
        print("                    Temperature increases progressively with retries to reach ~1.0")
        print("  --timeout <secs>  Overall request timeout in seconds (1-3600, default: 100)")
        print("  --max-tokens <n>  Maximum tokens to generate (100-100000, default: 50000)")
        print("  --format <mode>   Output format mode: 'json' or 'none' (default: none)")
        print("                    'json' forces pure JSON output (no thinking)")
        print("                    'none' allows model thinking and reasoning")
        print("  --pipeline <type> Processing pipeline: 'pdf-convert-png' or 'pdf-extract-txt'")
        print("                    'pdf-convert-png': Convert PDF to images (for vision models)")
        print("                    'pdf-extract-txt': Extract text using multiple methods (for text models)")
        print("                    Default: determined by prompt file or model type")
        print("\nOutput File Format:")
        print("  Default:          <pdf>.<timestamp>.<model>.thea_extract")
        print("  With suffix:      <pdf>.<timestamp>.<model>.<suffix>.thea_extract")
        print("  With prompt:      <pdf>.<timestamp>.<model>.<promptname>.thea_extract")
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
        print("  python thea.py --save-sidecars --dpi 150 '*.pdf'")
        print("\n  # High quality image extraction")
        print("  python thea.py --save-sidecars --dpi 600 --suffix hq 'important.pdf'")
        print("\n  # Extract text only without model processing")
        print("  python thea.py --sidecars-only --pipeline pdf-extract-txt '*.pdf'")
        print("\n  # Extract with Docling only without model processing")
        print("  python thea.py --sidecars-only --pipeline pdf-extract-docling 'Belege/*.pdf'")
        print("\n  # Increase attempts for unstable model")
        print("  python thea.py --max-attempts 5 '*.pdf'")
        print("\n  # Use a different model")
        print("  python thea.py -m gemma:14b '*.pdf'")
        print("\n  # Set higher initial temperature for more creative output")
        print("  python thea.py -t 0.7 '*.pdf'")
        print("\n  # Combine options: custom model with higher temperature")
        print("  python thea.py -m llama2:13b -t 0.5 --max-attempts 10 '*.pdf'")
        print("\n  # Clean ALL THEA files from current directory")
        print("  python thea.py --clean")
        print("\n  # Clean only pdf-extract-txt pipeline files")
        print("  python thea.py --clean --pipeline txt Belege/")
        print("\n  # Clean only pdf-extract-docling pipeline files")
        print("  python thea.py --clean --pipeline docling Belege/")
        print("\n  # Clean without confirmation prompt")
        print("  python thea.py --clean --force Belege/")
        print("\n  # Preview what would be deleted (dry run)")
        print("  python thea.py --clean --dry-run --pipeline txt Belege/")
        print("\nNotes:")
        print("  - Requires Ollama running on localhost:11434")
        print("  - Requires poppler-utils for PDF processing")
        print("  - Default model: gemma3:27b (override with -m/--model)")
        print("  - Skip mode is suffix-specific: only skips files with matching suffix")
        print("  - Prompt files use JSON format (or legacy plain text)")
        print("  - Default DPI: 300 (higher = better quality but larger files)")
        print("  - Sidecar files saved when --save-sidecars is used")
        print("  - Automatically retries if model gets stuck in repetitive patterns")
        print("\nEnvironment:")
        print("  - Python 3.x with virtual environment")
        print("  - Dependencies: pdf2image, Pillow, requests")
        print("  - Run 'npm run setup' for initial setup")
        sys.exit(1)
    
    # Load prompt configuration
    prompt_config = None
    
    # Priority 1: Try specified prompt file
    if prompt_file:
        prompt_config = load_prompt_file(prompt_file)
        if prompt_config:
            print(f"Using prompt file: {prompt_file}")
            # Extract prompt name for suffix if no explicit suffix given
            if not suffix and not prompt_config.get("legacy"):
                # Remove .prompt extension and use as suffix
                prompt_name = os.path.splitext(os.path.basename(prompt_file))[0]
                if prompt_name != ".prompt":  # Don't use empty suffix for default .prompt
                    suffix = prompt_name
                    print(f"  Auto-suffix: {suffix}")
        else:
            print(f"Warning: Could not load prompt file '{prompt_file}', using defaults")
    
    # Priority 2: Try default .prompt file if no prompt file specified
    if not prompt_config and not prompt_file:
        if os.path.exists(".prompt"):
            prompt_config = load_prompt_file(".prompt")
            if prompt_config:
                print("Using default .prompt file")
    
    # Priority 3: Fall back to hardcoded defaults
    if not prompt_config:
        prompt_config = {
            "system_prompt": {
                "suffix": "Extract all text from the provided PDF image(s) accurately. Then, count the total number of characters in the extracted text directly (do not count step-by-step or iteratively; just compute and output the exact count). Provide a one-word description of the document type in both German and English. Also, briefly summarize what the document is about content-wise in 1-2 sentences in both German and English.",
                "output_format": {
                    "type": "json",
                    "instructions": "Respond ONLY in this exact JSON format, nothing else",
                    "schema": {
                        "extracted_text": "string",
                        "character_count": "number",
                        "one_word_description_german": "string",
                        "one_word_description_english": "string",
                        "content_summary_german": "string",
                        "content_summary_english": "string"
                    }
                }
            },
            "user_prompt": {
                "template": "Extract the text from this PDF document '{{pdf_path}}', count its characters, describe it with one word in both German and English, and summarize its content in both German and English as instructed."
            },
            "settings": {}
        }
        if not prompt_file:  # Only show this if user didn't specify a prompt file
            print("Using hardcoded default prompts")
    
    # Apply settings from prompt config (can be overridden by command-line args)
    prompt_settings = prompt_config.get("settings", {})
    
    # Parameter priority: command-line > prompt file > defaults
    # Only apply prompt file settings if not specified on command line
    if not model_override and "model" in prompt_settings:
        model_override = prompt_settings["model"]
        print(f"  Using model from prompt: {model_override}")
    
    # For these, we check if they're still at default values
    if temperature == 0.1 and "temperature" in prompt_settings:
        temperature = prompt_settings["temperature"]
        print(f"  Using temperature from prompt: {temperature}")
    
    if max_attempts == 3 and "max_attempts" in prompt_settings:
        max_attempts = prompt_settings["max_attempts"]
        print(f"  Using max_attempts from prompt: {max_attempts}")
    
    if timeout == 100 and "timeout" in prompt_settings:
        timeout = prompt_settings["timeout"]
        print(f"  Using timeout from prompt: {timeout}")
    
    if max_tokens == 50000 and "max_tokens" in prompt_settings:
        max_tokens = prompt_settings["max_tokens"]
        print(f"  Using max_tokens from prompt: {max_tokens}")
    
    if format_mode is None and "format" in prompt_settings:
        format_value = prompt_settings["format"]
        format_mode = 'json' if format_value == 'json' else None
        if format_mode:
            print(f"  Using format from prompt: {format_mode}")
    
    if mode == 'skip' and "mode" in prompt_settings:
        mode = prompt_settings["mode"]
        print(f"  Using mode from prompt: {mode}")
    
    # Check for legacy parameters in prompt
    if not save_sidecars:
        if "save_sidecars" in prompt_settings:
            save_sidecars = prompt_settings["save_sidecars"]
            if save_sidecars:
                print(f"  Using save_sidecars from prompt: {save_sidecars}")
        elif "save_image" in prompt_settings:
            save_sidecars = prompt_settings["save_image"]
            if save_sidecars:
                print(f"  Using save_image from prompt as save_sidecars: {save_sidecars}")
        elif "save_extractions" in prompt_settings:
            save_sidecars = prompt_settings["save_extractions"]
            if save_sidecars:
                print(f"  Using save_extractions from prompt as save_sidecars: {save_sidecars}")
    
    if dpi == 300 and "dpi" in prompt_settings:
        dpi = prompt_settings["dpi"]
        print(f"  Using DPI from prompt: {dpi}")
    
    # Get endpoint URL
    endpoint_url = prompt_settings.get("endpoint_url", "https://b1s.hey.bahn.business/api/chat")
    
    # Build system prompt from config
    system_prompt = build_system_prompt(prompt_config)
    
    print(f"Mode: {mode}")
    if suffix:
        print(f"Suffix: {suffix}")
    if sidecars_only:
        print(f"Sidecars-only mode: enabled (skipping model processing)")
    elif save_sidecars:
        print(f"Save sidecars: enabled")
    print(f"DPI: {dpi}")
    print(f"Max attempts: {max_attempts}")
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
        models: list[str] = ["gemma3:12b"]  # Default model (smaller for faster switching)
    
    # Initialize pipeline based on prompt configuration or override
    if pipeline_override:
        # Use command-line override
        pipeline = PipelineManager.get_pipeline(pipeline_override, prompt_config.get("settings", {}).get("pipeline_config", {}))
        pipeline_type = pipeline_override
        print(f"Using pipeline override: {pipeline_type}")
    else:
        # Use prompt configuration
        pipeline = PipelineManager.get_pipeline_from_prompt(prompt_config)
        pipeline_type = pipeline.pipeline_type
    
    for pdf_path in pdf_paths:
        print(f"\nProcessing file: {pdf_path}")
        
        # Check if we should skip this file (do this BEFORE pipeline processing to avoid creating sidecar files)
        if mode == 'skip' and models:
            # Use the first model for the skip check
            model_part = models[0].replace(":", ".")
            
            # Different skip logic for sidecars-only mode vs normal mode
            if sidecars_only:
                # Check for existing sidecar files based on pipeline type
                existing_files = []
                
                if pipeline_type == "pdf-extract-docling":
                    # Check for any existing Docling sidecar files
                    existing_pattern = f"{pdf_path}.*.docling.*"
                    existing_files = glob.glob(existing_pattern)
                    
                elif pipeline_type == "pdf-extract-txt":
                    # Check for any existing text extraction sidecar files
                    patterns = [
                        f"{pdf_path}.*.pypdf2.txt",
                        f"{pdf_path}.*.pdfplumber.txt",
                        f"{pdf_path}.*.pymupdf.txt"
                    ]
                    for pattern in patterns:
                        existing_files.extend(glob.glob(pattern))
                    
                elif pipeline_type == "pdf-extract-png":
                    # Check for any existing PNG sidecar files
                    existing_pattern = f"{pdf_path}.*.png"
                    existing_files = glob.glob(existing_pattern)
                
                if existing_files:
                    suffix_msg = f" with suffix '{suffix}'" if suffix else ""
                    print(f"Skipping {pdf_path} with model {models[0]}{suffix_msg} - sidecars already exist ({len(existing_files)} file(s))")
                    continue
            else:
                # Normal mode: check for .thea_extract files
                if suffix:
                    existing_pattern = f"{pdf_path}.*.{model_part}.{suffix}.thea_extract"
                else:
                    existing_pattern = f"{pdf_path}.*.{model_part}.thea_extract"
                existing_files = glob.glob(existing_pattern)
                if existing_files:
                    suffix_msg = f" with suffix '{suffix}'" if suffix else ""
                    print(f"Skipping {pdf_path} with model {models[0]}{suffix_msg} - already processed ({len(existing_files)} existing file(s))")
                    continue
        
        # Process PDF through the selected pipeline
        if pipeline_type == "pdf-extract-png":
            # Image pipeline
            pipeline_data, pipeline_metadata = pipeline.process(pdf_path, dpi=dpi, save_sidecars=save_sidecars)
            base64_images, pil_images = pipeline_data
            
            if not base64_images:
                print(f"Skipping {pdf_path} - no images available")
                continue
            
            # For sidecars-only mode with PNG pipeline, save images now
            if sidecars_only and pil_images:
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                model_part = models[0].replace(":", ".") if models else "unknown"
                
                for i, image in enumerate(pil_images, 1):
                    if suffix:
                        image_file = f"{pdf_path}.{timestamp}.{model_part}.{suffix}.{dpi}p{i}.png"
                    else:
                        image_file = f"{pdf_path}.{timestamp}.{model_part}.{dpi}p{i}.png"
                    try:
                        image.save(image_file, format='PNG')
                        print(f"      Saved image: {image_file}")
                    except Exception as e:
                        print(f"      Error saving image {image_file}: {e}")
                
                print(f"  ✓ {len(pil_images)} PNG images saved for {pdf_path} (skipping model processing)")
                continue
        else:
            # Text extraction pipeline
            # Generate timestamp and model part for file naming
            import datetime
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            model_part = models[0].replace(":", ".") if models else "unknown"
            
            pipeline_data, pipeline_metadata = pipeline.process(
                pdf_path, 
                save_sidecars=save_sidecars,
                timestamp=timestamp,
                model_part=model_part,
                suffix=suffix
            )
            
            # Check if extraction was successful based on pipeline type
            if pipeline_type == "pdf-extract-docling":
                # Docling pipeline uses extraction_success flag
                if not pipeline_data or not pipeline_metadata.get("extraction_success", False):
                    print(f"Skipping {pdf_path} - extraction failed")
                    continue
            else:
                # Text extraction pipeline uses extraction_count
                if not pipeline_data or pipeline_metadata.get("extraction_count", 0) == 0:
                    print(f"Skipping {pdf_path} - no text extracted")
                    continue
            
            # Format for model
            pipeline_data = pipeline.format_for_model(pipeline_data, pipeline_metadata)
            pil_images = None  # No images for text pipeline
        
        # Check if we should skip model processing
        if sidecars_only:
            print(f"  ✓ Sidecars saved for {pdf_path} (skipping model processing)")
            continue
        
        for model in models:
            # Build user prompt from template
            user_prompt = build_user_prompt(prompt_config, pdf_path)
            
            # Pass additional parameters for the new JSON format
            process_with_model(
                model, pipeline_data, pdf_path, system_prompt, user_prompt, 
                mode, suffix, save_sidecars, pil_images, max_attempts, dpi, temperature,
                prompt_file=prompt_file,
                prompt_config=prompt_config,
                endpoint_url=endpoint_url,
                timeout=timeout,
                max_tokens=max_tokens,
                format_mode=format_mode,
                pipeline_type=pipeline_type,
                pipeline_metadata=pipeline_metadata
            )