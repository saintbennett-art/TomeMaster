import { saveBlobWithSovereignty } from './file_system_utils';

// [HANDSHAKE ANCHOR]: Managed via a dynamic producer to handle Windows interface jitters
let ACTIVE_PORT = "8080"; // Default anchor

function discoverActivePort(): string {
    if (typeof window !== 'undefined') {
        const urlParams = new URLSearchParams(window.location.search);
        const paramPort = urlParams.get('api_port');
        if (paramPort) {
            console.log(`[BOARDROOM HANDSHAKE]: Port discovered via URL: ${paramPort}`);
            return paramPort;
        }
    }
    return ACTIVE_PORT;
}

export async function getLiveApiBase(): Promise<string> {
    const port = discoverActivePort();
    // [INTERFACE SNAP]: Use 127.0.0.1 for consistent Windows resolution
    return `http://127.0.0.1:${port}/api/v1`;
}

// Global anchor that always reflects the current successful interface
export const API_BASE_HOLDER = { current: `http://127.0.0.1:${discoverActivePort()}/api/v1` };

// Initialize the bridge immediately upon module load
if (typeof window !== 'undefined') {
    getLiveApiBase().then(base => {
        API_BASE_HOLDER.current = base;
        console.log(`[BOARDROOM ACTIVE]: Base URL anchored at ${base}`);
    });
}


export async function uploadManuscript(file: File, isDemo: boolean = false, signal?: AbortSignal, isRecovery: boolean = false) {
  const formData = new FormData();
  formData.append("file", file);

  const provider = typeof window !== 'undefined' ? (localStorage.getItem('tome_master_provider') || 'gemini') : 'gemini';
  const apiKey = typeof window !== 'undefined' ? (localStorage.getItem(`tome_master_key_${provider}`) || '') : '';

  formData.append("api_key", apiKey);
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

export async function uploadManuscriptStream(file: File, onChunk: (data: any) => void, isDemo: boolean = false, signal?: AbortSignal) {
  const formData = new FormData();
  formData.append("file", file);

  const provider = typeof window !== 'undefined' ? (localStorage.getItem('tome_master_provider') || 'gemini') : 'gemini';
  const apiKey = typeof window !== 'undefined' ? (localStorage.getItem(`tome_master_key_${provider}`) || '') : '';

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
          console.error("Failed to parse ndjson line:", line);
        }
      }
    }
  }
}


export async function analyzeEmotionalArc(text: string, providerOverride?: string, modelOverride?: string) {
    const provider = providerOverride || (typeof window !== 'undefined' ? (localStorage.getItem('tome_master_provider') || 'gemini') : 'gemini');
    const apiKey = typeof window !== 'undefined' ? (localStorage.getItem(`tome_master_key_${provider}`) || '') : '';
    const local_mode = typeof window !== 'undefined' ? localStorage.getItem('tome_master_local_mode') === 'true' : false;
 
    let lastError = null;
    for (let i = 0; i < 3; i++) {
        try {
            const res = await safeFetch(`${API_BASE_HOLDER.current}/analysis/emotional-arc`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ text, provider, model: modelOverride, api_key: apiKey, local_mode }),
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
    userChapters?: any[], 
    customUrl?: string, 
    localMode: boolean = false, 
    synthesisMode: boolean = false, 
    customPrompt?: string,
    projectFolder?: string
) {
  const apiKey = localStorage.getItem(`tome_master_key_${provider || 'gemini'}`) || '';
  
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

export async function draftExpert(content: string, persona: string, userChapters: any[] | null = null, synthesisMode: boolean = false) {
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

export async function exportDocx(content: string, chapters: any[] = [], title?: string, author?: string, format: string = "chicago", coverImage?: string) {
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

export async function exportPdf(content: string, chapters: any[] = [], title?: string, author?: string, format: string = "chicago", coverImage?: string) {
  const res = await fetch(`${API_BASE_HOLDER.current}/document/export/pdf`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ content, chapters, title, author, format, cover_image: coverImage }),
  });

  if (!res.ok) throw new Error("Export failed");
  
  const blob = await res.blob();
  await saveBlobWithSovereignty(blob, `${title || "Manuscript"}.pdf`, "Manuscript (PDF)");
}

export async function exportEpub(content: string, chapters: any[] = [], title?: string, author?: string, format: string = "chicago", coverImage?: string) {
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
    apiKey: string, provider: string, isDemoMode: boolean, folderPath: string, 
    resetCache: boolean = false, mode: 'batch' | 'live' = 'batch', model?: string,
    fallbackProvider?: string, fallbackModel?: string
): Promise<{status: string, folder_path: string}> {
  // [SOVEREIGN PATIENCE]: Retry the transcription signal 3 times to account for engine warm-up
  let lastError = null;
  for (let i = 0; i < 3; i++) {
    try {
        const res = await safeFetch(`${API_BASE_HOLDER.current}/document/transcribe/start`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ 
                api_key: apiKey, provider, is_demo: isDemoMode, folder_path: folderPath, 
                reset_cache: resetCache, mode, model,
                fallback_provider: fallbackProvider,
                fallback_model: fallbackModel
            }),
        }, 300000); // [SOVEREIGN PATIENCE]: 5 minute window for user folder selection
        
        if ('isNetworkError' in res) throw new Error("CONNECTION_REFUSED");
        const response = res as Response;
        if (!response.ok) throw new Error(`Transcription Handshake Denied: ${response.status}`);
        
        return await response.json();
    } catch (e) {
        lastError = e;
        if (i < 2) await new Promise(r => setTimeout(r, 1000)); // Wait 1s between tries
    }
  }
  console.error("Directorial Link Severed after retries:", lastError);
  throw new Error("CONNECTION_REFUSED");
}

// [STABILITY]: Increased timeout and retry logic to prevent "Backend Failure" race conditions
export const checkBackendHealth = async (retries = 3): Promise<boolean> => {
    for (let i = 0; i < retries; i++) {
        try {
            const resp = await fetch(`${API_BASE_HOLDER.current}/ai/status`, { signal: AbortSignal.timeout(3000) });
            if (resp.ok) return true;
        } catch (e) {
            console.log(`ENGINE: Connection attempt ${i+1} failed. Retrying...`);
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

export async function anchorFolder(): Promise<{ status: string, folder_path: string | null }> {
    // [SOVEREIGN PATIENCE]: Retry the anchor signal 3 times to account for engine warm-up
    let lastError = null;
    for (let i = 0; i < 3; i++) {
        try {
            // [NATIVE DIALOG LOCK]: 5 minute timeout for user browsing
            const res = await safeFetch(`${API_BASE_HOLDER.current}/document/anchor`, {}, 300000);
            if ('isNetworkError' in res) throw new Error("CONNECTION_REFUSED");
            const response = res as Response;
            if (!response.ok) throw new Error("Anchor Handshake Failed");
            return await response.json();
        } catch (e) {
            lastError = e;
            if (i < 2) await new Promise(r => setTimeout(r, 800)); // Wait 800ms between tries
        }
    }
    console.error("Directorial Anchor Severed after retries:", lastError);
    throw lastError;
}

export async function checkTranscriptionStatus(summary: boolean = true): Promise<any> {
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
     const provider = providerOverride || (typeof window !== 'undefined' ? (localStorage.getItem('tome_master_provider') || 'gemini') : 'gemini');
    const apiKey = typeof window !== 'undefined' ? (localStorage.getItem(`tome_master_key_${provider}`) || '') : '';
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
     const provider = providerOverride || (typeof window !== 'undefined' ? (localStorage.getItem('tome_master_provider') || 'gemini') : 'gemini');
    const apiKey = typeof window !== 'undefined' ? (localStorage.getItem(`tome_master_key_${provider}`) || '') : '';
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
    } catch (e: any) {
        console.warn(`[Network Bridge] Connection to ${url} failed. Is the backend running?`, e);
        return { error: e.message || "Network error", isNetworkError: true };
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
    console.error("Directorial Link Severed during Activation:", e);
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
    } catch (e: any) {
        clearTimeout(timeoutId);
        if (e.name === 'AbortError') return { success: false, message: "Handshake Timeout: Network Obstruction / Global Saturation (30s)." };
        return { success: false, message: e.message || "Network Failure" };
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

export async function checkSystemHealth(): Promise<{ backend: boolean; vault: boolean; ollama: boolean }> {
    const health = { backend: false, vault: false, ollama: false };
    
    // 1. Backend Ping
    try {
        const res = await fetch(`${API_BASE_HOLDER.current.replace('/api/v1', '')}/`, { method: 'GET' });
        if (res.ok) health.backend = true;
    } catch (e) {}

    // 2. Vault Check
    const keys = localStorage.getItem('tome_master_vault');
    if (keys && keys.length > 10) health.vault = true;

    // 3. Ollama Check (Optional/Local)
    try {
        const res = await fetch('http://127.0.0.1:11434/api/tags', { method: 'GET' });
        if (res.ok) health.ollama = true;
    } catch (e) {}

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
        console.error("Super Muse Refinement Failure:", e);
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
        console.error("Directorial Briefing Failure:", e);
        return "Directorial link established. Standing by for manuscript resurrection.";
    }
}

/**
 * DIRECTORIAL CAPTURE
 * Transmits a demo recording to the backend for project-root storage.
 */
export async function uploadRecording(file: File, folderPath: string): Promise<any> {
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
        console.error("Directorial Capture Transmission Failure:", e);
        throw e;
    }
}

/**
 * ARCHITECTURAL SNAPSHOT
 * Transmits a high-fidelity image capture to the project root for archival.
 */
export async function saveSnapshot(dataUrl: string, folderPath: string): Promise<any> {
    try {
        const response = await fetch(`${API_BASE_HOLDER.current}/analysis/save-snapshot`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ data_url: dataUrl, folder_path: folderPath }),
        });
        if (!response.ok) throw new Error("Snapshot Handshake Failure");
        return await response.json();
    } catch (e) {
        console.error("Architectural Snapshot Transmission Failure:", e);
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
        console.error("Model Handshake Failed:", e);
        return [];
    }
}
