// --- [INDUSTRIAL SCHEMA DEFINITIONS] ---

export interface Chapter {
    id: string;
    title: string;
    suggested_title?: string;
    original_heading?: string;
    chapter_word_count: number;
    reading_time_mins?: number;
    startingWords?: string;
    content?: string;
    status?: 'draft' | 'reviewed' | 'sealed';
    chapter_number?: number;
    emotional_intensity?: number;
    summary?: string;
    content_warnings?: string[];
    starting_words?: string;
}

export interface TranscriptionPage {
    index: number;
    text: string;
    filename?: string;
}

export interface TranscriptionStatus {
    status: 'idle' | 'transcribing' | 'complete' | 'error' | 'audit' | 'awaiting_direction' | 'reviewing_injection';
    processed_images: number;
    total_images: number;
    current_image_b64?: string;
    current_extracted_text?: string;
    new_pages: TranscriptionPage[];
    missing_pages_count: number;
    error_message?: string;
    current_injection_page?: number;
    current_injection_text?: string;
}

export interface Suggestion {
    id: string;
    type: 'replace' | 'insert' | 'metadata';
    label?: string;
    original?: string;
    suggestion?: string;
    content?: string;
    reason: string;
}

export interface AgentReport {
    agent_id: string;
    timestamp: string;
    content: string;
    feedback: string;
    suggestions: Suggestion[];
    verdict?: 'pass' | 'fail' | 'needs_revision';
    _accounting?: {
        processing_time?: number;
        model_ref?: string;
        model_audit?: string;
        credits_consumed?: number;
        unit?: string;
        succeeded?: boolean;
    };
}

export interface MoodboardData {
    image_url: string;
    prompt: string;
    elements: string[];
}

export interface Character {
    name: string;
    role: string;
    traits: string;
    details: string;
}

export interface Location {
    name: string;
    type: string;
    description: string;
}

export interface ContinuityBibleData {
    characters: Character[];
    locations: Location[];
}

export interface ArcPoint {
    segment: string;
    score: number;
    chapter_word_count: number;
}

export interface SystemAudit {
    os?: string;
    ram_total: number;
    ram_used?: number;
    cpu_usage?: number;
}

export interface LedgerEntry {
    action?: string;
    timestamp: number;
    provider: string;
    metrics?: {
        total_tokens: number;
    };
}
