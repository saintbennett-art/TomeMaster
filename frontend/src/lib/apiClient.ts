import { saveBlobWithSovereignty } from './file_system_utils';
import { Chapter, TranscriptionStatus } from '@/types/industrial';
import { secureVault } from '@/lib/vault';

// Single source of truth lives in types/industrial.ts
export type { TranscriptionStatus };

// [HANDSHAKE FOUNDATION]: Dynamic Resolution (Zero Hardcoding)
export async function getLiveApiBase(): Promise<string> {
    if (typeof window !== 'undefined') {
        const urlParams = new URLSearchParams(window.location.search);
        const paramPort = urlParams.get('api_port');
        if (paramPort) {
            // [DESKTOP MODE]: Backend dynamically passed its port via URL
            return `http://127.0.0.1:${paramPort}/api/v1`;
        }
        
        // [PRODUCTION/DOCKER MODE]: Served statically by backend, use relative path to share the same origin port
        return `/api/v1`;
    }
    // Fallback for SSR
    return `/api/v1`;
}

// Global root that always reflects the current successful interface
export const API_BASE_HOLDER = { current: `/api/v1` };

// Initialize the bridge immediately upon module load
if (typeof window !== 'undefined') {
    getLiveApiBase().then(base => {
        API_BASE_HOLDER.current = base;
    });
}


export async function uploadManuscript(file: File, isDemo: boolean = false, signal?: AbortSignal, isRecovery: boolean = false) {
    const formData = new FormData();
    formData.append("file", file);

    const res = await fetch(`${API_BASE_HOLDER.current}/document/upload?is_demo=${isDemo}&recovery=${isRecovery}`, {
        method: "POST",
        body: formData,
        signal
    });

    if (!res.ok) {
        const errorData = await res.json().catch(() => ({ detail: "Upload failed" }));
        const msg = typeof errorData.detail === 'object' ? JSON.stringify(errorData.detail) : (errorData.detail || "Upload failed");
        throw new Error(msg);
    }
    return res.json();
}

export async function uploadManuscriptStream(file: File, onChunk: (data: Record<string, unknown>) => void, isDemo: boolean = false, signal?: AbortSignal) {
    const formData = new FormData();
    formData.append("file", file);

    const provider = typeof window !== 'undefined' ? (localStorage.getItem('tome_master_provider') || 'gemini') : 'gemini';
    const apiKey = typeof window !== 'undefined' ? (secureVault.load()[provider] || '') : '';

    formData.append("api_key", apiKey);
    const res = await fetch(`${API_BASE_HOLDER.current}/document/upload/stream?is_demo=${isDemo}`, {
        method: "POST",
        body: formData,
        signal
    });

    if (!res.ok) {
        const errorData = await res.json().catch(() => ({ detail: "Upload failed" }));
        const msg = typeof errorData.detail === 'object' ? JSON.stringify(errorData.detail) : (errorData.detail || "Upload failed");
        throw new Error(msg);
    }

    if (!res.body) throw new Error("No readable stream available");

    const reader = res.body.getReader();
    const decoder = new TextDecoder("utf-8");
    let buffer = "";

    while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        let newlineIndex: number;

        while ((newlineIndex = buffer.indexOf('\n')) !== -1) {
            const line = buffer.slice(0, newlineIndex);
            buffer = buffer.slice(newlineIndex + 1);

            if (line.trim()) {
                try {
                    const data = JSON.parse(line);
                    onChunk(data);
                } catch (e) {
                }
            }
        }
    }
}


export async function analyzeEmotionalArc(text: string, providerOverride?: string, modelOverride?: string) {
    const provider = providerOverride || (typeof window !== 'undefined' ? (localStorage.getItem('tome_master_provider') || 'gemini') : 'gemini');
    const local_mode = typeof window !== 'undefined' ? localStorage.getItem('tome_master_local_mode') === 'true' : false;

    let lastError = null;
    for (let i = 0; i < 3; i++) {
        try {
            const res = await safeFetch(`${API_BASE_HOLDER.current}/analysis/emotional-arc`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ text, provider, model: modelOverride, local_mode }),
            });

            if ('isNetworkError' in res) throw new Error("CONNECTION_REFUSED");
            const response = res as Response;
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ detail: "Analysis failed" }));
                throw new Error(errorData.detail || "Analysis failed");
            }
            return await response.json();
        } catch (e) {
            lastError = e;
            if (i < 2) await new Promise(r => setTimeout(r, 1000));
        }
    }
    throw lastError;
}

export async function runMultiAgentAnalysis(
    content: string,
    requestedPersonas: string[],
    provider?: string,
    model?: string,
    analyticScope: string = 'full',
    userChapters?: Chapter[],
    customUrl?: string,
    localMode: boolean = false,
    synthesisMode: boolean = false,
    customPrompt?: string,
    projectFolder?: string
) {
    const apiKey = typeof window !== 'undefined' ? (secureVault.load()[provider || 'gemini'] || '') : '';

    const res = await safeFetch(`${API_BASE_HOLDER.current}/analysis/convene`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            content,
            requested_personas: requestedPersonas,
            provider: provider || 'gemini',
            api_key: apiKey,
            model: model || 'auto',
            custom_url: customUrl,
            local_mode: localMode,
            analytic_scope: analyticScope,
            user_chapters: userChapters,
            synthesis_mode: synthesisMode,
            custom_prompt: customPrompt
        }),
    });

    if ('isNetworkError' in res) {
        throw new Error("Sovereign connection failed. The Boardroom engine is unreachable.");
    }

    const response = res as Response;
    if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: "Analysis failed" }));
        throw new Error(errorData.detail || "Analysis failed");
    }
    return response.json();
}

export async function draftExpert(content: string, persona: string, userChapters: Chapter[] | null = null, synthesisMode: boolean = false) {
    const res = await safeFetch(`${API_BASE_HOLDER.current}/analysis/draft-expert`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            content,
            persona,
            user_chapters: userChapters,
            synthesis_mode: synthesisMode
        }),
    });

    if ('isNetworkError' in res) {
        throw new Error("Local handshake timed out. High-fidelity drafting is offline.");
    }

    const response = res as Response;
    if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: "Drafting failed" }));
        throw new Error(errorData.detail || "Drafting failed");
    }
    return response.json();
}

export async function exportDocx(content: string, chapters: Chapter[] = [], title?: string, author?: string, format: string = "chicago", coverImage?: string) {
    const res = await fetch(`${API_BASE_HOLDER.current}/document/export/docx`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content, chapters, title, author, format, cover_image: coverImage }),
    });

    if (!res.ok) throw new Error("Export failed");

    const blob = await res.blob();
    await saveBlobWithSovereignty(blob, `${title || "Manuscript"}.docx`, "Manuscript (Word)");
}

export async function exportAnalysisReport(markdown: string, title?: string) {
    const res = await fetch(`${API_BASE_HOLDER.current}/analysis/export/docx`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ markdown }),
    });

    if (!res.ok) throw new Error("Export failed");

    const blob = await res.blob();
    await saveBlobWithSovereignty(blob, `${title || "Analysis_Report"}.docx`, "Boardroom Report (Word)");
}

export async function exportPdf(content: string, chapters: Chapter[] = [], title?: string, author?: string, format: string = "chicago", coverImage?: string) {
    const res = await fetch(`${API_BASE_HOLDER.current}/document/export/pdf`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content, chapters, title, author, format, cover_image: coverImage }),
    });

    if (!res.ok) throw new Error("Export failed");

    const blob = await res.blob();
    await saveBlobWithSovereignty(blob, `${title || "Manuscript"}.pdf`, "Manuscript (PDF)");
}

export async function exportEpub(content: string, chapters: Chapter[] = [], title?: string, author?: string, format: string = "chicago", coverImage?: string) {
    const res = await fetch(`${API_BASE_HOLDER.current}/document/export/epub`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content, chapters, title, author, format, cover_image: coverImage }),
    });

    if (!res.ok) throw new Error("Export failed");

    const blob = await res.blob();
    await saveBlobWithSovereignty(blob, `${title || "Manuscript"}.epub`, "Manuscript (ePUB)");
}

export async function startTranscription(
    folderPath: string,
    mode: 'batch' | 'live' = 'batch',
    provider: string = 'gemini',
    model: string = 'gemini-2.5-flash-preview-04-17',
    resetCache: boolean = false,
    apiKey: string = '',
    fallbackProvider: string = 'groq',
    fallbackModel: string = 'meta-llama/llama-4-scout-17b-16e-instruct'
): Promise<{ status: string, folder_path: string }> {
    let lastError = null;
    for (let i = 0; i < 3; i++) {
        try {
            const res = await safeFetch(`${API_BASE_HOLDER.current}/transcribe/start`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    folder_path: folderPath,
                    mode,
                    provider,
                    model,
                    reset_cache: resetCache,
                    api_key: apiKey,
                    fallback_provider: fallbackProvider,
                    fallback_model: fallbackModel
                }),
            }, 300000);

            if ('isNetworkError' in res) throw new Error("CONNECTION_REFUSED");
            const response = res as Response;
            if (!response.ok) throw new Error(`Transcription Handshake Denied: ${response.status}`);

            return await response.json();
        } catch (e) {
            lastError = e;
            if (i < 2) await new Promise(r => setTimeout(r, 1000));
        }
    }
    throw new Error("CONNECTION_REFUSED");
}

// [STABILITY]: Increased timeout and retry logic to prevent "Backend Failure" race conditions
export const checkBackendHealth = async (retries = 3): Promise<boolean> => {
    for (let i = 0; i < retries; i++) {
        try {
            const resp = await fetch(`${API_BASE_HOLDER.current}/ai/status`, { signal: AbortSignal.timeout(3000) });
            if (resp.ok) return true;
        } catch (e) {
            await new Promise(r => setTimeout(r, 1500));
        }
    }
    return false;
};

export async function clearTranscription(): Promise<boolean> {
    try {
        const res = await fetch(`${API_BASE_HOLDER.current}/document/transcribe/clear`, { method: 'POST' });
        return res.ok;
    } catch (e) {
        return false;
    }
}

export async function resortTranscription(folderPath: string): Promise<boolean> {
    try {
        const res = await fetch(`${API_BASE_HOLDER.current}/document/transcribe/resort?folder_path=${encodeURIComponent(folderPath)}`, {
            method: 'GET'
        });
        return res.ok;
    } catch (e) {
        return false;
    }
}

export async function resolveAudit(pageNumber: string, applyOffset: boolean = false): Promise<boolean> {
    try {
        const res = await fetch(`${API_BASE_HOLDER.current}/document/transcribe/resolve`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ page_number: pageNumber, apply_offset: applyOffset })
        });
        return res.ok;
    } catch (e) {
        return false;
    }
}

export async function setTranscriptionOffset(delta: number): Promise<boolean> {
    try {
        const res = await fetch(`${API_BASE_HOLDER.current}/document/transcribe/offset`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ delta })
        });
        return res.ok;
    } catch (e) {
        return false;
    }
}

export async function targetFolder(): Promise<{ status: string, folder_path: string | null }> {
    // [SOVEREIGN PATIENCE]: Retry the target signal 3 times to account for engine warm-up
    let lastError = null;
    for (let i = 0; i < 3; i++) {
        try {
            // [NATIVE DIALOG LOCK]: 5 minute timeout for user browsing
            const res = await safeFetch(`${API_BASE_HOLDER.current}/document/target`, {}, 300000);
            if ('isNetworkError' in res) throw new Error("CONNECTION_REFUSED");
            const response = res as Response;
            if (!response.ok) throw new Error("Target Handshake Failed");
            return await response.json();
        } catch (e) {
            lastError = e;
            if (i < 2) await new Promise(r => setTimeout(r, 800)); // Wait 800ms between tries
        }
    }
    throw lastError;
}

export async function pickManuscript(): Promise<{ status: string, file_path: string | null, folder_path: string | null, filename: string | null, is_parseable?: boolean }> {
    let lastError = null;
    for (let i = 0; i < 3; i++) {
        try {
            // [NATIVE DIALOG LOCK]: 5 minute timeout for user browsing
            const res = await safeFetch(`${API_BASE_HOLDER.current}/document/load`, {}, 300000);
            if ('isNetworkError' in res) throw new Error("CONNECTION_REFUSED");
            const response = res as Response;
            if (!response.ok) throw new Error("Manuscript Load Handshake Failed");
            return await response.json();
        } catch (e) {
            lastError = e;
            if (i < 2) await new Promise(r => setTimeout(r, 800));
        }
    }
    throw lastError;
}

export async function readLocalFile(path: string): Promise<{ content: string, html?: string }> {
    const res = await fetch(`${API_BASE_HOLDER.current}/document/read?path=${encodeURIComponent(path)}`);
    if (!res.ok) throw new Error("Failed to read local file");
    return await res.json();
}

export async function checkTranscriptionStatus(summary: boolean = true): Promise<TranscriptionStatus> {
    try {
        const res = await safeFetch(`${API_BASE_HOLDER.current}/document/transcribe/status?summary=${summary}`);
        if ('isNetworkError' in res) {
            return { status: 'standby', error_message: "Re-establishing High-Velocity Link..." };
        }
        const response = res as Response;
        if (!response.ok) return { status: 'error', error_message: "Sovereign Handshake Failed" };
        return await response.json();
    } catch (e) {
        return { status: 'error', error_message: "Polling Connection Interrupted" };
    }
}

export async function fetchMoodboard(text: string, providerOverride?: string, modelOverride?: string) {
    const provider = providerOverride || (typeof window !== 'undefined' ? (localStorage.getItem('tome_master_active_slot') || 'slot_primary') : 'slot_primary');
    const apiKey = typeof window !== 'undefined' ? (secureVault.load()[provider] || '') : '';
    const local_mode = typeof window !== 'undefined' ? localStorage.getItem('tome_master_local_mode') === 'true' : false;

    const res = await safeFetch(`${API_BASE_HOLDER.current}/analysis/moodboard`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text, provider, model: modelOverride, api_key: apiKey, local_mode }),
    });

    if ('isNetworkError' in res) {
        throw new Error("Visual Synthesis Offline: Connection to Moodboard engine failed.");
    }

    const response = res as Response;
    if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: "Moodboard generation failed" }));
        throw new Error(errorData.detail || "Moodboard generation failed");
    }
    return response.json();
}

export async function checkWorldBible(text: string, providerOverride?: string, modelOverride?: string) {
    const provider = providerOverride || (typeof window !== 'undefined' ? (localStorage.getItem('tome_master_active_slot') || 'slot_primary') : 'slot_primary');
    const apiKey = typeof window !== 'undefined' ? (secureVault.load()[provider] || '') : '';
    const local_mode = typeof window !== 'undefined' ? localStorage.getItem('tome_master_local_mode') === 'true' : false;

    const res = await safeFetch(`${API_BASE_HOLDER.current}/analysis/world-bible`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text, provider, model: modelOverride, api_key: apiKey, local_mode }),
    });

    if ('isNetworkError' in res) {
        throw new Error("Sovereign Wiki Offline: Connection to World Bible engine failed.");
    }

    const response = res as Response;
    if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: "World Bible extraction failed" }));
        throw new Error(errorData.detail || "World Bible extraction failed");
    }
    return response.json();
}

// Resilient Fetch Bridge: Prevents "Failed to fetch" crashes by returning an error object instead of throwing
async function safeFetch(url: string, options: RequestInit = {}, timeoutMs: number = 15000): Promise<Response | { error: string, isNetworkError: boolean }> {
    try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), timeoutMs); // configurable timeout to prevent infinite hangs
        const fetchOptions = { ...options, signal: controller.signal };

        const res = await fetch(url, fetchOptions);
        clearTimeout(timeoutId);
        return res;
    } catch (e) {
        const error = e as Error;
        return { error: error.message || "Network error", isNetworkError: true };
    }
}

export async function checkLicenseStatus() {
    const res = await safeFetch(`${API_BASE_HOLDER.current}/license/status`);

    if (!res || 'isNetworkError' in res) {
        // Return a simulated "offline" status instead of throwing
        return { is_activated: false, machine_id: "OFFLINE", error: "UNREACHABLE" };
    }

    // Now we know 'res' is a valid Response object
    const response = res as Response;
    if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        return { is_activated: false, machine_id: "ERROR", error: errorData.detail || "Server error" };
    }

    return response.json();
}

export async function activateLicense(key: string) {
    // [SOVEREIGN SNAP]: Re-align with the active portal to ensure absolute connectivity
    const activeBase = API_BASE_HOLDER.current;

    try {
        const res = await fetch(`${activeBase}/license/activate`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ key }),
        });

        if (!res.ok) {
            const errorData = await res.json().catch(() => ({ detail: "Handshake rejected by Sovereign Engine" }));
            throw new Error(errorData.detail || "Activation failed");
        }

        return await res.json();
    } catch (e: any) {
        if (e.message && e.message !== "Failed to fetch") {
            throw e;
        }
        throw new Error("Sovereign Engine Unreachable. Verify the backend window is open.");
    }
}

export async function fetchUsageHistory() {
    const res = await safeFetch(`${API_BASE_HOLDER.current}/analysis/usage`);
    if ('isNetworkError' in res) return { history: [], error: "OFFLINE" };
    if (!res.ok) throw new Error("Failed to fetch usage history");
    return res.json();
}

export async function fetchExpenditure() {
    const res = await safeFetch(`${API_BASE_HOLDER.current}/analysis/expenditure`);
    if ('isNetworkError' in res) return {};
    if (!res.ok) throw new Error("Failed to fetch expenditure data");
    return res.json();
}

export async function fetchOllamaStatus(apiKey?: string) {
    const url = `${API_BASE_HOLDER.current}/ai/ollama-status`;
    const res = await safeFetch(url);
    if ('isNetworkError' in res) return { status: "not_found", models: [], error: "OFFLINE" };
    if (!res.ok) throw new Error("Failed to check Ollama status");
    return res.json();
}

export async function fetchBitnetStatus() {
    const url = `${API_BASE_HOLDER.current}/ai/bitnet-status`;
    const res = await safeFetch(url);
    if ('isNetworkError' in res) return { status: "not_found", models: [], error: "OFFLINE" };
    if (!res.ok) throw new Error("Failed to check BitNet status");
    return res.json();
}

export async function validateAiKey(provider: string, apiKey: string, options: { custom_url?: string; model?: string } = {}): Promise<{ success: boolean; message: string }> {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 30000); // 30s Dead-man switch
    try {
        const response = await fetch(`${API_BASE_HOLDER.current}/analysis/validate-key`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                provider,
                api_key: apiKey,
                custom_url: options.custom_url,
                model: options.model
            }),
            signal: controller.signal
        });
        clearTimeout(timeoutId);
        return await response.json();
    } catch (e) {
        const error = e as Error;
        clearTimeout(timeoutId);
        if (error.name === 'AbortError') return { success: false, message: "Handshake Timeout: Network Obstruction / Global Saturation (30s)." };
        return { success: false, message: error.message || "Network Failure" };
    }
}

/**
 * SOVEREIGN INTELLIGENCE SCOUT
 * Dispatches a recursive discovery mission to find an unknown brand gateway.
 */
export async function discoverGateway(brandName: string, provider: string, apiKey: string): Promise<{ brand: string; url: string }> {
    const response = await fetch(`${API_BASE_HOLDER.current}/ai/discover`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ brand_name: brandName, provider, api_key: apiKey }),
    });
    if (!response.ok) throw new Error("Sovereign Scout Mission Failed: Handshake interrupted.");
    return response.json();
}

export async function getProjectLedger(folderPath: string) {
    const res = await safeFetch(`${API_BASE_HOLDER.current}/analysis/ledger?folder_path=${encodeURIComponent(folderPath)}`);
    if ('isNetworkError' in res || !res.ok) return { ledger: [] };
    return res.json();
}

export async function fetchVaultSync(): Promise<Record<string, string>> {
    try {
        const res = await safeFetch(`${API_BASE_HOLDER.current}/analysis/vault-sync`);
        if ('isNetworkError' in res) return {};
        const response = res as Response;
        if (!response.ok) return {};
        return await response.json();
    } catch (e) {
        return {};
    }
}

export async function saveVaultToEnv(keys: Record<string, string>): Promise<boolean> {
    try {
        const res = await safeFetch(`${API_BASE_HOLDER.current}/analysis/vault-save`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ keys })
        });
        if ('isNetworkError' in res) return false;
        const response = res as Response;
        return response.ok;
    } catch (e) {
        return false;
    }
}

export interface DiscoveredModel {
    id: string;
    name: string;
    description: string;
}

/**
 * [SOVEREIGN DISCOVERY]: Queries the backend which calls the provider's live API
 * using the stored key. The key determines what's available — zero assumptions.
 */
export async function fetchAvailableModels(provider: string): Promise<DiscoveredModel[]> {
    try {
        const res = await safeFetch(`${API_BASE_HOLDER.current}/analysis/models?provider=${encodeURIComponent(provider)}`);
        if ('isNetworkError' in res) return [];
        const response = res as Response;
        if (!response.ok) return [];
        const data = await response.json();
        return data.models || [];
    } catch (e) {
        return [];
    }
}

export async function checkSystemHealth(): Promise<{ backend: boolean; vault: boolean; ollama: boolean; bitnet: boolean }> {
    const health = { backend: false, vault: false, ollama: false, bitnet: false };

    // 1. Backend Ping
    try {
        const res = await fetch(`${API_BASE_HOLDER.current}/license/status`, { method: 'GET' });
        if (res.ok) health.backend = true;
    } catch (e) { }

    // 2. Vault Check
    const keys = secureVault.load();
    if (keys && Object.keys(keys).length > 0) health.vault = true;

    // 3. Ollama Check (Optional/Local)
    try {
        const res = await fetch('http://127.0.0.1:11434/api/tags', { method: 'GET' });
        if (res.ok) health.ollama = true;
    } catch (e) { }

    // 4. BitNet Status (local CPU inference on port 8080)
    try {
        const res = await fetch('http://127.0.0.1:8080/v1/models', { method: 'GET' });
        if (res.ok) health.bitnet = true;
    } catch (e) { }

    return health;
}

/**
 * SUPER MUSE PROSE REFINEMENT
 * Smooths dictated prose into Ron's authorial style using Style Mirror DNA.
 */
export async function refineProse(text: string, provider?: string, apiKey?: string): Promise<string> {
    try {
        const response = await fetch(`${API_BASE_HOLDER.current}/analysis/refine-prose`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                text,
                provider: provider || 'openai',
                api_key: apiKey
            }),
        });
        if (!response.ok) return text;
        const data = await response.json();
        return data.refined || text;
    } catch (e) {
        return text;
    }
}

export async function getBriefing(folderPath: string, provider?: string, apiKey?: string): Promise<string> {
    try {
        const response = await fetch(`${API_BASE_HOLDER.current}/analysis/briefing`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ folder_path: folderPath, provider: provider || 'openai', api_key: apiKey || '' }),
        });
        if (!response.ok) return "Operational link established. The boardroom is standing by.";
        const data = await response.json();
        return data.briefing || "Operational link established. Standing by.";
    } catch (e) {
        return "Directorial link established. Standing by for manuscript resurrection.";
    }
}

/**
 * DIRECTORIAL CAPTURE
 * Transmits a demo recording to the backend for project-root storage.
 */
export async function uploadRecording(file: File, folderPath: string): Promise<{ success: boolean, path?: string }> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('folder_path', folderPath);

    try {
        const response = await fetch(`${API_BASE_HOLDER.current}/analysis/save-recording`, {
            method: 'POST',
            body: formData,
        });
        if (!response.ok) throw new Error("Capture Handshake Failure");
        return await response.json();
    } catch (e) {
        throw e;
    }
}

/**
 * ARCHITECTURAL SNAPSHOT
 * Transmits a high-fidelity image capture to the project root for archival.
 */
export async function saveSnapshot(dataUrl: string, folderPath: string): Promise<{ success: boolean, path?: string }> {
    try {
        const response = await fetch(`${API_BASE_HOLDER.current}/analysis/save-snapshot`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ data_url: dataUrl, folder_path: folderPath }),
        });
        if (!response.ok) throw new Error("Snapshot Handshake Failure");
        return await response.json();
    } catch (e) {
        throw e;
    }
}

export async function fetchCloudModels(apiKey: string, provider: string): Promise<string[]> {
    try {
        const res = await fetch(`${API_BASE_HOLDER.current}/ai/models`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ api_key: apiKey, provider }),
        });
        if (!res.ok) return [];
        const data = await res.json();
        return data.models || [];
    } catch (e) {
        return [];
    }
}
