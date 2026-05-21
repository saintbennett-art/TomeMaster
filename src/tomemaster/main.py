import os
import sys

# Ensure root path is imported for get_key
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from pydantic import BaseModel
from crewai.flow.flow import Flow, listen, start
from tomemaster.crews.transcription_crew.transcription_crew import TranscriptionCrew
from tomemaster.crews.publishing_crew.publishing_crew import PublishingCrew
from tomemaster.vault_loader import inject_keys_to_env, load_vault
from get_key import get_machine_fingerprint
import hashlib

def generate_valid_license():
    machine_id = get_machine_fingerprint()
    combined = f"{machine_id}::TomeMaster-2026-BennettConsulting-Salt"
    full_hash = hashlib.sha256(combined.encode()).hexdigest()
    prefix = full_hash[:12].upper()
    return f"TOME-{prefix[:4]}-{prefix[4:8]}-{prefix[8:]}"

# Shared state moving through the pipeline
class TomeMasterState(BaseModel):
    folder_path: str = "./test_batch"
    raw_manuscript: str = ""
    chapterized_book: str = ""
    marketing_blurb: str = ""
    pacing_report: str = ""
    is_freemium: bool = True

class TomeMasterPipeline(Flow[TomeMasterState]):

    @start()
    def setup_security(self):
        print("🔐 Phase 0: Initializing Sovereign Security & Loading Vault...")
        if not inject_keys_to_env():
            print("❌ CRITICAL: Vault not found. Please run config_wizard.py first.")
            sys.exit(1)
            
        vault = load_vault()
        if vault.get('license_key') == generate_valid_license():
            print("✅ PRO LICENSE CONFIRMED. Watermarks disabled.")
            self.state.is_freemium = False
        else:
            print("⚠️ RUNNING IN FREEMIUM MODE. All outputs will be watermarked.")
            self.state.is_freemium = True

    @listen(setup_security)
    def run_transcription(self):
        print(f"🔍 Phase 1: Initiating Asynchronous Batch Transcription on {self.state.folder_path}...")
        # Kick off the isolated transcription sub-system with dynamic folder path
        tc = TranscriptionCrew()
        my_crew = tc.crew()
        my_crew.tasks = tc._generate_dynamic_tasks(self.state.folder_path)
        
        output = my_crew.kickoff()
        
        # [FERPA COMPLIANCE]: Only scrub the manuscript when user has explicitly enabled PII redaction
        sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "backend")))
        from services import settings_service
        prefs = settings_service.load_settings().get("preferences", {})
        if prefs.get("pii_scrub", False):
            from services.pii_scrubber import pii_scrubber
            safe_manuscript = pii_scrubber.anonymize_text(output.raw)
            self.state.raw_manuscript = safe_manuscript
        else:
            self.state.raw_manuscript = output.raw
        
        return self.state.raw_manuscript

    @listen(run_transcription)
    def run_chapterization(self):
        """Phase 2: Structural Editor — must complete before downstream specialists."""
        print("📖 Phase 2: Launching Structural Editor for Chapterization...")
        from tomemaster.crews.publishing_crew.publishing_crew import PublishingCrew
        pc = PublishingCrew()
        editor_agent = pc.editor()
        chapter_task = pc.chapterize_manuscript()
        from crewai import Crew, Process
        Crew(agents=[editor_agent], tasks=[chapter_task], process=Process.sequential, verbose=True).kickoff(
            inputs={"text": self.state.raw_manuscript}
        )
        print("✅ Chapterization complete.")

    # --- THE BOARDROOM FAN-OUT (Parallel Execution per Gemini Blueprint) ---
    # Both methods listen to the same trigger. CrewAI executes them simultaneously.

    @listen(run_chapterization)
    def run_marketing_analysis(self):
        """Phase 3A: Marketing Director generates assets in parallel."""
        print("📢 Phase 3A: Launching Marketing Strategy Loop...")
        from tomemaster.crews.publishing_crew.publishing_crew import PublishingCrew
        pc = PublishingCrew()
        director_agent = pc.director()
        marketing_task = pc.marketing_analysis()
        from crewai import Crew, Process
        Crew(agents=[director_agent], tasks=[marketing_task], process=Process.sequential, verbose=True).kickoff()

    @listen(run_chapterization)
    def run_pacing_analysis(self):
        """Phase 3B: Pacing Analyst generates report in parallel."""
        print("📈 Phase 3B: Launching Emotional Pacing Review...")
        from tomemaster.crews.publishing_crew.publishing_crew import PublishingCrew
        pc = PublishingCrew()
        analyst_agent = pc.analyst()
        pacing_task = pc.pacing_review()
        from crewai import Crew, Process
        Crew(agents=[analyst_agent], tasks=[pacing_task], process=Process.sequential, verbose=True).kickoff()

    @listen(run_marketing_analysis, run_pacing_analysis)
    def finalize_outputs(self):
        print("✨ Finalizing Artifacts...")
        if self.state.is_freemium:
            print("💧 Applying Freemium Watermarks to outputs...")
            watermark = "\n\n" + "="*50 + "\nPRODUCED WITH TOMEMASTER FREEMIUM\nPurchase a Pro License to remove this watermark.\n" + "="*50 + "\n"
            
            # [N2 FIX]: Resolve output_dir relative to project root, not CWD
            project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
            output_dir = os.path.join(project_root, "output")
            if os.path.exists(output_dir):
                for filename in os.listdir(output_dir):
                    if filename.endswith(".txt") or filename.endswith(".md"):
                        path = os.path.join(output_dir, filename)
                        with open(path, "a", encoding="utf-8") as f:
                            f.write(watermark)

        print("🚀 TomeMaster execution successfully completed.")

if __name__ == "__main__":
    pipeline = TomeMasterPipeline()
    pipeline.kickoff()
