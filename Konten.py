#!/usr/bin/env python3
"""
Konten.py - Gemeinsame Bibliothek für Kontoanalyse-Skripte
Enthält geteilte Funktionalität für Depotkonto.py, Girokonto.py und Geldmarktkonto.py
"""

import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from collections import defaultdict


class BaseKontoAnalyzer:
    """Basisklasse für alle Kontoanalyse-Klassen"""
    
    def __init__(self):
        self.base_path = Path("docs")
        
        # Mapping für Dokumenttypen
        self.doc_type_mapping = {
            "invoice": "Orderabrechnung",
            "statement": "Kontoauszug",
            "report": "Depotabschluss",
            "contract": "Vertrag",  
            "confirmation": "Bestätigung",
            "notification": "Mitteilung",
            "interest": "Zinsabrechnung",
            "other": "Sonstiges"
        }
        
    def load_thea_extract(self, file_path: Path) -> Dict[str, Any]:
        """Lädt eine .thea_extract Datei und gibt die geparsten Daten zurück"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data
        except Exception as e:
            print(f"Fehler beim Laden von {file_path}: {e}")
            return None
    
    def extract_document_type_from_docling(self, pdf_path: Path) -> str:
        """Extrahiert den Dokumenttyp aus der zugehörigen docling.json Datei"""
        # Fallback basierend auf Dateinamen-Mustern (höchste Priorität)
        filename_lower = pdf_path.name.lower()
        if 'depotabschluss' in filename_lower or 'ex-post-rep' in filename_lower:
            return 'Depotabschluss'
        elif 'orderabrechnung' in filename_lower:
            return 'Orderabrechnung'
        elif 'kapitalmassnahme' in filename_lower or 'kapitalmaßnahme' in filename_lower:
            return 'Kapitalmassnahme'
        elif 'kontoauszug' in filename_lower or 'auszug' in filename_lower:
            return 'Kontoauszug'
        elif 'zinsabrechnung' in filename_lower:
            return 'Zinsabrechnung'
        
        # Suche nach zugehöriger docling.json Datei für weitere Hinweise
        pdf_name = pdf_path.stem
        parent_dir = pdf_path.parent
        
        # Mögliche docling.json Dateien für diese PDF
        docling_patterns = [
            f"{pdf_name}.*.docling.json",
            f"{pdf_name}*.docling.json"
        ]
        
        for pattern in docling_patterns:
            docling_files = list(parent_dir.glob(pattern))
            if docling_files:
                try:
                    with open(docling_files[0], 'r', encoding='utf-8') as f:
                        docling_data = json.load(f)
                    doc_type = docling_data.get('extraction_metadata', {}).get('document_type', 'other')
                    # Spezielle Behandlung für statement -> Kontoauszug
                    if doc_type == 'statement':
                        return 'Kontoauszug'
                    return self.doc_type_mapping.get(doc_type, doc_type.capitalize())
                except Exception as e:
                    print(f"Fehler beim Lesen von {docling_files[0]}: {e}")
                    
        return "Document"
    
    def extract_date_from_filename(self, filename: str) -> Optional[str]:
        """Extrahiert das Datum aus dem Dateinamen"""
        # Suche nach YYYYMMDD Pattern
        date_match = re.search(r'(\d{8})', filename)
        if date_match:
            date_str = date_match.group(1)
            try:
                date_obj = datetime.strptime(date_str, '%Y%m%d')
                return date_obj.strftime('%Y-%m-%d')
            except:
                pass
        
        # Suche nach vom_DD_MM_YYYY Pattern (z.B. vom_01_04_2022)
        date_match = re.search(r'vom_(\d{2})_(\d{2})_(\d{4})', filename)
        if date_match:
            try:
                day, month, year = date_match.groups()
                date_obj = datetime(int(year), int(month), int(day))
                return date_obj.strftime('%Y-%m-%d')
            except:
                pass
        
        # Suche nach DD.MM.YYYY Pattern
        date_match = re.search(r'(\d{2})\.(\d{2})\.(\d{4})', filename)
        if date_match:
            try:
                day, month, year = date_match.groups()
                date_obj = datetime(int(year), int(month), int(day))
                return date_obj.strftime('%Y-%m-%d')
            except:
                pass
                
        return None
    
    def generate_document_table(self, account_path: Path, account_info: Dict) -> List[str]:
        """Generiert die Dokumententabelle für den zweiten Abschnitt"""
        md_lines = []
        md_lines.append("\n## Dokumentenübersicht\n")
        md_lines.append("| Datum | Dokumentname | Dokumenttyp |")
        md_lines.append("|-------|--------------|-------------|")
        
        # Sammle alle PDF-Dateien (beide Schreibweisen)
        pdf_files = list(account_path.glob("*.pdf")) + list(account_path.glob("*.PDF"))
        
        # Tracking für Statistiken
        doc_type_counts = defaultdict(int)
        unknown_docs = []
        
        # Erstelle Liste mit Dateiinformationen
        file_infos = []
        for pdf_file in pdf_files:
            date_str = self.extract_date_from_filename(pdf_file.name)
            doc_type = self.extract_document_type_from_docling(pdf_file)
            
            # Zähle Dokumenttypen
            doc_type_counts[doc_type] += 1
            
            # Sammle unbekannte Dokumente
            if doc_type == "Document":
                unknown_docs.append(pdf_file.name)
            
            file_infos.append({
                'date': date_str if date_str else '0000-00-00',
                'name': pdf_file.name,
                'type': doc_type,
                'path': f"docs/{account_info['folder']}/{pdf_file.name}"
            })
        
        # Sortiere nach Datum
        file_infos.sort(key=lambda x: x['date'])
        
        # Generiere Tabellenzeilen
        for info in file_infos:
            date_display = info['date'] if info['date'] != '0000-00-00' else 'N/A'
            # Erstelle Markdown-Link
            link = f"[{info['name']}]({info['path']})"
            # Markiere unbekannte Dokumente
            if info['type'] == "Document":
                md_lines.append(f"| {date_display} | ⚠️ {link} | **{info['type']}** |")
            else:
                md_lines.append(f"| {date_display} | {link} | {info['type']} |")
        
        # Erweiterte Zusammenfassung
        md_lines.append(f"\n*Gesamt: {len(pdf_files)} Dokumente*")
        
        # Typ-Statistiken
        if doc_type_counts:
            type_summary = " | ".join([f"{typ}: {count}" for typ, count in sorted(doc_type_counts.items())])
            md_lines.append(f"*{type_summary}*")
        
        # Warnung für unbekannte Dokumente
        if unknown_docs:
            md_lines.append(f"\n⚠️ **Warnung: {len(unknown_docs)} Dokumente ohne Typ-Klassifizierung:**")
            for doc in unknown_docs[:10]:  # Zeige max. 10
                md_lines.append(f"- {doc}")
            if len(unknown_docs) > 10:
                md_lines.append(f"- ... und {len(unknown_docs) - 10} weitere")
        
        md_lines.append("")
        
        return md_lines
    
    def extract_amounts_from_text(self, text: str) -> List[float]:
        """Extrahiert Geldbeträge aus Text"""
        amount_matches = re.findall(r'([\d.]+,\d{2})[\s]*EUR', text)
        return [float(a.replace('.', '').replace(',', '.')) for a in amount_matches]
    
    def extract_iban_from_text(self, text: str) -> Optional[str]:
        """Extrahiert IBAN aus Text"""
        iban_match = re.search(r'([A-Z]{2}\d{2}\s?[\dA-Z\s]+)', text)
        return iban_match.group(1) if iban_match else None
    
    def extract_balance_from_text(self, text: str) -> Optional[float]:
        """Extrahiert Kontosaldo aus Text"""
        saldo_patterns = [
            r'Saldo[\s:]+([+-]?[\d.]+,\d{2})',
            r'Guthaben[\s:]+([+-]?[\d.]+,\d{2})',
            r'Kontostand[\s:]+([+-]?[\d.]+,\d{2})',
            r'Neuer Saldo[\s:]+([+-]?[\d.]+,\d{2})'
        ]
        
        for pattern in saldo_patterns:
            match = re.search(pattern, text)
            if match:
                saldo_str = match.group(1).replace('.', '').replace(',', '.')
                return float(saldo_str)
        
        return None
    
    def get_base_transaction_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Extrahiert Basis-Transaktionsdaten aus thea_extract Daten"""
        if not data or 'response' not in data:
            return None
            
        response = data.get('response', {})
        json_data = response.get('json', {}) if response.get('json') else {}
        
        # Extrahiere Datum aus dem Dateinamen
        file_path = data.get('metadata', {}).get('file', {}).get('pdf_path', '')
        date_str = self.extract_date_from_filename(os.path.basename(file_path))
        
        # Extrahiere Text
        extracted_text = json_data.get('extracted_text', '') if json_data else ''
        
        return {
            'date': date_str,
            'document_type': json_data.get('document_type', ''),
            'extracted_text': extracted_text,
            'json_data': json_data,
            'original_file': os.path.basename(file_path),
            'description_german': json_data.get('three_word_description_german', ''),
            'description_english': json_data.get('three_word_description_english', ''),
            'summary_german': json_data.get('content_summary_german', '')
        }
    
    def generate_header_section(self, company_name: str, account_type: str, 
                               account_number: str, total_pdf_files: int, 
                               total_thea_files: int, **kwargs) -> List[str]:
        """Generiert den standardisierten Header-Abschnitt"""
        md = []
        
        # Abschnitt 1: Firmen- und Kontoübersicht
        md.append(f"# {company_name} - {account_type}\n")
        md.append(f"## Kontoübersicht\n")
        md.append(f"- **Firma:** {company_name}")
        md.append(f"- **Kontotyp:** {account_type}")
        
        # Account-spezifisches Feld (Kontonummer oder Depotnummer)
        if account_type == "Depotkonto":
            md.append(f"- **Depotnummer:** {account_number}")
        else:
            md.append(f"- **Kontonummer:** {account_number}")
        
        # Verbesserte Dokumentenzählung
        md.append(f"- **PDF-Dokumente:** {total_pdf_files} Dateien")
        
        # Berechne Prozentsatz und zeige Analysestatus
        if total_pdf_files > 0:
            percentage = (total_thea_files / total_pdf_files) * 100
            md.append(f"- **Davon analysiert:** {total_thea_files} ({percentage:.1f}%)")
            not_analyzed = total_pdf_files - total_thea_files
            if not_analyzed > 0:
                md.append(f"- **Noch zu analysieren:** {not_analyzed} Dateien")
        else:
            md.append(f"- **Davon analysiert:** {total_thea_files}")
        
        # Zusätzliche optionale Felder für Saldo und Datum
        latest_saldo = kwargs.get('latest_saldo')
        latest_saldo_date = kwargs.get('latest_saldo_date')
        
        if latest_saldo is not None:
            if account_type == "Depotkonto":
                saldo_text = f"- **Letzter Depotbestand:** {latest_saldo:,.2f} EUR"
            else:
                saldo_text = f"- **Letzter Saldo:** {latest_saldo:,.2f} EUR"
            
            if latest_saldo_date:
                saldo_text += f" (vom {latest_saldo_date})"
            md.append(saldo_text)
        
        # Zinssatz für Geldmarktkonto
        if 'latest_zinssatz' in kwargs and kwargs['latest_zinssatz'] is not None:
            md.append(f"- **Aktueller Zinssatz:** {kwargs['latest_zinssatz']:.2f}%")
            
        md.append(f"- **Zuletzt aktualisiert:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        return md
    
    def save_markdown(self, content: str, output_file: str) -> None:
        """Speichert den Markdown-Inhalt in eine Datei"""
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(content)
    
    def print_summary(self, output_file: str, analysis: Dict[str, Any]) -> None:
        """Gibt eine Zusammenfassung der Analyse aus"""
        print(f"✓ {output_file} erstellt")
        print(f"  - {analysis['total_pdf_files']} PDF-Dokumente gefunden")
        print(f"  - {analysis['total_thea_files']} THEA-Analysen verarbeitet")


def calculate_monthly_aggregates(transactions: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Berechnet monatliche Aggregate aus Transaktionen"""
    monthly_data = defaultdict(lambda: {
        'count': 0,
        'volume': 0,
        'eingaenge': 0,
        'ausgaenge': 0
    })
    
    for trans in transactions:
        if trans.get('date'):
            month_key = trans['date'][:7]  # YYYY-MM
            monthly_data[month_key]['count'] += 1
            
            # Volumen
            if 'max_amount' in trans and trans['max_amount'] > 0:
                monthly_data[month_key]['volume'] += trans['max_amount']
            
            # Ein- und Ausgänge
            if 'eingaenge' in trans:
                monthly_data[month_key]['eingaenge'] += trans.get('eingaenge', 0)
            if 'ausgaenge' in trans:
                monthly_data[month_key]['ausgaenge'] += trans.get('ausgaenge', 0)
    
    return dict(monthly_data)


def calculate_yearly_aggregates(transactions: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Berechnet jährliche Aggregate aus Transaktionen"""
    yearly_data = defaultdict(lambda: {
        'count': 0,
        'volume': 0,
        'eingaenge': 0,
        'ausgaenge': 0,
        'zinsertraege': 0
    })
    
    for trans in transactions:
        if trans.get('date'):
            year = trans['date'][:4]
            yearly_data[year]['count'] += 1
            
            # Volumen
            if 'max_amount' in trans and trans['max_amount'] > 0:
                yearly_data[year]['volume'] += trans['max_amount']
            
            # Ein- und Ausgänge
            if 'eingaenge' in trans:
                yearly_data[year]['eingaenge'] += trans.get('eingaenge', 0)
            if 'ausgaenge' in trans:
                yearly_data[year]['ausgaenge'] += trans.get('ausgaenge', 0)
            
            # Zinserträge
            if 'zinsertrag' in trans and trans['zinsertrag']:
                yearly_data[year]['zinsertraege'] += trans['zinsertrag']
    
    return dict(yearly_data)