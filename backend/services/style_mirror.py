import re
from collections import Counter

class StyleMirror:
    def __init__(self):
        self.dna = {
            "avg_sentence_length": 15,
            "vocabulary_complexity": "moderate",
            "punctuation_habits": {},
            "common_rhythms": []
        }

    def load_dna(self, dna_data: dict):
        """[SOVEREIGN HYDRATION]: Injects an existing DNA fingerprint into the mirror."""
        if dna_data:
            self.dna.update(dna_data)

    def extract_authorial_dna(self, text: str):
        """[SOVEREIGN ANALYSIS]: Extracts the stylistic fingerprint of the provided manuscript text."""
        if not text or len(text) < 100:
            return self.dna

        # 1. Sentence Length Analysis
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        if sentences:
            avg_len = sum(len(s.split()) for s in sentences) / len(sentences)
            self.dna["avg_sentence_length"] = round(avg_len, 2)

        # 2. Punctuation Fingerprint
        punctuation = re.findall(r'[,;:\-\(\)\"\']', text)
        self.dna["punctuation_habits"] = dict(Counter(punctuation))

        # 3. Vocabulary Cadence
        words = text.lower().split()
        unique_words = len(set(words))
        if unique_words / len(words) > 0.6:
            self.dna["vocabulary_complexity"] = "high"
        elif unique_words / len(words) > 0.4:
            self.dna["vocabulary_complexity"] = "moderate"
        else:
            self.dna["vocabulary_complexity"] = "lean"

        return self.dna

    def get_muse_prompt_prefix(self):
        """[SOVEREIGN INJECTION]: Generates a system prompt prefix to force the AI into the mirrored style."""
        return (
            f"STYLE MIRROR ACTIVE: Mirror the author's voice. "
            f"Cadence: {self.dna['vocabulary_complexity']}. "
            f"Sentence Density: ~{self.dna['avg_sentence_length']} words. "
            f"Punctuation Pattern: {self.dna['punctuation_habits']}. "
            f"Maintain high fidelity to these authorial rhythms."
        )

# Global singleton for the boardroom
MIRROR = StyleMirror()
