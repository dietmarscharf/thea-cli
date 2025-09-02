#!/usr/bin/env python3
"""
Script to check and compare duplicate files between BLUEITS and Ramteid accounts
"""

import os
import hashlib
from pathlib import Path

def calculate_md5(file_path):
    """Calculate MD5 checksum of a file"""
    hash_md5 = hashlib.md5()
    try:
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    except Exception as e:
        return f"Error: {str(e)}"

def main():
    # List of duplicate files found between companies
    duplicates = [
        "Orderabrechnung_-bestaetigung_ISIN_US88160R1014_TESLA_INC_vom_15_07_2024.PDF",
        "Orderabrechnung_-bestaetigung_ISIN_US88160R1014_TESLA_INC_vom_15_12_2023.PDF",
        "Orderabrechnung_-bestaetigung_ISIN_US88160R1014_TESLA_INC_vom_11_09_2023_1.PDF",
        "Orderabrechnung_-bestaetigung_ISIN_US88160R1014_TESLA_INC_vom_11_09_2023.PDF",
        "Orderabrechnung_-bestaetigung_ISIN_US88160R1014_TESLA_INC_vom_10_10_2023.PDF",
        "Orderabrechnung_-bestaetigung_ISIN_US88160R1014_TESLA_INC_vom_17_07_2023.PDF",
        "Orderabrechnung_-bestaetigung_ISIN_US88160R1014_TESLA_INC_vom_19_07_2023.PDF",
        "Orderabrechnung_-bestaetigung_ISIN_US88160R1014_TESLA_INC_vom_04_05_2023.PDF",
        "20211103_Orderabrechnung_-bestaetigung_ISIN_US88160R1014_TESLA_INC_vom_02_11_2021_1.pdf",
        "20211027_Orderabrechnung_-bestaetigung_ISIN_US88160R1014_TESLA_INC_vom_26_10_2021.pdf",
        "20211103_Orderabrechnung_-bestaetigung_ISIN_US88160R1014_TESLA_INC_vom_02_11_2021.pdf",
        "20211027_Orderabrechnung_-bestaetigung_ISIN_US88160R1014_TESLA_INC_vom_26_10_2021_1.pdf",
        "20210305_Orderabrechnung_-bestaetigung_ISIN_US88160R1014_TESLA_INC_vom_04_03_2021.pdf",
        "20210224_Orderabrechnung_-bestaetigung_ISIN_US88160R1014_TESLA_INC_vom_23_02_2021.pdf",
        "20210108_Orderabrechnung_-bestaetigung_ISIN_US88160R1014_TESLA_INC_vom_07_01_2021.pdf",
        "20210116_Orderabrechnung_-bestaetigung_ISIN_US88160R1014_TESLA_INC_vom_14_01_2021.pdf",
        "20210113_Orderabrechnung_-bestaetigung_ISIN_US88160R1014_TESLA_INC_vom_12_01_2021.pdf",
        "20210113_Orderabrechnung_-bestaetigung_ISIN_US88160R1014_TESLA_INC_vom_12_01_2021_4.pdf",
        "20210113_Orderabrechnung_-bestaetigung_ISIN_US88160R1014_TESLA_INC_vom_12_01_2021_2.pdf",
        "20210113_Orderabrechnung_-bestaetigung_ISIN_US88160R1014_TESLA_INC_vom_12_01_2021_3.pdf",
        "20210113_Orderabrechnung_-bestaetigung_ISIN_US88160R1014_TESLA_INC_vom_12_01_2021_1.pdf",
        "20210107_Orderabrechnung_-bestaetigung_ISIN_US88160R1014_TESLA_INC_vom_06_01_2021.pdf",
        "20201222_Orderabrechnung_-bestaetigung_ISIN_US88160R1014_TESLA_INC_vom_21_12_2020_1.pdf",
        "20201222_Orderabrechnung_-bestaetigung_ISIN_US88160R1014_TESLA_INC_vom_21_12_2020.pdf",
        "20201229_Orderabrechnung_-bestaetigung_ISIN_US88160R1014_TESLA_INC_vom_28_12_2020.pdf",
        "20201223_Orderabrechnung_-bestaetigung_ISIN_US88160R1014_TESLA_INC_vom_22_12_2020.pdf",
        "20201222_Orderabrechnung_-bestaetigung_ISIN_US88160R1014_TESLA_INC_vom_21_12_2020_2.pdf",
        "20201223_Orderabrechnung_-bestaetigung_ISIN_US88160R1014_TESLA_INC_vom_22_12_2020_1.pdf"
    ]
    
    print("=== DUPLICATE FILES CHECKSUM COMPARISON ===\n")
    print(f"{'Filename':<80} {'BLUEITS MD5':<32} {'Ramteid MD5':<32} {'Match':<10}")
    print("-" * 160)
    
    results = []
    
    for filename in duplicates:
        blueits_path = Path("BLUEITS-Depotkonto-7274079") / filename
        ramteid_path = Path("Ramteid-Depotkonto-7274087") / filename
        
        blueits_md5 = "Not found"
        ramteid_md5 = "Not found"
        match = "N/A"
        
        if blueits_path.exists():
            blueits_md5 = calculate_md5(blueits_path)
        
        if ramteid_path.exists():
            ramteid_md5 = calculate_md5(ramteid_path)
        
        if blueits_md5 != "Not found" and ramteid_md5 != "Not found":
            match = "✓ SAME" if blueits_md5 == ramteid_md5 else "✗ DIFFERENT"
        
        print(f"{filename:<80} {blueits_md5[:32]:<32} {ramteid_md5[:32]:<32} {match:<10}")
        
        results.append({
            'file': filename,
            'blueits_md5': blueits_md5,
            'ramteid_md5': ramteid_md5,
            'match': match
        })
    
    # Summary
    same_count = sum(1 for r in results if r['match'] == "✓ SAME")
    different_count = sum(1 for r in results if r['match'] == "✗ DIFFERENT")
    not_found_count = sum(1 for r in results if r['match'] == "N/A")
    
    print("\n" + "=" * 160)
    print(f"\nSUMMARY:")
    print(f"  Files with same content: {same_count}")
    print(f"  Files with different content: {different_count}")
    print(f"  Files not found in both locations: {not_found_count}")
    print(f"  Total duplicate files checked: {len(duplicates)}")
    
    # Save detailed report
    with open("duplicate_checksums.txt", "w") as f:
        f.write("DUPLICATE FILES CHECKSUM REPORT\n")
        f.write("=" * 80 + "\n\n")
        for r in results:
            f.write(f"File: {r['file']}\n")
            f.write(f"  BLUEITS MD5: {r['blueits_md5']}\n")
            f.write(f"  Ramteid MD5: {r['ramteid_md5']}\n")
            f.write(f"  Status: {r['match']}\n\n")
        
        f.write(f"\nSUMMARY:\n")
        f.write(f"  Files with same content: {same_count}\n")
        f.write(f"  Files with different content: {different_count}\n")
        f.write(f"  Files not found in both locations: {not_found_count}\n")
        f.write(f"  Total duplicate files checked: {len(duplicates)}\n")
    
    print("\nDetailed report saved to: duplicate_checksums.txt")

if __name__ == "__main__":
    main()