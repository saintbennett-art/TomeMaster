# TomeMaster Architecture Documentation Pack

This comprehensive documentation pack provides a deep dive into the architecture, logic, security, and codebase of the TomeMaster system, fulfilling the architectural generation requirements.

---

## 1. Core Architecture & Logic Diagrams

### 1. System Context Diagram (C4 Level 1)
This diagram illustrates TomeMaster within its broader ecosystem, showing external actors and boundaries.

```mermaid
C4Context
    title System Context diagram for TomeMaster
    
    Person(author, "Author/Director", "Uses TomeMaster to ingest, transcribe, format, and analyze manuscript drafts.")
    System(tomemaster, "TomeMaster SaaS", "Manuscript Formatting and Editorial Workspace.")
    
    System_Ext(gemini, "Gemini API", "Provides core LLM reasoning, analysis, and formatting.")
    System_Ext(ollama, "Ollama Local", "Local LLM inference fallback for privacy/offline mode.")
    System_Ext(anthropic, "Anthropic API", "Provides alternative LLM prose optimization.")
    System_Ext(local_fs, "Local Filesystem", "Read/Write RTF and JSON vault storage.")
    
    Rel(author, tomemaster, "Interacts with UI, uploads manuscripts, edits text")
    Rel(tomemaster, gemini, "Sends text chunks for formatting & structural analysis")
    Rel(tomemaster, ollama, "Sends text for local AI inference (offline mode)")
    Rel(tomemaster, anthropic, "Sends text for style mirroring")
    Rel(tomemaster, local_fs, "Reads RTF, saves exports, manages configuration")
```

### 2. Container Diagram (C4 Level 2)
This diagram breaks down the TomeMaster system into its primary containers.

```mermaid
C4Container
    title Container diagram for TomeMaster

    Person(author, "Author/Director", "User")
    
    Container_Boundary(c1, "TomeMaster Desktop Application") {
        Container(spa, "Single Page Application", "Next.js, React", "Provides the primary interface (Workstation, Sidebar, Editor).")
        Container(api, "Local Backend API", "Python, FastAPI", "Handles local system operations, AI orchestrations, and file parsing.")
        ContainerDb(local_storage, "Local Browser Storage", "LocalStorage", "Stores settings, vaults, API keys, and UI state.")
        ContainerDb(file_system, "App Directory / File System", "RTF, JSON", "Persists document edits, telemetry logs, and export artifacts.")
    }

    System_Ext(llm_providers, "External LLM Providers", "Gemini, Anthropic")
    System_Ext(ollama, "Local LLM Backend", "Ollama API")

    Rel(author, spa, "Uses", "HTTPS/Localhost")
    Rel(spa, api, "Makes API calls to", "JSON/REST (localhost:8000)")
    Rel(spa, local_storage, "Reads/Writes state")
    Rel(api, file_system, "Reads/Writes RTF/Logs")
    Rel(api, llm_providers, "Makes secure API calls to", "HTTPS")
    Rel(api, ollama, "Requests local inference", "HTTP (localhost:11434)")
```

### 3. Component Diagram (C4 Level 3)
A detailed view of the Python FastAPI Backend.

```mermaid
C4Component
    title Component diagram for TomeMaster API

    Container_Boundary(api, "FastAPI Backend") {
        Component(router_doc, "Document Router", "FastAPI Router", "Routes RTF/Doc ingestion requests.")
        Component(router_ai, "AI Router", "FastAPI Router", "Routes structural analysis and model discovery.")
        Component(router_transcribe, "Transcription Router", "FastAPI Router", "Routes automated text transcription/stitching.")
        
        Component(service_doc, "Document Parser", "Python Service", "Strips RTF, extracts text, handles file I/O.")
        Component(service_ai, "AI Service", "Python Service", "Orchestrates API calls to Gemini/Ollama, handles fallback logic.")
        Component(service_transcribe, "Transcriber Service", "Python Service", "Manages the automated transcription loop and chunking.")
        Component(service_settings, "Settings Service", "Python Service", "Manages environment variables and local settings.json.")
        
        Rel(router_doc, service_doc, "Uses")
        Rel(router_ai, service_ai, "Uses")
        Rel(router_transcribe, service_transcribe, "Uses")
        Rel(service_transcribe, service_ai, "Uses for logic formatting")
    }
```

### 4. Application Logic Flowchart
The core transcription and ingestion loop.

```mermaid
flowchart TD
    A[Upload Manuscript] --> B{Is RTF?}
    B -- Yes --> C[Extract Text (DocumentParser)]
    B -- No --> D[Reject/Convert]
    C --> E[Chunk Text for Transcription]
    E --> F[Send Chunk to TranscriberService]
    F --> G{Cloud or Local Mode?}
    G -- Cloud --> H[Invoke Gemini API]
    G -- Local --> I[Invoke Ollama API]
    H --> J[Apply Style/Formatting]
    I --> J
    J --> K[Stitch to Main Manuscript]
    K --> L{More Chunks?}
    L -- Yes --> F
    L -- No --> M[Generate Table of Contents]
    M --> N[Complete Transcription]
```

### 5. Sequence Diagrams (Transcription Flow)
Shows the step-by-step execution across components for a transcription request.

```mermaid
sequenceDiagram
    participant User
    participant Frontend
    participant DocumentRouter
    participant TranscriberService
    participant AIService
    participant LLM

    User->>Frontend: Start Transcription
    Frontend->>DocumentRouter: POST /api/v1/transcribe/start
    DocumentRouter->>TranscriberService: Initialize Task
    TranscriberService-->>DocumentRouter: Task ID returned
    DocumentRouter-->>Frontend: 202 Accepted (Task ID)
    
    loop Every Chunk
        TranscriberService->>AIService: Request formatting for Chunk N
        AIService->>LLM: HTTP Request (Gemini/Ollama)
        LLM-->>AIService: Formatted Text Response
        AIService-->>TranscriberService: Processed Chunk
        TranscriberService->>TranscriberService: Append to document (Stitching)
    end
    
    Frontend->>DocumentRouter: GET /api/v1/transcribe/status
    DocumentRouter-->>Frontend: Status: Completed
    Frontend->>User: Display Processed Document
```

### 6. State Machine Diagram
Illustrates the UI State transitions for a Workspace session.

```mermaid
stateDiagram-v2
    [*] --> Uninitialized
    Uninitialized --> OnboardingModal: No Local Config
    Uninitialized --> WorkspaceLoaded: Config Exists
    
    OnboardingModal --> WorkspaceLoaded: Set Provider/Keys
    
    state WorkspaceLoaded {
        [*] --> Idle
        Idle --> CloudGate: Action requires Cloud
        CloudGate --> OnlineMode: Confirm
        CloudGate --> Idle: Cancel
        
        Idle --> Transcribing: Start Upload
        Transcribing --> Transcribing: Loop Chunks
        Transcribing --> Idle: Complete
        
        Idle --> StructuralAnalysis: Open Nerve Center
        StructuralAnalysis --> Idle: Close Modal
    }
    
    WorkspaceLoaded --> [*]: Close App
```

---

## 2. Security & Handshake Diagrams

### 7. Authentication Handshake Diagram
Shows how the frontend safely passes keys to the backend without persistent DB storage.

```mermaid
sequenceDiagram
    participant Frontend
    participant SettingsModal
    participant LocalStorage
    participant FastAPI_Backend
    participant LLM_API

    Frontend->>LocalStorage: Read `tome_master_vault`
    LocalStorage-->>Frontend: Vault JSON (Encrypted/Base64)
    Frontend->>SettingsModal: Display Key Status
    
    User->>SettingsModal: Enter New API Key
    SettingsModal->>LocalStorage: Save Updated Vault
    
    Frontend->>FastAPI_Backend: POST Request + Headers: {"X-API-Key": "[User_Key]"}
    FastAPI_Backend->>FastAPI_Backend: Extract Key into Request Context
    FastAPI_Backend->>LLM_API: Secure HTTPS Call with Bearer/x-goog-api-key
    LLM_API-->>FastAPI_Backend: Response
    FastAPI_Backend-->>Frontend: Formatted Content
```

### 8. Data‑Flow Diagram (DFD with Trust Boundaries)
Focuses on trust boundaries between the desktop environment and external services.

```mermaid
C4Container
    title Data-Flow Diagram (Trust Boundaries)

    System_Boundary(local_pc, "Local Machine Boundary (TRUSTED)") {
        Container(spa, "Next.js Frontend", "Browser Context")
        Container(api, "FastAPI Service", "System Process")
        ContainerDb(fs, "Local File System", "Disk")
    }

    System_Boundary(external_apis, "External Cloud Providers (UNTRUSTED)") {
        System_Ext(gemini, "Google AI API")
        System_Ext(anthropic, "Anthropic API")
    }

    Rel(spa, api, "Raw Text / Settings", "HTTP")
    Rel(api, fs, "RTF Extraction / JSON Persistence", "I/O")
    
    UpdateRelStyle(spa, api, $textColor="green", $lineColor="green")
    UpdateRelStyle(api, fs, $textColor="green", $lineColor="green")
    
    Rel(api, gemini, "API Key + Chunks", "HTTPS (TLS)")
    UpdateRelStyle(api, gemini, $textColor="red", $lineColor="red")
```

---

## 3. Source‑Code–Level Analysis Reports

### 9. Static Code Analysis Report
**Summary Overview:**

*   **Dependency Graph:**
    *   **Frontend:** Next.js, React, Tailwind CSS, Lucide React (Icons).
    *   **Backend:** FastAPI, Pydantic, Uvicorn, python-dotenv, requests/httpx.
*   **Cyclomatic Complexity:**
    *   `TranscriberService.py`: **High** (Due to chunking, error retry loops, and stitching logic). Refactoring suggested for retry handling.
    *   `AIService.py`: **Medium** (Multiple provider failover blocks).
*   **Code Smells:**
    *   Frequent use of synchronous file I/O operations inside `async` FastAPI routes (e.g., `DocumentParser.py`). Should be offloaded to `run_in_threadpool` or `aiofiles`.
*   **Dead Code:** Minimal dead code observed; legacy endpoints exist in `ai.py` (e.g., `debug_ollama`).
*   **Security Vulnerabilities:**
    *   *Risk:* CORS configuration currently allows `http://(localhost|127\.0\.0\.1)(:\d+)?$`, which is standard for desktop apps but should not be exposed externally.
    *   *Risk:* API keys are passed via LocalStorage; acceptable for a strictly local standalone desktop app, but vulnerable to XSS if external scripts are ever loaded.

### 10. Call Graph / Function Dependency Graph
**Key Execution Path for AI Formatting:**
```text
[Frontend] Home.tsx (handleAnalysis)
  └── [Frontend] apiClient.ts (post /api/v1/analysis)
       └── [Backend] routers/analysis.py (analyze_endpoint)
            ├── [Backend] services/document_parser.py (extract_text)
            └── [Backend] services/ai_service.py (orchestrate_ai_call)
                 ├── [Backend] services/sovereign_guardrails.py (check_provider_status)
                 └── [External] httpx.post (Google/Anthropic/Ollama)
```

### 11. API Endpoint Inventory
*   **`GET /`**: Static frontend fallback.
*   **`POST /api/v1/analysis/structural`**: Performs structural manuscript analysis via LLM.
*   **`POST /api/v1/document/upload`**: Ingests RTF/TXT files.
*   **`GET /api/v1/document/export`**: Triggers RTF rebuild and download.
*   **`POST /api/v1/transcribe/start`**: Initiates the background transcription engine.
*   **`GET /api/v1/transcribe/status`**: Long-polling/status check for transcription engine.
*   **`GET /api/v1/ai/status`**: Diagnostic ping to check Ollama/Gemini availability.
*   **`POST /api/v1/settings/sync`**: Syncs vault keys between frontend and backend configuration.

### 12. Security Audit Report
*   **Insecure Functions:** `os.system` / `subprocess.Popen` utilized in build scripts (`build_native.py`). Ensure arguments are sanitized.
*   **Unsafe Deserialization:** Standard JSON parsing used. No Python `pickle` objects detected.
*   **Injection Risks:** Path Traversal risk if filename inputs in `/api/v1/document/*` are not sanitized before `os.path.join`. Verified `document_parser.py` implements basename extraction.
*   **Missing Input Validation:** Some dynamic metadata inputs in the UI rely on loose typing. (Addressing 'any' types as part of Sovereign Hardening).
*   **Weak Crypto Usage:** None detected. Vault relies on base platform TLS for external transit.

### 13. Logging & Telemetry Flow Report
*   **What is logged:** 
    *   API handshake successes/failures (`handshake_forensics.txt`).
    *   Transcription chunk completion rates and page stitching indices (`tail_audit.txt`).
    *   Token usage and LLM response times (`api_usage_log.jsonl`).
*   **Where logs go:**
    *   Local filesystem at the application root.
*   **Metadata captured:** Timestamps, Provider Name, Model ID, Latency (ms), Chunk Size, Error codes. No plain-text manuscript data is logged to prevent data leaks.
