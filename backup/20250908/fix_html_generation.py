#!/usr/bin/env python3
"""
Script to fix the HTML generation in Depotkonto.py
"""

import re

# Read the current file
with open('Depotkonto.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find the generate_html method and replace references to 'md' with proper HTML generation
# The current method still uses md.append() which is wrong

# Replace the faulty md references
content = re.sub(r'\bmd\.extend\(', 'html_parts.extend(', content)
content = re.sub(r'\bmd\.append\(', 'html_parts.append(', content)
content = re.sub(r'\bmd\s*=\s*\[\]', 'html_parts = []', content)

# Also need to update the return statement
content = re.sub(
    r"return '\n'.join\(md\)",
    "return html + '\\n'.join(html_parts) + self._create_html_footer()",
    content
)

# Write the fixed content back
with open('Depotkonto_fixed.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Fixed file created as Depotkonto_fixed.py")
print("Now need to add proper HTML generation for tables and content")