# KNOWLEDGE BASE DIRECTIVE (MANDATORY ROUTING)

**CRITICAL INSTRUCTION FOR ALL AI AGENTS:**

This `knowledge.md` file is NOT the complete knowledge base. It is a routing anchor. 

If you are reading this file, you MUST immediately scan and ingest the contents of the surrounding subdirectories, as they contain the actual, immutable protocols for this project.

## Required Knowledge Subdirectories to Audit:
1. `core_architecture/`
2. `governance_protocol/`
3. `master_directive/`
4. `sovereign_guardrails/`

Failure to read and obey the `metadata.json` and `artifacts/*.md` files within these subdirectories will result in architectural drift and violations of the Zero Assumption Policy (ZAP). 

**DO NOT PROCEED WITH ANY TASK UNTIL YOU HAVE REVIEWED THE ACTIVE DIRECTIVES IN THESE FOLDERS.**

---

## 🔒 DIRECTORIAL LOCK PROTOCOL
All rules within this Knowledge Base (including subdirectories) are **LOCKED**. 
No AI agent may alter, delete, or override existing rules without explicit Directorial approval. 
However, **new rules may be appended** to these documents as vulnerabilities are discovered and patched.

---

## 🛡️ SECURE CODING & HYGIENE DIRECTIVE
To prevent systemic vulnerabilities, the following rules MUST be strictly adhered to:

### 1. ZERO-TRUST SECRETS & AUTHENTICATION
*   **No Query Parameter Leaks:** API keys and sensitive tokens MUST NEVER be transmitted via URL query parameters. Pass them via HTTP Headers or POST bodies.
*   **No Plaintext Secrets Exposure:** Never return API keys in unauthenticated GET endpoints.
*   **No Hardcoded Backdoors:** Master passwords or developer bypasses must never be hardcoded into the source.

### 2. FILESYSTEM SOVEREIGNTY (ANTI-TRAVERSAL)
*   **Mandatory Path Validation:** Any client-provided `folder_path` or `filename` MUST be validated using `os.path.realpath()` against a permitted base directory before any filesystem operation.
*   **No Blind Concatenation:** Never blindly join a user-supplied filename to a path.

### 3. NETWORK & CORS INTEGRITY
*   **Strict CORS Policy:** Never combine `allow_origins=["*"]` with `allow_credentials=True`.
*   **Content Security Policy (CSP):** Avoid `unsafe-eval` and `unsafe-inline`. Do not hardcode dynamic ports in the CSP.

### 4. DATA SANITIZATION & SCHEMA VALIDATION
*   **DOM Injection Guard:** All external text MUST be sanitized (e.g., via DOMPurify) before being injected into React state.
*   **Strict State Hydration:** JSON data loaded from disk must be validated against a schema before updating global state.

### 5. INDUSTRIAL ERROR HANDLING
*   **No Bare Exceptions:** `except: pass` is strictly forbidden.
*   **No Traceback Leaks:** Never dump raw Python tracebacks to user-facing `.txt` files.
*   **Guaranteed Cleanup:** Temporary files must be cleaned up in a `finally` block.

### 6. ANTI-HALLUCINATION & CONCURRENCY
*   **Signature Verification:** Do not call functions that do not exist or use hallucinated Model IDs.
*   **Lock Mutations:** Global state mutations MUST occur within the same threading lock to prevent TOCTOU race conditions.
*   **No Endpoint Shadowing:** Every FastAPI route must have a unique function name.
