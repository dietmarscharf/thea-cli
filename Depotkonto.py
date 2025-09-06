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
    
    def is_stock_isin(self, isin: str) -> bool:
        """
        Bestimmt ob eine ISIN eine Aktie oder ein Nicht-Aktien-Produkt ist.
        
        Aktien:
        - US88160R1014 (TESLA INC)
        - Weitere US-Aktien (US...)
        
        Nicht-Aktien (Derivate, Zertifikate, strukturierte Produkte):
        - DE000JN9UFS3 (J.P. Morgan Structured Product)
        - Andere strukturierte Produkte und Derivate
        """
        if not isin:
            return False
            
        # Tesla und andere US-Aktien sind Aktien
        if isin.startswith('US'):
            return True
            
        # DE-ISINs können Aktien oder Derivate sein
        # Bekannte Derivate/Zertifikate explizit als Nicht-Aktien markieren
        known_derivatives = [
            'DE000JN9UFS3',  # J.P. Morgan Structured Product
            # Weitere bekannte Derivate können hier hinzugefügt werden
        ]
        
        if isin in known_derivatives:
            return False
            
        # Standard: DE-ISINs als Aktien behandeln, außer sie sind als Derivate bekannt
        # Dies kann je nach Portfolio angepasst werden
        if isin.startswith('DE'):
            # Wenn nicht in der Liste der bekannten Derivate, als Aktie behandeln
            return isin not in known_derivatives
            
        # Andere Länder-ISINs (FR, GB, etc.) sind üblicherweise Aktien
        return True
    
    def extract_trading_details(self, text: str) -> Dict[str, Any]:
        """
        Extrahiert detaillierte Handelsinformationen aus Orderabrechnungen.
        
        Wichtige Hinweise zu Gebühren:
        - Viele Transaktionen haben legitim KEINE Gebühren (wenn Kurswert = Ausmachender Betrag)
        - Dies tritt häufig auf bei: Sparplänen, Aktionsangeboten, Teilausführungen
        - Typische Gebührenstruktur wenn vorhanden:
          * Provision: 0,25% - 1% des Ordervolumens
          * Handelsplatzgebühr: 2-5 EUR
          * Mindestgebühr: 8-10 EUR  
          * USt: 19% auf alle Gebühren (bereits in Gebührenbetrag enthalten)
        """
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
            'net_amount': None,
            'execution_date': None  # Neu: Explizites Ausführungsdatum
        }
        
        # Extrahiere Stückzahl (mit Unterstützung für deutsche Tausendertrennzeichen)
        shares_match = re.search(r'Stück\s+([\d.]+)', text)
        if shares_match:
            # Entferne deutsche Tausendertrennzeichen (Punkt) vor der Konvertierung
            shares_str = shares_match.group(1).replace('.', '')
            details['shares'] = int(shares_str)
        
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
        # Erweiterte Patterns für verschiedene Layouts
        kurswert_patterns = [
            r'Kurswert\s+([\d.,]+)[\s-]*EUR',  # Standard mit EUR
            r'Kurswert\s+([\d.,]+)\s*\n\s*EUR',  # EUR auf nächster Zeile
            r'Kurswert[\s\n]+([\d.,]+)',  # Ohne EUR-Anforderung
            r'Kurswert\s*\|\s*([\d.,]+)',  # Mit Pipe-Separator
        ]
        
        for pattern in kurswert_patterns:
            kurswert_match = re.search(pattern, text, re.MULTILINE | re.DOTALL)
            if kurswert_match:
                value_str = kurswert_match.group(1).replace('.', '').replace(',', '.')
                try:
                    value = float(value_str)
                    if value > 0:  # Plausibilitätsprüfung
                        details['gross_amount'] = value
                        break
                except ValueError:
                    continue
        
        # Extrahiere Provision/Gebühren mit erweiterten Patterns
        fee_patterns = [
            # Spezifische Gebührenarten
            r'Provision\s+([\d.,]+)[\s-]*EUR',
            r'Handelsplatzgebühr\s+([\d.,]+)[\s-]*EUR',
            r'Maklercourtage\s+([\d.,]+)[\s-]*EUR',
            r'Fremdspesen\s+([\d.,]+)[\s-]*EUR',
            r'Börsengebühr\s+([\d.,]+)[\s-]*EUR',
            r'Transaktionsentgelt\s+([\d.,]+)[\s-]*EUR',
            r'Orderprovision\s+([\d.,]+)[\s-]*EUR',
            # Summen und Gesamtbeträge
            r'Gebühren\s+gesamt\s+([\d.,]+)[\s-]*EUR',
            r'Summe\s+Gebühren\s+([\d.,]+)[\s-]*EUR',
            r'Provision\s+und\s+Gebühren\s+([\d.,]+)[\s-]*EUR',
            # Mit Pipe-Separator
            r'Provision\s*\|\s*([\d.,]+)\s*€',
            r'Gebühren\s*\|\s*([\d.,]+)\s*€',
            r'Handelsplatzgebühr\s*\|\s*([\d.,]+)\s*€',
            r'Summe\s*\|\s*([\d.,]+)\s*€',
            # Minus-Beträge (Gebühren als Abzug)
            r'[\-\s]+([\d.,]+)\s*EUR\s*(?:Provision|Gebühr)',
            r'Abzüge\s+([\d.,]+)\s*EUR',
            # Allgemeinere Patterns
            r'Gebühren[^\d]+([\d.,]+)\s*(?:EUR|€)',
            r'Entgelte[^\d]+([\d.,]+)\s*(?:EUR|€)',
            r'Kosten[^\d]+([\d.,]+)\s*(?:EUR|€)'
        ]
        
        total_fees = 0.0
        fees_found = []
        
        # Suche nach allen Gebührenposten und summiere sie
        for pattern in fee_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                fee_value = float(match.replace('.', '').replace(',', '.'))
                if fee_value > 0 and fee_value < 10000:  # Plausibilitätsprüfung
                    fees_found.append(fee_value)
        
        # Verwende die höchste gefundene Gebühr (wahrscheinlich die Summe)
        if fees_found:
            details['fees'] = max(fees_found)
        
        # Extrahiere Veräußerungsgewinn/Verlust mit erweiterten Patterns
        # Spezialbehandlung für vertikales Layout (Sparkasse-Format)
        vertical_layout_match = re.search(
            r'Ermittlung steuerrelevante Erträge\s+Veräußerungs(?:gewinn|verlust)\s+Ausmachender Betrag',
            text, re.IGNORECASE
        )
        
        if vertical_layout_match:
            # Bei vertikalem Layout: Erste Zahl = Gewinn/Verlust, Zweite Zahl = Ausmachender Betrag
            lines = text[vertical_layout_match.end():].split('\n')
            numbers_found = []
            for i, line in enumerate(lines[:15]):  # Schaue die nächsten 15 Zeilen
                # Suche nach Zahlen mit oder ohne EUR in derselben oder nächsten Zeilen
                # Unterstützt auch nachgestelltes Minus (deutsches Buchführungsformat)
                number_match = re.search(r'([-]?[\d]{1,3}(?:\.[\d]{3})*(?:,[\d]{2})?[-]?)', line)
                if number_match:
                    # Prüfe ob EUR in derselben oder in den nächsten 2 Zeilen ist
                    # (EUR kann auf einer separaten Zeile stehen)
                    has_eur = ('EUR' in line or 
                              (i+1 < len(lines) and 'EUR' in lines[i+1]) or
                              (i+2 < len(lines) and 'EUR' in lines[i+2]))
                    if has_eur:
                        # Prüfe ob es eine plausible Zahl ist
                        # Behandle nachgestelltes Minus
                        raw_number = number_match.group(1)
                        test_str = raw_number.rstrip('-').replace('.', '').replace(',', '.')
                        try:
                            test_val = float(test_str)
                            if test_val > 100:  # Ignoriere kleine Zahlen
                                numbers_found.append(raw_number)
                        except:
                            pass
                if len(numbers_found) >= 2:
                    break
            
            if len(numbers_found) >= 2:
                # Konvertiere beide Zahlen mit Unterstützung für nachgestelltes Minus
                num1_str = numbers_found[0]
                num2_str = numbers_found[1]
                
                # Prüfe und behandle nachgestelltes Minus
                value1_sign = -1.0 if num1_str.endswith('-') else 1.0
                value2_sign = -1.0 if num2_str.endswith('-') else 1.0
                
                value1 = float(num1_str.rstrip('-').replace('.', '').replace(',', '.')) * value1_sign
                value2 = float(num2_str.rstrip('-').replace('.', '').replace(',', '.')) * value2_sign
                
                # Debug-Ausgabe für BLUEITS-Transaktionen
                if 'BLUEITS' in text[:1000] and 'Verkauf' in text[:1000]:
                    print(f"  Debug: Vertikales Layout - Wert1={value1}, Wert2={value2}")
                    if details.get('gross_amount'):
                        print(f"  Debug: Kurswert={details['gross_amount']}")
                
                # Verbesserte Zuordnungslogik
                # Prinzip: Der Ausmachende Betrag ist IMMER ähnlich zum Kurswert
                # Der Gewinn/Verlust ist IMMER deutlich kleiner
                
                if details.get('gross_amount'):
                    kurswert = details['gross_amount']
                    
                    # Berechne absolute Differenzen zum Kurswert
                    diff1_to_kurswert = abs(value1 - kurswert)
                    diff2_to_kurswert = abs(value2 - kurswert)
                    
                    # Der Wert mit der kleineren Differenz zum Kurswert ist der Ausmachende Betrag
                    if diff1_to_kurswert < diff2_to_kurswert:
                        # value1 ist näher am Kurswert -> Ausmachender Betrag
                        details['net_amount'] = value1
                        details['profit_loss'] = value2
                        if 'BLUEITS' in text[:1000]:
                            print(f"  -> Zuordnung: Ausmachend={value1:.2f}, G/V={value2:.2f}")
                    else:
                        # value2 ist näher am Kurswert -> Ausmachender Betrag  
                        details['net_amount'] = value2
                        details['profit_loss'] = value1
                        if 'BLUEITS' in text[:1000]:
                            print(f"  -> Zuordnung: Ausmachend={value2:.2f}, G/V={value1:.2f}")
                else:
                    # Ohne Kurswert: Der größere Wert ist fast immer der Ausmachende Betrag
                    # (da Gewinn/Verlust normalerweise nur ein Bruchteil des Transaktionswerts ist)
                    if value2 > value1 * 3:  # Wenn value2 deutlich größer
                        details['profit_loss'] = value1
                        details['net_amount'] = value2
                    elif value1 > value2 * 3:  # Wenn value1 deutlich größer
                        details['profit_loss'] = value2
                        details['net_amount'] = value1
                    else:
                        # Bei ähnlichen Werten: Dokumentreihenfolge (erst G/V, dann Ausmachend)
                        details['profit_loss'] = value1
                        details['net_amount'] = value2
        else:
            # Standard Patterns für normale Layouts
            profit_loss_patterns = [
                # Patterns mit nachgestelltem Minus (deutsches Buchführungsformat)
                (r'Veräußerungsverlust\s+([\d.,]+)-\s*EUR', -1.0),  # Verlust mit nachgestelltem Minus
                (r'Veräußerungsgewinn\s+([\d.,]+)\s*EUR', 1.0),     # Gewinn ohne Minus
                # Standard Patterns (mit vorangestelltem Minus)
                (r'Veräußerungsgewinn\s+([-]?[\d.,]+)\s*EUR', 1.0),  # Positiv
                (r'Veräußerungsverlust\s+([-]?[\d.,]+)\s*EUR', -1.0), # Negativ
                # Alternative Begriffe
                (r'Gewinn\s+aus\s+Verkauf\s+([\d.,]+)-?\s*EUR', lambda x: -1.0 if x.endswith('-') else 1.0),
                (r'Verlust\s+aus\s+Verkauf\s+([\d.,]+)-?\s*EUR', -1.0),
                (r'Realisierter\s+Gewinn\s+([\d.,]+)-?\s*EUR', lambda x: -1.0 if x.endswith('-') else 1.0),
                (r'Realisierter\s+Verlust\s+([\d.,]+)-?\s*EUR', -1.0),
                # Mit Pipe-Separator
                (r'Veräußerungsgewinn\s*\|\s*([-]?[\d.,]+)\s*€', 1.0),
                (r'Veräußerungsverlust\s*\|\s*([-]?[\d.,]+)\s*€', -1.0),
                # Spezielle Formate (Betrag in Klammern = negativ)
                (r'Veräußerungsergebnis\s+\(([\d.,]+)\)\s*EUR', -1.0),  # In Klammern = Verlust
                (r'Veräußerungsergebnis\s+([\d.,]+)\s*EUR', 1.0),       # Ohne Klammern = Gewinn
                # Allgemeinere Patterns
                (r'Gewinn/Verlust\s+([-]?[\d.,]+)\s*(?:EUR|€)', 1.0),
                (r'Ergebnis\s+([-]?[\d.,]+)\s*(?:EUR|€)', 1.0)
            ]
            
            for pattern, multiplier in profit_loss_patterns:
                match = re.search(pattern, text)
                if match:
                    # Extrahiere den Wert und entferne nachgestelltes Minus
                    value_str = match.group(1).rstrip('-')
                    # Prüfe ob ursprünglich ein nachgestelltes Minus vorhanden war
                    has_trailing_minus = match.group(1).endswith('-')
                    # Konvertiere zu float (deutsches Format)
                    value = float(value_str.replace('.', '').replace(',', '.'))
                    # Wende Multiplier an, berücksichtige nachgestelltes Minus
                    if callable(multiplier):
                        details['profit_loss'] = value * (multiplier(match.group(1)))
                    else:
                        # Bei nachgestelltem Minus ist der Wert immer negativ
                        if has_trailing_minus and multiplier > 0:
                            details['profit_loss'] = -value
                        else:
                            details['profit_loss'] = value * multiplier
                    break
        
        # Extrahiere Ausmachender Betrag (Netto) - nur wenn nicht bereits aus vertikalem Layout extrahiert
        if not details.get('net_amount'):
            ausmachend_patterns = [
                r'Ausmachender\s+Betrag\s+([\d.,]+)\s*EUR',
                r'Zu\s+Ihren\s+Gunsten\s+([\d.,]+)\s*EUR',
                r'Zu\s+Ihren\s+Lasten\s+([\d.,]+)\s*EUR',
                r'Abrechnungsbetrag\s+([\d.,]+)\s*EUR',
                r'Endbetrag\s+([\d.,]+)\s*EUR',
                r'Gesamt\s+([\d.,]+)\s*EUR',
                # Mit Pipe-Separator
                r'Ausmachender\s+Betrag\s*\|\s*([\d.,]+)\s*€',
                r'Gesamt\s*\|\s*([\d.,]+)\s*€'
            ]
            
            for pattern in ausmachend_patterns:
                match = re.search(pattern, text)
                if match:
                    details['net_amount'] = float(match.group(1).replace('.', '').replace(',', '.'))
                    break
        
        # Fallback: Berechne Gebühren aus Differenz wenn möglich
        if details['gross_amount'] and details['net_amount'] and not details['fees']:
            # Bei Verkauf: Gebühren = Kurswert - Ausmachend
            # Bei Kauf: Gebühren = Ausmachend - Kurswert
            diff = abs(details['gross_amount'] - details['net_amount'])
            if diff > 0 and diff < details['gross_amount'] * 0.1:  # Max 10% Gebühren
                details['fees'] = diff
        
        # Validierung der extrahierten Werte
        if details.get('gross_amount') and details.get('net_amount'):
            # Bei Verkäufen sollte net_amount >= gross_amount - fees sein
            if details.get('profit_loss') is not None:
                # Prüfe ob der Gewinn/Verlust plausibel ist
                if abs(details['profit_loss']) > details['gross_amount']:
                    # Gewinn/Verlust kann nicht größer als der Kurswert sein
                    # Möglicherweise wurden die Werte vertauscht
                    print(f"  ⚠️  Warnung: Unplausibler G/V-Wert: {details['profit_loss']} bei Kurswert {details['gross_amount']}")
            
            # Prüfe ob Ausmachender Betrag plausibel ist
            if details['net_amount'] < details['gross_amount'] * 0.5:
                # Ausmachender Betrag sollte nicht weniger als 50% des Kurswerts sein (außer bei hohen Gebühren)
                if not details.get('fees') or details['fees'] < details['gross_amount'] * 0.5:
                    print(f"  ⚠️  Warnung: Unplausibler Ausmachender Betrag: {details['net_amount']} bei Kurswert {details['gross_amount']}")
        
        # Extrahiere Stichtag/Valuta/Ausführungsdatum
        stichtag_patterns = [
            # Valuta oder Schlusstag
            r'Valuta\s*[:\s]\s*(\d{1,2})\.(\d{1,2})\.(\d{4})',
            r'Schlusstag\s*[:\s]\s*(\d{1,2})\.(\d{1,2})\.(\d{4})',
            r'Schlusstag\s+(\d{1,2})\.(\d{1,2})\.(\d{4})',
            r'Ausführungstag\s*[:\s]\s*(\d{1,2})\.(\d{1,2})\.(\d{4})',
            r'Ausführung\s+am\s+(\d{1,2})\.(\d{1,2})\.(\d{4})',
            r'Geschäftstag\s*[:\s]\s*(\d{1,2})\.(\d{1,2})\.(\d{4})',
            r'Handelstag\s*[:\s]\s*(\d{1,2})\.(\d{1,2})\.(\d{4})',
            # Mit Pipe-Separator
            r'Valuta\s*\|\s*(\d{1,2})\.(\d{1,2})\.(\d{4})',
            r'Schlusstag\s*\|\s*(\d{1,2})\.(\d{1,2})\.(\d{4})',
            r'Geschäftstag\s*\|\s*(\d{1,2})\.(\d{1,2})\.(\d{4})',
            # Datum in Tabellen
            r'\|\s*(\d{1,2})\.(\d{1,2})\.(\d{4})\s*\|.*(?:Valuta|Schlusstag)',
            # Stichtag für Depotabschlüsse
            r'Stichtag\s*[:\s]\s*(\d{1,2})\.(\d{1,2})\.(\d{4})',
            r'per\s+(\d{1,2})\.(\d{1,2})\.(\d{4})',
            r'Stand\s*[:\s]\s*(\d{1,2})\.(\d{1,2})\.(\d{4})',
            # Fallback: Erstes Datum nach bestimmten Keywords
            r'(?:Kauf|Verkauf|Order)\s+vom\s+(\d{1,2})\.(\d{1,2})\.(\d{4})'
        ]
        
        for pattern in stichtag_patterns:
            match = re.search(pattern, text)
            if match:
                day, month, year = match.groups()
                details['stichtag'] = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
                break
        
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
        
        # Check for capital measures (stock splits, etc.)
        if ('kapitalmaßnahme' in extracted_lower or 'kapitalmassnahme' in extracted_lower or
            'aktiensplit' in extracted_lower or 'stock split' in extracted_lower or
            'neueinteilung des grundkapitals' in extracted_lower or
            'kapitalmaßnahme' in filename_lower or 'kapitalmassnahme' in filename_lower):
            transaction_type = 'Kapitalmaßnahme'
        # Check for cost information documents (MiFID II Kostenaufstellung)
        # These are specifically the Ex-Post cost reports, not regular orders mentioning cost information
        elif ('information über kosten und nebenkosten' in extracted_lower or 
            'ex-post-kosteninformation' in extracted_lower or
            ('dienstleistungskosten' in extracted_lower and 'übergreifende kosten' in extracted_lower)):
            transaction_type = 'Kostenaufstellung'
        # Check for depot statements (various formats)
        elif any(term in extracted_lower for term in ['depotabschluss', 'jahresabschluss', 'jahresdepotauszug', 'depotauszug', 'ex-post-rep']):
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
            # Check for limit order confirmation (Vormerkung) first
            if 'auftragsbestätigung' in extracted_lower or 'vormerkungsentgelt' in extracted_lower:
                transaction_type = 'Limit-Order-Vormerkung'
            # Check for order cancellation
            elif 'streichungsbestätigung' in extracted_lower or 'order wurde' in extracted_lower and 'gestrichen' in extracted_lower:
                transaction_type = 'Orderabrechnung-Stornierung'
            # Determine if buy or sell
            elif 'verkauf' in extracted_lower or 'sell' in extracted_lower:
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
            
        # Bestimme Wertpapiertyp (Aktie oder Nicht-Aktie)
        security_type = 'stock' if self.is_stock_isin(isin) else 'non-stock' if isin else None
        
        # Kombiniere alle Daten
        result = {
            **base_data,
            'type': transaction_type,
            'period': period,
            'isin': isin,
            'security_type': security_type,  # Neu: Typ des Wertpapiers
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
                            
                            # Tabellen ohne Trennzeichen (mit deutscher Zahlenformatierung)
                            r'Stück\s+([\d.]+)(?:\s|$)',     # Stück 950 oder Stück 1.665
                            r'([\d.]+)\s+Stück',              # 950 Stück oder 1.665 Stück
                            
                            # In Zeilen mit TESLA (mit deutscher Zahlenformatierung)
                            r'TESLA[^\n]*?([\d.]{2,6})\s+Stück',
                            r'TESLA[^\n]*?Stück\s+([\d.]{2,6})',
                            
                            # Mit ISIN - removed to avoid capturing dates
                            # r'US88160R1014[^\n]*?(\d{3,4})\s+',
                            r'US88160R1014[^\n]*?Stück\s+([\d.]{2,6})',
                            
                            # Spezielle Formate (mit deutscher Zahlenformatierung)
                            r'Bestand:\s*([\d.]+)\s+Stück',
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
                                        if 1 <= test_shares <= 100000 and not (2020 <= test_shares <= 2030):
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
    
    def extract_cost_information(self, depot_path: Path) -> Dict[str, List[Dict]]:
        """Extrahiert detaillierte Kosteninformationen aus MiFID II Dokumenten"""
        cost_data_by_year = {}
        
        # Finde alle Kosteninformations-Dokumente
        for thea_file in depot_path.glob("*Depotabschluss*.thea_extract"):
            data = self.load_thea_extract(thea_file)
            if data:
                extracted_text = data.get('response', {}).get('json', {}).get('extracted_text', '')
                file_path = data.get('metadata', {}).get('file', {}).get('pdf_path', '')
                file_name = os.path.basename(file_path)
                
                # Prüfe ob es ein Kosteninformations-Dokument ist
                if 'information über kosten' in extracted_text.lower() or 'kosteninformation' in extracted_text.lower():
                    # Extrahiere das Jahr aus dem Text
                    year_match = re.search(r'für das Jahr (\d{4})', extracted_text)
                    if year_match:
                        year = year_match.group(1)
                        
                        cost_info = {
                            'year': year,
                            'doc_date': self.extract_date_from_filename(file_name),
                            'file': file_name,
                            'total_costs': None,
                            'total_costs_net': None,
                            'total_costs_vat': None,
                            'service_costs_once': None,
                            'service_costs_ongoing': None,
                            'depot_fees': None,
                            'depot_fees_net': None,
                            'depot_fees_vat': None,
                            'product_costs': None,
                            'trading_volume': None,
                            'avg_depot_value': None,
                            'cost_percentage_volume': None,
                            'cost_percentage_depot': None,
                            'vat_rate': 19  # Standard USt-Satz in Deutschland
                        }
                        
                        # Extrahiere Dienstleistungskosten (Service/Trading costs)
                        # Handle both formats: with pipe separator and without
                        service_patterns = [
                            r'Dienstleistungskosten\s*\|\s*([\d.,]+)\s*€',  # With pipe separator
                            r'Dienstleistungskosten[^\d]+([\d.,]+)\s*€'     # General pattern
                        ]
                        for pattern in service_patterns:
                            service_match = re.search(pattern, extracted_text)
                            if service_match:
                                cost_info['service_costs'] = float(service_match.group(1).replace('.', '').replace(',', '.'))
                                break
                        else:
                            cost_info['service_costs'] = 0.0
                        
                        # Extrahiere Übergreifende Kosten (Depotentgelte)
                        depot_fees = re.search(r'Übergreifende Kosten[^\d]+([\d.,]+)\s*€', extracted_text)
                        if depot_fees:
                            cost_info['depot_fees'] = float(depot_fees.group(1).replace('.', '').replace(',', '.'))
                        else:
                            cost_info['depot_fees'] = 0.0
                        
                        # Berechne korrekte Gesamtkosten (Service + Depot)
                        cost_info['total_costs'] = cost_info['service_costs'] + cost_info['depot_fees']
                        
                        # Falls keine separaten Kosten gefunden, suche nach Gesamtkosten in der rechten Spalte
                        if cost_info['total_costs'] == 0:
                            # Suche nach dem Pattern "| Gesamtkosten | ... | XXX,XX € |" (rechteste Spalte)
                            total_pattern = r'\|\s*Gesamtkosten\s*\|(?:[^|]*\|){4}\s*([\d.,]+)\s*€'
                            total_match = re.search(total_pattern, extracted_text)
                            if total_match:
                                cost_info['total_costs'] = float(total_match.group(1).replace('.', '').replace(',', '.'))
                        
                        # Extrahiere Umsatzvolumen
                        volume = re.search(r'Umsatzvolumen[^\d]+([\d.,]+)\s*Euro', extracted_text)
                        if volume:
                            cost_info['trading_volume'] = float(volume.group(1).replace('.', '').replace(',', '.'))
                        
                        # Extrahiere durchschnittlichen Depotbestand
                        avg_depot = re.search(r'Durchschnittsdepotbestand[^\d]+([\d.,]+)\s*Euro', extracted_text)
                        if avg_depot:
                            cost_info['avg_depot_value'] = float(avg_depot.group(1).replace('.', '').replace(',', '.'))
                        
                        # Berechne USt-Anteile (die Kosten sind Bruttobeträge inkl. 19% USt)
                        if cost_info['service_costs']:
                            # Nettobetrag = Bruttobetrag / 1.19
                            cost_info['service_costs_net'] = round(cost_info['service_costs'] / 1.19, 2)
                            # USt = Brutto - Netto
                            cost_info['service_costs_vat'] = round(cost_info['service_costs'] - cost_info['service_costs_net'], 2)
                        else:
                            cost_info['service_costs_net'] = 0.0
                            cost_info['service_costs_vat'] = 0.0
                        
                        if cost_info['depot_fees']:
                            # Nettobetrag = Bruttobetrag / 1.19
                            cost_info['depot_fees_net'] = round(cost_info['depot_fees'] / 1.19, 2)
                            # USt = Brutto - Netto  
                            cost_info['depot_fees_vat'] = round(cost_info['depot_fees'] - cost_info['depot_fees_net'], 2)
                        else:
                            cost_info['depot_fees_net'] = 0.0
                            cost_info['depot_fees_vat'] = 0.0
                        
                        # Berechne Gesamt-Netto und Gesamt-USt
                        if cost_info['total_costs']:
                            cost_info['total_costs_net'] = round(cost_info['total_costs'] / 1.19, 2)
                            cost_info['total_costs_vat'] = round(cost_info['total_costs'] - cost_info['total_costs_net'], 2)
                        
                        # Berechne Kostenquoten
                        if cost_info['total_costs'] and cost_info['trading_volume'] and cost_info['trading_volume'] > 0:
                            cost_info['cost_percentage_volume'] = round(cost_info['total_costs'] / cost_info['trading_volume'] * 100, 2)
                        
                        if cost_info['total_costs'] and cost_info['avg_depot_value'] and cost_info['avg_depot_value'] > 0:
                            cost_info['cost_percentage_depot'] = round(cost_info['total_costs'] / cost_info['avg_depot_value'] * 100, 2)
                        
                        cost_data_by_year[year] = cost_info
        
        return cost_data_by_year
    
    def analyze_depot(self, depot_name: str) -> Dict[str, Any]:
        """Analysiert alle Dateien eines Depots mit erweiterter Datenqualitätsprüfung"""
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
        
        # Datenqualitäts-Statistiken
        data_quality = {
            'total_transactions': 0,
            'with_fees': 0,
            'without_fees': 0,
            'with_execution_date': 0,
            'with_profit_loss': 0,
            'missing_isin': 0,
            'missing_amounts': 0,
            'suspicious_fees': 0  # Gebühren > 10% des Volumens
        }
        
        for file_path in thea_files:
            data = self.load_thea_extract(file_path)
            if data:
                transaction = self.extract_transaction_data(data)
                if transaction:
                    transactions.append(transaction)
                    statistics[transaction['type']] += 1
                    if transaction['isin']:
                        isin_groups[transaction['isin']].append(transaction)
                    
                    # Sammle Datenqualitäts-Statistiken
                    data_quality['total_transactions'] += 1
                    
                    # Prüfe Gebühren
                    if transaction.get('fees') and transaction['fees'] > 0:
                        data_quality['with_fees'] += 1
                        # Prüfe auf verdächtig hohe Gebühren (> 10% des Volumens)
                        if transaction.get('gross_amount') and transaction['gross_amount'] > 0:
                            fee_percentage = (transaction['fees'] / transaction['gross_amount']) * 100
                            if fee_percentage > 10:
                                data_quality['suspicious_fees'] += 1
                    else:
                        # Prüfe ob legitim keine Gebühren (Kurswert = Ausmachend)
                        if transaction.get('gross_amount') and transaction.get('net_amount'):
                            if abs(transaction['gross_amount'] - transaction['net_amount']) < 0.01:
                                data_quality['without_fees'] += 1  # Legitim keine Gebühren
                    
                    # Prüfe Ausführungsdatum
                    if transaction.get('stichtag') and transaction['stichtag'] != transaction.get('date'):
                        data_quality['with_execution_date'] += 1
                    
                    # Prüfe Gewinn/Verlust bei Verkäufen
                    if 'Verkauf' in transaction['type'] and transaction.get('profit_loss') is not None:
                        data_quality['with_profit_loss'] += 1
                    
                    # Prüfe fehlende ISINs
                    if not transaction.get('isin'):
                        data_quality['missing_isin'] += 1
                    
                    # Prüfe fehlende Beträge
                    if not transaction.get('gross_amount') and not transaction.get('net_amount'):
                        data_quality['missing_amounts'] += 1
        
        # Sortiere Transaktionen nach Datum
        transactions.sort(key=lambda x: x['date'] if x['date'] else '0000-00-00')
        
        # Extrahiere Depot-Salden
        balance_info = self.extract_depot_balance(depot_path)
        
        # Extrahiere Kosteninformationen
        cost_info = self.extract_cost_information(depot_path)
        
        # Ausgabe der Datenqualitäts-Statistiken
        if data_quality['total_transactions'] > 0:
            print(f"\n  Datenqualitäts-Statistiken für {depot_name}:")
            print(f"  - Transaktionen mit Gebühren: {data_quality['with_fees']}/{data_quality['total_transactions']} ({data_quality['with_fees']*100/data_quality['total_transactions']:.1f}%)")
            print(f"  - Transaktionen ohne Gebühren (legitim): {data_quality['without_fees']}/{data_quality['total_transactions']} ({data_quality['without_fees']*100/data_quality['total_transactions']:.1f}%)")
            print(f"  - Mit explizitem Ausführungsdatum: {data_quality['with_execution_date']}/{data_quality['total_transactions']} ({data_quality['with_execution_date']*100/data_quality['total_transactions']:.1f}%)")
            
            # Warnungen für Datenqualitätsprobleme
            if data_quality['suspicious_fees'] > 0:
                print(f"  ⚠️  Verdächtig hohe Gebühren (>10%): {data_quality['suspicious_fees']} Transaktionen")
            if data_quality['missing_isin'] > 0:
                print(f"  ⚠️  Fehlende ISINs: {data_quality['missing_isin']} Transaktionen")
            if data_quality['missing_amounts'] > 0:
                print(f"  ⚠️  Fehlende Beträge: {data_quality['missing_amounts']} Transaktionen")
            
            # Erfolgsrate für Gewinn/Verlust bei Verkäufen (ohne Kapitalmaßnahmen)
            verkauf_count = sum(1 for t in transactions if 'Verkauf' in t['type'] and t['type'] != 'Kapitalmaßnahme')
            if verkauf_count > 0:
                gv_rate = (data_quality['with_profit_loss'] / verkauf_count) * 100
                print(f"  - Verkäufe mit G/V-Daten: {data_quality['with_profit_loss']}/{verkauf_count} ({gv_rate:.1f}%)")
        
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
            'latest_balance_date': balance_info['latest_balance_date'],
            'cost_information': cost_info,  # Füge Kosteninformationen hinzu
            'data_quality': data_quality  # Füge Datenqualitäts-Statistiken hinzu
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
            latest_saldo_date=self.format_date_german(analysis.get('latest_balance_date')) if analysis.get('latest_balance_date') else None
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
                    doc_date = self.format_date_german(statement['doc_date'] if statement.get('doc_date') else 'N/A')
                    balance_date = self.format_date_german(statement['balance_date'] if statement.get('balance_date') else 'N/A')
                    
                    # Formatiere Stück und ISIN
                    shares_str = str(statement['shares']) if statement.get('shares') else '-'
                    isin_str = statement['isin'] if statement.get('isin') else '-'
                    
                    # Formatiere Depotbestand mit deutschem Tausendertrennzeichen
                    if statement.get('closing_balance') is not None:
                        closing = self.format_number_german(statement['closing_balance'], 2)
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
                latest_date = self.format_date_german(analysis.get('latest_balance_date', 'N/A'))
                latest_balance_str = self.format_number_german(analysis['latest_balance'], 2)
                md.append(f"\n**Letzter bekannter Depotbestand: {latest_balance_str} EUR** (Stand: {latest_date})")
            
            total_statements = len(analysis.get('depot_statements', []))
            if total_statements > 0:
                first_date = min(s['balance_date'] for s in analysis['depot_statements'] if s.get('balance_date'))
                last_date = max(s['balance_date'] for s in analysis['depot_statements'] if s.get('balance_date'))
                first_date_german = self.format_date_german(first_date)
                last_date_german = self.format_date_german(last_date)
                md.append(f"*Gesamtzeitraum: {first_date_german} bis {last_date_german}*")
        
        # Abschnitt 3: Jährliche Kostenanalyse (MiFID II)
        if analysis.get('cost_information'):
            md.append(f"\n## Jährliche Kostenanalyse (MiFID II)\n")
            md.append("Gesetzlich vorgeschriebene Kostenaufstellung gemäß Art. 50 der Verordnung (EU) 2017/565:")
            md.append("\n| Jahr | Dokumentdatum | Dienstleistungskosten (netto) | Depotentgelte (netto) | Zwischensumme (netto) | USt (19%) | Gesamtkosten (brutto) | Umsatzvolumen | Ø Depotbestand | Kostenquote | Dokument |")
            md.append("|------|---------------|------------------------------|----------------------|---------------------|-----------|----------------------|---------------|----------------|-------------|----------|")
            
            # Sortiere nach Jahr
            years = sorted(analysis['cost_information'].keys())
            
            for year in years:
                cost_data = analysis['cost_information'][year]
                
                # Formatiere Beträge deutsch
                service_costs_net = self.format_number_german(cost_data['service_costs_net'], 2) if cost_data.get('service_costs_net') else '-'
                depot_fees_net = self.format_number_german(cost_data['depot_fees_net'], 2) if cost_data.get('depot_fees_net') else '-'
                subtotal_net = self.format_number_german(cost_data['total_costs_net'], 2) if cost_data.get('total_costs_net') else '-'
                total_costs = self.format_number_german(cost_data['total_costs'], 2) if cost_data.get('total_costs') else '-'
                total_vat = self.format_number_german(cost_data['total_costs_vat'], 2) if cost_data.get('total_costs_vat') else '-'
                volume = self.format_number_german(cost_data['trading_volume'], 2) if cost_data.get('trading_volume') else '-'
                avg_depot = self.format_number_german(cost_data['avg_depot_value'], 2) if cost_data.get('avg_depot_value') else '-'
                
                # Kostenquote (ohne %-Zeichen, da es im Header steht)
                if cost_data.get('cost_percentage_depot'):
                    cost_quote = self.format_number_german(cost_data['cost_percentage_depot'], 2)
                else:
                    cost_quote = '-'
                
                # Formatiere Dokumentdatum
                doc_date = self.format_date_german(cost_data.get('doc_date', ''))
                
                # Erstelle Dokumentlink
                file_name = cost_data.get('file', '')
                if len(file_name) > 40:
                    display_name = file_name[:37] + "..."
                else:
                    display_name = file_name
                doc_link = f"[{display_name}](docs/{analysis['depot_info']['folder']}/{file_name})"
                
                md.append(f"| {year} | {doc_date} | {service_costs_net} | {depot_fees_net} | {subtotal_net} | {total_vat} | {total_costs} | {volume} | {avg_depot} | {cost_quote} | {doc_link} |")
            
            # Zusammenfassung der Kosten
            if len(years) > 0:
                # Berechne Summen
                total_all_costs = sum(c['total_costs'] for c in analysis['cost_information'].values() if c.get('total_costs'))
                total_all_volume = sum(c['trading_volume'] for c in analysis['cost_information'].values() if c.get('trading_volume'))
                
                if total_all_costs > 0:
                    total_str = self.format_number_german(total_all_costs, 2)
                    md.append(f"\n**Gesamtkosten {years[0]}-{years[-1]}: {total_str} €**")
                
                if total_all_volume > 0:
                    volume_str = self.format_number_german(total_all_volume, 2)
                    md.append(f"*Gesamtes Handelsvolumen: {volume_str} €*")
                
                # Durchschnittliche Kostenquote
                quotes = [c['cost_percentage_depot'] for c in analysis['cost_information'].values() if c.get('cost_percentage_depot')]
                if quotes:
                    avg_quote = sum(quotes) / len(quotes)
                    md.append(f"*Durchschnittliche jährliche Kostenquote: {avg_quote:.2f}%*")
                
                # Umfassende Erläuterungen zur Kostenstruktur
                md.append("\n### Erläuterungen zur Kostenberechnung:")
                md.append("\n**Kostenzusammensetzung:**")
                md.append("- **Dienstleistungskosten:** Beinhalten alle Kosten für Wertpapiergeschäfte (Kauf/Verkauf), Ordergebühren und sonstige Transaktionskosten")
                md.append("- **Depotentgelte:** Jährliche Verwahrungsgebühren für die Führung des Depotkontos (übergreifende Kosten)")
                md.append("- **Zwischensumme (netto):** Summe aus Dienstleistungskosten und Depotentgelten ohne Umsatzsteuer")
                md.append("- **USt (19%):** Gesetzliche Umsatzsteuer auf alle Kosten (sowohl Dienstleistungs- als auch Depotentgelte)")
                md.append("- **Gesamtkosten (brutto):** Vollständige Kosten inklusive 19% Umsatzsteuer")
                
                md.append("\n**Wichtige Hinweise:**")
                md.append("- ✓ Die Depotentgelte sind **in den Gesamtkosten enthalten** (Dienstleistungskosten + Depotentgelte = Gesamtkosten)")
                md.append("- ✓ Alle Beträge in den verlinkten Dokumenten sind **Bruttobeträge** (bereits inkl. 19% USt)")
                md.append("- ✓ Die Nettobeträge werden berechnet: Netto = Brutto ÷ 1,19")
                md.append("- ✓ Die USt wird berechnet: USt = Brutto - Netto")
                
                md.append("\n**Berechnungsbeispiel 2021:**")
                if '2021' in analysis['cost_information']:
                    cost_2021 = analysis['cost_information']['2021']
                    service_gross = cost_2021.get('service_costs', 0)
                    depot_gross = cost_2021.get('depot_fees', 0)
                    total_gross = cost_2021.get('total_costs', 0)
                    
                    md.append(f"- Dienstleistungskosten (brutto): {service_gross:.2f} € ÷ 1,19 = {service_gross/1.19:.2f} € (netto)")
                    md.append(f"- Depotentgelte (brutto): {depot_gross:.2f} € ÷ 1,19 = {depot_gross/1.19:.2f} € (netto)")
                    md.append(f"- **Gesamtkosten: {service_gross:.2f} € + {depot_gross:.2f} € = {total_gross:.2f} € (brutto)**")
                
                md.append("\n*Diese Aufstellung entspricht den gesetzlichen Anforderungen gemäß Art. 50 der Verordnung (EU) 2017/565 (MiFID II).*")
        
        # Abschnitt 4: Dokumententabelle (MOVED AFTER COST OVERVIEW)
        doc_table_lines = self.generate_document_table(analysis['depot_path'], analysis['depot_info'])
        md.extend(doc_table_lines)
        
        # Abschnitt 5: Transaktionsstatistik
        md.append(f"\n## Transaktionsstatistik\n")
        
        # Gruppiere nach Hauptkategorie für bessere Übersicht
        categories = {
            'Depotabschluss': [],
            'Orderabrechnung': [],
            'Kostenaufstellung': [],
            'Sonstige': []
        }
        
        for trans_type, count in sorted(analysis['statistics'].items()):
            if 'Depotabschluss' in trans_type:
                categories['Depotabschluss'].append((trans_type, count))
            elif 'Orderabrechnung' in trans_type:
                categories['Orderabrechnung'].append((trans_type, count))
            elif 'Limit-Order-Vormerkung' in trans_type:
                categories['Orderabrechnung'].append((trans_type, count))
            elif 'Kostenaufstellung' in trans_type:
                categories['Kostenaufstellung'].append((trans_type, count))
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
        
        # Zeige Kostenaufstellung-Kategorien
        if categories['Kostenaufstellung']:
            md.append("\n### Kostenaufstellungen (MiFID II)")
            for trans_type, count in categories['Kostenaufstellung']:
                md.append(f"- **{trans_type}:** {count}")
        
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
        
        # Abschnitt 6: Wertpapiere nach ISIN
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
        
        # Abschnitt 7: Detaillierter Transaktionsverlauf
        md.append(f"\n## Transaktionsverlauf (Detailliert)\n")
        
        # Legende der Spalten
        md.append("### Legende der Spalten:")
        md.append("- **Nr.**: Laufende Nummer der Transaktion")
        md.append("- **Stichtag**: Valuta-/Ausführungsdatum der Transaktion")
        md.append("- **Dok.datum**: Datum der Dokumenterstellung")
        md.append("- **G/V Akt.**: Gewinn/Verlust aus Aktienverkäufen (EUR)")
        md.append("- **Kum. Akt.**: Kumulierter Gewinn/Verlust Aktien (EUR)")
        md.append("- **G/V N-Akt.**: Gewinn/Verlust aus Nicht-Aktien (Derivate, Zertifikate, strukturierte Produkte) (EUR)")
        md.append("- **Kum. N-Akt.**: Kumulierter Gewinn/Verlust Nicht-Aktien (EUR)")
        md.append("- **G/V Ges.**: Gewinn/Verlust Gesamt (EUR)")
        md.append("- **Kum. Ges.**: Kumulierter Gewinn/Verlust Gesamt (EUR)")
        md.append("")
        
        # Tabellenkopf (verkürzt wegen Platzmangel)
        md.append("| Nr. | Stichtag | Dok.datum | Typ | ISIN | Stück | Kurs | Kurswert | Geb. | USt | Ausmach. | G/V Akt. | Kum. Akt. | G/V N-Akt. | Kum. N-Akt. | G/V Ges. | Kum. Ges. | Dokument |")
        md.append("|-----|----------|-----------|-----|------|-------|------|----------|------|-----|----------|----------|-----------|------------|-------------|----------|-----------|----------|")
        
        # Variablen für kumulierte Gewinn/Verluste
        cumulative_stock = 0.0
        cumulative_non_stock = 0.0
        cumulative_total = 0.0
        transaction_number = 0  # Laufende Nummer für Transaktionen
        
        for trans in analysis['transactions']:
            transaction_number += 1  # Erhöhe die laufende Nummer
            # Extrahiere Stichtag und Dokumentdatum
            stichtag = self.format_date_german(trans.get('stichtag', trans.get('date', 'N/A')))
            doc_date = self.format_date_german(trans['date'] if trans['date'] else 'N/A')
            trans_type = trans['type']
            
            # Kürze den Transaktionstyp für bessere Lesbarkeit
            if 'Orderabrechnung-' in trans_type:
                display_type = trans_type.replace('Orderabrechnung-', '')
            elif 'Limit-Order-Vormerkung' in trans_type:
                display_type = 'Vormerkung'
            elif 'Depotabschluss-' in trans_type:
                display_type = 'Depotabschluss'
            else:
                display_type = trans_type
            
            # Bestimme Farbmarkierung für Verkäufe
            row_style = ""
            if 'Verkauf' in trans_type:
                if trans.get('profit_loss') is not None:
                    if trans['profit_loss'] > 0:
                        # Gewinn - dunkelgrün
                        row_style = ' style="background-color: #d4edda;"'
                    elif trans['profit_loss'] == 0:
                        # Kein Gewinn/Verlust - auch grün
                        row_style = ' style="background-color: #d4edda;"'
                    else:
                        # Verlust - rot
                        row_style = ' style="background-color: #f8d7da;"'
            
            # Formatiere Typ mit Farbmarkierung
            if row_style:
                display_type = f'<span{row_style}>{display_type}</span>'
            
            isin = trans['isin'] if trans['isin'] else 'N/A'
            
            # Handelsdaten formatieren
            shares = str(trans.get('shares', '')) if trans.get('shares') else '-'
            
            # Kurs - bei mehreren Kursen zeige Durchschnitt
            if trans.get('execution_price_min') and trans.get('execution_price_max'):
                # Teilausführungen mit mehreren Kursen - zeige Durchschnitt
                price_str = self.format_number_german(trans.get('execution_price_avg', 0), 2)
            elif trans.get('execution_price'):
                price_str = self.format_number_german(trans['execution_price'], 2)
            else:
                price_str = '-'
            
            # Kurswert (netto - ohne Gebühren)
            kurswert_netto = self.format_number_german(trans['gross_amount'], 2) if trans.get('gross_amount') else '-'
            
            # Gebühren und USt-Berechnung
            if trans.get('fees'):
                # Die Gebühren sind bereits brutto (inkl. 19% USt)
                fees_gross = trans['fees']
                fees_net = fees_gross / 1.19
                fees_vat = fees_gross - fees_net
                gebühren_netto_str = self.format_number_german(fees_net, 2)
                ust_str = self.format_number_german(fees_vat, 2)
            else:
                gebühren_netto_str = '-'
                ust_str = '-'
                fees_gross = 0
                fees_net = 0
                fees_vat = 0
            
            # Ausmachender Betrag (brutto = Kurswert + Gebühren inkl. USt)
            if trans.get('net_amount'):
                ausmachend_brutto = self.format_number_german(trans['net_amount'], 2)
            elif trans.get('gross_amount'):
                # Berechne Ausmachend = Kurswert + Gebühren (brutto)
                ausmachend_val = trans['gross_amount'] + fees_gross
                ausmachend_brutto = self.format_number_german(ausmachend_val, 2)
            else:
                ausmachend_brutto = '-'
            
            # Gewinn/Verlust aufgeteilt nach Aktien und Nicht-Aktien
            gv_aktien_str = '-'
            kum_aktien_str = '-'
            gv_non_aktien_str = '-'
            kum_non_aktien_str = '-'
            gv_gesamt_str = '-'
            kum_gesamt_str = '-'
            
            if trans.get('profit_loss') is not None:
                profit_loss_val = trans['profit_loss']
                is_stock = trans.get('security_type') == 'stock'
                
                # Aktualisiere kumulierte Werte basierend auf Wertpapiertyp
                if is_stock:
                    cumulative_stock += profit_loss_val
                    # Formatiere Aktien G/V
                    if profit_loss_val > 0:
                        gv_aktien_str = f'<span style="color: green; font-weight: bold;">{self.format_number_german(profit_loss_val, 2, show_sign=True)}</span>'
                    elif profit_loss_val == 0:
                        gv_aktien_str = f'<span style="color: black;">0,00</span>'
                    else:
                        gv_aktien_str = f'<span style="color: red; font-weight: bold;">{self.format_number_german(profit_loss_val, 2)}</span>'
                    
                    # Formatiere kumulierten Aktien G/V
                    if cumulative_stock > 0:
                        kum_aktien_str = f'<span style="color: green; font-weight: bold;">{self.format_number_german(cumulative_stock, 2, show_sign=True)}</span>'
                    elif cumulative_stock == 0:
                        kum_aktien_str = f'<span style="color: black;">0,00</span>'
                    else:
                        kum_aktien_str = f'<span style="color: red; font-weight: bold;">{self.format_number_german(cumulative_stock, 2)}</span>'
                    
                    # Nicht-Aktien bleiben leer
                    gv_non_aktien_str = '-'
                    kum_non_aktien_str = self.format_number_german(cumulative_non_stock, 2) if cumulative_non_stock != 0 else '-'
                    
                else:
                    cumulative_non_stock += profit_loss_val
                    # Formatiere Nicht-Aktien G/V
                    if profit_loss_val > 0:
                        gv_non_aktien_str = f'<span style="color: green; font-weight: bold;">{self.format_number_german(profit_loss_val, 2, show_sign=True)}</span>'
                    elif profit_loss_val == 0:
                        gv_non_aktien_str = f'<span style="color: black;">0,00</span>'
                    else:
                        gv_non_aktien_str = f'<span style="color: red; font-weight: bold;">{self.format_number_german(profit_loss_val, 2)}</span>'
                    
                    # Formatiere kumulierten Nicht-Aktien G/V
                    if cumulative_non_stock > 0:
                        kum_non_aktien_str = f'<span style="color: green; font-weight: bold;">{self.format_number_german(cumulative_non_stock, 2, show_sign=True)}</span>'
                    elif cumulative_non_stock == 0:
                        kum_non_aktien_str = f'<span style="color: black;">0,00</span>'
                    else:
                        kum_non_aktien_str = f'<span style="color: red; font-weight: bold;">{self.format_number_german(cumulative_non_stock, 2)}</span>'
                    
                    # Aktien bleiben leer
                    gv_aktien_str = '-'
                    kum_aktien_str = self.format_number_german(cumulative_stock, 2) if cumulative_stock != 0 else '-'
                
                # Gesamt G/V immer berechnen
                cumulative_total += profit_loss_val
                
                # Formatiere Gesamt G/V
                if profit_loss_val > 0:
                    gv_gesamt_str = f'<span style="color: green; font-weight: bold;">{self.format_number_german(profit_loss_val, 2, show_sign=True)}</span>'
                elif profit_loss_val == 0:
                    gv_gesamt_str = f'<span style="color: black;">0,00</span>'
                else:
                    gv_gesamt_str = f'<span style="color: red; font-weight: bold;">{self.format_number_german(profit_loss_val, 2)}</span>'
                
                # Formatiere kumulierten Gesamt G/V
                if cumulative_total > 0:
                    kum_gesamt_str = f'<span style="color: green; font-weight: bold;">{self.format_number_german(cumulative_total, 2, show_sign=True)}</span>'
                elif cumulative_total == 0:
                    kum_gesamt_str = f'<span style="color: black;">0,00</span>'
                else:
                    kum_gesamt_str = f'<span style="color: red; font-weight: bold;">{self.format_number_german(cumulative_total, 2)}</span>'
            
            # Entfernt - wird durch ausmachend_brutto ersetzt
            
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
            
            # Erstelle die detaillierte Tabellenzeile mit allen neuen Spalten
            md.append(f"| {transaction_number} | {stichtag} | {doc_date} | {display_type} | {isin_display} | {shares} | {price_str} | {kurswert_netto} | {gebühren_netto_str} | {ust_str} | {ausmachend_brutto} | {gv_aktien_str} | {kum_aktien_str} | {gv_non_aktien_str} | {kum_non_aktien_str} | {gv_gesamt_str} | {kum_gesamt_str} | {pdf_link} |")
        
        # Zusammenfassung Transaktionsverlauf
        total_trans = len(analysis['transactions'])
        
        # Count different transaction types
        depotabschluss_count = sum(1 for t in analysis['transactions'] if 'Depotabschluss' in t['type'])
        orderabrechnung_count = sum(1 for t in analysis['transactions'] if 'Orderabrechnung' in t['type'] or t['type'] == 'Limit-Order-Vormerkung')
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
        
        # Performance-Zusammenfassung
        md.append(f"\n### Performance-Zusammenfassung:")
        cumulative_stock_str = self.format_number_german(cumulative_stock, 2, show_sign=True)
        cumulative_non_stock_str = self.format_number_german(cumulative_non_stock, 2, show_sign=True)
        cumulative_total_str = self.format_number_german(cumulative_total, 2, show_sign=True)
        
        md.append(f"- **Aktien Gesamt:** {cumulative_stock_str} EUR (Kumuliert)")
        md.append(f"- **Nicht-Aktien Gesamt:** {cumulative_non_stock_str} EUR (Kumuliert)")
        md.append(f"- **Gesamtergebnis:** {cumulative_total_str} EUR")
        
        # Steuerliche Hinweise
        md.append(f"\n### Steuerliche Hinweise:")
        md.append("- **Aktiengewinne:** Unterliegen der Abgeltungssteuer (25% + SolZ + ggf. KiSt)")
        md.append("- **Nicht-Aktien (Derivate/Zertifikate):** Verluste nur mit Gewinnen aus Termingeschäften verrechenbar (§ 20 Abs. 6 EStG)")
        md.append("- **Verlustverrechnungstöpfe:** Aktien- und Derivatverluste werden steuerlich getrennt behandelt")
        
        # Farbcodierung-Legende
        md.append(f"\n### Farbcodierung:")
        md.append("- 🟢 **Grüne Schrift**: Gewinnbringende Verkäufe")
        md.append("- 🔴 **Rote Schrift**: Verlustbehaftete Verkäufe")
        md.append("- **Grüner Hintergrund**: Verkaufstransaktion mit Gewinn")
        md.append("- **Roter Hintergrund**: Verkaufstransaktion mit Verlust")
        
        # Abschnitt 8: Zeitliche Verteilung
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