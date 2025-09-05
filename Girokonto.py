#!/usr/bin/env python3
"""
Girokonto.py - Analyse und Markdown-Generierung für Girokonten
Verarbeitet BLUEITS-Girokonto-200750750 und Ramteid-Girokonto-21377502
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Any
from collections import defaultdict

from Konten import BaseKontoAnalyzer, calculate_monthly_aggregates, calculate_yearly_aggregates

class GirokontoAnalyzer(BaseKontoAnalyzer):
    def __init__(self):
        super().__init__()
        self.accounts = {
            "BLUEITS": {
                "folder": "BLUEITS-Girokonto-200750750",
                "account_number": "200750750",
                "output_file": "BLUEITS-Girokonto.md",
                "company_name": "BLUEITS GmbH"
            },
            "Ramteid": {
                "folder": "Ramteid-Girokonto-21377502",
                "account_number": "21377502",
                "output_file": "Ramteid-Girokonto.md",
                "company_name": "Ramteid GmbH"
            }
        }
        
        
    
    def extract_transaction_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Extrahiert girokonto-spezifische Transaktionsdaten"""
        base_data = self.get_base_transaction_data(data)
        if not base_data:
            return None
            
        extracted_text = base_data['extracted_text']
        
        # Extrahiere IBAN
        iban = self.extract_iban_from_text(extracted_text)
        
        # Extrahiere Beträge
        amounts = self.extract_amounts_from_text(extracted_text)
        
        # Extrahiere Saldo
        saldo = self.extract_balance_from_text(extracted_text)
        
        # Bestimme Transaktionstyp
        transaction_type = 'Kontoauszug'
        if 'Kontoauszug' in extracted_text:
            transaction_type = 'Kontoauszug'
        elif 'Lastschrift' in extracted_text:
            transaction_type = 'Lastschrift'
        elif 'Überweisung' in extracted_text:
            transaction_type = 'Überweisung'
        elif 'Gutschrift' in extracted_text:
            transaction_type = 'Gutschrift'
            
        # Extrahiere Bewegungen (Ein-/Ausgänge)
        eingaenge = []
        ausgaenge = []
        
        # Suche nach typischen Mustern für Eingänge und Ausgänge
        if 'Gutschrift' in extracted_text or 'Eingang' in extracted_text:
            for amount in amounts[:5]:  # Erste 5 Beträge prüfen
                if amount > 0:
                    eingaenge.append(amount)
                    
        if 'Lastschrift' in extracted_text or 'Belastung' in extracted_text:
            for amount in amounts[:5]:
                if amount > 0:
                    ausgaenge.append(amount)
            
        return {
            **base_data,
            'type': transaction_type,
            'iban': iban,
            'amounts': amounts,
            'max_amount': max(amounts) if amounts else 0,
            'saldo': saldo,
            'eingaenge': sum(eingaenge),
            'ausgaenge': sum(ausgaenge),
            'anzahl_bewegungen': len(amounts)
        }
    
    def extract_latest_balance(self, account_path: Path) -> Dict[str, Any]:
        """Extrahiert den letzten Kontosaldo aus Kontoauszügen"""
        latest_saldo = None
        latest_saldo_date = None
        
        # Finde alle Kontoauszug-Dateien
        for thea_file in account_path.glob("*Kontoauszug*.thea_extract"):
            data = self.load_thea_extract(thea_file)
            if data:
                extracted_text = data.get('response', {}).get('json', {}).get('extracted_text', '')
                file_path = data.get('metadata', {}).get('file', {}).get('pdf_path', '')
                date_str = self.extract_date_from_filename(os.path.basename(file_path))
                
                # Extrahiere Saldo
                saldo = self.extract_balance_from_text(extracted_text)
                
                if saldo is not None and date_str:
                    # Aktualisiere letzten Saldo wenn neuer
                    if not latest_saldo_date or date_str > latest_saldo_date:
                        latest_saldo = saldo
                        latest_saldo_date = date_str
        
        return {
            'latest_saldo': latest_saldo,
            'latest_saldo_date': latest_saldo_date
        }
    
    def analyze_account(self, account_name: str) -> Dict[str, Any]:
        """Analysiert alle Dateien eines Girokontos"""
        account_info = self.accounts[account_name]
        account_path = self.base_path / account_info['folder']
        
        if not account_path.exists():
            print(f"Konto-Ordner nicht gefunden: {account_path}")
            return None
            
        # Sammle alle Dateien
        thea_files = list(account_path.glob("*.thea_extract"))
        pdf_files = list(account_path.glob("*.pdf")) + list(account_path.glob("*.PDF"))
        
        print(f"Gefunden: {len(pdf_files)} PDF-Dateien und {len(thea_files)} .thea_extract Dateien in {account_name}")
        
        transactions = []
        statistics = defaultdict(int)
        monthly_data = defaultdict(lambda: {'eingaenge': 0, 'ausgaenge': 0, 'count': 0})
        
        for file_path in thea_files:
            data = self.load_thea_extract(file_path)
            if data:
                transaction = self.extract_transaction_data(data)
                if transaction:
                    transactions.append(transaction)
                    statistics[transaction['type']] += 1
                    
                    # Monatliche Aggregation
                    if transaction['date']:
                        month_key = transaction['date'][:7]
                        monthly_data[month_key]['eingaenge'] += transaction['eingaenge']
                        monthly_data[month_key]['ausgaenge'] += transaction['ausgaenge']
                        monthly_data[month_key]['count'] += 1
                        if transaction['saldo']:
                            monthly_data[month_key]['saldo'] = transaction['saldo']
        
        # Sortiere Transaktionen nach Datum
        transactions.sort(key=lambda x: x['date'] if x['date'] else '0000-00-00')
        
        # Berechne Gesamtstatistiken
        total_eingaenge = sum(t['eingaenge'] for t in transactions)
        total_ausgaenge = sum(t['ausgaenge'] for t in transactions)
        
        # Extrahiere letzten Saldo
        balance_info = self.extract_latest_balance(account_path)
        
        return {
            'account_name': account_name,
            'account_number': account_info['account_number'],
            'company_name': account_info['company_name'],
            'total_pdf_files': len(pdf_files),
            'total_thea_files': len(thea_files),
            'transactions': transactions,
            'statistics': dict(statistics),
            'monthly_data': dict(monthly_data),
            'total_eingaenge': total_eingaenge,
            'total_ausgaenge': total_ausgaenge,
            'account_path': account_path,
            'account_info': account_info,
            'latest_saldo': balance_info['latest_saldo'],
            'latest_saldo_date': balance_info['latest_saldo_date']
        }
    
    def generate_markdown(self, analysis: Dict[str, Any]) -> str:
        """Generiert Markdown-Bericht aus der Analyse"""
        if not analysis:
            return "# Fehler bei der Analyse\n\nKeine Daten verfügbar."
            
        md = []
        
        # Abschnitt 1: Firmen- und Kontoübersicht
        header_lines = self.generate_header_section(
            company_name=analysis['company_name'],
            account_type="Girokonto",
            account_number=analysis['account_number'],
            total_pdf_files=analysis['total_pdf_files'],
            total_thea_files=analysis['total_thea_files'],
            latest_saldo=analysis.get('latest_saldo'),
            latest_saldo_date=analysis.get('latest_saldo_date')
        )
        md.extend(header_lines)
        
        # Abschnitt 2: Dokumententabelle
        doc_table_lines = self.generate_document_table(analysis['account_path'], analysis['account_info'])
        md.extend(doc_table_lines)
        
        # Abschnitt 3: Kontobewegungen Gesamt
        md.append(f"\n## Kontobewegungen Gesamt\n")
        md.append(f"- **Gesamteingänge:** {analysis['total_eingaenge']:,.2f} EUR")
        md.append(f"- **Gesamtausgänge:** {analysis['total_ausgaenge']:,.2f} EUR")
        md.append(f"- **Differenz:** {(analysis['total_eingaenge'] - analysis['total_ausgaenge']):,.2f} EUR\n")
        
        # Abschnitt 4: Dokumenttypen
        md.append(f"\n## Dokumenttypen\n")
        for doc_type, count in analysis['statistics'].items():
            md.append(f"- **{doc_type}:** {count}")
        
        # Abschnitt 5: Monatliche Übersicht
        if analysis['monthly_data']:
            md.append(f"\n## Monatliche Übersicht\n")
            md.append("| Monat | Eingänge (EUR) | Ausgänge (EUR) | Saldo (EUR) | Anzahl Docs |")
            md.append("|-------|----------------|----------------|-------------|-------------|")
            
            for month in sorted(analysis['monthly_data'].keys()):
                data = analysis['monthly_data'][month]
                eingaenge = data['eingaenge']
                ausgaenge = data['ausgaenge']
                saldo = data.get('saldo', 0)
                count = data['count']
                
                saldo_str = f"{saldo:,.2f}" if saldo else "N/A"
                md.append(f"| {month} | {eingaenge:,.2f} | {ausgaenge:,.2f} | {saldo_str} | {count} |")
            
            # Zusammenfassung
            months = list(analysis['monthly_data'].keys())
            if months:
                first_month = min(months)
                last_month = max(months)
                md.append(f"\n*Gesamt: {len(months)} Monate ({first_month} bis {last_month})*")
        
        # Abschnitt 6: Dokumentenübersicht
        md.append(f"\n## Dokumentenanalyse\n")
        md.append("| Datum | Typ | Bewegungen | Saldo (EUR) | Beschreibung |")
        md.append("|-------|-----|------------|-------------|--------------|")
        
        for trans in analysis['transactions']:
            date = trans['date'] if trans['date'] else 'N/A'
            trans_type = trans['type']
            bewegungen = trans['anzahl_bewegungen']
            saldo = f"{trans['saldo']:,.2f}" if trans['saldo'] else 'N/A'
            desc = trans['description_german']
            
            md.append(f"| {date} | {trans_type} | {bewegungen} | {saldo} | {desc} |")
        
        # Zusammenfassung
        md.append(f"\n*Gesamt: {len(analysis['transactions'])} analysierte Dokumente*")
        
        # Abschnitt 7: Jahresübersicht
        yearly_data = calculate_yearly_aggregates(analysis['transactions'])
        if yearly_data:
            md.append(f"\n## Jahresübersicht\n")
            md.append("| Jahr | Eingänge (EUR) | Ausgänge (EUR) | Differenz (EUR) | Dokumente |")
            md.append("|------|----------------|----------------|-----------------|-----------|")
            
            for year in sorted(yearly_data.keys()):
                data = yearly_data[year]
                eingaenge = data['eingaenge']
                ausgaenge = data['ausgaenge']
                differenz = eingaenge - ausgaenge
                count = data['count']
                
                md.append(f"| {year} | {eingaenge:,.2f} | {ausgaenge:,.2f} | {differenz:,.2f} | {count} |")
            
            # Zusammenfassung
            years = list(yearly_data.keys())
            if years:
                first_year = min(years)
                last_year = max(years)
                total_docs = sum(data['count'] for data in yearly_data.values())
                md.append(f"\n*Gesamt: {len(years)} Jahre ({first_year}-{last_year}), {total_docs} Dokumente*")
        
        return '\n'.join(md)
    
    def run(self):
        """Hauptfunktion - analysiert beide Girokonten und generiert Markdown-Dateien"""
        for account_name in self.accounts.keys():
            print(f"\nAnalysiere {account_name} Girokonto...")
            analysis = self.analyze_account(account_name)
            
            if analysis:
                markdown_content = self.generate_markdown(analysis)
                output_file = self.accounts[account_name]['output_file']
                
                self.save_markdown(markdown_content, output_file)
                self.print_summary(output_file, analysis)
            else:
                print(f"✗ Fehler bei der Analyse von {account_name}")

if __name__ == "__main__":
    analyzer = GirokontoAnalyzer()
    analyzer.run()