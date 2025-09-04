#!/usr/bin/env python3
"""
Depotkonto.py - Analyse und Markdown-Generierung für Depotkonten
Verarbeitet BLUEITS-Depotkonto-7274079 und Ramteid-Depotkonto-7274087
"""

import re
from pathlib import Path
from typing import Dict, List, Any
from collections import defaultdict

from Konten import BaseKontoAnalyzer, calculate_monthly_aggregates


class DepotkontoAnalyzer(BaseKontoAnalyzer):
    def __init__(self):
        super().__init__()
        self.depots = {
            "BLUEITS": {
                "folder": "BLUEITS-Depotkonto-7274079",
                "depot_number": "7274079",
                "output_file": "BLUEITS-Depotkonto.md",
                "company_name": "BLUEITS GmbH"
            },
            "Ramteid": {
                "folder": "Ramteid-Depotkonto-7274087",
                "depot_number": "7274087",
                "output_file": "Ramteid-Depotkonto.md",
                "company_name": "Ramteid GmbH"
            }
        }
    
    def extract_transaction_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Extrahiert depot-spezifische Transaktionsdaten"""
        base_data = self.get_base_transaction_data(data)
        if not base_data:
            return None
            
        extracted_text = base_data['extracted_text']
        
        # Extrahiere ISIN
        isin_match = re.search(r'([A-Z]{2}[A-Z0-9]{10})', extracted_text)
        isin = isin_match.group(1) if isin_match else None
        
        # Extrahiere Beträge
        amounts = self.extract_amounts_from_text(extracted_text)
        
        # Bestimme Transaktionstyp
        transaction_type = 'Unbekannt'
        if 'Verkauf' in extracted_text or 'verkauf' in extracted_text.lower():
            transaction_type = 'Verkauf'
        elif 'Kauf' in extracted_text or 'kauf' in extracted_text.lower():
            transaction_type = 'Kauf'
        elif 'Depotabschluss' in extracted_text:
            transaction_type = 'Depotabschluss'
            
        return {
            **base_data,
            'type': transaction_type,
            'isin': isin,
            'amounts': amounts,
            'max_amount': max(amounts) if amounts else 0
        }
    
    def analyze_depot(self, depot_name: str) -> Dict[str, Any]:
        """Analysiert alle Dateien eines Depots"""
        depot_info = self.depots[depot_name]
        depot_path = self.base_path / depot_info['folder']
        
        if not depot_path.exists():
            print(f"Depot-Ordner nicht gefunden: {depot_path}")
            return None
            
        # Sammle alle .thea_extract Dateien
        thea_files = list(depot_path.glob("*.thea_extract"))
        pdf_files = list(depot_path.glob("*.pdf")) + list(depot_path.glob("*.PDF"))
        
        print(f"Gefunden: {len(pdf_files)} PDF-Dateien und {len(thea_files)} .thea_extract Dateien in {depot_name}")
        
        transactions = []
        statistics = defaultdict(int)
        isin_groups = defaultdict(list)
        
        for file_path in thea_files:
            data = self.load_thea_extract(file_path)
            if data:
                transaction = self.extract_transaction_data(data)
                if transaction:
                    transactions.append(transaction)
                    statistics[transaction['type']] += 1
                    if transaction['isin']:
                        isin_groups[transaction['isin']].append(transaction)
        
        # Sortiere Transaktionen nach Datum
        transactions.sort(key=lambda x: x['date'] if x['date'] else '0000-00-00')
        
        return {
            'depot_name': depot_name,
            'depot_number': depot_info['depot_number'],
            'company_name': depot_info['company_name'],
            'total_pdf_files': len(pdf_files),
            'total_thea_files': len(thea_files),
            'transactions': transactions,
            'statistics': dict(statistics),
            'isin_groups': dict(isin_groups),
            'depot_path': depot_path,
            'depot_info': depot_info
        }
    
    def generate_markdown(self, analysis: Dict[str, Any]) -> str:
        """Generiert Markdown-Bericht aus der Analyse"""
        if not analysis:
            return "# Fehler bei der Analyse\n\nKeine Daten verfügbar."
            
        md = []
        
        # Abschnitt 1: Firmen- und Kontoübersicht
        header_lines = self.generate_header_section(
            company_name=analysis['company_name'],
            account_type="Depotkonto",
            account_number=analysis['depot_number'],
            total_pdf_files=analysis['total_pdf_files'],
            total_thea_files=analysis['total_thea_files']
        )
        md.extend(header_lines)
        
        # Abschnitt 2: Dokumententabelle
        doc_table_lines = self.generate_document_table(analysis['depot_path'], analysis['depot_info'])
        md.extend(doc_table_lines)
        
        # Abschnitt 3: Transaktionsstatistik
        md.append(f"\n## Transaktionsstatistik\n")
        for trans_type, count in analysis['statistics'].items():
            md.append(f"- **{trans_type}:** {count}")
        
        # Abschnitt 4: Wertpapiere nach ISIN
        if analysis['isin_groups']:
            md.append(f"\n## Wertpapiere (nach ISIN)\n")
            for isin, trans_list in analysis['isin_groups'].items():
                md.append(f"\n### {isin}")
                md.append(f"- **Anzahl Transaktionen:** {len(trans_list)}")
                
                # Berechne Summen
                verkauf_summe = sum(t['max_amount'] for t in trans_list if t['type'] == 'Verkauf')
                kauf_summe = sum(t['max_amount'] for t in trans_list if t['type'] == 'Kauf')
                
                if verkauf_summe > 0:
                    md.append(f"- **Verkaufssumme:** {verkauf_summe:,.2f} EUR")
                if kauf_summe > 0:
                    md.append(f"- **Kaufsumme:** {kauf_summe:,.2f} EUR")
        
        # Abschnitt 5: Transaktionsverlauf
        md.append(f"\n## Transaktionsverlauf\n")
        md.append("| Datum | Typ | ISIN | Betrag (EUR) | Beschreibung |")
        md.append("|-------|-----|------|--------------|--------------|")
        
        for trans in analysis['transactions']:
            date = trans['date'] if trans['date'] else 'N/A'
            trans_type = trans['type']
            isin = trans['isin'] if trans['isin'] else 'N/A'
            amount = f"{trans['max_amount']:,.2f}" if trans['max_amount'] > 0 else 'N/A'
            desc = trans['description_german']
            
            md.append(f"| {date} | {trans_type} | {isin} | {amount} | {desc} |")
        
        # Abschnitt 6: Zeitliche Verteilung
        md.append(f"\n## Zeitliche Verteilung\n")
        
        # Nutze die gemeinsame Funktion
        monthly_groups = calculate_monthly_aggregates(analysis['transactions'])
        
        if monthly_groups:
            md.append("| Monat | Anzahl Transaktionen | Gesamtvolumen (EUR) |")
            md.append("|-------|---------------------|---------------------|")
            
            for month in sorted(monthly_groups.keys()):
                data = monthly_groups[month]
                md.append(f"| {month} | {data['count']} | {data['volume']:,.2f} |")
        
        return '\n'.join(md)
    
    def run(self):
        """Hauptfunktion - analysiert beide Depots und generiert Markdown-Dateien"""
        for depot_name in self.depots.keys():
            print(f"\nAnalysiere {depot_name} Depot...")
            analysis = self.analyze_depot(depot_name)
            
            if analysis:
                markdown_content = self.generate_markdown(analysis)
                output_file = self.depots[depot_name]['output_file']
                
                self.save_markdown(markdown_content, output_file)
                self.print_summary(output_file, analysis)
                print(f"  - {len(analysis['transactions'])} Transaktionen analysiert")
            else:
                print(f"✗ Fehler bei der Analyse von {depot_name}")


if __name__ == "__main__":
    analyzer = DepotkontoAnalyzer()
    analyzer.run()