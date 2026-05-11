import re
import math
from collections import Counter

def calculate_sentence_variance(text: str) -> float:
    """[RHYTHM ANALYZER]: Calculates the standard deviation of sentence lengths to detect authorial cadence."""
    sentences = re.split(r'[.!?]+', text)
    lengths = [len(s.split()) for s in sentences if s.strip()]
    
    if not lengths:
        return 0.0
        
    avg = sum(lengths) / len(lengths)
    variance = sum((x - avg) ** 2 for x in lengths) / len(lengths)
    return round(math.sqrt(variance), 2)

def calculate_readability(text: str) -> str:
    """[READABILITY ENGINE]: Simple Flesch-style complexity estimation."""
    words = text.split()
    if not words: return "lean"
    
    avg_word_len = sum(len(w) for w in words) / len(words)
    
    if avg_word_len > 6.0: return "academic/high-density"
    if avg_word_len > 5.0: return "literary/moderate"
    return "conversational/lean"

def extract_signature_punctuation(text: str) -> dict:
    """[TEXTURE ANALYSIS]: Maps the frequency of rhetorical punctuation (semicolons, dashes, etc.)."""
    targets = [';', ':', '—', '-', '...', '!', '?', '"', '(', ')']
    punctuation = [char for char in text if char in targets]
    return dict(Counter(punctuation))
