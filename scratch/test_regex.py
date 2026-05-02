import os
import re

folder = r"C:/Users/saint/OneDrive/Documents/This Close/Demo/This Close"
output_path = os.path.join(folder, "Unified_Manuscript.md")

with open(output_path, "r", encoding="utf-8") as mr:
    m_content = mr.read()

pattern = r'--- \[PAGE START: page_(\d+)\.rtf\] ---\n(.*?)(?=\n--- \[PAGE START:|\n--- \[MISSING PAGE:|\n--- \[UNSORTED|$)'
matches = re.finditer(pattern, m_content, re.DOTALL)
count = 0
for match in matches:
    count += 1

print(f"Matches found: {count}")
