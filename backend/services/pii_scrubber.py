from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine
import logging

from .logger_service import siem_logger

class PIIScrubberService:
    def __init__(self):
        try:
            self.analyzer = AnalyzerEngine()
            self.anonymizer = AnonymizerEngine()
            siem_logger.info("PII Scrubber Initialized successfully.", extra={"event_type": "SECURITY_INIT"})
        except Exception as e:
            siem_logger.error(f"Failed to initialize PII Scrubber: {e}", extra={"event_type": "SECURITY_FAILURE"})
            raise RuntimeError("Govt Compliance Failure: PII Scrubber could not boot.") from e

    def anonymize_text(self, text: str) -> str:
        """
        Scans and redacts PII from the provided text before it leaves the boundary.
        Fails closed on error.
        """
        if not text:
            return text
            
        try:
            # Analyze for PII entities (PERSON, PHONE_NUMBER, EMAIL_ADDRESS, LOCATION, etc.)
            results = self.analyzer.analyze(text=text, entities=["PERSON", "PHONE_NUMBER", "EMAIL_ADDRESS", "US_SSN", "US_PASSPORT"], language='en')
            
            # Anonymize the text using the identified entities
            anonymized_result = self.anonymizer.anonymize(text=text, analyzer_results=results)
            return anonymized_result.text
            
        except Exception as e:
            siem_logger.error("PII Scrubbing failed. Blocking outbound text.", extra={"event_type": "DATA_LEAK_PREVENTION"})
            # Fail closed: If we can't guarantee it's clean, we don't send it.
            raise ValueError("Govt Compliance Block: PII Scrubbing failed on this chunk.") from e

# Singleton instance
pii_scrubber = PIIScrubberService()
