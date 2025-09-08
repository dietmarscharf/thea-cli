#!/usr/bin/env python3
"""Replace the generate_html method with the complete version"""

# Read the original file
with open('Depotkonto.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Read the complete HTML generation method
with open('complete_html_generate.py', 'r', encoding='utf-8') as f:
    new_method_lines = f.readlines()

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

# Replace the method
new_lines = lines[:start_line] + new_method_lines + lines[end_line:]

# Write the modified file
with open('Depotkonto.py', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print("✓ Successfully replaced generate_html method with complete version")
print(f"  Removed {end_line - start_line} lines")
print(f"  Added {len(new_method_lines)} lines")