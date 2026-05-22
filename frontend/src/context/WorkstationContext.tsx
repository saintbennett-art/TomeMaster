"use client";

import React, { createContext, useContext, useState, useEffect, useCallback } from "react";
import { get, set } from "idb-keyval";
import {
    checkTranscriptionStatus, targetFolder, pickManuscript, readLocalFile,
    API_BASE_HOLDER, startTranscription
} from "@/lib/apiClient";
import { TranscriptionStatus } from "@/types/industrial";

// --- [STRICT WORKSTATION INTERFACES] ---
export interface WorkstationState {
    bookTitle: string;
    authorName: string;
    coverImage: string | null;
    activeFolderPath: string | null;
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
    activeEnhancements: string[];
}

export interface WorkstationActions {
    setBookTitle: (val: string) => void;
    setAuthorName: (val: string) => void;
    setCoverImage: (val: string | null) => void;
    setActiveFolderPath: (val: string | null) => void;
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
    loadManuscript: () => Promise<void>;
    loadSealedManuscript: () => Promise<void>;
    establishProject: () => Promise<void>;
    invokeTranscription: () => Promise<void>;
    confirmInjection: () => Promise<void>;
    cancelInjection: () => Promise<void>;
    abortTranscription: (mode: 'current' | 'all') => Promise<void>;
    resolveAuditInput: (val: string) => Promise<void>;
    resolveInjection: (decision: 'accept' | 'reject' | 'quit') => Promise<void>;
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
    const [activeFolderPath, setActiveFolderPath] = useState<string | null>(null);
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
    const [activeEnhancements, setActiveEnhancements] = useState<string[]>([]);

    const notify = useCallback((message: string) => {
        window.dispatchEvent(new CustomEvent('tome-master-guide-speak', { detail: { text: message } }));
    }, []);

    const establishProject = async () => {
        try {
            const result = await targetFolder();
            if ((result.status === 'success' || result.status === 'established' || result.status === 'targeted') && result.folder_path) {
                setActiveFolderPath(result.folder_path);
                await set('tome_master_active_folder', result.folder_path);
                    notify(`Project Established: ${result.folder_path}`);
            }
        } catch (err) {
            notify("Handshake Failed: Engine is unreachable.");
        }
    };

    const loadManuscript = async () => {
        try {
            const result = await pickManuscript();
            if (result.status === 'loaded' && result.file_path) {
                setActiveFolderPath(result.folder_path);
                await set('tome_master_active_folder', result.folder_path);
                await set('tome_master_active_file', result.file_path);
                
                // [AUTO-HYDRATION]: If it's a markdown or text file, load it immediately
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
                        // [SMART ROUTE]: If the backend says this file is parseable
                        // (digital PDF with text layer, Word doc, or legacy format), auto-start
                        // transcription — the backend will text-parse instead of OCR.
                        if (result.is_parseable) {
                            const legacy = ['doc', 'wpd', 'wps', 'odt'].includes(ext || '');
                            notify(legacy
                                ? "Legacy document detected — resurrecting manuscript text..."
                                : "Digital document detected — extracting text (no OCR needed)...");
                            // Auto-trigger transcription; backend smart-routes to text parser
                            await invokeTranscription();
                        } else {
                            notify("ACTION REQUIRED: This is a scanned document. Click 'Transcribe' to OCR the manuscript.");
                        }
                    } else {
                        notify("Ready for Structural Audit.");
                    }
                }
            }
        } catch (err) {
            notify("Sovereign Ingestion Failed: Engine is unreachable.");
        }
    };

    const loadSealedManuscript = async () => {
        try {
            notify("Invoking native picker for Sealed Manuscript...");
            const result = await pickManuscript();
            
            if (result.status === 'loaded' && result.file_path) {
                notify(`Accessing: ${result.filename}...`);
                setActiveFolderPath(result.folder_path);
                await set('tome_master_active_folder', result.folder_path);
                
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

    const confirmInjection = async () => {
        try { await fetch(`${API_BASE_HOLDER.current}/transcribe/confirm`, { method: 'POST' }); notify("Injected."); } catch (err) {}
    };

    const cancelInjection = async () => {
        try { await fetch(`${API_BASE_HOLDER.current}/transcribe/cancel`, { method: 'POST' }); notify("Aborted."); } catch (err) {}
    };

    const abortTranscription = async (mode: 'current' | 'all') => {
        try {
            await fetch(`${API_BASE_HOLDER.current}/transcribe/abort?mode=${mode}`, { method: 'POST' });
            setIsTranscribing(false);
            notify(`Abort Sequence Initiated: ${mode}`);
        } catch (err) {}
    };

    const resolveAuditInput = async (val: string) => {
        try { await fetch(`${API_BASE_HOLDER.current}/transcribe/resolve_audit?value=${encodeURIComponent(val)}`, { method: 'POST' }); } catch (err) {}
    };

    const resolveInjection = async (decision: 'accept' | 'reject' | 'quit') => {
        try { await fetch(`${API_BASE_HOLDER.current}/transcribe/resolve_injection?decision=${decision}`, { method: 'POST' }); } catch (err) {}
    };

    const toggleEnhancement = (id: string) => {
        setActiveEnhancements(prev => {
            const next = prev.includes(id) ? prev.filter(e => e !== id) : [...prev, id];
            set('tome_master_active_enhancements', next);
            return next;
        });
    };

    const hydrate = useCallback(async () => {
        const folder = await get<string>('tome_master_active_folder');
        if (folder) setActiveFolderPath(folder);

        const filePath = await get<string>('tome_master_active_file');
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

        const enhancements = await get<string[]>('tome_master_active_enhancements');
        if (enhancements) setActiveEnhancements(enhancements);

        try {
            const res = await fetch(`${API_BASE_HOLDER.current}/license/status`);
            const data = await res.json();
            if (data.is_activated) setIsActivated(true);
        } catch (e) {}
    }, []);

    useEffect(() => { hydrate(); }, [hydrate]);

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
        bookTitle, authorName, coverImage, activeFolderPath,
        isTranscribing, transcriptionStatus, processedPageCount, transcriptionMode,
        isActivated, language, isSettingsOpen, isHelpOpen, isEnhancementHubOpen,
        isAuditOpen, isLedgerOpen, isReportOpen, isStructuralModalOpen, isFocusMode,
        activeEnhancements
    };

    const workstationActions: WorkstationActions = {
        setBookTitle, setAuthorName, setCoverImage, setActiveFolderPath,
        setIsTranscribing, setTranscriptionStatus, setProcessedPageCount, setTranscriptionMode,
        setIsActivated, setLanguage, setIsSettingsOpen, setIsHelpOpen, setIsEnhancementHubOpen,
        setIsAuditOpen, setIsLedgerOpen, setIsReportOpen, setIsStructuralModalOpen, setIsFocusMode,
        loadManuscript, loadSealedManuscript, establishProject, invokeTranscription, confirmInjection, cancelInjection, abortTranscription,
        resolveAuditInput, resolveInjection, notify, hydrate,
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
