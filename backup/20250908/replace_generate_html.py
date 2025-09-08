#!/usr/bin/env python3
"""Replace the generate_html method with a working HTML version"""

import re

# Read the file
with open('Depotkonto.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find the start and end of generate_html method
start_line = None
end_line = None

for i, line in enumerate(lines):
    if 'def generate_html(self, analysis:' in line:
        start_line = i
    elif start_line is not None and line.strip().startswith('def ') and not line.strip().startswith('def _'):
        end_line = i
        break

if start_line is None or end_line is None:
    print(f"Could not find method boundaries. Start: {start_line}, End: {end_line}")
    exit(1)

print(f"Found generate_html from line {start_line+1} to {end_line}")

# Create the new method
new_method = '''    def generate_html(self, analysis: Dict[str, Any]) -> str:
        """Generiert HTML-Bericht aus der Analyse"""
        if not analysis:
            return self._create_error_html()
        
        # Start HTML document
        html = self._create_html_header(analysis)
        
        # Main heading and info box
        html += f"""
    <h1>{analysis['company_name']} - Depotkonto {analysis['depot_number']}</h1>
    
    <div class="info-box">
        <h2 style="color: white; border: none; margin: 0;">Kontoübersicht</h2>
        <div class="info-grid">
            <div class="info-item">
                <div class="info-label">Kontoinhaber</div>
                <div class="info-value">{analysis['company_name']}</div>
            </div>
            <div class="info-item">
                <div class="info-label">Depotnummer</div>
                <div class="info-value">{analysis['depot_number']}</div>
            </div>
            <div class="info-item">
                <div class="info-label">PDF-Dokumente</div>
                <div class="info-value">{analysis['total_pdf_files']}</div>
            </div>
            <div class="info-item">
                <div class="info-label">THEA-Analysen</div>
                <div class="info-value">{analysis['total_thea_files']}</div>
            </div>"""
        
        if analysis.get('latest_balance'):
            latest_balance_str = self.format_number_german(analysis['latest_balance'], 2)
            latest_date = self.format_date_german(analysis.get('latest_balance_date'))
            html += f"""
            <div class="info-item">
                <div class="info-label">Letzter Depotbestand</div>
                <div class="info-value">{latest_balance_str} EUR</div>
            </div>
            <div class="info-item">
                <div class="info-label">Stand</div>
                <div class="info-value">{latest_date}</div>
            </div>"""
        
        html += """
        </div>
    </div>
"""
        
        # Transaction statistics
        if analysis.get('statistics'):
            html += "<h2>Transaktionsstatistik</h2>"
            html += '<div class="stats-grid">'
            
            # Group statistics
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
                elif 'Kostenaufstellung' in trans_type:
                    categories['Kostenaufstellung'].append((trans_type, count))
                else:
                    categories['Sonstige'].append((trans_type, count))
            
            for category, items in categories.items():
                if items:
                    html += f'<div class="stat-card"><h4>{category}</h4><ul>'
                    for trans_type, count in items:
                        display_type = trans_type.replace(f'{category}-', '')
                        html += f'<li>{display_type}: {count}</li>'
                    html += '</ul></div>'
            
            html += '</div>'
        
        # Transaction table with special row coloring
        if analysis.get('transactions'):
            html += """
    <h2>Transaktionsverlauf</h2>
    <table>
        <thead>
            <tr>
                <th>Nr.</th>
                <th>Wertst.</th>
                <th>Handel</th>
                <th>Dokument</th>
                <th>Typ</th>
                <th>ISIN</th>
                <th>Stück</th>
                <th>Kurs</th>
                <th>Kurswert</th>
                <th>G/V</th>
                <th>Dokument</th>
            </tr>
        </thead>
        <tbody>
"""
            
            # Create depot statement lookup for enrichment
            depot_statement_lookup = {}
            balance_info = analysis.get('balance_info', {})
            for stmt in balance_info.get('statements', []):
                file_key = os.path.basename(stmt['file'])
                depot_statement_lookup[file_key] = {
                    'isin': stmt.get('isin'),
                    'shares': stmt.get('shares'),
                    'balance': stmt.get('closing_balance')
                }
            
            transaction_number = 0
            for trans in analysis['transactions']:
                transaction_number += 1
                
                # Date formatting
                value_date = trans.get('value_date')
                execution_date = trans.get('execution_date')
                doc_date = trans.get('date')
                
                if not value_date:
                    value_date = execution_date or trans.get('stichtag') or doc_date
                if not execution_date:
                    execution_date = trans.get('stichtag') or doc_date
                
                value_date_str = self.format_date_german(value_date) if value_date else 'N/A'
                execution_date_str = self.format_date_german(execution_date) if execution_date else 'N/A'
                doc_date_str = self.format_date_german(doc_date) if doc_date else 'N/A'
                
                trans_type = trans['type']
                
                # Determine row class based on transaction type
                row_class = ""
                if 'Depotabschluss' in trans_type:
                    row_class = "depot-statement-row"
                    # Enrich with depot statement data
                    file_key = os.path.basename(trans.get('file', ''))
                    if file_key in depot_statement_lookup:
                        stmt_data = depot_statement_lookup[file_key]
                        trans['isin'] = trans.get('isin') or stmt_data.get('isin')
                        trans['shares'] = trans.get('shares') or stmt_data.get('shares')
                elif 'Verkauf' in trans_type and 'Ausführungsanzeige' not in trans_type:
                    if trans.get('profit_loss') is not None:
                        if trans['profit_loss'] > 0:
                            row_class = "profit-row"
                        elif trans['profit_loss'] < 0:
                            row_class = "loss-row"
                        else:
                            row_class = "neutral-row"
                elif trans_type not in ['Kauf', 'Orderabrechnung-Kauf']:
                    row_class = "misc-row"
                
                # Format display values
                isin = trans.get('isin', 'N/A')
                shares = str(trans.get('shares', '')) if trans.get('shares') else '-'
                
                if trans.get('execution_price'):
                    price_str = self.format_number_german(trans['execution_price'], 2)
                else:
                    price_str = '-'
                
                kurswert = self.format_number_german(trans['gross_amount'], 2) if trans.get('gross_amount') else '-'
                
                profit_loss_str = '-'
                if trans.get('profit_loss') is not None:
                    profit_loss_str = self.format_number_german(trans['profit_loss'], 2)
                
                # Shorten document name
                doc_name = trans.get('file', '')
                if len(doc_name) > 30:
                    doc_name = doc_name[:27] + '...'
                
                doc_link = f'<a href="docs/{analysis["depot_info"]["folder"]}/{trans.get("file", "")}">{doc_name}</a>'
                
                # Shorten type display
                if 'Orderabrechnung-' in trans_type:
                    display_type = trans_type.replace('Orderabrechnung-', '')
                elif 'Depotabschluss-' in trans_type:
                    display_type = 'Depotabschluss'
                else:
                    display_type = trans_type
                
                html += f"""
            <tr class="{row_class}">
                <td>{transaction_number}</td>
                <td>{value_date_str}</td>
                <td>{execution_date_str}</td>
                <td>{doc_date_str}</td>
                <td>{display_type}</td>
                <td>{isin}</td>
                <td>{shares}</td>
                <td class="number">{price_str}</td>
                <td class="number">{kurswert}</td>
                <td class="number">{profit_loss_str}</td>
                <td>{doc_link}</td>
            </tr>"""
            
            html += """
        </tbody>
    </table>
"""
        
        # Add footer
        html += self._create_html_footer()
        
        return html
    
'''

# Replace the method
new_lines = lines[:start_line] + [new_method] + lines[end_line:]

# Write the modified file
with open('Depotkonto.py', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print("✓ Successfully replaced generate_html method")
print(f"  Removed {end_line - start_line} lines")
print(f"  Added {len(new_method.splitlines())} lines")