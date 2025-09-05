#!/usr/bin/env python3
"""
Script zur Analyse und Korrektur der Depot-Extraktionsprobleme
"""

import re
import json
from pathlib import Path
from typing import Dict, Optional, Tuple

class DepotExtractionFixer:
    def __init__(self):
        self.base_path = Path("/mnt/c/Projects/THEA/docs")
        self.issues = []
        self.fixes = []
        
    def load_thea_extract(self, file_path: Path) -> Optional[Dict]:
        """Lädt eine .thea_extract Datei"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Fehler beim Laden von {file_path}: {e}")
            return None
    
    def detect_document_type(self, extracted_text: str) -> str:
        """Erkennt den Dokumenttyp basierend auf Inhalt"""
        text_lower = extracted_text.lower()
        
        # Kosteninformation
        if 'information über kosten' in text_lower or 'kosteninformation' in text_lower:
            return 'cost_information'
        
        # Depotabschluss
        if 'depotabschluss' in text_lower or 'ex-post' in text_lower:
            # Prüfe ob es ein echter Depotabschluss ist
            if 'summe kurswerte' in text_lower or 'depotbestand' in text_lower or 'stück' in text_lower:
                return 'depot_statement'
            elif 'kein bestand vorhanden' in text_lower:
                return 'depot_statement_empty'
            else:
                # Könnte Kosteninformation sein die als Depotabschluss benannt ist
                if 'kosten' in text_lower and 'nebenkosten' in text_lower:
                    return 'cost_information'
                return 'depot_statement'
        
        return 'unknown'
    
    def extract_shares_from_cost_info(self, extracted_text: str) -> Optional[int]:
        """Extrahiert Stückzahl aus Kosteninformations-Dokumenten"""
        # Suche nach Stückzahl in verschiedenen Formaten
        patterns = [
            r'Stückzahl[:\s]+(\d+)',
            r'Anzahl[:\s]+(\d+)',
            r'(\d+)\s+Stück',
            r'Bestand[:\s]+(\d+)\s+Stück',
            # In Tabellen
            r'\|\s*(\d+)\s*\|\s*US88160R1014',  # Stückzahl vor ISIN
            r'US88160R1014\s*\|\s*(\d+)',       # Stückzahl nach ISIN
        ]
        
        for pattern in patterns:
            match = re.search(pattern, extracted_text)
            if match:
                return int(match.group(1))
        
        return None
    
    def extract_shares_from_depot_statement(self, extracted_text: str) -> Optional[int]:
        """Extrahiert Stückzahl aus echten Depotabschlüssen"""
        # Erweiterte Patterns für verschiedene Tabellenformate
        patterns = [
            # Standard Tabellen mit | Trennzeichen
            r'\|\s*Stück\s*\|\s*(\d+)',
            r'Stück\s+\|\s+(\d+)',
            
            # Tabellen ohne Trennzeichen
            r'Stück\s+(\d+)(?:\s|$)',
            r'(\d+)\s+Stück',
            
            # In Zeilen mit TESLA
            r'TESLA[^\n]*?(\d{3,4})\s+Stück',
            r'TESLA[^\n]*?Stück\s+(\d{3,4})',
            
            # Mit ISIN
            r'US88160R1014[^\n]*?(\d{3,4})\s+',
            r'US88160R1014[^\n]*?Stück\s+(\d{3,4})',
            
            # Spezielle Formate
            r'Bestand:\s*(\d+)\s+Stück',
            r'Anzahl:\s*(\d+)',
            r'Position[^\n]*?(\d{3,4})\s+Stück',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, extracted_text)
            if matches:
                # Bei mehreren Matches, nimm den größten plausiblen Wert
                for match in matches:
                    shares = int(match)
                    if 100 <= shares <= 10000:  # Plausible Range für Tesla-Aktien
                        return shares
        
        return None
    
    def analyze_document(self, file_path: Path) -> Dict:
        """Analysiert ein einzelnes Dokument"""
        data = self.load_thea_extract(file_path)
        if not data:
            return {'file': str(file_path), 'error': 'Cannot load file'}
        
        extracted_text = data.get('response', {}).get('json', {}).get('extracted_text', '')
        pdf_path = data.get('metadata', {}).get('file', {}).get('pdf_path', '')
        
        doc_type = self.detect_document_type(extracted_text)
        
        shares = None
        if doc_type == 'cost_information':
            shares = self.extract_shares_from_cost_info(extracted_text)
        elif doc_type == 'depot_statement':
            shares = self.extract_shares_from_depot_statement(extracted_text)
        
        # Extrahiere ISIN
        isin = None
        isin_match = re.search(r'(US88160R1014)', extracted_text)
        if isin_match:
            isin = isin_match.group(1)
        
        # Extrahiere Depotbestand
        balance = None
        if doc_type == 'depot_statement':
            # Suche nach Kurswert/Depotbestand
            balance_patterns = [
                r'Summe\s+Kurswerte[^\d]*?([\d.,]+)',
                r'Kurswert[^\d]*?([\d.,]+)\s*EUR',
                r'Depotbestand[^\d]*?([\d.,]+)',
            ]
            for pattern in balance_patterns:
                match = re.search(pattern, extracted_text, re.IGNORECASE)
                if match:
                    balance_str = match.group(1).replace('.', '').replace(',', '.')
                    try:
                        balance = float(balance_str)
                        if balance > 100:  # Mindestens 100 EUR
                            break
                    except ValueError:
                        pass
        
        return {
            'file': file_path.name,
            'pdf_path': pdf_path,
            'doc_type': doc_type,
            'shares': shares,
            'isin': isin,
            'balance': balance,
            'has_shares': shares is not None,
            'has_isin': isin is not None,
            'has_balance': balance is not None and balance > 0
        }
    
    def analyze_all_depots(self):
        """Analysiert alle Depot-Dokumente"""
        depot_folders = [
            'BLUEITS-Depotkonto-7274079',
            'Ramteid-Depotkonto-7274087'
        ]
        
        for folder in depot_folders:
            print(f"\n{'='*60}")
            print(f"Analysiere {folder}")
            print('='*60)
            
            depot_path = self.base_path / folder
            if not depot_path.exists():
                print(f"Ordner nicht gefunden: {depot_path}")
                continue
            
            # Finde alle Depotabschluss-Dateien
            depot_files = list(depot_path.glob("*Depotabschluss*.thea_extract"))
            
            # Kategorisiere Dokumente
            cost_info_docs = []
            depot_statements_with_shares = []
            depot_statements_missing_shares = []
            empty_depot_statements = []
            
            for file_path in depot_files:
                result = self.analyze_document(file_path)
                
                if result['doc_type'] == 'cost_information':
                    cost_info_docs.append(result)
                elif result['doc_type'] == 'depot_statement_empty':
                    empty_depot_statements.append(result)
                elif result['doc_type'] == 'depot_statement':
                    if result['has_shares']:
                        depot_statements_with_shares.append(result)
                    else:
                        depot_statements_missing_shares.append(result)
            
            # Ausgabe der Ergebnisse
            print(f"\nGefundene Dokumenttypen:")
            print(f"  - Depotabschlüsse mit Stückzahlen: {len(depot_statements_with_shares)}")
            print(f"  - Depotabschlüsse OHNE Stückzahlen: {len(depot_statements_missing_shares)}")
            print(f"  - Leere Depotabschlüsse: {len(empty_depot_statements)}")
            print(f"  - Kosteninformationen: {len(cost_info_docs)}")
            
            if depot_statements_missing_shares:
                print(f"\nDepotabschlüsse ohne Stückzahlen (müssen geprüft werden):")
                for doc in depot_statements_missing_shares:
                    print(f"  - {doc['file']}")
                    if doc['has_balance']:
                        print(f"    Balance: {doc['balance']:.2f} EUR")
                    if doc['has_isin']:
                        print(f"    ISIN: {doc['isin']}")
            
            if cost_info_docs:
                print(f"\nKosteninformations-Dokumente:")
                for doc in cost_info_docs:
                    print(f"  - {doc['file']}")
                    if doc['has_shares']:
                        print(f"    Stückzahl gefunden: {doc['shares']}")
                    else:
                        print(f"    KEINE Stückzahl gefunden")
            
            # Speichere Issues für späteren Fix
            for doc in depot_statements_missing_shares:
                self.issues.append({
                    'depot': folder,
                    'file': doc['file'],
                    'type': 'missing_shares',
                    'doc_type': doc['doc_type']
                })
            
            for doc in cost_info_docs:
                self.issues.append({
                    'depot': folder,
                    'file': doc['file'],
                    'type': 'misclassified_as_depot',
                    'doc_type': doc['doc_type']
                })
    
    def generate_fix_recommendations(self):
        """Generiert Empfehlungen zur Behebung der Probleme"""
        print(f"\n{'='*60}")
        print("EMPFEHLUNGEN ZUR BEHEBUNG")
        print('='*60)
        
        print("\n1. DOKUMENTTYP-ERKENNUNG:")
        print("   Füge in Depotkonto.py eine Funktion zur Dokumenttyp-Erkennung hinzu:")
        print("   - Prüfe auf 'Information über Kosten' → cost_information")
        print("   - Prüfe auf 'Summe Kurswerte' → depot_statement")
        print("   - Prüfe auf 'kein Bestand vorhanden' → depot_statement_empty")
        
        print("\n2. ERWEITERTE STÜCKZAHL-EXTRAKTION:")
        print("   Erweitere die Regex-Patterns für verschiedene Tabellenformate:")
        print("   - Tabellen mit und ohne | Trennzeichen")
        print("   - Stückzahl vor/nach dem Wort 'Stück'")
        print("   - Stückzahl in Zeilen mit TESLA oder ISIN")
        
        print("\n3. SEPARATE BEHANDLUNG VON KOSTENINFORMATIONEN:")
        print("   - Erkenne Kosteninformationen und behandle sie separat")
        print("   - Extrahiere Stückzahlen aus Kosteninformationen wenn vorhanden")
        print("   - Markiere sie klar als Kosteninformation, nicht als Depotabschluss")
        
        print("\n4. VERBESSERTE BALANCE-EXTRAKTION:")
        print("   - Suche in mehreren Zeilen nach 'Summe Kurswerte'")
        print("   - Berücksichtige verschiedene Tabellenformate")
        print("   - Verwende den höchsten gefundenen Wert über 100 EUR")

if __name__ == "__main__":
    fixer = DepotExtractionFixer()
    fixer.analyze_all_depots()
    fixer.generate_fix_recommendations()