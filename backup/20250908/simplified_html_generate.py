def generate_html(self, analysis: Dict[str, Any]) -> str:
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
        for stmt in analysis.get('balance_info', {}).get('statements', []):
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
                file_key = os.path.basename(trans['file'])
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
                <td>{price_str}</td>
                <td>{kurswert}</td>
                <td>{profit_loss_str}</td>
                <td>{doc_link}</td>
            </tr>"""
        
        html += """
        </tbody>
    </table>
"""
    
    # Add footer
    html += self._create_html_footer()
    
    return html