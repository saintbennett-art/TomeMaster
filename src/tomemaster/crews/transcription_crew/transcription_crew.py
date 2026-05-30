"""
[TRANSCRIPTION CREW]: CrewAI crew with smart routing.

Smart routing (PRs #7-#10): parseable documents (.docx, .pdf with text layer,
.doc, .wpd, .wps, .odt) are text-extracted locally — zero API credits.
Only actual scanned images (.jpg, .png, .webp) and scanned PDFs hit the
vision AI agent.

Model selection is dynamic via settings_service.get_model_for_role() —
no hardcoded model names.
"""
import os
import sys
import glob
from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task

# Ensure backend is importable
_backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "backend"))
if _backend_path not in sys.path:
    sys.path.insert(0, _backend_path)

# ─── Smart Routing Imports ────────────────────────────────────────
from services.transcriber.vision_processor import is_parseable_document, parse_document_text
from services.transcriber.artifact_steward import save_page_artifact
from services.transcriber.asset_scanner import natural_sort_key, extract_sequence_number, is_cover_asset

# ─── Supported Extensions ────────────────────────────────────────
_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}
_DOC_EXTS = {".pdf", ".docx", ".doc", ".wpd", ".wps", ".odt"}
_ALL_EXTS = _IMAGE_EXTS | _DOC_EXTS


def _resolve_scribe_model() -> str:
    """Resolves the vision model dynamically from user settings.

    Falls back to env var SCRIBE_MODEL, then to a safe default.
    Never hardcoded to a single provider.
    """
    try:
        from services.settings_service import get_model_for_role
        config = get_model_for_role("TRANSCRIBER_LEAD")
        model = config.get("model") if config else None
        if model and model != "auto":
            # CrewAI expects "provider/model" format
            provider = config.get("provider", "gemini")
            if "/" not in model:
                return f"{provider}/{model}"
            return model
    except Exception as e:
        print(f"[CREW]: Could not resolve dynamic model: {e}")

    return os.environ.get("SCRIBE_MODEL", "gemini/gemini-2.5-flash")


def ui_sync_callback(task_output):
    """Pushes completed page results to the frontend via TRANSCRIPTION_STATE."""
    try:
        from services import transcriber_service
        from services import settings_service

        output_text = task_output.raw

        # [FERPA COMPLIANCE]: Only scrub PII when the user has explicitly enabled it
        prefs = settings_service.load_settings().get("preferences", {})
        if prefs.get("pii_scrub", False):
            from services.pii_scrubber import pii_scrubber
            output_text = pii_scrubber.anonymize_text(output_text)

        with transcriber_service.TRANSCRIPTION_LOCK:
            transcriber_service.TRANSCRIPTION_STATE["processed_images"] += 1
            transcriber_service.TRANSCRIPTION_STATE["stream_buffer"].append({
                "text": output_text,
                "preview": output_text[:50] + "..."
            })
    except Exception as e:
        print("UI Sync Error:", e)


def _smart_route_parseable(file_path: str, folder_path: str, page_index: int) -> bool:
    """[SMART ROUTE]: Text-extracts a parseable document and writes RTF artifacts.

    Returns True if the file was handled locally (no AI needed).
    Returns False if the file needs to go to the Scribe agent.
    """
    if not is_parseable_document(file_path):
        return False

    basename = os.path.basename(file_path)
    ext = os.path.splitext(basename)[1].lower()
    print(f"[SMART ROUTE]: {basename} → text parse (no OCR, no API credits)")

    text = parse_document_text(file_path)
    if not text:
        print(f"[SMART ROUTE]: Text extraction failed for {basename}, falling back to OCR")
        return False

    # Write RTF artifact(s) — multi-page documents produce multiple RTFs
    import re
    pages = re.findall(
        r'<page><number>(\d+)</number><text>(.*?)</text></page>',
        text, re.DOTALL
    )

    if pages:
        for page_num_str, page_text in pages:
            idx = page_index + int(page_num_str) - 1
            save_page_artifact(folder_path, page_num_str, page_text.strip(), file_path, physical_index=idx)
    else:
        # Single block of text — save as one artifact
        save_page_artifact(folder_path, str(page_index), text.strip(), file_path, physical_index=page_index)

    # Sync to UI
    try:
        from services import transcriber_service
        with transcriber_service.TRANSCRIPTION_LOCK:
            transcriber_service.TRANSCRIPTION_STATE["processed_images"] += 1
            preview = text[:80].replace('\n', ' ')
            transcriber_service.TRANSCRIPTION_STATE["stream_buffer"].append({
                "text": f"[TEXT PARSE] {basename}: {len(pages) if pages else 1} page(s) extracted",
                "preview": preview + "..."
            })
    except Exception:
        pass

    return True


@CrewBase
class TranscriptionCrew:
    agents_config = 'config/agents.yaml'
    tasks_config = 'config/tasks.yaml'

    @agent
    def scribe(self) -> Agent:
        model = _resolve_scribe_model()
        print(f"[CREW]: Scribe agent using model: {model}")
        return Agent(
            config=self.agents_config['scribe'],
            llm=model,
            multimodal=True,
            allow_delegation=False,
            verbose=True
        )

    @task
    def compile_manuscript(self) -> Task:
        return Task(
            config=self.tasks_config['compile_manuscript'],
            agent=self.scribe(),
            output_file="./output/raw_manuscript.txt"
        )

    @crew
    def crew(self) -> Crew:
        scribe_agent = self.scribe()
        return Crew(
            agents=[scribe_agent],
            tasks=[],  # Tasks generated dynamically based on inputs
            process=Process.sequential,
            max_rpm=15
        )

    def _generate_dynamic_tasks(self, folder_path: str):
        """[SMART ROUTING]: Scans folder, routes each file optimally.

        - Parseable documents (.docx, digital .pdf, .doc, .wpd, .wps, .odt)
          → text-extracted locally, RTF written, NO AI task created
        - Scanned images (.jpg, .png, .webp) and scanned PDFs
          → AI vision task created for the Scribe agent
        """
        scribe_agent = self.scribe()
        target_folder = folder_path if folder_path else "./test_batch"

        # [SOVEREIGN DISCOVERY]: Find all manuscript assets
        all_files = []
        if os.path.exists(target_folder):
            for f in os.listdir(target_folder):
                ext = os.path.splitext(f.lower())[1]
                if ext in _ALL_EXTS and not is_cover_asset(f):
                    all_files.append(os.path.join(target_folder, f))

        all_files.sort(key=natural_sort_key)

        print(f"[CREW]: Discovered {len(all_files)} manuscript assets in {target_folder}")

        # [SMART ROUTING PASS]: Parse what we can locally, queue the rest for AI
        tasks_array = []
        page_index = 1
        parsed_count = 0
        ocr_count = 0

        for file_path in all_files:
            ext = os.path.splitext(file_path.lower())[1]

            # Try smart routing first (text extraction — free)
            if ext in _DOC_EXTS:
                if _smart_route_parseable(file_path, target_folder, page_index):
                    parsed_count += 1
                    # Estimate pages for index advancement
                    if ext == ".pdf":
                        try:
                            import fitz
                            doc = fitz.open(file_path)
                            page_index += len(doc)
                            doc.close()
                        except Exception:
                            page_index += 1
                    else:
                        page_index += 1
                    continue
                # Smart route returned False → scanned PDF, fall through to OCR

            # [OCR PATH]: Image or scanned PDF → Scribe agent
            if ext == ".pdf":
                # Scanned PDF: split into page images for the vision agent
                try:
                    import fitz
                    pdf_doc = fitz.open(file_path)
                    for pg_num in range(len(pdf_doc)):
                        page = pdf_doc.load_page(pg_num)
                        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
                        img_path = os.path.join(target_folder, f"_scan_p{page_index}.png")
                        pix.save(img_path)

                        filename = f"scan_page_{page_index}.png"
                        page_task = Task(
                            description=self.tasks_config['transcribe_page']['description'].format(filename=filename),
                            expected_output=self.tasks_config['transcribe_page']['expected_output'],
                            agent=scribe_agent,
                            async_execution=True,
                            images=[img_path],
                            callback=ui_sync_callback
                        )
                        tasks_array.append(page_task)
                        page_index += 1
                        ocr_count += 1
                    pdf_doc.close()
                except Exception as e:
                    print(f"[CREW ERROR]: Failed to split scanned PDF {file_path}: {e}")
            else:
                # Standard image file
                filename = os.path.basename(file_path)
                page_task = Task(
                    description=self.tasks_config['transcribe_page']['description'].format(filename=filename),
                    expected_output=self.tasks_config['transcribe_page']['expected_output'],
                    agent=scribe_agent,
                    async_execution=True,
                    images=[file_path],
                    callback=ui_sync_callback
                )
                tasks_array.append(page_task)
                page_index += 1
                ocr_count += 1

        print(f"[CREW]: Smart routing complete — {parsed_count} text-parsed (free), {ocr_count} queued for OCR")

        # Append the synchronous compile task at the end with context
        if tasks_array:
            compile_task = self.compile_manuscript()
            compile_task.context = tasks_array
            tasks_array.append(compile_task)

        return tasks_array
