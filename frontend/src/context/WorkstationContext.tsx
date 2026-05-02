"use client";

import React, { createContext, useContext, useState, useEffect, useCallback, useRef } from "react";
import { get, set } from "idb-keyval";
import { 
    checkTranscriptionStatus, startTranscription, anchorFolder, 
    clearTranscription, checkLicenseStatus, API_BASE_HOLDER,
    resortTranscription
} from "@/lib/apiClient";
import { loadCompressed, saveCompressed } from "@/lib/storage_utils";

// --- Types ---
interface WorkstationState {
    // Project Metadata
    bookTitle: string;
    authorName: string;
    coverImage: string | null;
    
    // Editor State
    content: string;
    htmlContent: string;
    chapters: any[];
    aiChapters: any[];
    agentReports: Record<string, any>;
    arcData: any[];
    wordCount: number;
    misspelledCount: number;
    activePage: number;
    selectedText: string;
    currentChapterId: string | null;
    currentParagraphText: string;
    
    // Engine State
    activeFolderPath: string | null;
    isTranscribing: boolean;
    transcriptionStatus: any;
    processedPageCount: number;
    transcriptionMode: 'batch' | 'live';
    transcriptionReset: boolean;
    
    // [SOVEREIGN TASK ANCHORS]
    providerTranscribe: string;
    modelTranscribe: string;
    providerBoardroom: string;
    modelBoardroom: string;
    providerFallback: string;
    modelFallback: string;

    // System State
    isOfflineMode: boolean;
    activeProvider: string;
    activeModel: string;
    isActivated: boolean;
    language: 'en-US' | 'en-GB' | 'en-CA';
    isFocusMode: boolean;
    
    // UI Visibility
    isSettingsOpen: boolean;
    isHelpOpen: boolean;
    isEnhancementHubOpen: boolean;
    activeEnhancements: string[];
    analysisTrigger: number;
    isAuditOpen: boolean;
    isLedgerOpen: boolean;
    isReportOpen: boolean;
    isDemoMode: boolean;
    isInvokeLoading: boolean;
    isStructuralModalOpen: boolean;
}

interface WorkstationActions {
    setBookTitle: (val: string) => void;
    setAuthorName: (val: string) => void;
    setCoverImage: (val: string | null) => void;
    setContent: React.Dispatch<React.SetStateAction<string>>;
    setHtmlContent: React.Dispatch<React.SetStateAction<string>>;
    setChapters: (val: any[]) => void;
    setAiChapters: (val: any[]) => void;
    setAgentReports: (val: Record<string, any>) => void;
    setArcData: (val: any[]) => void;
    setActivePage: (val: number) => void;
    setSelectedText: (val: string) => void;
    setCurrentChapterId: (val: string | null) => void;
    setCurrentParagraphText: (val: string) => void;
    setWordCount: (val: number) => void;
    setMisspelledCount: (val: number) => void;
    setIsTranscribing: (val: boolean) => void;
    setTranscriptionStatus: (val: any) => void;
    setProcessedPageCount: React.Dispatch<React.SetStateAction<number>>;
    setActiveFolderPath: (val: string | null) => void;
    setTranscriptionMode: (val: 'batch' | 'live') => void;
    setTranscriptionReset: (val: boolean) => void;
    setProviderFallback: (val: string) => void;
    setModelFallback: (val: string) => void;
    setIsOfflineMode: (val: boolean) => void;
    setActiveProvider: (val: string) => void;
    setActiveModel: (val: string) => void;
    setIsFocusMode: (val: boolean) => void;
    setIsSettingsOpen: (open: boolean) => void;
    setIsHelpOpen: (open: boolean) => void;
    setIsEnhancementHubOpen: (open: boolean) => void;
    toggleEnhancement: (id: string) => void;
    setAnalysisTrigger: (fn: (prev: number) => number) => void;
    setIsAuditOpen: (val: boolean) => void;
    setIsLedgerOpen: (val: boolean) => void;
    setIsReportOpen: (val: boolean) => void;
    setIsDemoMode: (val: boolean) => void;
    setIsStructuralModalOpen: (val: boolean) => void;
    
    // Operational Handshaking
    anchorProject: () => Promise<void>;
    invokeTranscription: () => Promise<void>;
    syncTableOfContents: (editorRef: any) => void;
    hydrate: () => Promise<void>;
    loadManuscript: () => Promise<void>;
    notify: (text: string) => void;
    setIsActivated: (val: boolean) => void;
    setLanguage: (lang: 'en-US' | 'en-GB' | 'en-CA') => void;
}

const StateContext = createContext<WorkstationState | undefined>(undefined);
const ActionsContext = createContext<WorkstationActions | undefined>(undefined);

// --- Provider ---
export const WorkstationProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
    // Project Metadata
    const [bookTitle, setBookTitleState] = useState("Manuscript");
    const [authorName, setAuthorNameState] = useState("Author");
    const [coverImage, setCoverImageState] = useState<string | null>(null);

    // Editor State
    const [content, setContent] = useState("");
    const [htmlContent, setHtmlContent] = useState("");
    const [chapters, setChapters] = useState<any[]>([]);
    const [aiChapters, setAiChapters] = useState<any[]>([]);
    const [agentReports, setAgentReports] = useState<Record<string, any>>({});
    const [arcData, setArcData] = useState<any[]>([]);
    const [wordCount, setWordCount] = useState(0);
    const [misspelledCount, setMisspelledCount] = useState(0);
    const [activePage, setActivePage] = useState(1);
    const [selectedText, setSelectedText] = useState("");
    const [currentChapterId, setCurrentChapterId] = useState<string | null>(null);
    const [currentParagraphText, setCurrentParagraphText] = useState("");

    // Engine State
    const [activeFolderPath, setActiveFolderPath] = useState<string | null>(null);
    const [isTranscribing, setIsTranscribing] = useState(false);
    const [transcriptionStatus, setTranscriptionStatus] = useState<any>(null);
    const [processedPageCount, setProcessedPageCount] = useState(0);
    const [transcriptionMode, setTranscriptionMode] = useState<'batch' | 'live'>('batch');
    const [transcriptionReset, setTranscriptionReset] = useState(false);
    
    // [SOVEREIGN TASK ANCHORS]
    const [providerTranscribe, setProviderTranscribe] = useState('gemini');
    const [modelTranscribe, setModelTranscribe] = useState('auto');
    const [providerBoardroom, setProviderBoardroom] = useState('gemini');
    const [modelBoardroom, setModelBoardroom] = useState('auto');
    const [providerFallback, setProviderFallback] = useState('openai');
    const [modelFallback, setModelFallback] = useState('gpt-4o-mini');

    // System State
    // [FIX #1]: Renamed internal setter to avoid infinite recursion
    const [isOfflineMode, setIsOfflineModeState] = useState(false);
    const [activeProvider, setActiveProviderState] = useState('gemini');
    const [activeModel, setActiveModelState] = useState('auto');
    const [isActivated, setIsActivated] = useState(false);
    const [language, setLanguage] = useState<'en-US' | 'en-GB' | 'en-CA'>('en-US');
    const [isFocusMode, setIsFocusMode] = useState(false);

    // UI Visibility
    const [isSettingsOpen, setIsSettingsOpen] = useState(false);
    const [isHelpOpen, setIsHelpOpen] = useState(false);
    const [isEnhancementHubOpen, setIsEnhancementHubOpen] = useState(false);
    const [activeEnhancements, setActiveEnhancements] = useState<string[]>([]);
    const [analysisTrigger, setAnalysisTrigger] = useState(0);
    const [isAuditOpen, setIsAuditOpen] = useState(false);
    const [isLedgerOpen, setIsLedgerOpen] = useState(false);
    const [isReportOpen, setIsReportOpen] = useState(false);
    const [isDemoMode, setIsDemoMode] = useState(false);
    const [isInvokeLoading, setIsInvokeLoading] = useState(false);
    const [isStructuralModalOpen, setIsStructuralModalOpen] = useState(false);

    const toggleEnhancement = (id: string) => {
        setActiveEnhancements(prev => 
            prev.includes(id) ? prev.filter(e => e !== id) : [...prev, id]
        );
    };

    const notify = useCallback((text: string) => {
        window.dispatchEvent(new CustomEvent('tome-master-guide-speak', { detail: { text } }));
    }, []);

    // --- Persisted Metadata Setters ---
    const setBookTitle = (val: string) => {
        setBookTitleState(val);
        set('tome_master_draft_title', val);
    };
    const setAuthorName = (val: string) => {
        setAuthorNameState(val);
        set('tome_master_draft_author', val);
    };
    const setCoverImage = (val: string | null) => {
        setCoverImageState(val);
        set('tome_master_draft_cover', val);
    };

    // [FIX #1]: Wrapper calls the RENAMED state setter, not itself
    const setIsOfflineMode = (val: boolean) => {
        setIsOfflineModeState(val);
        localStorage.setItem('tome_master_offline_mode', String(val));
    };
    const setActiveProvider = (val: string) => {
        setActiveProviderState(val);
        localStorage.setItem('tome_master_provider', val);
        window.dispatchEvent(new CustomEvent('tome-master-settings-changed'));
    };
    const setActiveModel = (val: string) => {
        setActiveModelState(val);
        localStorage.setItem('tome_master_model', val);
    };

    // --- Operations ---
    const anchorProject = async () => {
        try {
            const result = await anchorFolder();
            if ((result.status === 'success' || result.status === 'anchored') && result.folder_path) {
                setActiveFolderPath(result.folder_path);
                if (typeof window !== 'undefined') (window as any)._tome_active_path = result.folder_path;
                await set('tome_master_active_folder', result.folder_path);
                notify(`Project Anchored: ${result.folder_path}`);
                
                // [AUTO-LOAD]: After anchoring, immediately attempt to load the manuscript
                await loadManuscript();
            }
        } catch (err) {
            console.error("Anchoring Failure:", err);
            notify("Handshake Failed: Engine is unreachable.");
        }
    };

    const loadManuscript = async () => {
        const folder = activeFolderPath || await get<string>('tome_master_active_folder');
        if (!folder) {
            notify("No project anchored. Please anchor a project first.");
            return;
        }
        try {
            notify("Resurrecting manuscript from vault...");
            // [INDUSTRIAL PULSE]: Force an ingestion check to ensure the backend is in sync
            await fetch(`${API_BASE_HOLDER.current}/transcribe/ingest?folder_path=${encodeURIComponent(folder)}`);
            
            const state = await checkTranscriptionStatus(false);
            setTranscriptionStatus({...state});
            
            if (state.status === 'sewing') {
                notify("Voice of TomeMaster: Assembly is in progress. Hydrating the editor shortly...");
                // Poll every 2 seconds until complete
                const poll = setInterval(async () => {
                    const nextState = await checkTranscriptionStatus(false);
                    setTranscriptionStatus({...nextState});
                    if (nextState.status === 'complete' && nextState.text) {
                        clearInterval(poll);
                        setContent(nextState.text);
                        setHtmlContent(nextState.text.split('\n\n').map(p => `<p>${p.replace(/\n/g, '<br/>')}</p>`).join(''));
                        notify(nextState.error_message || "Manuscript restored to editor.");
                    }
                }, 2000);
                return;
            }

            if (state.text) {
                // [SHADOW-SAVE]: Redundant storage of the active path for session recovery
                localStorage.setItem('tome_master_shadow_path', folder);
                
                setContent(state.text);
                const paragraphs = state.text.split('\n\n');
                let html = "";
                for (let i = 0; i < paragraphs.length; i++) {
                    const p = paragraphs[i].trim();
                    if (p) html += `<p>${p.replace(/\n/g, '<br/>')}</p>`;
                }
                setHtmlContent(html);
                notify(state.error_message || "Manuscript restored to editor.");
            } else {
                notify("No unified manuscript found. Transcribe the project first.");
            }
        } catch (e) {
            console.error("Load Failure:", e);
            notify("Handshake Failed: Engine could not load manuscript.");
        }
    };

    const invokeTranscription = async () => {
        if (isInvokeLoading) return;
        setIsInvokeLoading(true);
        try {
            notify("Ingesting manuscript assets...");
            // [RESET]: If we are stuck in an error or already transcribing, 
            // Clearing deck...
            if (transcriptionStatus?.status === 'error') {
                await clearTranscription();
            }

            // [STEALTH STITCH]: If we are 100% digitized but need a manuscript re-assembly, skip the modal.
            const isFullyDigitized = (transcriptionStatus?.total_images || 0) > 0 && 
                                   (transcriptionStatus?.total_images === transcriptionStatus?.processed_images);
            const hasRootWork = transcriptionStatus?.status === 'sewing'; // 'sewing' means ingest found RTFs in root

            if (isFullyDigitized || hasRootWork) {
                const stitchMsg = hasRootWork 
                    ? "Voice of TomeMaster: New prose artifacts detected in the root. Executing industrial assembly to unify your work."
                    : "Voice of TomeMaster: I have identified existing artifacts. Assembling your manuscript foundations now. Please stand by for hydration.";
                
                notify(stitchMsg);
                
                // We DON'T set setIsTranscribing(true) here to keep the modal hidden
                const success = await resortTranscription(activeFolderPath || '');
                setIsInvokeLoading(false);
                
                if (success) {
                    // Force a quick manual load since we aren't polling
                    setTimeout(() => loadManuscript(), 1000);
                } else {
                    notify("Stitching Failure. Verify the project folder is still anchored.");
                }
                return;
            }

            notify(`Invoking Engine (${transcriptionMode.toUpperCase()} MODE)...`);
            
            // [NEURAL PULSE]: Refresh vault data immediately to ensure we aren't using stale state
            const freshVaultStr = localStorage.getItem('tome_master_vault') || '{}';
            const vault = JSON.parse(freshVaultStr);
            
            const provider = vault.provider_transcribe || localStorage.getItem('tome_master_provider') || 'gemini';
            const apiKey = vault[provider] || '';
            const selectedModel = vault.model_transcribe || vault[`model_${provider}`] || null;
            
            const fallbackProvider = vault.provider_fallback || null;
            const fallbackModel = vault.model_fallback || null;
            
            console.log(`[INGESTION INITIATED]: Provider: ${provider}, Model: ${selectedModel}`);

            const started = await startTranscription(
                apiKey, provider, isDemoMode, activeFolderPath || '', transcriptionReset, transcriptionMode, selectedModel,
                fallbackProvider, fallbackModel
            );
            
            if (started && started.status === 'started') {
                const path = started.folder_path;
                setActiveFolderPath(path || null);
                if (path) set('tome_master_active_folder', path);
                
                setContent("");
                setHtmlContent("");
                setChapters([]);
                setAiChapters([]);
                setAgentReports({});
                setProcessedPageCount(0);
                setIsTranscribing(true);
                setTranscriptionStatus(prev => ({
                    ...prev,
                    status: 'indexing',
                    processed_images: prev?.processed_images || 0,
                    total_images: prev?.total_images || 0,
                    current_batch: 0
                }));
                
                notify(transcriptionReset ? "Progress wiped. Starting fresh from Page 1." : "Scanning for new pages.");
            } else {
                notify("Ingestion Cancelled. Standby for new operational directive.");
                setIsTranscribing(false);
            }
        } catch (e: any) {
            setIsTranscribing(true); // Keep UI in error state
            setTranscriptionStatus({ 
                status: 'error', 
                error_message: e.message || "Engine Connection Interrupted" 
            });
            notify(`CRITICAL ENGINE FAILURE: ${e.message || "Unknown error"}`);
            setIsTranscribing(false);
        } finally {
            setIsInvokeLoading(false);
        }
    };

    const syncTableOfContents = (editorRef: any) => {
        if (!editorRef?.current) return;
        editorRef.current.purgePdfMarkers();
        const freshTOC = editorRef.current.generateTOC();
        if (freshTOC && Array.isArray(freshTOC)) {
            setChapters(freshTOC);
            set('tome_master_draft_toc', freshTOC);
        }
    };

    const hydrate = useCallback(async () => {
        try {
            const savedHtml = await loadCompressed<string>('tome_master_draft_html');
            const savedText = await loadCompressed<string>('tome_master_draft_text');
            if (savedHtml) {
                setHtmlContent(savedHtml);
                setContent(savedText || "");
            }
            const savedTOC = await get<any[]>('tome_master_draft_toc');
            if (savedTOC && Array.isArray(savedTOC)) setChapters(savedTOC);
            const savedAI = await get<any[]>('tome_master_draft_ai');
            if (savedAI && Array.isArray(savedAI)) setAiChapters(savedAI);
            const savedReports = await get<Record<string, any>>('tome_master_draft_reports');
            if (savedReports) setAgentReports(savedReports);
            const savedArc = await get<any[]>('tome_master_draft_arc');
            if (savedArc && Array.isArray(savedArc)) setArcData(savedArc);
            const savedApplied = await get<string[]>('tome_master_draft_applied_warnings');
            const savedFolder = await get<string>('tome_master_active_folder') || localStorage.getItem('tome_master_shadow_path');
            if (savedFolder) {
                setActiveFolderPath(savedFolder);
                console.log(`HYDRATION: Project Anchor restored from Vault: ${savedFolder}`);
                // [AUTO-PULSE]: Re-ingest the project baseline to update counters without user intervention
                try {
                    await fetch(`${API_BASE_HOLDER.current}/transcribe/ingest?folder_path=${encodeURIComponent(savedFolder)}`);
                    // [HYDRATION SYNC]: Immediately pull the results of the scan into the UI
                    const state = await checkTranscriptionStatus(false); // [FULL]: We want the text if it exists
                    setTranscriptionStatus({...state});
                    
                    // [SOVEREIGN SYNC]: If the engine has a sealed manuscript, end the amnesia
                    if (state.text && !content) {
                        console.log("HYDRATION: Injecting sealed manuscript into editor.");
                        setContent(state.text);
                        setHtmlContent(state.text.split('\n\n').map(p => `<p>${p.replace(/\n/g, '<br/>')}</p>`).join(''));
                    }

                    // [STATE SYNC]: Ensure the 'Active' badge reflects the real backend mode
                    if (state.status === 'running' || state.status === 'indexing' || state.status === 'sewing') {
                        setIsTranscribing(true);
                    } else {
                        setIsTranscribing(false);
                    }
                } catch (e) {
                    console.warn("HYDRATION: Auto-Pulse failed.");
                }
            }
            
            const savedTitle = await get<string>('tome_master_draft_title');
            if (savedTitle) setBookTitleState(savedTitle);
            const savedAuthor = await get<string>('tome_master_draft_author');
            if (savedAuthor) setAuthorNameState(savedAuthor);
            const savedCover = await get<string>('tome_master_draft_cover');
            if (savedCover) setCoverImageState(savedCover);

            // [FIX #2]: Use the renamed state setters, not the wrapper functions
            try {
                const status = await checkLicenseStatus();
                setIsActivated(status.is_activated);
            } catch (e) {
                console.error("License check failed:", e);
            }
            
            const vaultStr = localStorage.getItem('tome_master_vault') || '{}';
            const vault = JSON.parse(vaultStr);
            setProviderTranscribe(vault.provider_transcribe || 'gemini');
            setModelTranscribe(vault.model_transcribe || 'auto');
            setProviderBoardroom(vault.provider_boardroom || 'gemini');
            setModelBoardroom(vault.model_boardroom || 'auto');
            setProviderFallback(vault.provider_fallback || 'openai');
            setModelFallback(vault.model_fallback || 'gpt-4o-mini');

            setIsOfflineModeState(localStorage.getItem('tome_master_offline_mode') === 'true');
            setActiveProviderState(localStorage.getItem('tome_master_provider') || 'gemini');
            setActiveModelState(localStorage.getItem('tome_master_model') || 'auto');
        } catch (err) {
            console.error("Hydration Failure:", err);
        }
    }, []);

    useEffect(() => {
        hydrate();
    }, [hydrate]);

    // Listen for settings changes from other windows/components
    useEffect(() => {
        if (typeof window === 'undefined') return;
        const handleSettingsChange = () => {
            const vaultStr = localStorage.getItem('tome_master_vault') || '{}';
            const vault = JSON.parse(vaultStr);
            setProviderTranscribe(vault.provider_transcribe || 'gemini');
            setModelTranscribe(vault.model_transcribe || 'auto');
            setProviderBoardroom(vault.provider_boardroom || 'gemini');
            setModelBoardroom(vault.model_boardroom || 'auto');
            
            setActiveProviderState(localStorage.getItem('tome_master_provider') || 'gemini');
            setActiveModelState(localStorage.getItem('tome_master_model') || 'auto');
        };
        window.addEventListener('storage', handleSettingsChange);
        window.addEventListener('tome-master-settings-changed', handleSettingsChange);
        return () => {
            window.removeEventListener('storage', handleSettingsChange);
            window.removeEventListener('tome-master-settings-changed', handleSettingsChange);
        };
    }, []);

    // Auto-save logic
    useEffect(() => {
        if (!htmlContent) return;
        const timeout = setTimeout(async () => {
            try {
                await saveCompressed('tome_master_draft_html', htmlContent);
                await saveCompressed('tome_master_draft_text', content);
                const wc = content.trim().split(/\s+/).filter(w => w.length > 0).length;
                setWordCount(wc);
                const mc = document.querySelectorAll('.misspelled-word').length;
                setMisspelledCount(mc);
            } catch (err: any) {
                console.warn("Storage pressure detected. Auto-save failed.");
            }
        }, 2500);
        return () => clearTimeout(timeout);
    }, [htmlContent, content]);

    // Persist chapters, reports, arc data
    useEffect(() => {
        if (chapters && chapters.length > 0) set('tome_master_draft_toc', chapters);
    }, [chapters]);
    useEffect(() => {
        if (aiChapters && aiChapters.length > 0) set('tome_master_draft_ai', aiChapters);
    }, [aiChapters]);
    useEffect(() => {
        if (agentReports && Object.keys(agentReports).length > 0) set('tome_master_draft_reports', agentReports);
    }, [agentReports]);
    useEffect(() => {
        if (arcData && arcData.length > 0) set('tome_master_draft_arc', arcData);
    }, [arcData]);

    // [INDUSTRIAL SCOUT]: Background polling to detect new physical files in the root
    useEffect(() => {
        // [SOVEREIGN HOLIDAY]: The Scout only runs if there are identified gaps in the manuscript sequence.
        const missingCount = transcriptionStatus?.missing_pages_count || 0;
        if (!activeFolderPath || isTranscribing || missingCount === 0) return;
        
        const scout = setInterval(async () => {
            try {
                // Perform a quick ingestion pulse
                const res = await fetch(`${API_BASE_HOLDER.current}/transcribe/ingest?folder_path=${encodeURIComponent(activeFolderPath)}`);
                if (res.ok) {
                    const state = await checkTranscriptionStatus(true);
                    if (state.status === 'sewing') {
                        // Backend started a stitch! Update UI to reflect 'Ingestion Protocol Active'
                        setIsTranscribing(true);
                        setTranscriptionStatus(state);
                        notify("Voice of TomeMaster: New manuscript assets identified in the root. I am assembling your foundations automatically.");
                    }
                }
            } catch (e) {
                console.warn("SCOUT ERROR: Ingestion pulse interrupted.");
            }
        }, 60000); // Pulse every 60 seconds

        return () => clearInterval(scout);
    }, [activeFolderPath, isTranscribing, notify]);

    const state: WorkstationState = {
        bookTitle, authorName, coverImage, content, htmlContent, chapters, aiChapters, 
        agentReports, arcData, wordCount, misspelledCount, activePage, selectedText,
        currentChapterId, currentParagraphText, activeFolderPath, isTranscribing, 
        transcriptionStatus, processedPageCount, transcriptionMode, transcriptionReset,
        providerTranscribe, modelTranscribe, providerBoardroom, modelBoardroom,
        providerFallback, modelFallback,
        isOfflineMode, activeProvider, activeModel, isActivated, language, isFocusMode,
        isSettingsOpen, isHelpOpen, isEnhancementHubOpen, activeEnhancements, analysisTrigger,
        isAuditOpen,
        isLedgerOpen,
        isReportOpen,
        isDemoMode,
        isInvokeLoading,
        isStructuralModalOpen
    };

    const actions: WorkstationActions = {
        setBookTitle, setAuthorName, setCoverImage, setContent, setHtmlContent,
        setChapters, setAiChapters, setAgentReports, setArcData, setActivePage,
        setSelectedText, setCurrentChapterId, setCurrentParagraphText,
        setWordCount, setMisspelledCount,
        setIsTranscribing, setTranscriptionStatus, setProcessedPageCount,
        setActiveFolderPath, setTranscriptionMode, setTranscriptionReset, 
        setProviderFallback, setModelFallback,
        setIsOfflineMode, setActiveProvider, setActiveModel,
        setIsFocusMode, setIsAuditOpen, setIsLedgerOpen, setIsReportOpen, setIsDemoMode,
        setIsStructuralModalOpen, setIsHelpOpen, setIsEnhancementHubOpen, toggleEnhancement, setAnalysisTrigger,
        setIsSettingsOpen,
        anchorProject, loadManuscript, invokeTranscription, syncTableOfContents, hydrate, notify,
        setIsActivated, setLanguage
    };

    return (
        <StateContext.Provider value={state}>
            <ActionsContext.Provider value={actions}>
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
