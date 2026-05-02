import re

text = """
This is a sentence that goes

on and on but it was cut

off by the margin of the

physical page.

And here is a new paragraph.
"""

def restore_text_flow(content: str) -> str:
    # Merge \n\n if the preceding character is not a sentence ender.
    # We consider . ? ! " ' as sentence enders.
    # So if it ends with a letter, digit, comma, dash, etc., we merge.
    merged = re.sub(r'([^.?!\"\'])\s*\n+\s*([a-zA-Z0-9])', r'\1 \2', content)
    return merged

print("Before:")
print(repr(text))
print("After:")
print(repr(restore_text_flow(text)))
