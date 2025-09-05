#!/usr/bin/env python3
"""
Geldmarktkonto.py - Analyse und Markdown-Generierung für Geldmarktkonten
Verarbeitet BLUEITS-Geldmarktkonto-21503990 und Ramteid-Geldmarktkonto-21504006
"""

import re
from pathlib import Path
from typing import Dict, List, Any
from collections import defaultdict

from Konten import BaseKontoAnalyzer, calculate_monthly_aggregates, calculate_yearly_aggregates


class GeldmarktkontoAnalyzer(BaseKontoAnalyzer):
    def __init__(self):
        super().__init__()
        self.accounts = {
            "BLUEITS": {
                "folder": "BLUEITS-Geldmarktkonto-21503990",
                "account_number": "21503990",
                "output_file": "BLUEITS-Geldmarktkonto.md",
                "company_name": "BLUEITS GmbH"
            },
            "Ramteid": {
                "folder": "Ramteid-Geldmarktkonto-21504006",
                "account_number": "21504006",
                "output_file": "Ramteid-Geldmarktkonto.md",
                "company_name": "Ramteid GmbH"
            }
        }
        
        # Erweitere das Mapping für Zinsdokumente
        self.doc_type_mapping['interest'] = 'Zinsabrechnung'
    
    def extract_transaction_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Extrahiert geldmarktkonto-spezifische Transaktionsdaten"""
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
        
        # Suche nach Zinssätzen
        zins_matches = re.findall(r'([\d,]+)\s*%', extracted_text)
        zinssaetze = [float(z.replace(',', '.')) for z in zins_matches]
        
        # Extrahiere Zinserträge
        zinsertrag = None
        zins_patterns = [
            r'Zinsen[\s:]+([+-]?[\d.]+,\d{2})',
            r'Zinsertrag[\s:]+([+-]?[\d.]+,\d{2})',
            r'Habenzinsen[\s:]+([+-]?[\d.]+,\d{2})'
        ]
        
        for pattern in zins_patterns:
            match = re.search(pattern, extracted_text)
            if match:
                zins_str = match.group(1).replace('.', '').replace(',', '.')
                zinsertrag = float(zins_str)
                break
        
        # Bestimme Transaktionstyp
        transaction_type = 'Kontoauszug'
        if 'Zinsabrechnung' in extracted_text:
            transaction_type = 'Zinsabrechnung'
        elif 'Kontoauszug' in extracted_text:
            transaction_type = 'Kontoauszug'
        elif 'Jahresabschluss' in extracted_text:
            transaction_type = 'Jahresabschluss'
        elif 'Gutschrift' in extracted_text:
            transaction_type = 'Gutschrift'
        elif 'Überweisung' in extracted_text:
            transaction_type = 'Überweisung'
            
        # Extrahiere Ein- und Ausgänge
        eingaenge = []
        ausgaenge = []
        
        # Analysiere Bewegungen basierend auf Schlüsselwörtern
        if 'Gutschrift' in extracted_text or 'Eingang' in extracted_text or 'Zinsen' in extracted_text:
            for amount in amounts[:3]:  # Erste 3 Beträge als potenzielle Eingänge
                if amount > 0 and amount < 1000000:  # Plausibilitätsprüfung
                    eingaenge.append(amount)
                    
        if 'Auszahlung' in extracted_text or ('Überweisung' in extracted_text and 'zu Lasten' in extracted_text):
            for amount in amounts[:3]:
                if amount > 0 and amount < 1000000:
                    ausgaenge.append(amount)
            
        return {
            **base_data,
            'type': transaction_type,
            'iban': iban,
            'amounts': amounts,
            'saldo': saldo,
            'zinssaetze': zinssaetze,
            'aktueller_zinssatz': max(zinssaetze) if zinssaetze else None,
            'zinsertrag': zinsertrag,
            'eingaenge': sum(eingaenge),
            'ausgaenge': sum(ausgaenge),
            'max_amount': max(amounts) if amounts else 0
        }
    
    def analyze_account(self, account_name: str) -> Dict[str, Any]:
        """Analysiert alle Dateien eines Geldmarktkontos"""
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
        monthly_data = defaultdict(lambda: {
            'eingaenge': 0, 
            'ausgaenge': 0, 
            'zinsertraege': 0,
            'count': 0,
            'saldo': None,
            'zinssatz': None
        })
        
        total_zinsertraege = 0
        
        for file_path in thea_files:
            data = self.load_thea_extract(file_path)
            if data:
                transaction = self.extract_transaction_data(data)
                if transaction:
                    transactions.append(transaction)
                    statistics[transaction['type']] += 1
                    
                    if transaction['zinsertrag']:
                        total_zinsertraege += transaction['zinsertrag']
                    
                    # Monatliche Aggregation
                    if transaction['date']:
                        month_key = transaction['date'][:7]
                        monthly_data[month_key]['eingaenge'] += transaction['eingaenge']
                        monthly_data[month_key]['ausgaenge'] += transaction['ausgaenge']
                        if transaction['zinsertrag']:
                            monthly_data[month_key]['zinsertraege'] += transaction['zinsertrag']
                        monthly_data[month_key]['count'] += 1
                        
                        if transaction['saldo']:
                            monthly_data[month_key]['saldo'] = transaction['saldo']
                        if transaction['aktueller_zinssatz']:
                            monthly_data[month_key]['zinssatz'] = transaction['aktueller_zinssatz']
        
        # Sortiere Transaktionen nach Datum
        transactions.sort(key=lambda x: x['date'] if x['date'] else '0000-00-00')
        
        # Berechne Gesamtstatistiken
        total_eingaenge = sum(t['eingaenge'] for t in transactions)
        total_ausgaenge = sum(t['ausgaenge'] for t in transactions)
        
        # Finde aktuellsten Zinssatz
        latest_zinssatz = None
        for trans in reversed(transactions):
            if trans['aktueller_zinssatz']:
                latest_zinssatz = trans['aktueller_zinssatz']
                break
        
        # Finde aktuellsten Saldo und Datum
        latest_saldo = None
        latest_saldo_date = None
        for trans in reversed(transactions):
            if trans['saldo']:
                latest_saldo = trans['saldo']
                latest_saldo_date = trans['date']
                break
        
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
            'total_zinsertraege': total_zinsertraege,
            'latest_zinssatz': latest_zinssatz,
            'latest_saldo': latest_saldo,
            'latest_saldo_date': latest_saldo_date,
            'account_path': account_path,
            'account_info': account_info
        }
    
    def generate_markdown(self, analysis: Dict[str, Any]) -> str:
        """Generiert Markdown-Bericht aus der Analyse"""
        if not analysis:
            return "# Fehler bei der Analyse\n\nKeine Daten verfügbar."
            
        md = []
        
        # Abschnitt 1: Firmen- und Kontoübersicht
        header_lines = self.generate_header_section(
            company_name=analysis['company_name'],
            account_type="Geldmarktkonto",
            account_number=analysis['account_number'],
            total_pdf_files=analysis['total_pdf_files'],
            total_thea_files=analysis['total_thea_files'],
            latest_saldo=analysis['latest_saldo'],
            latest_saldo_date=analysis.get('latest_saldo_date'),
            latest_zinssatz=analysis['latest_zinssatz']
        )
        md.extend(header_lines)
        
        # Abschnitt 2: Dokumententabelle
        doc_table_lines = self.generate_document_table(analysis['account_path'], analysis['account_info'])
        md.extend(doc_table_lines)
        
        # Abschnitt 3: Finanzdaten Gesamt
        md.append(f"\n## Finanzdaten Gesamt\n")
        md.append(f"- **Gesamteingänge:** {analysis['total_eingaenge']:,.2f} EUR")
        md.append(f"- **Gesamtausgänge:** {analysis['total_ausgaenge']:,.2f} EUR")
        md.append(f"- **Zinserträge gesamt:** {analysis['total_zinsertraege']:,.2f} EUR")
        md.append(f"- **Netto-Zufluss:** {(analysis['total_eingaenge'] - analysis['total_ausgaenge']):,.2f} EUR\n")
        
        # Abschnitt 4: Dokumenttypen
        md.append(f"\n## Dokumenttypen\n")
        for doc_type, count in analysis['statistics'].items():
            md.append(f"- **{doc_type}:** {count}")
        
        # Abschnitt 5: Monatliche Übersicht
        if analysis['monthly_data']:
            md.append(f"\n## Monatliche Übersicht\n")
            md.append("| Monat | Eingänge | Ausgänge | Zinserträge | Saldo | Zinssatz | Docs |")
            md.append("|-------|----------|----------|-------------|-------|----------|------|")
            
            for month in sorted(analysis['monthly_data'].keys()):
                data = analysis['monthly_data'][month]
                eingaenge = f"{data['eingaenge']:,.2f}" if data['eingaenge'] > 0 else "-"
                ausgaenge = f"{data['ausgaenge']:,.2f}" if data['ausgaenge'] > 0 else "-"
                zinsertraege = f"{data['zinsertraege']:,.2f}" if data['zinsertraege'] > 0 else "-"
                saldo = f"{data['saldo']:,.2f}" if data['saldo'] else "-"
                zinssatz = f"{data['zinssatz']:.2f}%" if data['zinssatz'] else "-"
                count = data['count']
                
                md.append(f"| {month} | {eingaenge} | {ausgaenge} | {zinsertraege} | {saldo} | {zinssatz} | {count} |")
            
            # Zusammenfassung
            months = list(analysis['monthly_data'].keys())
            if months:
                first_month = min(months)
                last_month = max(months)
                md.append(f"\n*Gesamt: {len(months)} Monate ({first_month} bis {last_month})*")
        
        # Abschnitt 6: Zinsanalyse
        zins_transactions = [t for t in analysis['transactions'] if t['zinsertrag'] and t['zinsertrag'] > 0]
        if zins_transactions:
            md.append(f"\n## Zinsanalyse\n")
            md.append("| Datum | Zinsertrag (EUR) | Zinssatz (%) | Beschreibung |")
            md.append("|-------|------------------|--------------|--------------|")
            
            for trans in zins_transactions:
                date = trans['date'] if trans['date'] else 'N/A'
                zinsertrag = f"{trans['zinsertrag']:,.2f}"
                zinssatz = f"{trans['aktueller_zinssatz']:.2f}" if trans['aktueller_zinssatz'] else "N/A"
                desc = trans['description_german']
                
                md.append(f"| {date} | {zinsertrag} | {zinssatz} | {desc} |")
            
            # Zusammenfassung
            total_zinsertrag = sum(t['zinsertrag'] for t in zins_transactions)
            md.append(f"\n*Gesamt: {len(zins_transactions)} Zinsbuchungen, Gesamtertrag: {total_zinsertrag:,.2f} EUR*")
        
        # Abschnitt 7: Jahresübersicht
        yearly_data = calculate_yearly_aggregates(analysis['transactions'])
        
        # Ergänze Zinserträge in yearly_data
        for trans in analysis['transactions']:
            if trans['date'] and trans['zinsertrag']:
                year = trans['date'][:4]
                if year not in yearly_data:
                    yearly_data[year] = {'eingaenge': 0, 'ausgaenge': 0, 'zinsertraege': 0, 'count': 0}
                yearly_data[year]['zinsertraege'] += trans['zinsertrag']
        
        if yearly_data:
            md.append(f"\n## Jahresübersicht\n")
            md.append("| Jahr | Eingänge | Ausgänge | Zinserträge | Netto | Dokumente |")
            md.append("|------|----------|----------|-------------|-------|-----------|")
            
            for year in sorted(yearly_data.keys()):
                data = yearly_data[year]
                eingaenge = f"{data['eingaenge']:,.2f}" if data['eingaenge'] > 0 else "-"
                ausgaenge = f"{data['ausgaenge']:,.2f}" if data['ausgaenge'] > 0 else "-"
                zinsertraege = f"{data.get('zinsertraege', 0):,.2f}" if data.get('zinsertraege', 0) > 0 else "-"
                netto = data['eingaenge'] - data['ausgaenge'] + data.get('zinsertraege', 0)
                netto_str = f"{netto:,.2f}"
                count = data['count']
                
                md.append(f"| {year} | {eingaenge} | {ausgaenge} | {zinsertraege} | {netto_str} | {count} |")
            
            # Zusammenfassung
            years = list(yearly_data.keys())
            if years:
                first_year = min(years)
                last_year = max(years)
                total_docs = sum(data['count'] for data in yearly_data.values())
                md.append(f"\n*Gesamt: {len(years)} Jahre ({first_year}-{last_year}), {total_docs} Dokumente*")
        
        # Abschnitt 8: Letzte Dokumente
        md.append(f"\n## Letzte Dokumente (max. 20)\n")
        md.append("| Datum | Typ | Saldo (EUR) | Zinssatz | Beschreibung |")
        md.append("|-------|-----|-------------|----------|--------------|")
        
        for trans in analysis['transactions'][-20:]:
            date = trans['date'] if trans['date'] else 'N/A'
            trans_type = trans['type']
            saldo = f"{trans['saldo']:,.2f}" if trans['saldo'] else 'N/A'
            zinssatz = f"{trans['aktueller_zinssatz']:.2f}%" if trans['aktueller_zinssatz'] else 'N/A'
            desc = trans['description_german']
            
            md.append(f"| {date} | {trans_type} | {saldo} | {zinssatz} | {desc} |")
        
        # Zusammenfassung
        shown = min(20, len(analysis['transactions']))
        total = len(analysis['transactions'])
        if shown < total:
            md.append(f"\n*Zeige die letzten {shown} von {total} Dokumenten*")
        else:
            md.append(f"\n*Gesamt: {total} Dokumente*")
        
        return '\n'.join(md)
    
    def run(self):
        """Hauptfunktion - analysiert beide Geldmarktkonten und generiert Markdown-Dateien"""
        for account_name in self.accounts.keys():
            print(f"\nAnalysiere {account_name} Geldmarktkonto...")
            analysis = self.analyze_account(account_name)
            
            if analysis:
                markdown_content = self.generate_markdown(analysis)
                output_file = self.accounts[account_name]['output_file']
                
                self.save_markdown(markdown_content, output_file)
                self.print_summary(output_file, analysis)
                print(f"  - Zinserträge gesamt: {analysis['total_zinsertraege']:,.2f} EUR")
                if analysis['latest_zinssatz']:
                    print(f"  - Aktueller Zinssatz: {analysis['latest_zinssatz']:.2f}%")
            else:
                print(f"✗ Fehler bei der Analyse von {account_name}")


if __name__ == "__main__":
    analyzer = GeldmarktkontoAnalyzer()
    analyzer.run()