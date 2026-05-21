import asyncio
from services.exporter import generate_docx

async def test():
    try:
        html = "<h1>Test</h1><p>Paragraph</p>"
        res = generate_docx(html, [])
        print("DOCX Success, size:", len(res.getvalue()))
    except Exception as e:
        print("DOCX Error:", str(e))

asyncio.run(test())
