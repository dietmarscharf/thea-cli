#!/usr/bin/env python3
"""Find all failed THEA extracts where response.json is null or errors exist"""

import json
import os
import glob
from pathlib import Path

def check_thea_extract(file_path):
    """Check if a THEA extract file indicates a failed extraction"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        # Check if response.json is null
        if data.get('response', {}).get('json') is None:
            # Check if there are errors
            if data.get('errors'):
                return True, data.get('errors')
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return False, None
    
    return False, None

def find_failed_extracts():
    """Find all failed THEA extracts in docs/ folder"""
    failed_files = []
    
    # Find all .thea_extract files
    pattern = "docs/**/*.thea_extract"
    files = glob.glob(pattern, recursive=True)
    
    print(f"Checking {len(files)} THEA extract files...")
    
    for file_path in files:
        is_failed, errors = check_thea_extract(file_path)
        if is_failed:
            # Extract base PDF filename
            base_name = Path(file_path).name
            # Remove the timestamp and suffix to get original PDF name
            parts = base_name.split('.')
            # Find where the timestamp starts (format: YYYYMMDD_HHMMSS)
            for i, part in enumerate(parts):
                if len(part) == 15 and part[8] == '_':  # timestamp format
                    pdf_name = '.'.join(parts[:i])
                    break
            else:
                pdf_name = "Unknown"
            
            failed_files.append({
                'thea_extract': file_path,
                'pdf_name': pdf_name,
                'errors': errors
            })
    
    return failed_files

def get_sidecar_files(thea_extract_path):
    """Get all sidecar files for a THEA extract"""
    base_path = thea_extract_path.replace('.thea_extract', '')
    sidecars = []
    
    # Check for docling sidecars
    for ext in ['.docling.txt', '.docling.json', '.docling.md']:
        sidecar = base_path + ext
        if os.path.exists(sidecar):
            sidecars.append(sidecar)
    
    return sidecars

def main():
    failed = find_failed_extracts()
    
    if not failed:
        print("No failed THEA extracts found!")
        return
    
    print(f"\nFound {len(failed)} failed THEA extracts:")
    print("=" * 80)
    
    all_files_to_delete = []
    pdfs_to_reextract = set()
    
    for item in failed:
        print(f"\nPDF: {item['pdf_name']}")
        print(f"Extract: {item['thea_extract']}")
        print(f"Errors: {item['errors']}")
        
        # Add to deletion list
        all_files_to_delete.append(item['thea_extract'])
        
        # Find sidecars
        sidecars = get_sidecar_files(item['thea_extract'])
        if sidecars:
            print(f"Sidecars: {len(sidecars)} files")
            for sidecar in sidecars:
                print(f"  - {os.path.basename(sidecar)}")
                all_files_to_delete.append(sidecar)
        
        # Extract folder and PDF name for re-extraction
        folder = os.path.dirname(item['thea_extract'])
        pdfs_to_reextract.add(os.path.join(folder, item['pdf_name']))
    
    print("\n" + "=" * 80)
    print(f"Total files to delete: {len(all_files_to_delete)}")
    print(f"PDFs needing re-extraction: {len(pdfs_to_reextract)}")
    
    # Save deletion list
    with open('failed_extracts_to_delete.txt', 'w') as f:
        for file_path in all_files_to_delete:
            f.write(file_path + '\n')
    print("\nDeletion list saved to: failed_extracts_to_delete.txt")
    
    # Save PDFs to re-extract
    with open('pdfs_to_reextract.txt', 'w') as f:
        for pdf in sorted(pdfs_to_reextract):
            f.write(pdf + '\n')
    print("PDFs to re-extract saved to: pdfs_to_reextract.txt")

if __name__ == "__main__":
    main()