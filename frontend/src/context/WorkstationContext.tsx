"use client";

import React, { createContext, useContext, useState, useEffect, useRef, useCallback } from "react";
// [LEGACY RECOVERY ONLY]: read old IndexedDB pointers during migration; no new writes.
import { get } from "idb-keyval";
import {
    checkTranscriptionStatus, targetFolder, pickManuscript, readLocalFile,
    API_BASE_HOLDER, startTranscription, resolveAudit, uploadToProject, uploadManuscript,
    saveProjectState, loadProjectState
} from "@/lib/apiClient";
import { loadPreferences, getPref, setPref } from "@/lib/preferences";
import { TranscriptionStatus } from "@/types/industrial";

// --- [STRICT WORKSTATION INTERFACES] ---
export interface WorkstationState {
    bookTitle: string;
    authorName: string;
    coverImage: string | null;
    activeFolderPath: string | null;
    activeFilePath: string | null;
    isTranscribing: boolean;
    transcriptionStatus: TranscriptionStatus | null;
    processedPageCount: number;
    transcriptionMode: 'batch' | 'live';
    isActivated: boolean;
    language: 'en-US' | 'en-GB' | 'en-CA';
    isSettingsOpen: boolean;
    isHelpOpen: boolean;
    isEnhancementHubOpen: boolean;
    isAuditOpen: boolean;
    isLedgerOpen: boolean;
    isReportOpen: boolean;
    isStructuralModalOpen: boolean;
    isFocusMode: boolean;
    isOfflineMode: boolean;
    activeEnhancements: string[];
}

export interface WorkstationActions {
    setBookTitle: (val: string) => void;
    setAuthorName: (val: string) => void;
    setCoverImage: (val: string | null) => void;
    setActiveFolderPath: (val: string | null) => void;
    setActiveFilePath: (val: string | null) => void;
    setIsTranscribing: (val: boolean) => void;
    setTranscriptionStatus: React.Dispatch<React.SetStateAction<TranscriptionStatus | null>>;
    setProcessedPageCount: React.Dispatch<React.SetStateAction<number>>;
    setTranscriptionMode: (val: 'batch' | 'live') => void;
    setIsActivated: (val: boolean) => void;
    setLanguage: (lang: 'en-US' | 'en-GB' | 'en-CA') => void;
    setIsSettingsOpen: (open: boolean) => void;
    setIsHelpOpen: (open: boolean) => void;
    setIsEnhancementHubOpen: (open: boolean) => void;
    setIsAuditOpen: (val: boolean) => void;
    setIsLedgerOpen: (val: boolean) => void;
    setIsReportOpen: (val: boolean) => void;
    setIsStructuralModalOpen: (val: boolean) => void;
    setIsFocusMode: (val: boolean) => void;
    setIsOfflineMode: (val: boolean) => void;
    loadManuscript: () => Promise<void>;
    loadManuscriptFromUpload: (file: File) => Promise<void>;
    loadSealedManuscript: () => Promise<void>;
    establishProject: () => Promise<void>;
    invokeTranscription: () => Promise<void>;
    abortTranscription: (mode: 'current' | 'all') => Promise<void>;
    resolveAuditInput: (val: string) => Promise<void>;
    notify: (message: string) => void;
    hydrate: () => Promise<void>;
    toggleEnhancement: (id: string) => void;
}

const StateContext = createContext<WorkstationState | undefined>(undefined);
const ActionsContext = createContext<WorkstationActions | undefined>(undefined);

export const WorkstationProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
    const [bookTitle, setBookTitle] = useState("Manuscript");
    const [authorName, setAuthorName] = useState("Author");
    const [coverImage, setCoverImage] = useState<string | null>(null);
    // Gates metadata persistence until hydrate() runs, so defaults can't clobber saved values.
    const metadataHydratedRef = useRef(false);
    const [activeFolderPath, setActiveFolderPath] = useState<string | null>(null);
    const [activeFilePath, setActiveFilePath] = useState<string | null>(null);
    const [isTranscribing, setIsTranscribing] = useState(false);
    const [transcriptionStatus, setTranscriptionStatus] = useState<TranscriptionStatus | null>(null);
    const [processedPageCount, setProcessedPageCount] = useState(0);
    const [transcriptionMode, setTranscriptionMode] = useState<'batch' | 'live'>('live');
    const [isActivated, setIsActivated] = useState(false);
    const [language, setLanguage] = useState<'en-US' | 'en-GB' | 'en-CA'>('en-US');
    const [isSettingsOpen, setIsSettingsOpen] = useState(false);
    const [isHelpOpen, setIsHelpOpen] = useState(false);
    const [isEnhancementHubOpen, setIsEnhancementHubOpen] = useState(false);
    const [isAuditOpen, setIsAuditOpen] = useState(false);
    const [isLedgerOpen, setIsLedgerOpen] = useState(false);
    const [isReportOpen, setIsReportOpen] = useState(false);
    const [isStructuralModalOpen, setIsStructuralModalOpen] = useState(false);
    const [isFocusMode, setIsFocusMode] = useState(false);
    const [isOfflineMode, setIsOfflineMode] = useState(false);
    const [activeEnhancements, setActiveEnhancements] = useState<string[]>([]);

    const notify = useCallback((message: string) => {
        window.dispatchEvent(new CustomEvent('tome-master-guide-speak', { detail: { text: message } }));
    }, []);

    const establishProject = async () => {
        try {
            const result = await targetFolder();
            if ((result.status === 'success' || result.status === 'established' || result.status === 'targeted') && result.folder_path) {
                setActiveFolderPath(result.folder_path);
                // [FILES-ONLY]: remember the last project in the vault (reopen on launch).
                setPref('last_project', { folder: result.folder_path, file: null });
                    notify(`Project Established: ${result.folder_path}`);
            }
        } catch (err) {
            notify("Handshake Failed: Engine is unreachable.");
        }
    };

    // [SHARED LOAD LOGIC]: handles a picker/upload result identically — text
    // formats hydrate immediately; .docx/.doc/.wpd/.wps/.odt/text-pdf route to the
    // full backend parser via transcription; scanned docs prompt OCR. Both the
    // native picker AND the browser upload feed through here → zero format loss.
    const applyPickResult = async (result: { status: string; file_path?: string | null; folder_path?: string | null; filename?: string | null; is_parseable?: boolean }) => {
        if (result.status !== 'loaded' || !result.file_path) return;
        setActiveFolderPath(result.folder_path || null);
        setActiveFilePath(result.file_path || null);
        setPref('last_project', { folder: result.folder_path || null, file: result.file_path || null });

        const ext = result.file_path.split('.').pop()?.toLowerCase();
        if (['md', 'markdown', 'txt'].includes(ext || '')) {
            notify(`Recovering prose from: ${result.filename}...`);
            const data = await readLocalFile(result.file_path);
            if (data.content) {
                window.dispatchEvent(new CustomEvent('tome-master-editor-hydrate', {
                    detail: {
                        content: data.content,
                        html: data.html || `<p>${data.content.replace(/\n/g, '<br>')}</p>`
                    }
                }));
                notify(`Manuscript Ingested & Hydrated: ${result.filename}`);
            }
        } else {
            notify(`Manuscript Ingested: ${result.filename}`);
            notify(`Command set to: ${result.folder_path}`);
            if (['pdf', 'docx', 'doc', 'wpd', 'wps', 'odt'].includes(ext || '')) {
                // [SMART ROUTE]: parseable (digital PDF / Word doc / legacy) → the
                // backend text-parses (legacy via legacy_parser); else it's a scan → OCR.
                if (result.is_parseable) {
                    const legacy = ['doc', 'wpd', 'wps', 'odt'].includes(ext || '');
                    notify(legacy
                        ? "Legacy document detected — resurrecting manuscript text..."
                        : "Digital document detected — extracting text (no OCR needed)...");
                    await invokeTranscription();
                } else {
                    notify("ACTION REQUIRED: This is a scanned document. Click 'Transcribe' to OCR the manuscript.");
                }
            } else {
                notify("Ready for Structural Audit.");
            }
        }
    };

    const loadManuscript = async () => {
        try {
            const result = await pickManuscript();   // desktop native picker
            await applyPickResult(result);
        } catch (err) {
            notify("Sovereign Ingestion Failed: Engine is unreachable.");
        }
    };

    // [BROWSER LOAD]: feed a browser-picked File through the SAME pipeline as the
    // native picker — every format the desktop app supports, none dropped.
    const loadManuscriptFromUpload = async (file: File) => {
        try {
            const ext = file.name.split('.').pop()?.toLowerCase() || '';
            // [STRUCTURED LOAD]: .docx is a finished manuscript — parse it with
            // mammoth (real <h1>/<h2> headings + TOC) and hydrate the editor
            // directly. The editor rebuilds the TOC sidebar from the headings.
            // Do NOT route it through transcription (that flattens the structure).
            if (ext === 'docx') {
                notify(`Loading ${file.name}…`);
                const parsed = await uploadManuscript(file);
                if (parsed && (parsed.content || parsed.raw_text)) {
                    window.dispatchEvent(new CustomEvent('tome-master-editor-hydrate', {
                        detail: { html: parsed.content || '', content: parsed.raw_text || '' }
                    }));
                    const words = typeof parsed.word_count === 'number' ? parsed.word_count.toLocaleString() : '?';
                    notify(`Loaded: ${file.name} (${words} words — chapter headings + TOC preserved)`);
                    return;
                }
                notify(`Could not parse ${file.name}.`);
                return;
            }
            // Legacy (.doc/.wpd/.wps/.odt), scanned PDF, etc. → full pipeline.
            notify(`Uploading ${file.name}…`);
            const result = await uploadToProject(file);
            await applyPickResult(result);
        } catch (err) {
            notify(`Load failed: ${err instanceof Error ? err.message : String(err)}`);
        }
    };

    const loadSealedManuscript = async () => {
        try {
            notify("Invoking native picker for Sealed Manuscript...");
            const result = await pickManuscript();
            
            if (result.status === 'loaded' && result.file_path) {
                notify(`Accessing: ${result.filename}...`);
                setActiveFolderPath(result.folder_path);
                setActiveFilePath(result.file_path || null);
                setPref('last_project', { folder: result.folder_path || null, file: result.file_path || null });

                // Read the content
                const data = await readLocalFile(result.file_path);
                if (data.content) {
                    // [HYDRATION]: Force the editor to update with the recovered prose
                    window.dispatchEvent(new CustomEvent('tome-master-editor-hydrate', { 
                        detail: { 
                            content: data.content,
                            html: data.html || `<p>${data.content.replace(/\n/g, '<br>')}</p>`
                        } 
                    }));
                    notify(`Sovereign Restoration Complete: ${result.filename}`);
                } else {
                    notify("Restore Failed: File appears empty or corrupted.");
                }
            } else if (result.status === 'cancelled') {
                notify("Restoration Aborted.");
            }
        } catch (err) {
            console.error("Restoration Error:", err);
            notify("Sovereign Restoration Failed: Handshake error.");
        }
    };

    const invokeTranscription = async () => {
        if (!activeFolderPath) { notify("Select a project folder first."); return; }
        setIsTranscribing(true);
        try {
            // [SOVEREIGN DISCOVERY]: Backend resolves provider/model/key from Settings vault.
            // The API key configured in Settings determines the engine — nothing hardcoded here.
            await startTranscription(activeFolderPath, transcriptionMode);
            notify("Ingestion Pulse Detected. Monitoring engine...");
        } catch (err) {
            setIsTranscribing(false);
            notify("Engine Ignition Failed.");
        }
    };

    // [REMOVED]: confirmInjection / cancelInjection / resolveInjection — they
    // posted to endpoints that never existed and were wired to no UI element.

    const abortTranscription = async (mode: 'current' | 'all') => {
        try {
            const res = await fetch(`${API_BASE_HOLDER.current}/transcribe/abort?mode=${mode}`, { method: 'POST' });
            if (!res.ok) {
                notify(`Abort request refused by engine (HTTP ${res.status}).`);
                return;
            }
            const data = await res.json();
            setIsTranscribing(false);
            notify(data.was_active
                ? "Transcription halted. In-flight work stops at the next safe point."
                : "No transcription was running — state reset.");
        } catch (err) {
            notify("Abort failed: engine unreachable.");
        }
    };

    const resolveAuditInput = async (val: string) => {
        const ok = await resolveAudit(val, false);
        notify(ok
            ? `Audit resolved: page ${val} committed.`
            : "Audit resolution refused — no audit is awaiting input.");
    };

    const toggleEnhancement = (id: string) => {
        setActiveEnhancements(prev => {
            const next = prev.includes(id) ? prev.filter(e => e !== id) : [...prev, id];
            // [FILES-ONLY]: enhancements are per-project → persist into the project file.
            saveProjectState(activeFolderPath, { active_enhancements: next });
            return next;
        });
    };

    const hydrate = useCallback(async () => {
        // [FILES-ONLY]: the last project (folder + file) lives in vault preferences;
        // fall back to the legacy IndexedDB pointers so an existing user isn't reset.
        await loadPreferences();
        const last = getPref<{ folder?: string | null; file?: string | null }>('last_project', {});
        const folder = last.folder || await get<string>('tome_master_active_folder') || null;
        if (folder) setActiveFolderPath(folder);

        const filePath = last.file || await get<string>('tome_master_active_file') || null;
        if (filePath) setActiveFilePath(filePath);
        if (filePath) {
            const ext = filePath.split('.').pop()?.toLowerCase();
            if (['md', 'markdown', 'txt'].includes(ext || '')) {
                try {
                    const data = await readLocalFile(filePath);
                    if (data.content) {
                        window.dispatchEvent(new CustomEvent('tome-master-editor-hydrate', { 
                            detail: { 
                                content: data.content,
                                html: data.html || `<p>${data.content.replace(/\n/g, '<br>')}</p>`
                            } 
                        }));
                    }
                } catch (e) {}
            }
        }

        // [FILES-ONLY]: project metadata + enhancements live in tome_master_project.json.
        // [LEGACY RECOVERY]: fall back to the old IndexedDB values so an existing user's
        // title/author/cover/enhancements are never lost (then re-saved into the file).
        const project = await loadProjectState(folder || null);

        const enhancements = (Array.isArray(project.active_enhancements) ? project.active_enhancements : null)
            || await get<string[]>('tome_master_active_enhancements');
        if (enhancements) setActiveEnhancements(enhancements as string[]);

        const title = (project.draft_title as string) || await get<string>('tome_master_draft_title') || "";
        const author = (project.draft_author as string) || await get<string>('tome_master_draft_author') || "";
        const cover = (project.draft_cover as string) || await get<string>('tome_master_draft_cover') || "";
        if (title) setBookTitle(title);
        if (author) setAuthorName(author);
        if (cover) setCoverImage(cover);
        metadataHydratedRef.current = true;

        try {
            const res = await fetch(`${API_BASE_HOLDER.current}/license/status`);
            const data = await res.json();
            if (data.is_activated) setIsActivated(true);
        } catch (e) {}
    }, []);

    useEffect(() => { hydrate(); }, [hydrate]);

    // [PERSIST]: project metadata survives reload; skip until hydrate restored saved
    // values. Writes the metadata slice into tome_master_project.json (merged
    // server-side with the editor's draft slice).
    useEffect(() => {
        if (!metadataHydratedRef.current) return;
        saveProjectState(activeFolderPath, {
            draft_title: bookTitle,
            draft_author: authorName,
            ...(coverImage ? { draft_cover: coverImage } : {}),
        });
    }, [bookTitle, authorName, coverImage, activeFolderPath]);

    useEffect(() => {
        const pulse = setInterval(async () => {
            try {
                // Heartbeat to keep backend alive and sync activation
                await fetch(`${API_BASE_HOLDER.current}/ai/status`);
                const res = await fetch(`${API_BASE_HOLDER.current}/license/status`);
                const data = await res.json();
                setIsActivated(data.is_activated);
            } catch (e) {}
        }, 15000);
        return () => clearInterval(pulse);
    }, []);

    const workstationState: WorkstationState = {
        bookTitle, authorName, coverImage, activeFolderPath, activeFilePath,
        isTranscribing, transcriptionStatus, processedPageCount, transcriptionMode,
        isActivated, language, isSettingsOpen, isHelpOpen, isEnhancementHubOpen,
        isAuditOpen, isLedgerOpen, isReportOpen, isStructuralModalOpen, isFocusMode,
        isOfflineMode, activeEnhancements
    };

    const workstationActions: WorkstationActions = {
        setBookTitle, setAuthorName, setCoverImage, setActiveFolderPath, setActiveFilePath,
        setIsTranscribing, setTranscriptionStatus, setProcessedPageCount, setTranscriptionMode,
        setIsActivated, setLanguage, setIsSettingsOpen, setIsHelpOpen, setIsEnhancementHubOpen,
        setIsAuditOpen, setIsLedgerOpen, setIsReportOpen, setIsStructuralModalOpen, setIsFocusMode,
        setIsOfflineMode,
        loadManuscript, loadManuscriptFromUpload, loadSealedManuscript, establishProject, invokeTranscription, abortTranscription,
        resolveAuditInput, notify, hydrate,
        toggleEnhancement
    };

    return (
        <StateContext.Provider value={workstationState}>
            <ActionsContext.Provider value={workstationActions}>
                {children}
            </ActionsContext.Provider>
        </StateContext.Provider>
    );
};

export const useWorkstationState = () => {
    const context = useContext(StateContext);
    if (!context) throw new Error("useWorkstationState must be used within WorkstationProvider");
    return context;
};

export const useWorkstationActions = () => {
    const context = useContext(ActionsContext);
    if (!context) throw new Error("useWorkstationActions must be used within WorkstationProvider");
    return context;
};
