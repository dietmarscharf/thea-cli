#!/usr/bin/env python3
"""
Depotkonto.py - Analyse und Markdown-Generierung für Depotkonten
Verarbeitet BLUEITS-Depotkonto-7274079 und Ramteid-Depotkonto-7274087
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Any
from collections import defaultdict

from Konten import BaseKontoAnalyzer, calculate_monthly_aggregates


def format_date_german(date_str: str) -> str:
    """Konvertiert ISO-Datum (YYYY-MM-DD) in deutsches Format (DD.MM.YYYY)"""
    if not date_str or date_str == 'N/A':
        return 'N/A'
    try:
        parts = date_str.split('-')
        if len(parts) == 3:
            return f"{parts[2]}.{parts[1]}.{parts[0]}"
    except:
        pass
    return date_str


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
    
    def extract_trading_details(self, text: str) -> Dict[str, Any]:
        """Extrahiert detaillierte Handelsinformationen aus Orderabrechnungen"""
        details = {
            'shares': None,
            'execution_price': None,
            'execution_price_min': None,
            'execution_price_max': None,
            'execution_price_avg': None,
            'limit_price': None,
            'gross_amount': None,
            'fees': None,
            'profit_loss': None,
            'net_amount': None
        }
        
        # Extrahiere Stückzahl
        shares_match = re.search(r'Stück\s+(\d+)', text)
        if shares_match:
            details['shares'] = int(shares_match.group(1))
        
        # Extrahiere Limit (falls vorhanden)
        limit_match = re.search(r'Limit\s+([\d.,]+)\s*EUR', text)
        if limit_match:
            details['limit_price'] = float(limit_match.group(1).replace('.', '').replace(',', '.'))
        
        # Extrahiere Ausführungskurs(e) und dedupliziere
        exec_prices = re.findall(r'Ausführungskurs\s+([\d.,]+)\s*EUR', text)
        if exec_prices:
            # Konvertiere und dedupliziere Kurse
            prices = list(set([float(p.replace('.', '').replace(',', '.')) for p in exec_prices]))
            prices.sort()  # Sortiere für konsistente Min/Max
            
            if len(prices) == 1:
                details['execution_price'] = prices[0]
            else:
                # Nur bei tatsächlich verschiedenen Kursen
                details['execution_price_min'] = prices[0]
                details['execution_price_max'] = prices[-1]
                details['execution_price_avg'] = sum(prices) / len(prices)
        
        # Extrahiere Kurswert (Brutto)
        kurswert_match = re.search(r'Kurswert\s+([\d.,]+)[\s-]*EUR', text)
        if kurswert_match:
            details['gross_amount'] = float(kurswert_match.group(1).replace('.', '').replace(',', '.'))
        
        # Extrahiere Provision/Gebühren
        provision_match = re.search(r'Provision\s+([\d.,]+)[\s-]*EUR', text)
        if provision_match:
            details['fees'] = float(provision_match.group(1).replace('.', '').replace(',', '.'))
        
        # Extrahiere Veräußerungsgewinn/Verlust
        gewinn_match = re.search(r'Veräußerungsgewinn\s+([-]?[\d.,]+)\s*EUR', text)
        if gewinn_match:
            details['profit_loss'] = float(gewinn_match.group(1).replace('.', '').replace(',', '.'))
        else:
            # Alternativ: Veräußerungsverlust
            verlust_match = re.search(r'Veräußerungsverlust\s+([-]?[\d.,]+)\s*EUR', text)
            if verlust_match:
                details['profit_loss'] = -float(verlust_match.group(1).replace('.', '').replace(',', '.'))
        
        # Extrahiere Ausmachender Betrag (Netto)
        ausmachend_match = re.search(r'Ausmachender Betrag\s+([\d.,]+)\s*EUR', text)
        if ausmachend_match:
            details['net_amount'] = float(ausmachend_match.group(1).replace('.', '').replace(',', '.'))
        
        return details
    
    def extract_transaction_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Extrahiert depot-spezifische Transaktionsdaten"""
        base_data = self.get_base_transaction_data(data)
        if not base_data:
            return None
            
        extracted_text = base_data['extracted_text']
        
        # Extrahiere ISIN
        isin_match = re.search(r'([A-Z]{2}[A-Z0-9]{10})', extracted_text)
        isin = isin_match.group(1) if isin_match else None
        
        # Extrahiere detaillierte Handelsdaten
        trading_details = self.extract_trading_details(extracted_text)
        
        # Fallback auf alte Methode für Kompatibilität
        amounts = self.extract_amounts_from_text(extracted_text)
        
        # Bestimme Transaktionstyp und Periode
        transaction_type = 'Unbekannt'
        period = None
        extracted_lower = extracted_text.lower()
        filename_lower = base_data.get('original_file', '').lower()
        date_str = base_data.get('date', '')
        
        # Check for depot statements (various formats)
        if any(term in extracted_lower for term in ['depotabschluss', 'jahresabschluss', 'jahresdepotauszug', 'depotauszug', 'ex-post-rep']):
            # Determine if annual or quarterly
            if 'jahresabschluss' in extracted_lower or 'jahres' in extracted_lower:
                transaction_type = 'Depotabschluss-Jahresabschluss'
                period = 'Jährlich'
            elif date_str and len(date_str) >= 7:
                month = int(date_str[5:7]) if date_str[5:7].isdigit() else 0
                if month == 1:
                    transaction_type = 'Depotabschluss-Jahresabschluss'
                    period = 'Jährlich'
                elif month in [4, 5]:
                    transaction_type = 'Depotabschluss-Quartal'
                    period = 'Q1'
                elif month == 7:
                    transaction_type = 'Depotabschluss-Quartal'
                    period = 'Q2'
                elif month == 10:
                    transaction_type = 'Depotabschluss-Quartal'
                    period = 'Q3'
                else:
                    transaction_type = 'Depotabschluss'
            else:
                transaction_type = 'Depotabschluss'
        # Fallback: check filename for depot statement indicators
        elif any(term in filename_lower for term in ['depotabschluss', 'ex-post-rep', 'jahresabschluss']):
            if 'jahresabschluss' in filename_lower:
                transaction_type = 'Depotabschluss-Jahresabschluss'
                period = 'Jährlich'
            else:
                transaction_type = 'Depotabschluss'
        # Check for Orderabrechnung/Wertpapierabrechnung
        elif 'orderabrechnung' in filename_lower or 'wertpapier' in extracted_lower:
            # Determine if buy or sell
            if 'verkauf' in extracted_lower or 'sell' in extracted_lower:
                transaction_type = 'Orderabrechnung-Verkauf'
            elif 'kauf' in extracted_lower or 'buy' in extracted_lower or 'erwerb' in extracted_lower:
                transaction_type = 'Orderabrechnung-Kauf'
            else:
                # Try to detect from "Wertpapier Abrechnung" header
                if 'wertpapier abrechnung verkauf' in extracted_lower:
                    transaction_type = 'Orderabrechnung-Verkauf'
                elif 'wertpapier abrechnung kauf' in extracted_lower:
                    transaction_type = 'Orderabrechnung-Kauf'
                else:
                    transaction_type = 'Orderabrechnung'
        # Standard buy/sell detection  
        elif 'verkauf' in extracted_lower or 'sell' in extracted_lower:
            transaction_type = 'Verkauf'
        elif 'kauf' in extracted_lower or 'buy' in extracted_lower or 'erwerb' in extracted_lower:
            transaction_type = 'Kauf'
            
        # Special handling for failed extractions
        if transaction_type == 'Unbekannt':
            # Check if it's a failed Orderabrechnung based on filename
            if 'orderabrechnung' in filename_lower:
                transaction_type = 'Orderabrechnung-Fehlgeschlagen'
            
        # Kombiniere alle Daten
        result = {
            **base_data,
            'type': transaction_type,
            'period': period,
            'isin': isin,
            'amounts': amounts,
            'max_amount': max(amounts) if amounts else 0,
            # Neue detaillierte Handelsdaten
            **trading_details
        }
        
        # Verwende net_amount als max_amount wenn verfügbar (genauer)
        if trading_details.get('net_amount'):
            result['max_amount'] = trading_details['net_amount']
        elif trading_details.get('gross_amount'):
            result['max_amount'] = trading_details['gross_amount']
            
        return result
    
    def detect_document_type(self, extracted_text: str) -> str:
        """Erkennt den Dokumenttyp basierend auf Inhalt"""
        text_lower = extracted_text.lower()
        
        # Kosteninformation - diese werden oft fälschlicherweise als Depotabschluss benannt
        if 'information über kosten' in text_lower or 'kosteninformation' in text_lower:
            return 'cost_information'
        
        # Depotabschluss
        if 'depotabschluss' in text_lower or 'ex-post' in text_lower:
            # Prüfe ob es ein echter Depotabschluss mit Bestand ist
            if 'summe kurswerte' in text_lower or 'depotbestand' in text_lower or 'stück' in text_lower:
                return 'depot_statement'
            elif 'kein bestand vorhanden' in text_lower:
                return 'depot_statement_empty'
            else:
                # Zusätzliche Prüfung für versteckte Kosteninformationen
                if 'kosten' in text_lower and 'nebenkosten' in text_lower:
                    return 'cost_information'
                return 'depot_statement'
        
        return 'unknown'
    
    def extract_depot_balance(self, depot_path: Path) -> Dict[str, Any]:
        """Extrahiert Depot-Salden aus Depotabschluss-Dokumenten"""
        depot_statements = []
        cost_information_docs = []  # Separate Liste für Kosteninformationen
        latest_balance = None
        latest_balance_date = None
        
        # Finde alle Depotabschluss-Dateien
        for thea_file in depot_path.glob("*Depotabschluss*.thea_extract"):
            data = self.load_thea_extract(thea_file)
            if data:
                extracted_text = data.get('response', {}).get('json', {}).get('extracted_text', '')
                file_path = data.get('metadata', {}).get('file', {}).get('pdf_path', '')
                file_name = os.path.basename(file_path)
                doc_date = self.extract_date_from_filename(file_name)
                
                # Erkenne Dokumenttyp
                doc_type = self.detect_document_type(extracted_text)
                
                # Überspringe Kosteninformationen für Depot-Tabelle
                if doc_type == 'cost_information':
                    cost_information_docs.append({
                        'doc_date': doc_date,
                        'file': file_name,
                        'pdf_path': file_path,
                        'type': 'cost_information'
                    })
                    continue  # Nicht in Depot-Statements aufnehmen
                
                # Extrahiere das tatsächliche Stichtagsdatum (z.B. "per 31.12.2021")
                balance_date = None
                balance_date_match = re.search(r'per\s+(\d{1,2})\.(\d{1,2})\.(\d{4})', extracted_text)
                if balance_date_match:
                    day, month, year = balance_date_match.groups()
                    balance_date = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
                
                # Bestimme ob Jahres- oder Quartalsabschluss basierend auf Stichtag
                if balance_date:
                    month = int(balance_date[5:7])
                    # Jahresabschlüsse sind immer zum 31.12.
                    statement_type = 'annual' if month == 12 else 'quarterly'
                else:
                    # Fallback auf Dokumentdatum
                    statement_type = 'annual' if doc_date and doc_date[5:7] == '01' else 'quarterly'
                
                # Extrahiere Depotbestand (Closing Balance)
                closing_balance = None
                
                # Extrahiere Stückzahl und ISIN
                shares = None
                isin = None
                security_name = None
                
                # Spezielle Prüfung für "kein Bestand vorhanden"
                if re.search(r'kein\s+Bestand\s+vorhanden', extracted_text, re.IGNORECASE):
                    closing_balance = 0.0
                    shares = None
                    isin = None
                else:
                    # Verbesserte Suche nach Kurswert in Tabellen mit verschiedenen Formatierungen
                    # Spezieller Fall für Tabellenlayout wo "Summe Kurswerte" in einer Spalte und Betrag in anderer ist
                    if 'Summe Kurswerte' in extracted_text or 'Summe' in extracted_text:
                        lines = extracted_text.split('\n')
                        for i, line in enumerate(lines):
                            if 'Summe Kurswerte' in line or ('Summe' in line and '|' in line):
                                # Extrahiere alle Zahlen aus der aktuellen Zeile (deutsche Formatierung mit . als Tausendertrennzeichen)
                                numbers = re.findall(r'[\d]{1,3}(?:\.[\d]{3})*,[\d]{2}', line)
                                # Nimm den größten Wert (der Depotbestand, nicht die Stückzahl)
                                largest_value = 0
                                for num in numbers:
                                    # Konvertiere deutsches in Python-Format
                                    balance_str = num.replace('.', '').replace(',', '.')
                                    try:
                                        test_balance = float(balance_str)
                                        # Nimm den größten Wert, der mindestens 5000 EUR ist
                                        # (um kleine Stückzahlen zu vermeiden, aber erlaubt kleinere Depots)
                                        if test_balance > largest_value and test_balance > 5000:
                                            largest_value = test_balance
                                    except ValueError:
                                        pass
                                
                                # Wenn kein Wert in der gleichen Zeile gefunden, prüfe die nächste Zeile (multi-row table format)
                                if largest_value == 0 and i + 1 < len(lines):
                                    next_line = lines[i + 1]
                                    # Suche nach Werten in der nächsten Zeile (für multi-row tables)
                                    numbers_next = re.findall(r'[\d]{1,3}(?:\.[\d]{3})*,[\d]{2}', next_line)
                                    for num in numbers_next:
                                        balance_str = num.replace('.', '').replace(',', '.')
                                        try:
                                            test_balance = float(balance_str)
                                            # Akzeptiere auch kleinere Werte in multi-row format (min 1000 EUR)
                                            if test_balance > largest_value and test_balance > 1000:
                                                largest_value = test_balance
                                        except ValueError:
                                            pass
                                
                                if largest_value > 0:
                                    closing_balance = largest_value
                                    break
                                if closing_balance and closing_balance > 0:
                                    break
                    
                    # Fallback auf Pattern-Matching
                    if closing_balance is None:
                        kurswert_patterns = [
                            r'Summe\s+Kurswerte\s*\|\s*([+-]?[\d.,]+)',  # Mit Tabellen-Separator
                            r'Summe\s+([+-]?[\d.,]+)',  # Summe gefolgt von Zahl
                            r'([+-]?[\d.,]+)\s*\|\s*$',  # Zahl am Ende einer Tabellenzeile
                            r'Summe\s+Kurswerte\s*([+-]?[\d.,]+)',
                            r'Kurswert\s+in\s+EUR[^\d]*([+-]?[\d.,]+)',  # Kurswert in EUR
                            r'Kurswert.*?([+-]?[\d.,]+)\s*(?:EUR|€)',  # Kurswert mit Betrag
                        ]
                        
                        for pattern in kurswert_patterns:
                            # Suche nach allen Matches, nicht nur dem ersten
                            matches = re.findall(pattern, extracted_text, re.IGNORECASE)
                            if matches:
                                largest_value = 0
                                for match_str in matches:
                                    balance_str = match_str.replace('.', '').replace(',', '.')
                                    try:
                                        test_balance = float(balance_str)
                                        # Nimm den größten Wert über 5000 EUR
                                        if test_balance > largest_value and test_balance > 5000:
                                            largest_value = test_balance
                                    except ValueError:
                                        pass
                                if largest_value > 0:
                                    closing_balance = largest_value
                                    break
                    
                    # Fallback auf andere Balance-Muster
                    if closing_balance is None:
                        closing_patterns = [
                            r'Depotbestand[:\s]+([+-]?[\d.,]+)\s*(?:EUR|€)',
                            r'Durchschnittsdepotbestand[:\s]+([+-]?[\d.,]+)\s*(?:EUR|€)',
                            r'bewerteten?\s+Durchschnittsdepotbestand[:\s]+(?:in Höhe von\s+)?([+-]?[\d.,]+)\s*(?:EUR|Euro|€)',
                            r'Endsaldo[:\s]+([+-]?[\d.,]+)\s*(?:EUR|€)',
                        ]
                        
                        for pattern in closing_patterns:
                            match = re.search(pattern, extracted_text, re.IGNORECASE)
                            if match:
                                balance_str = match.group(1).replace('.', '').replace(',', '.')
                                try:
                                    closing_balance = float(balance_str)
                                    if closing_balance > 0:
                                        break
                                except ValueError:
                                    pass
                
                # Default zu 0 wenn nichts gefunden
                if closing_balance is None:
                    closing_balance = 0.0
                
                # Extrahiere Stückzahl und ISIN wenn Bestand vorhanden
                if closing_balance and closing_balance > 0:
                    # Spezialbehandlung für vertikales Layout (Stück auf eigener Zeile)
                    if 'Stück' in extracted_text and shares is None:
                        # Suche nach "Stück" und dann die nächste Zahl
                        lines = extracted_text.split('\n')
                        for i, line in enumerate(lines):
                            if 'Stück' in line:
                                # Schaue in den nächsten 5 Zeilen nach einer Zahl
                                for j in range(i+1, min(i+6, len(lines))):
                                    # Deutsche Zahlenformatierung: 1.300 = 1300
                                    number_match = re.search(r'^\s*([\d.]+)\s*$', lines[j])
                                    if number_match:
                                        number_str = number_match.group(1).replace('.', '')
                                        try:
                                            test_shares = int(number_str)
                                            if 100 <= test_shares <= 10000:  # Plausible Range
                                                shares = test_shares
                                                break
                                        except ValueError:
                                            pass
                                if shares:
                                    break
                    
                    # Fallback auf andere Patterns wenn noch keine Stückzahl gefunden
                    if shares is None:
                        shares_patterns = [
                            # Markdown Tabellen mit | Trennzeichen und deutscher Zahlenformatierung
                            r'\|\s*Stück\s*\|\s*([\d.,]+)',  # | Stück | 1.300 oder | Stück | 1,300
                            # Standard Tabellen mit | Trennzeichen
                            r'\|\s*Stück\s*\|\s*(\d+)',  # | Stück | 950
                            r'Stück\s+\|\s+([\d.,]+)',   # Stück | 1.300
                            r'Stück\s+\|\s+(\d+)',        # Stück | 950
                            
                            # Tabellen ohne Trennzeichen
                            r'Stück\s+(\d+)(?:\s|$)',     # Stück 950
                            r'(\d+)\s+Stück',              # 950 Stück
                            
                            # In Zeilen mit TESLA
                            r'TESLA[^\n]*?(\d{2,4})\s+Stück',
                            r'TESLA[^\n]*?Stück\s+(\d{2,4})',
                            
                            # Mit ISIN - removed to avoid capturing dates
                            # r'US88160R1014[^\n]*?(\d{3,4})\s+',
                            r'US88160R1014[^\n]*?Stück\s+(\d{2,4})',
                            
                            # Spezielle Formate
                            r'Bestand:\s*(\d+)\s+Stück',
                            r'Anzahl:\s*(\d+)',
                            r'Position[^\n]*?(\d{3,4})\s+Stück',
                        ]
                        
                        for pattern in shares_patterns:
                            matches = re.findall(pattern, extracted_text)
                            if matches:
                                # Bei mehreren Matches, nimm den größten plausiblen Wert
                                for match in matches:
                                    # Handle German number formatting (1.300 = 1300)
                                    number_str = match.replace('.', '').replace(',', '')
                                    try:
                                        test_shares = int(number_str)
                                        # Exclude year-like numbers (2020-2030) and use plausible share range
                                        if 10 <= test_shares <= 10000 and not (2020 <= test_shares <= 2030):
                                            shares = test_shares
                                            break
                                    except ValueError:
                                        pass
                                if shares:
                                    break
                    
                    # Extrahiere ISIN
                    isin_match = re.search(r'([A-Z]{2}[A-Z0-9]{10})', extracted_text)
                    if isin_match:
                        isin = isin_match.group(1)
                        
                    # Extrahiere Wertpapiername (optional)
                    if isin == 'US88160R1014':
                        security_name = 'TESLA INC'
                
                depot_statements.append({
                    'doc_date': doc_date,
                    'balance_date': balance_date if balance_date else doc_date,
                    'closing_balance': closing_balance,
                    'shares': shares,
                    'isin': isin,
                    'security_name': security_name,
                    'file': file_name,
                    'type': statement_type,
                    'pdf_path': file_path
                })
                
                # Aktualisiere letzten Saldo basierend auf Stichtag
                check_date = balance_date if balance_date else doc_date
                if closing_balance > 0:  # Nur positive Salden berücksichtigen
                    if not latest_balance_date or (check_date and check_date > latest_balance_date):
                        latest_balance = closing_balance
                        latest_balance_date = check_date
        
        # Sortiere Statements nach Stichtag
        depot_statements.sort(key=lambda x: x['balance_date'] if x['balance_date'] else '0000-00-00')
        
        # Separiere Jahres- und Quartalsabschlüsse und sortiere nach Stichtag
        annual_statements = [s for s in depot_statements if s['type'] == 'annual']
        annual_statements.sort(key=lambda x: x['balance_date'] if x['balance_date'] else '0000-00-00')
        
        quarterly_statements = [s for s in depot_statements if s['type'] == 'quarterly']
        quarterly_statements.sort(key=lambda x: x['balance_date'] if x['balance_date'] else '0000-00-00')
        
        # Log wenn Kosteninformationen gefunden wurden
        if cost_information_docs:
            print(f"  Info: {len(cost_information_docs)} Kosteninformations-Dokumente gefunden (werden nicht in Depot-Tabelle aufgenommen)")
        
        return {
            'statements': depot_statements,
            'annual_statements': annual_statements,
            'quarterly_statements': quarterly_statements,
            'cost_information_docs': cost_information_docs,  # Füge Kosteninformationen separat hinzu
            'latest_balance': latest_balance,
            'latest_balance_date': latest_balance_date
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
        
        # Extrahiere Depot-Salden
        balance_info = self.extract_depot_balance(depot_path)
        
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
            'depot_info': depot_info,
            'depot_statements': balance_info['statements'],
            'annual_statements': balance_info['annual_statements'],
            'quarterly_statements': balance_info['quarterly_statements'],
            'latest_balance': balance_info['latest_balance'],
            'latest_balance_date': balance_info['latest_balance_date']
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
            total_thea_files=analysis['total_thea_files'],
            latest_saldo=analysis.get('latest_balance'),
            latest_saldo_date=format_date_german(analysis.get('latest_balance_date')) if analysis.get('latest_balance_date') else None
        )
        md.extend(header_lines)
        
        # Abschnitt 2: Depotabschluss-Übersicht (MOVED BEFORE DOCUMENT TABLE)
        if analysis.get('depot_statements'):
            md.append(f"\n## Depotabschluss-Übersicht\n")
            
            # Kombiniere Jahres- und Quartalsabschlüsse
            all_statements = []
            
            # Füge Jahresabschlüsse hinzu mit Typ-Markierung
            for statement in analysis.get('annual_statements', []):
                statement_copy = statement.copy()
                statement_copy['type_display'] = 'Jahresabschluss'
                all_statements.append(statement_copy)
            
            # Füge Quartalsabschlüsse hinzu mit Typ-Markierung
            for statement in analysis.get('quarterly_statements', []):
                statement_copy = statement.copy()
                statement_copy['type_display'] = 'Quartalsabschluss'
                all_statements.append(statement_copy)
            
            # Sortiere alle Statements chronologisch nach Stichtag
            all_statements.sort(key=lambda x: x['balance_date'] if x['balance_date'] else '0000-00-00')
            
            if all_statements:
                md.append("### Alle Depotabschlüsse (chronologisch)")
                md.append("| Typ | Stichtag | Dokumentdatum | Stück | ISIN | Depotbestand (EUR) | Dokument |")
                md.append("|-----|----------|---------------|-------|------|-------------------|----------|")
                
                for statement in all_statements:
                    # Bestimme Typ-Anzeige
                    type_display = statement['type_display']
                    
                    # Konvertiere Daten ins deutsche Format
                    doc_date = format_date_german(statement['doc_date'] if statement.get('doc_date') else 'N/A')
                    balance_date = format_date_german(statement['balance_date'] if statement.get('balance_date') else 'N/A')
                    
                    # Formatiere Stück und ISIN
                    shares_str = str(statement['shares']) if statement.get('shares') else '-'
                    isin_str = statement['isin'] if statement.get('isin') else '-'
                    
                    # Formatiere Depotbestand mit deutschem Tausendertrennzeichen
                    if statement.get('closing_balance') is not None:
                        closing = f"{statement['closing_balance']:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
                    else:
                        closing = 'N/A'
                    
                    # Kürze den Dateinamen für die Anzeige
                    file_name = statement['file']
                    if len(file_name) > 40:
                        display_name = file_name[:37] + '...'
                    else:
                        display_name = file_name
                    # Erstelle Link zum Dokument
                    doc_link = f"[{display_name}](docs/{analysis['depot_info']['folder']}/{file_name})"
                    md.append(f"| {type_display} | {balance_date} | {doc_date} | {shares_str} | {isin_str} | {closing} | {doc_link} |")
                
                # Zusammenfassung
                annual_count = len(analysis.get('annual_statements', []))
                quarterly_count = len(analysis.get('quarterly_statements', []))
                md.append(f"\n*Gesamt: {annual_count} Jahresabschlüsse und {quarterly_count} Quartalsabschlüsse*\n")
            
            # Gesamtzusammenfassung
            if analysis.get('latest_balance'):
                latest_date = format_date_german(analysis.get('latest_balance_date', 'N/A'))
                latest_balance_str = f"{analysis['latest_balance']:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
                md.append(f"\n**Letzter bekannter Depotbestand: {latest_balance_str} EUR** (Stand: {latest_date})")
            
            total_statements = len(analysis.get('depot_statements', []))
            if total_statements > 0:
                first_date = min(s['balance_date'] for s in analysis['depot_statements'] if s.get('balance_date'))
                last_date = max(s['balance_date'] for s in analysis['depot_statements'] if s.get('balance_date'))
                first_date_german = format_date_german(first_date)
                last_date_german = format_date_german(last_date)
                md.append(f"*Gesamtzeitraum: {first_date_german} bis {last_date_german}*")
        
        # Abschnitt 3: Dokumententabelle (MOVED AFTER DEPOT OVERVIEW)
        doc_table_lines = self.generate_document_table(analysis['depot_path'], analysis['depot_info'])
        md.extend(doc_table_lines)
        
        # Abschnitt 4: Transaktionsstatistik
        md.append(f"\n## Transaktionsstatistik\n")
        
        # Gruppiere nach Hauptkategorie für bessere Übersicht
        categories = {
            'Depotabschluss': [],
            'Orderabrechnung': [],
            'Sonstige': []
        }
        
        for trans_type, count in sorted(analysis['statistics'].items()):
            if 'Depotabschluss' in trans_type:
                categories['Depotabschluss'].append((trans_type, count))
            elif 'Orderabrechnung' in trans_type:
                categories['Orderabrechnung'].append((trans_type, count))
            else:
                categories['Sonstige'].append((trans_type, count))
        
        # Zeige Depotabschluss-Kategorien
        if categories['Depotabschluss']:
            md.append("### Depotabschlüsse")
            for trans_type, count in categories['Depotabschluss']:
                display_type = trans_type.replace('Depotabschluss-', '')
                md.append(f"- **{display_type}:** {count}")
        
        # Zeige Orderabrechnung-Kategorien
        if categories['Orderabrechnung']:
            md.append("\n### Orderabrechnungen")
            for trans_type, count in categories['Orderabrechnung']:
                display_type = trans_type.replace('Orderabrechnung-', '')
                md.append(f"- **{display_type}:** {count}")
        
        # Zeige sonstige Kategorien
        if categories['Sonstige']:
            md.append("\n### Sonstige")
            for trans_type, count in categories['Sonstige']:
                md.append(f"- **{trans_type}:** {count}")
        
        # Warnung für fehlgeschlagene Extraktionen
        failed_count = analysis['statistics'].get('Orderabrechnung-Fehlgeschlagen', 0)
        if failed_count > 0:
            md.append(f"\n⚠️ **Warnung: {failed_count} Orderabrechnungen konnten nicht vollständig extrahiert werden**")
            md.append("Diese Dokumente erfordern manuelle Überprüfung oder erneute Verarbeitung.")
        
        # Warnung für unbekannte Transaktionen
        if 'Unbekannt' in analysis['statistics'] and analysis['statistics']['Unbekannt'] > 0:
            unknown_count = analysis['statistics']['Unbekannt']
            md.append(f"\n⚠️ **Warnung: {unknown_count} Dokumente ohne Typ-Erkennung**")
        
        # Abschnitt 4: Wertpapiere nach ISIN
        if analysis['isin_groups']:
            md.append(f"\n## Wertpapiere (nach ISIN)\n")
            for isin, trans_list in analysis['isin_groups'].items():
                # Warnung für Test-ISINs
                if isin == "DE0001234567":
                    md.append(f"\n### ⚠️ {isin} (UNGÜLTIGE TEST-ISIN)")
                    md.append(f"- ⚠️ **WARNUNG: Dies ist eine Test-ISIN und sollte nicht in Produktivdaten vorkommen!**")
                else:
                    md.append(f"\n### {isin}")
                md.append(f"- **Anzahl Transaktionen:** {len(trans_list)}")
                
                # Berechne Summen
                verkauf_summe = sum(t['max_amount'] for t in trans_list if t['type'] == 'Verkauf')
                kauf_summe = sum(t['max_amount'] for t in trans_list if t['type'] == 'Kauf')
                
                if verkauf_summe > 0:
                    md.append(f"- **Verkaufssumme:** {verkauf_summe:,.2f} EUR")
                if kauf_summe > 0:
                    md.append(f"- **Kaufsumme:** {kauf_summe:,.2f} EUR")
        
        # Abschnitt 5: Detaillierter Transaktionsverlauf
        md.append(f"\n## Transaktionsverlauf (Detailliert)\n")
        md.append("| Datum | Typ | ISIN | Stück | Kurs/Aktie | Brutto (EUR) | Gebühren | Gewinn/Verlust | Netto (EUR) | Dokument |")
        md.append("|-------|-----|------|-------|------------|--------------|----------|----------------|-------------|----------|")
        
        for trans in analysis['transactions']:
            date = format_date_german(trans['date'] if trans['date'] else 'N/A')
            trans_type = trans['type']
            
            # Kürze den Transaktionstyp für bessere Lesbarkeit
            if 'Orderabrechnung-' in trans_type:
                display_type = trans_type.replace('Orderabrechnung-', '')
            elif 'Depotabschluss-' in trans_type:
                display_type = 'Depotabschluss'
            else:
                display_type = trans_type
            
            isin = trans['isin'] if trans['isin'] else 'N/A'
            
            # Handelsdaten formatieren
            shares = str(trans.get('shares', '')) if trans.get('shares') else '-'
            
            # Kurs/Aktie - bei mehreren Kursen zeige Spanne
            if trans.get('execution_price_min') and trans.get('execution_price_max'):
                # Teilausführungen mit mehreren Kursen
                price_str = f"{trans['execution_price_min']:.2f}-{trans['execution_price_max']:.2f} (⌀{trans['execution_price_avg']:.2f})"
            elif trans.get('execution_price'):
                price_str = f"{trans['execution_price']:.2f}"
            elif trans.get('limit_price'):
                price_str = f"Limit: {trans['limit_price']:.2f}"
            else:
                price_str = '-'
            
            # Brutto
            gross = f"{trans['gross_amount']:,.2f}" if trans.get('gross_amount') else '-'
            
            # Gebühren
            fees = f"-{trans['fees']:.2f}" if trans.get('fees') else '-'
            
            # Gewinn/Verlust
            if trans.get('profit_loss'):
                if trans['profit_loss'] > 0:
                    profit_loss = f"+{trans['profit_loss']:,.2f}"
                else:
                    profit_loss = f"{trans['profit_loss']:,.2f}"
            else:
                profit_loss = '-'
            
            # Netto (oder Fallback auf max_amount)
            if trans.get('net_amount'):
                net = f"{trans['net_amount']:,.2f}"
            elif trans.get('max_amount') and trans.get('max_amount') > 0:
                net = f"{trans['max_amount']:,.2f}"
            else:
                net = 'N/A'
            
            # Erstelle Link zum PDF-Dokument
            pdf_file = trans.get('original_file', '')
            if pdf_file:
                # Kürze den Dateinamen für die Anzeige, aber behalte die Erweiterung
                display_name = pdf_file
                if len(pdf_file) > 40:
                    display_name = pdf_file[:37] + '...'
                pdf_link = f"[{display_name}](docs/{analysis['depot_info']['folder']}/{pdf_file})"
            else:
                pdf_link = 'N/A'
            
            # Markiere Test-ISINs und erstelle Tabellenzeile
            if isin == "DE0001234567":
                isin_display = f"⚠️ **{isin}**"
            else:
                isin_display = isin
            
            # Erstelle die detaillierte Tabellenzeile
            md.append(f"| {date} | {display_type} | {isin_display} | {shares} | {price_str} | {gross} | {fees} | {profit_loss} | {net} | {pdf_link} |")
        
        # Zusammenfassung Transaktionsverlauf
        total_trans = len(analysis['transactions'])
        
        # Count different transaction types
        depotabschluss_count = sum(1 for t in analysis['transactions'] if 'Depotabschluss' in t['type'])
        orderabrechnung_count = sum(1 for t in analysis['transactions'] if 'Orderabrechnung' in t['type'])
        verkauf_count = sum(1 for t in analysis['transactions'] if t['type'] == 'Verkauf')
        kauf_count = sum(1 for t in analysis['transactions'] if t['type'] == 'Kauf')
        unknown_count = sum(1 for t in analysis['transactions'] if t['type'] == 'Unbekannt')
        failed_count = sum(1 for t in analysis['transactions'] if 'Fehlgeschlagen' in t['type'])
        
        md.append(f"\n*Gesamt: {total_trans} Transaktionen*")
        if depotabschluss_count > 0:
            md.append(f"*- Depotabschlüsse: {depotabschluss_count}*")
        if orderabrechnung_count > 0:
            md.append(f"*- Orderabrechnungen: {orderabrechnung_count}*")
        if verkauf_count > 0:
            md.append(f"*- Verkäufe (sonstige): {verkauf_count}*")
        if kauf_count > 0:
            md.append(f"*- Käufe (sonstige): {kauf_count}*")
        if failed_count > 0:
            md.append(f"⚠️ **{failed_count} fehlgeschlagene Extraktionen**")
        if unknown_count > 0:
            md.append(f"⚠️ **{unknown_count} unbekannte Dokumente**")
        
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
            
            # Zusammenfassung
            if monthly_groups:
                months = list(monthly_groups.keys())
                first_month = min(months)
                last_month = max(months)
                total_years = len(set(m[:4] for m in months))
                md.append(f"\n*Aktivität in {len(months)} Monaten über {total_years} Jahre ({first_month} bis {last_month})*")
        
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