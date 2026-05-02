import os
import re

folder = r"C:/Users/saint/OneDrive/Documents/This Close/Demo/This Close"
output_path = os.path.join(folder, "Unified_Manuscript.md")

manuscript_pages = {}
if os.path.exists(output_path):
    with open(output_path, "r", encoding="utf-8") as mr:
        m_content = mr.read()
        pattern = r'--- \[PAGE START: page_(\d+)\.rtf\] ---\n(.*?)(?=\n--- \[PAGE START:|\n--- \[MISSING PAGE:|\n--- \[UNSORTED|$)'
        matches = re.finditer(pattern, m_content, re.DOTALL)
        for match in matches:
            p_num = int(match.group(1))
            p_text = match.group(2).strip()
            manuscript_pages[p_num] = p_text

total_goal = 498
expected_range = set(range(1, total_goal + 1))
root_nums = set()
gaps = [i for i in expected_range if i not in root_nums and i not in manuscript_pages]
print(f"Gaps found: {len(gaps)}")
if len(gaps) > 0:
    print(f"First 10 gaps: {gaps[:10]}")
    print(f"Is 1 in manuscript_pages? {1 in manuscript_pages}")
