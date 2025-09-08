#!/usr/bin/env python3
"""Delete all failed THEA extracts and their sidecar files"""

import os
import sys

def delete_files():
    """Delete all files listed in failed_extracts_to_delete.txt"""
    
    if not os.path.exists('failed_extracts_to_delete.txt'):
        print("Error: failed_extracts_to_delete.txt not found!")
        return 1
    
    with open('failed_extracts_to_delete.txt', 'r') as f:
        files = [line.strip() for line in f if line.strip()]
    
    if not files:
        print("No files to delete.")
        return 0
    
    print(f"Deleting {len(files)} files...")
    deleted = 0
    failed = 0
    
    for file_path in files:
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                deleted += 1
                print(f"✓ Deleted: {os.path.basename(file_path)}")
            except Exception as e:
                failed += 1
                print(f"✗ Failed to delete {file_path}: {e}")
        else:
            print(f"- Already gone: {os.path.basename(file_path)}")
    
    print(f"\n{deleted} files deleted successfully")
    if failed > 0:
        print(f"{failed} files failed to delete")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(delete_files())