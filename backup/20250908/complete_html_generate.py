    def generate_html(self, analysis: Dict[str, Any]) -> str:
        """Generiert vollständigen HTML-Bericht aus der Analyse"""
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
        
        # SECTION 1: Depotabschluss-Übersicht (Depot Statement Overview)
        if analysis.get('depot_statements'):
            html += "<h2>Depotabschluss-Übersicht</h2>"
            
            # Combine annual and quarterly statements
            all_statements = []
            
            for statement in analysis.get('annual_statements', []):
                statement_copy = statement.copy()
                statement_copy['type_display'] = 'Jahresabschluss'
                all_statements.append(statement_copy)
            
            for statement in analysis.get('quarterly_statements', []):
                statement_copy = statement.copy()
                statement_copy['type_display'] = 'Quartalsabschluss'
                all_statements.append(statement_copy)
            
            # Sort by balance date
            all_statements.sort(key=lambda x: x['balance_date'] if x['balance_date'] else '0000-00-00')
            
            if all_statements:
                html += """
    <h3>Alle Depotabschlüsse (chronologisch)</h3>
    <table>
        <thead>
            <tr>
                <th>Typ</th>
                <th>Stichtag</th>
                <th>Dokumentdatum</th>
                <th>Stück</th>
                <th>ISIN</th>
                <th>Depotbestand (EUR)</th>
                <th>Dokument</th>
            </tr>
        </thead>
        <tbody>
"""
                for statement in all_statements:
                    type_display = statement['type_display']
                    doc_date = self.format_date_german(statement.get('doc_date', 'N/A'))
                    balance_date = self.format_date_german(statement.get('balance_date', 'N/A'))
                    shares_str = str(statement['shares']) if statement.get('shares') else '-'
                    isin_str = statement.get('isin', '-')
                    
                    if statement.get('closing_balance') is not None:
                        closing = self.format_number_german(statement['closing_balance'], 2)
                    else:
                        closing = 'N/A'
                    
                    file_name = statement['file']
                    display_name = file_name[:37] + '...' if len(file_name) > 40 else file_name
                    doc_link = f'<a href="docs/{analysis["depot_info"]["folder"]}/{file_name}">{display_name}</a>'
                    
                    html += f"""
            <tr>
                <td>{type_display}</td>
                <td>{balance_date}</td>
                <td>{doc_date}</td>
                <td class="number">{shares_str}</td>
                <td>{isin_str}</td>
                <td class="number">{closing}</td>
                <td>{doc_link}</td>
            </tr>"""
                
                html += """
        </tbody>
    </table>
"""
                # Summary
                annual_count = len(analysis.get('annual_statements', []))
                quarterly_count = len(analysis.get('quarterly_statements', []))
                html += f'<p><em>Gesamt: {annual_count} Jahresabschlüsse und {quarterly_count} Quartalsabschlüsse</em></p>'
            
            # Overall summary
            if analysis.get('latest_balance'):
                latest_date = self.format_date_german(analysis.get('latest_balance_date', 'N/A'))
                latest_balance_str = self.format_number_german(analysis['latest_balance'], 2)
                html += f'<p><strong>Letzter bekannter Depotbestand: {latest_balance_str} EUR</strong> (Stand: {latest_date})</p>'
            
            total_statements = len(analysis.get('depot_statements', []))
            if total_statements > 0:
                first_date = min(s['balance_date'] for s in analysis['depot_statements'] if s.get('balance_date'))
                last_date = max(s['balance_date'] for s in analysis['depot_statements'] if s.get('balance_date'))
                first_date_german = self.format_date_german(first_date)
                last_date_german = self.format_date_german(last_date)
                html += f'<p><em>Gesamtzeitraum: {first_date_german} bis {last_date_german}</em></p>'
        
        # SECTION 2: Jährliche Kostenanalyse (MiFID II)
        if analysis.get('cost_information'):
            html += """
    <h2>Jährliche Kostenanalyse (MiFID II)</h2>
    <p>Gesetzlich vorgeschriebene Kostenaufstellung gemäß Art. 50 der Verordnung (EU) 2017/565:</p>
    <table>
        <thead>
            <tr>
                <th>Jahr</th>
                <th>Dokumentdatum</th>
                <th>Dienstleistungskosten (netto)</th>
                <th>Depotentgelte (netto)</th>
                <th>Zwischensumme (netto)</th>
                <th>USt (19%)</th>
                <th>Gesamtkosten (brutto)</th>
                <th>Umsatzvolumen</th>
                <th>Ø Depotbestand</th>
                <th>Kostenquote</th>
                <th>Dokument</th>
            </tr>
        </thead>
        <tbody>
"""
            # Sort by year
            years = sorted(analysis['cost_information'].keys())
            
            for year in years:
                cost_data = analysis['cost_information'][year]
                
                # Format amounts in German style
                service_costs_net = self.format_number_german(cost_data.get('service_costs_net', 0), 2)
                depot_fees_net = self.format_number_german(cost_data.get('depot_fees_net', 0), 2)
                subtotal_net = self.format_number_german(cost_data.get('total_costs_net', 0), 2)
                total_costs = self.format_number_german(cost_data.get('total_costs', 0), 2)
                total_vat = self.format_number_german(cost_data.get('total_costs_vat', 0), 2)
                volume = self.format_number_german(cost_data.get('trading_volume', 0), 2) if cost_data.get('trading_volume') else '-'
                avg_depot = self.format_number_german(cost_data.get('avg_depot_value', 0), 2) if cost_data.get('avg_depot_value') else '-'
                
                # Cost percentage
                if cost_data.get('cost_percentage_depot'):
                    cost_quote = self.format_number_german(cost_data['cost_percentage_depot'], 2) + '%'
                else:
                    cost_quote = '-'
                
                # Format document date
                doc_date = self.format_date_german(cost_data.get('doc_date', ''))
                
                # Create document link
                file_name = cost_data.get('file', '')
                display_name = file_name[:37] + "..." if len(file_name) > 40 else file_name
                doc_link = f'<a href="docs/{analysis["depot_info"]["folder"]}/{file_name}">{display_name}</a>'
                
                html += f"""
            <tr>
                <td>{year}</td>
                <td>{doc_date}</td>
                <td class="number">{service_costs_net}</td>
                <td class="number">{depot_fees_net}</td>
                <td class="number">{subtotal_net}</td>
                <td class="number">{total_vat}</td>
                <td class="number"><strong>{total_costs}</strong></td>
                <td class="number">{volume}</td>
                <td class="number">{avg_depot}</td>
                <td class="number">{cost_quote}</td>
                <td>{doc_link}</td>
            </tr>"""
            
            html += """
        </tbody>
    </table>
"""
            # Cost summary
            if len(years) > 0:
                total_all_costs = sum(c.get('total_costs', 0) for c in analysis['cost_information'].values())
                total_all_volume = sum(c.get('trading_volume', 0) for c in analysis['cost_information'].values() if c.get('trading_volume'))
                
                if total_all_costs > 0:
                    total_str = self.format_number_german(total_all_costs, 2)
                    html += f'<p><strong>Gesamtkosten {years[0]}-{years[-1]}: {total_str} €</strong></p>'
                
                if total_all_volume > 0:
                    volume_str = self.format_number_german(total_all_volume, 2)
                    html += f'<p><em>Gesamtes Handelsvolumen: {volume_str} €</em></p>'
                
                # Explanations
                html += """
    <div class="explanation-box">
        <h3>Erläuterungen zur Kostenberechnung:</h3>
        <h4>Kostenzusammensetzung:</h4>
        <ul>
            <li><strong>Dienstleistungskosten:</strong> Beinhalten alle Kosten für Wertpapiergeschäfte (Kauf/Verkauf), Ordergebühren und sonstige Transaktionskosten</li>
            <li><strong>Depotentgelte:</strong> Jährliche Verwahrungsgebühren für die Führung des Depotkontos (übergreifende Kosten)</li>
            <li><strong>Zwischensumme (netto):</strong> Summe aus Dienstleistungskosten und Depotentgelten ohne Umsatzsteuer</li>
            <li><strong>USt (19%):</strong> Gesetzliche Umsatzsteuer auf alle Kosten</li>
            <li><strong>Gesamtkosten (brutto):</strong> Vollständige Kosten inklusive 19% Umsatzsteuer</li>
        </ul>
        <h4>Wichtige Hinweise:</h4>
        <ul>
            <li>✓ Die Depotentgelte sind <strong>in den Gesamtkosten enthalten</strong></li>
            <li>✓ Alle Beträge in den verlinkten Dokumenten sind <strong>Bruttobeträge</strong> (bereits inkl. 19% USt)</li>
            <li>✓ Die Nettobeträge werden berechnet: Netto = Brutto ÷ 1,19</li>
        </ul>
        <p><em>Diese Aufstellung entspricht den gesetzlichen Anforderungen gemäß Art. 50 der Verordnung (EU) 2017/565 (MiFID II).</em></p>
    </div>
"""
        
        # SECTION 3: Transaction statistics
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
        
        # SECTION 4: Wertpapiere nach ISIN
        if analysis.get('isin_groups'):
            html += "<h2>Wertpapiere (nach ISIN)</h2>"
            for isin, trans_list in analysis['isin_groups'].items():
                if isin == "DE0001234567":
                    html += f'<h3>⚠️ {isin} (UNGÜLTIGE TEST-ISIN)</h3>'
                    html += '<p class="warning">⚠️ <strong>WARNUNG: Dies ist eine Test-ISIN und sollte nicht in Produktivdaten vorkommen!</strong></p>'
                else:
                    html += f'<h3>{isin}</h3>'
                
                html += f'<p><strong>Anzahl Transaktionen:</strong> {len(trans_list)}</p>'
                
                # Calculate sums
                verkauf_summe = sum(t['max_amount'] for t in trans_list if t['type'] == 'Verkauf' or 'Verkauf' in t['type'])
                kauf_summe = sum(t['max_amount'] for t in trans_list if t['type'] == 'Kauf' or 'Kauf' in t['type'])
                
                if verkauf_summe > 0:
                    html += f'<p><strong>Verkaufssumme:</strong> {self.format_number_german(verkauf_summe, 2)} EUR</p>'
                if kauf_summe > 0:
                    html += f'<p><strong>Kaufsumme:</strong> {self.format_number_german(kauf_summe, 2)} EUR</p>'
        
        # SECTION 5: Enhanced Transaction table with cumulative P&L
        if analysis.get('transactions'):
            html += """
    <h2>Transaktionsverlauf (Detailliert)</h2>
    
    <h3>Legende der Spalten:</h3>
    <ul>
        <li><strong>Nr.:</strong> Laufende Nummer der Transaktion</li>
        <li><strong>Wertst.:</strong> Wertstellungsdatum/Valuta (Settlement)</li>
        <li><strong>Handel:</strong> Handelstag/Schlusstag (Ausführung)</li>
        <li><strong>Dokument:</strong> Dokumenterstellungsdatum</li>
        <li><strong>G/V:</strong> Gewinn/Verlust der Transaktion (EUR)</li>
        <li><strong>Kum. G/V:</strong> Kumulierter Gewinn/Verlust (EUR)</li>
    </ul>
    
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
                <th>Kum. G/V</th>
                <th>Dokument</th>
            </tr>
        </thead>
        <tbody>
"""
            
            # Create depot statement lookup for enrichment
            depot_statement_lookup = {}
            for stmt in analysis.get('depot_statements', []):
                file_key = os.path.basename(stmt['file'])
                depot_statement_lookup[file_key] = {
                    'isin': stmt.get('isin'),
                    'shares': stmt.get('shares'),
                    'balance': stmt.get('closing_balance')
                }
            
            transaction_number = 0
            cumulative_pnl = 0.0
            
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
                
                # Update cumulative P&L for sales
                if 'Verkauf' in trans_type and trans.get('profit_loss') is not None:
                    cumulative_pnl += trans['profit_loss']
                
                # Determine row class based on transaction type
                row_class = ""
                if 'Depotabschluss' in trans_type:
                    row_class = "depot-statement-row"
                    # Enrich with depot statement data
                    file_key = os.path.basename(trans.get('original_file', ''))
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
                    profit_loss_str = self.format_number_german(trans['profit_loss'], 2, show_sign=True)
                
                cumulative_str = self.format_number_german(cumulative_pnl, 2, show_sign=True) if cumulative_pnl != 0 else '-'
                
                # Shorten document name
                doc_name = trans.get('original_file', '')
                if len(doc_name) > 30:
                    doc_name = doc_name[:27] + '...'
                
                doc_link = f'<a href="docs/{analysis["depot_info"]["folder"]}/{trans.get("original_file", "")}">{doc_name}</a>'
                
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
                <td class="number">{shares}</td>
                <td class="number">{price_str}</td>
                <td class="number">{kurswert}</td>
                <td class="number {'positive' if trans.get('profit_loss', 0) > 0 else 'negative' if trans.get('profit_loss', 0) < 0 else ''}">{profit_loss_str}</td>
                <td class="number {'positive' if cumulative_pnl > 0 else 'negative' if cumulative_pnl < 0 else ''}">{cumulative_str}</td>
                <td>{doc_link}</td>
            </tr>"""
            
            html += """
        </tbody>
    </table>
"""
            
            # Performance summary
            total_sales = sum(1 for t in analysis['transactions'] if 'Verkauf' in t['type'] and t.get('profit_loss') is not None)
            total_profit = sum(t['profit_loss'] for t in analysis['transactions'] if 'Verkauf' in t['type'] and t.get('profit_loss', 0) > 0)
            total_loss = sum(t['profit_loss'] for t in analysis['transactions'] if 'Verkauf' in t['type'] and t.get('profit_loss', 0) < 0)
            
            if total_sales > 0:
                html += f"""
    <h3>Performance-Zusammenfassung:</h3>
    <ul>
        <li><strong>Anzahl Verkäufe mit G/V:</strong> {total_sales}</li>
        <li><strong>Gesamtgewinn:</strong> <span class="positive">{self.format_number_german(total_profit, 2)} EUR</span></li>
        <li><strong>Gesamtverlust:</strong> <span class="negative">{self.format_number_german(total_loss, 2)} EUR</span></li>
        <li><strong>Netto G/V:</strong> <span class="{'positive' if cumulative_pnl > 0 else 'negative'}">{self.format_number_german(cumulative_pnl, 2)} EUR</span></li>
    </ul>
"""
        
        # SECTION 6: Zeitliche Verteilung (Time Distribution)
        if analysis.get('transactions'):
            monthly_groups = calculate_monthly_aggregates(analysis['transactions'])
            
            if monthly_groups:
                html += """
    <h2>Zeitliche Verteilung</h2>
    <table>
        <thead>
            <tr>
                <th>Monat</th>
                <th>Anzahl Transaktionen</th>
                <th>Gesamtvolumen (EUR)</th>
            </tr>
        </thead>
        <tbody>
"""
                for month in sorted(monthly_groups.keys()):
                    data = monthly_groups[month]
                    html += f"""
            <tr>
                <td>{month}</td>
                <td class="number">{data['count']}</td>
                <td class="number">{self.format_number_german(data['volume'], 2)}</td>
            </tr>"""
                
                html += """
        </tbody>
    </table>
"""
                # Summary
                months = list(monthly_groups.keys())
                first_month = min(months)
                last_month = max(months)
                total_years = len(set(m[:4] for m in months))
                html += f'<p><em>Aktivität in {len(months)} Monaten über {total_years} Jahre ({first_month} bis {last_month})</em></p>'
        
        # Add footer
        html += self._create_html_footer()
        
        return html