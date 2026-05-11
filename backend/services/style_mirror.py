from .ai import linguistic_steward

class StyleMirror:
    def __init__(self):
        self.dna = {
            "avg_sentence_length": 15,
            "rhythm_variance": 0,
            "vocabulary_complexity": "moderate",
            "punctuation_habits": {},
        }

    def load_dna(self, dna_data: dict):
        """[SOVEREIGN HYDRATION]: Injects an existing DNA fingerprint into the mirror."""
        if dna_data:
            self.dna.update(dna_data)

    def extract_authorial_dna(self, text: str):
        """[SOVEREIGN ANALYSIS]: Extracts the stylistic fingerprint of the provided manuscript text."""
        if not text or len(text) < 100:
            return self.dna

        # 1. Rhythmic Analysis
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        if sentences:
            avg_len = sum(len(s.split()) for s in sentences) / len(sentences)
            self.dna["avg_sentence_length"] = round(avg_len, 2)
            self.dna["rhythm_variance"] = linguistic_steward.calculate_sentence_variance(text)

        # 2. Punctuation Fingerprint
        self.dna["punctuation_habits"] = linguistic_steward.extract_signature_punctuation(text)

        # 3. Readability & Complexity
        self.dna["vocabulary_complexity"] = linguistic_steward.calculate_readability(text)

        return self.dna

    def get_muse_prompt_prefix(self):
        """[SOVEREIGN INJECTION]: Generates a system prompt prefix to force the AI into the mirrored style."""
        rhythm = "Monotone" if self.dna['rhythm_variance'] < 5 else "Rhythmic" if self.dna['rhythm_variance'] < 10 else "High-Variation/Experimental"
        
        return (
            f"STYLE MIRROR ACTIVE: Mirror the author's voice. "
            f"Complexity: {self.dna['vocabulary_complexity']}. "
            f"Rhythm Profile: {rhythm} (Variance: {self.dna['rhythm_variance']}). "
            f"Avg Sentence Length: {self.dna['avg_sentence_length']} words. "
            f"Punctuation Texture: {self.dna['punctuation_habits']}. "
            f"Maintain strict fidelity to these authorial patterns."
        )

# Global singleton for the boardroom
MIRROR = StyleMirror()
