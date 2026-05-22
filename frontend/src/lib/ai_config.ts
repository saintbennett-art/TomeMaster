/**
 * 🛡️ SOVEREIGN INTELLIGENCE CONFIGURATION v5.1
 * --------------------------------------------------
 * This library defines the mandatory architectural foundations for Tome-Master.
 * Gemini 3.1 Pro is the production standard. Regression is forbidden.
 * --------------------------------------------------
 */

export interface Provider {
    id: string;
    name: string;
    model: string;
    color: string;
    placeholder: string;
    link: string;
    linkLabel: string;
    description: string;
    nomenclatureNote: string;
    defaultModel: string;
}

export const MASTER_PROVIDER_LIBRARY: Provider[] = [
    {
        id: 'gemini',
        name: 'Gemini 3.1 Pro',
        model: 'gemini-3.1-pro-preview',
        color: 'text-indigo-400',
        placeholder: 'Enter Gemini API Key...',
        link: 'https://aistudio.google.com/app/apikey',
        linkLabel: 'Get Gemini Key',
        description: 'Primary Narrative Apex. Hard-bound to the 3.1 Pro architecture for directorial fidelity.',
        nomenclatureNote: 'Absolute Synchrony: Backend technical ID securely maps to public Directorial Standards.',
        defaultModel: 'gemini-3.1-pro-preview'
    },
    {
        id: 'openai',
        name: 'OpenAI GPT-4o',
        model: 'gpt-4o',
        color: 'text-emerald-400',
        placeholder: 'Enter OpenAI API Key...',
        link: 'https://platform.openai.com/api-keys',
        linkLabel: 'Get OpenAI Key',
        description: 'Logical Synchronization Engine. High-precision structural and logical audit.',
        nomenclatureNote: 'Deep Logic: Utilized for high-fidelity specialist handshakes.',
        defaultModel: 'gpt-4o-mini'
    },
    {
        id: 'anthropic',
        name: 'Claude 3.5 Sonnet',
        model: 'claude-3-5-sonnet-latest',
        color: 'text-orange-400',
        placeholder: 'Enter Anthropic API Key...',
        link: 'https://console.anthropic.com/settings/keys',
        linkLabel: 'Get Claude Key',
        description: 'Prose & Linguistic Orchestrator. Specialized in creative texture and stylistic audits.',
        nomenclatureNote: 'Creative Texture: Calibrated for maximal narrative resonance.',
        defaultModel: 'claude-3-5-sonnet-20241022'
    },
    {
        id: 'groq',
        name: 'Groq High-Velocity',
        model: 'llama-3.3-70b-versatile',
        color: 'text-rose-400',
        placeholder: 'Enter Groq API Key...',
        link: 'https://console.groq.com/keys',
        linkLabel: 'Get Groq Key',
        description: 'LPU Acceleration Engine. Processes 400-page audits in seconds via Llama-3.3.',
        nomenclatureNote: 'Velocity Lock: Ultra-low latency LPU inference for real-time directorial feedback.',
        defaultModel: 'meta-llama/llama-4-scout-17b-16e-instruct'
    },
    {
        id: 'ollama',
        name: 'Local Intelligence',
        model: 'mistral',
        color: 'text-zinc-400',
        placeholder: 'Enter Custom Ollama URL...',
        link: 'https://ollama.com',
        linkLabel: 'Local Deployment',
        description: 'Sovereign Offline Intelligence. Executes specialized audits on local hardware.',
        nomenclatureNote: 'Sovereign Link: Port 11434 mandatory for local logistical handshakes.',
        defaultModel: 'llama3'
    },
    {
        id: 'bitnet',
        name: 'BitNet CPU Engine',
        model: 'ggml-model-i2_s',
        color: 'text-cyan-400',
        placeholder: 'http://localhost:8080',
        link: 'https://github.com/microsoft/BitNet',
        linkLabel: 'BitNet Setup',
        description: 'Sovereign 1-Bit Intelligence. Microsoft BitNet 1.58-bit ternary LLMs — runs entirely on CPU, no GPU required. Ultra-low power, zero cloud dependency.',
        nomenclatureNote: 'CPU Apex: 1.58-bit ternary weights bypass floating-point math entirely. Addition and subtraction only. Port 8080 default.',
        defaultModel: 'ggml-model-i2_s'
    }
];

export interface GatewaySlot {
    id: string;
    label: string;
    status: 'unestablished' | 'established' | 'offline';
    color: string;
    description: string;
    apexRole: string;
    mappedProviderId?: string;
}

/**
 * 🛡️ SOVEREIGN GATEWAY REGISTRY
 * Upgraded logic: Slots now ACT AS CONTAINERS for the library providers.
 * This ensures that a persona like "Copy Editor" can be assigned to a specific gateway.
 */
export const SOVEREIGN_SLOT_REGISTRY: GatewaySlot[] = [
    { 
        id: 'slot_primary', 
        label: 'Primary Gateway', 
        status: 'unestablished',
        color: 'text-indigo-400', 
        description: 'The Lead Directorial Intelligence. Responsible for high-fidelity narrative audits.',
        apexRole: 'NARRATIVE_ARCHITECT',
        mappedProviderId: 'gemini'
    },
    { 
        id: 'slot_specialist', 
        label: 'Specialist Node', 
        status: 'unestablished',
        color: 'text-emerald-400', 
        description: 'Logical and structural audit specialist.',
        apexRole: 'COPY_EDITOR',
        mappedProviderId: 'openai'
    },
    { 
        id: 'slot_velocity', 
        label: 'Velocity Engine', 
        status: 'unestablished',
        color: 'text-rose-400', 
        description: 'High-speed LPU acceleration for real-time transcription.',
        apexRole: 'TRANSCRIBER_LEAD',
        mappedProviderId: 'groq'
    }
];

export const isVisionModel = (modelId: string): boolean => {
    if (!modelId) return false;
    const m = modelId.toLowerCase();
    // [SOVEREIGN GUARD]: Versatile models are TEXT-ONLY. Exclusion is mandatory.
    if (m.includes('versatile') || m.includes('instant') || m.includes('text')) return false;

    // Groq Vision Models (Must explicitly contain 'vision')
    if (m.includes('vision')) return true;
    // Gemini Standard Vision Support
    if (m.includes('gemini')) return true;
    // OpenAI Standard Vision Support
    if (m.includes('gpt-4o')) return true;
    // Anthropic Standard Vision Support
    if (m.includes('claude-3-5') || m.includes('claude-3-opus')) return true;
    return false;
};
