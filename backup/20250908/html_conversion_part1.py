# This file contains the complete HTML generation method
# Part 1: Helper methods and main structure

def _create_html_header(self, analysis: Dict[str, Any]) -> str:
    """Erstellt den HTML-Header mit umfassendem CSS"""
    company_name = analysis['company_name']
    depot_number = analysis['depot_number']
    
    return f"""<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{company_name} - Depotkonto {depot_number}</title>
    <style>
        /* Grundlegende Styles */
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background: #f5f5f5;
            color: #333;
            line-height: 1.6;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        
        /* Überschriften */
        h1 {{
            color: #2c3e50;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
            margin-bottom: 30px;
        }}
        
        h2 {{
            color: #34495e;
            margin-top: 40px;
            margin-bottom: 20px;
            border-bottom: 2px solid #ecf0f1;
            padding-bottom: 8px;
        }}
        
        h3 {{
            color: #7f8c8d;
            margin-top: 25px;
            margin-bottom: 15px;
        }}
        
        /* Info-Box für Kontoübersicht */
        .info-box {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 30px;
        }}
        
        .info-box .info-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-top: 15px;
        }}
        
        .info-box .info-item {{
            background: rgba(255,255,255,0.1);
            padding: 10px;
            border-radius: 4px;
        }}
        
        .info-box .info-label {{
            font-size: 0.85em;
            opacity: 0.9;
            margin-bottom: 5px;
        }}
        
        .info-box .info-value {{
            font-size: 1.2em;
            font-weight: bold;
        }}
        
        /* Tabellen */
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            font-size: 14px;
        }}
        
        th {{
            background: #34495e;
            color: white;
            padding: 12px 8px;
            text-align: left;
            font-weight: 500;
            position: sticky;
            top: 0;
            z-index: 10;
        }}
        
        td {{
            padding: 10px 8px;
            border-bottom: 1px solid #ecf0f1;
        }}
        
        tr:hover {{
            background: #f8f9fa;
        }}
        
        /* Alternating row colors for better readability */
        tbody tr:nth-child(even) {{
            background-color: #f9f9f9;
        }}
        
        /* Spezielle Zeilen-Styles für Transaktionen */
        .profit-row {{
            background-color: #0173B2 !important;
            color: white !important;
        }}
        
        .profit-row td {{
            color: white !important;
        }}
        
        .loss-row {{
            background-color: #DE8F05 !important;
            color: white !important;
        }}
        
        .loss-row td {{
            color: white !important;
        }}
        
        .depot-statement-row {{
            background-color: #000000 !important;
            color: white !important;
        }}
        
        .depot-statement-row td {{
            color: white !important;
        }}
        
        .depot-statement-row a {{
            color: #64b5f6 !important;
        }}
        
        .misc-row {{
            color: #6c757d !important;
        }}
        
        .misc-row td {{
            color: #6c757d !important;
        }}
        
        .neutral-row {{
            background-color: #e9ecef !important;
        }}
        
        /* Links */
        a {{
            color: #3498db;
            text-decoration: none;
        }}
        
        a:hover {{
            text-decoration: underline;
        }}
        
        .profit-row a, .loss-row a {{
            color: white !important;
            text-decoration: underline;
        }}
        
        /* Zahlen-Formatierung */
        .number {{
            text-align: right;
            font-family: "Courier New", monospace;
        }}
        
        .positive {{
            color: #27ae60;
            font-weight: bold;
        }}
        
        .negative {{
            color: #e74c3c;
            font-weight: bold;
        }}
        
        /* Statistik-Boxen */
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }}
        
        .stat-card {{
            background: #f8f9fa;
            padding: 15px;
            border-radius: 8px;
            border-left: 4px solid #3498db;
        }}
        
        .stat-card h4 {{
            margin: 0 0 10px 0;
            color: #34495e;
        }}
        
        .stat-card ul {{
            margin: 5px 0;
            padding-left: 20px;
        }}
        
        /* Warnungen */
        .warning {{
            background: #fff3cd;
            border-left: 4px solid #ffc107;
            padding: 15px;
            margin: 20px 0;
            border-radius: 4px;
        }}
        
        .warning strong {{
            color: #856404;
        }}
        
        /* Erläuterungen */
        .explanation-box {{
            background: #e3f2fd;
            border-left: 4px solid #2196f3;
            padding: 15px;
            margin: 20px 0;
            border-radius: 4px;
        }}
        
        .explanation-box h4 {{
            margin-top: 0;
            color: #1565c0;
        }}
        
        /* Footer */
        .footer {{
            margin-top: 50px;
            padding-top: 20px;
            border-top: 2px solid #ecf0f1;
            text-align: center;
            color: #7f8c8d;
            font-size: 0.9em;
        }}
        
        /* Responsive Design */
        @media (max-width: 768px) {{
            .container {{
                padding: 15px;
            }}
            
            table {{
                font-size: 12px;
            }}
            
            th, td {{
                padding: 6px 4px;
            }}
            
            .info-grid {{
                grid-template-columns: 1fr;
            }}
        }}
        
        /* Print styles */
        @media print {{
            body {{
                background: white;
            }}
            
            .container {{
                box-shadow: none;
                padding: 0;
            }}
            
            .page-break {{
                page-break-after: always;
            }}
        }}
    </style>
</head>
<body>
<div class="container">
"""

def _create_html_footer(self) -> str:
    """Erstellt den HTML-Footer"""
    from datetime import datetime
    current_date = datetime.now().strftime("%d.%m.%Y %H:%M")
    
    return f"""
    <div class="footer">
        <p>Erstellt am {current_date} mit THEA Document Analysis System</p>
        <p>© 2024 - Automated Financial Document Processing</p>
    </div>
</div>
</body>
</html>"""

def _create_error_html(self) -> str:
    """Erstellt eine Fehler-HTML-Seite"""
    return """<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Fehler bei der Analyse</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
        .error { background: #fff; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        h1 { color: #dc3545; }
    </style>
</head>
<body>
    <div class="error">
        <h1>Fehler bei der Analyse</h1>
        <p>Keine Daten verfügbar.</p>
    </div>
</body>
</html>"""