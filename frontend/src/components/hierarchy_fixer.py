import os

def fix_hierarchy():
    path = r'c:\Users\saint\.gemini\antigravity\playground\dark-schrodinger\frontend\src\components\MainEditor.tsx'
    with open(path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # 1. Stabilize Header Assembly (lines 1070-1085)
    header_fixed = False
    for i in range(len(lines)):
        if "Kindle Previewer 3" in lines[i]:
            # We found the transition. We need to find the </header> and ensure 4 divs are before it.
            for j in range(i, i+15):
                if "</header>" in lines[j]:
                    new_header_block = [
                        "                    </div>\n",
                        "                  )}\n",
                        "                </div>\n",
                        "              </div>\n",
                        "            </div>\n",
                        "          </div>\n",
                        "        </header>\n"
                    ]
                    # Find where the block starts (usually after the </a> tag)
                    for k in range(i, j):
                        if "</a>" in lines[k]:
                            lines[k+1:j+1] = new_header_block
                            header_fixed = True
                            break
                if header_fixed: break
        if header_fixed: break

    # 2. Stabilize Footer Assembly
    # Outer Wrappers opened at 833, 834, 835, 1102, 1103. 
    # Header was closed above.
    # We need precisely 4-5 divs before the </main> tag.
    footer_lines = [
        "                 )}\n",
        "              </div>\n",
        "           </div>\n",
        "        </div>\n",
        "      </div>\n",
        "    </div>\n",
        "  </div>\n",
        "</main>\n",
        "  );\n",
        "}\n"
    ]
    
    # Find the </main> tag and replace the surrounding closure
    for i in range(len(lines)-1, 0, -1):
        if "</main>" in lines[i]:
            # Backtrack to the first expression closing (usually line 1301 area)
            for j in range(i, i-10, -1):
                if ")}" in lines[j] or "</div>" in lines[j]:
                    lines[j:len(lines)] = footer_lines
                    break
            break

    with open(path, 'w', encoding='utf-8') as f:
        f.writelines(lines)
    print("Sovereign Structural Restoration: SUCCESS")

if __name__ == "__main__":
    fix_hierarchy()
