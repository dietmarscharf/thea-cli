#!/usr/bin/env python3
"""Test HTML generation by creating a minimal HTML output"""

from Depotkonto import DepotkontoAnalyzer

# Create analyzer instance
analyzer = DepotkontoAnalyzer()

# Create a minimal test analysis
test_analysis = {
    'company_name': 'BLUEITS GmbH',
    'depot_number': '7274079',
    'total_pdf_files': 314,
    'total_thea_files': 314,
    'latest_balance': 123456.78,
    'latest_balance_date': '2024-01-15',
    'transactions': [],
    'statistics': {},
    'isin_groups': {},
    'depot_info': {'folder': 'BLUEITS-Depotkonto-7274079'},
    'depot_path': analyzer.base_path / 'BLUEITS-Depotkonto-7274079'
}

# Test the HTML header generation
try:
    html_header = analyzer._create_html_header(test_analysis)
    print("✓ HTML header generated successfully")
    print(f"  Header length: {len(html_header)} chars")
except Exception as e:
    print(f"✗ Error generating header: {e}")

# Test the HTML footer generation
try:
    html_footer = analyzer._create_html_footer()
    print("✓ HTML footer generated successfully")
    print(f"  Footer length: {len(html_footer)} chars")
except Exception as e:
    print(f"✗ Error generating footer: {e}")

# Create a simple HTML file
simple_html = html_header + """
    <h1>BLUEITS GmbH - Depotkonto 7274079</h1>
    
    <div class="info-box">
        <h2 style="color: white; border: none; margin: 0;">Kontoübersicht</h2>
        <div class="info-grid">
            <div class="info-item">
                <div class="info-label">Kontoinhaber</div>
                <div class="info-value">BLUEITS GmbH</div>
            </div>
            <div class="info-item">
                <div class="info-label">Depotnummer</div>
                <div class="info-value">7274079</div>
            </div>
            <div class="info-item">
                <div class="info-label">PDF-Dokumente</div>
                <div class="info-value">314</div>
            </div>
            <div class="info-item">
                <div class="info-label">THEA-Analysen</div>
                <div class="info-value">314</div>
            </div>
        </div>
    </div>
    
    <h2>Test Table</h2>
    <table>
        <thead>
            <tr>
                <th>Date</th>
                <th>Type</th>
                <th>Amount</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td>01.01.2024</td>
                <td>Buy</td>
                <td>1.000,00 EUR</td>
            </tr>
            <tr class="profit-row">
                <td>15.01.2024</td>
                <td>Sell (Profit)</td>
                <td>1.500,00 EUR</td>
            </tr>
            <tr class="loss-row">
                <td>20.01.2024</td>
                <td>Sell (Loss)</td>
                <td>800,00 EUR</td>
            </tr>
            <tr class="depot-statement-row">
                <td>31.01.2024</td>
                <td>Depot Statement</td>
                <td>123.456,78 EUR</td>
            </tr>
        </tbody>
    </table>
""" + html_footer

# Save test HTML
with open('test_output.html', 'w', encoding='utf-8') as f:
    f.write(simple_html)

print("\n✓ Test HTML file created: test_output.html")
print(f"  Total size: {len(simple_html)} chars")