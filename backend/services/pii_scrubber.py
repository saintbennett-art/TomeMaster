import logging

from .logger_service import siem_logger

# [SOVEREIGN BUNDLE]: presidio + spacy are heavy (and fragile to bundle into a
# PyInstaller exe). PII scrubbing is OFF by default (gated by
# preferences.pii_scrub), so we keep those imports and the engine build LAZY —
# they only load the first time scrubbing is actually invoked. This keeps the
# default desktop build lean, fast to boot, and free of the compliance stack.


class PIIScrubberService:
    def __init__(self):
        self.analyzer = None
        self.anonymizer = None

    def _ensure_engines(self):
        """Build the presidio engines on first use. Raises a clear error if the
        compliance stack isn't installed (the default sovereign build omits it)."""
        if self.analyzer is not None:
            return
        try:
            from presidio_analyzer import AnalyzerEngine
            from presidio_anonymizer import AnonymizerEngine

            self.analyzer = AnalyzerEngine()
            self.anonymizer = AnonymizerEngine()
            siem_logger.info(
                "PII Scrubber initialized.", extra={"event_type": "SECURITY_INIT"}
            )
        except Exception as e:
            siem_logger.error(
                f"Failed to initialize PII Scrubber: {e}",
                extra={"event_type": "SECURITY_FAILURE"},
            )
            raise RuntimeError(
                "PII scrubbing is enabled but the compliance stack "
                "(presidio-analyzer, presidio-anonymizer, spacy) is not installed "
                "in this build."
            ) from e

    def anonymize_text(self, text: str) -> str:
        """
        Scans and redacts PII from the provided text before it leaves the boundary.
        Fails closed on error.
        """
        if not text:
            return text

        self._ensure_engines()
        try:
            # Analyze for PII entities (PERSON, PHONE_NUMBER, EMAIL_ADDRESS, LOCATION, etc.)
            results = self.analyzer.analyze(text=text, entities=["PERSON", "PHONE_NUMBER", "EMAIL_ADDRESS", "US_SSN", "US_PASSPORT"], language='en')

            # Anonymize the text using the identified entities
            anonymized_result = self.anonymizer.anonymize(text=text, analyzer_results=results)
            return anonymized_result.text

        except Exception as e:
            # The scrubber is opt-in (gated by preferences.pii_scrub). When the
            # caller has explicitly turned it on but the engine itself faults,
            # surface the failure to the caller rather than corrupting prose.
            # Logged for SIEM; the call stack decides whether to abort.
            siem_logger.error(
                f"PII Scrubbing engine failure: {e}",
                extra={"event_type": "DATA_LEAK_PREVENTION"},
            )
            raise ValueError(f"PII Scrubbing engine failure: {e}") from e

# Singleton instance (cheap now — engines build lazily on first scrub)
pii_scrubber = PIIScrubberService()
