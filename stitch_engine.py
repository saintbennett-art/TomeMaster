with open('backend/services/ai_service.py', 'w', encoding='utf-8') as f:
    for part in ['engine_p1.txt', 'engine_p2.txt', 'engine_p3.txt']:
        with open(part, 'r', encoding='utf-8') as p:
            f.write(p.read())
print("Stitch Complete: ai_service.py re-unified to absolute origin.")
