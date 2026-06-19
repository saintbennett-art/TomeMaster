"use client";

import React, { createContext, useContext, useState, useEffect, useRef, useCallback } from "react";
import { Chapter, AgentReport, ArcPoint } from "@/types/industrial";
import { useWorkstationState } from "./WorkstationContext";
import { saveProjectState, loadProjectState } from "@/lib/apiClient";
// [LEGACY RECOVERY]: read-only access to the old IndexedDB draft store so an
// existing user's manuscript is migrated into the project file, never lost.
import { get as idbGet } from "idb-keyval";
import { loadCompressed } from "@/lib/storage_utils";

// --- [STRICT DOMAIN INTERFACES] ---
export interface EditorState {
    content: string;
    htmlContent: string;
    wordCount: number;
    chapters: Chapter[];
    agentReports: Record<string, AgentReport>;
    arcData: ArcPoint[];
    activePage: number;
    currentChapterId: string | null;
    currentParagraphText: string;
    misspelledCount: number;
    selectedText: string;
}

export interface EditorActions {
    setContent: React.Dispatch<React.SetStateAction<string>>;
    setHtmlContent: React.Dispatch<React.SetStateAction<string>>;
    setChapters: React.Dispatch<React.SetStateAction<Chapter[]>>;
    setAgentReports: React.Dispatch<React.SetStateAction<Record<string, AgentReport>>>;
    setArcData: React.Dispatch<React.SetStateAction<ArcPoint[]>>;
    setActivePage: React.Dispatch<React.SetStateAction<number>>;
    setCurrentChapterId: React.Dispatch<React.SetStateAction<string | null>>;
    setCurrentParagraphText: React.Dispatch<React.SetStateAction<string>>;
    setMisspelledCount: React.Dispatch<React.SetStateAction<number>>;
    setWordCount: React.Dispatch<React.SetStateAction<number>>;
    setSelectedText: React.Dispatch<React.SetStateAction<string>>;
    processTextParallel: (rawText: string) => void;
}

const EditorStateContext = createContext<EditorState | undefined>(undefined);
const EditorActionsContext = createContext<EditorActions | undefined>(undefined);

export const EditorProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
    const [content, setContent] = useState("");
    const [htmlContent, setHtmlContent] = useState("");
    const [wordCount, setWordCount] = useState(0);
    const [chapters, setChapters] = useState<Chapter[]>([]);
    const [agentReports, setAgentReports] = useState<Record<string, AgentReport>>({});
    const [arcData, setArcData] = useState<ArcPoint[]>([]);
    const [activePage, setActivePage] = useState(0);
    const [currentChapterId, setCurrentChapterId] = useState<string | null>(null);
    const [currentParagraphText, setCurrentParagraphText] = useState("");
    const [misspelledCount, setMisspelledCount] = useState(0);
    const [selectedText, setSelectedText] = useState("");

    // [FILES-ONLY]: the draft persists to tome_master_project.json in the active
    // project folder (or the backend default workspace when none is open).
    const { activeFolderPath, activeFilePath } = useWorkstationState();
    // Gate autosave until the first restore completes, so empty initial state can't
    // overwrite a saved draft before it's loaded.
    const draftHydratedRef = useRef(false);

    const workerRef = useRef<Worker | null>(null);

    useEffect(() => {
        if (typeof window !== 'undefined') {
            workerRef.current = new Worker(new URL('../lib/workstation.worker.ts', import.meta.url));
            workerRef.current.onmessage = (e) => {
                const { type, htmlContent: processedHtml, wordCount: processedWordCount } = e.data;
                if (type === 'TEXT_PROCESSED') {
                    setHtmlContent(processedHtml);
                    setWordCount(processedWordCount);
                }
            };
        }
        return () => { workerRef.current?.terminate(); };
    }, []);

    const processTextParallel = useCallback((rawText: string) => {
        if (workerRef.current) {
            workerRef.current.postMessage({ type: 'PROCESS_TEXT', content: rawText });
        }
    }, []);

    // [AUTOSAVE]: Silent, debounced persistence of the live draft to the project
    // file (tome_master_project.json). Merged server-side with the metadata slice.
    useEffect(() => {
        if (!draftHydratedRef.current) return;
        if (!htmlContent && !content) return;
        const timeout = setTimeout(() => {
            saveProjectState(activeFolderPath, {
                draft_html: htmlContent,
                draft_text: content,
                draft_toc: chapters,
                draft_reports: agentReports,
                draft_arc: arcData,
                draft_ts: Date.now(),
            });
        }, 2500);
        return () => clearTimeout(timeout);
    }, [htmlContent, content, chapters, agentReports, arcData, activeFolderPath]);

    // [RESTORE]: Rehydrate the draft from the project file whenever the active
    // folder resolves/changes. An opened active TEXT file wins (its content is
    // hydrated by WorkstationContext), so skip the draft restore then.
    useEffect(() => {
        let cancelled = false;
        (async () => {
            try {
                const ext = activeFilePath?.split('.').pop()?.toLowerCase();
                if (activeFilePath && ['md', 'markdown', 'txt'].includes(ext || '')) {
                    draftHydratedRef.current = true;
                    return;
                }
                const state = await loadProjectState(activeFolderPath);
                if (cancelled) return;
                let html = (state.draft_html as string) || "";
                let text = (state.draft_text as string) || "";
                let toc = (Array.isArray(state.draft_toc) ? state.draft_toc : null) as Chapter[] | null;
                let reports = (state.draft_reports as Record<string, AgentReport>) || null;
                let arc = (Array.isArray(state.draft_arc) ? state.draft_arc : null) as ArcPoint[] | null;
                let migratedFromLegacy = false;

                // [LEGACY RECOVERY]: project file empty → fall back to the old
                // IndexedDB draft so a pre-migration manuscript is never lost.
                if (!html && !text) {
                    try {
                        const lh = await loadCompressed<string>('tome_master_draft_html');
                        const lt = await loadCompressed<string>('tome_master_draft_text');
                        if (cancelled) return;
                        if (lh || lt) {
                            html = lh || "";
                            text = lt || "";
                            const ltoc = await idbGet('tome_master_draft_toc');
                            if (Array.isArray(ltoc) && ltoc.length) toc = ltoc as Chapter[];
                            const lrep = await idbGet('tome_master_draft_reports');
                            if (lrep) reports = lrep as Record<string, AgentReport>;
                            const larc = await idbGet('tome_master_draft_arc');
                            if (Array.isArray(larc) && larc.length) arc = larc as ArcPoint[];
                            migratedFromLegacy = true;
                        }
                    } catch { /* old store unreadable — nothing to recover */ }
                }

                if (cancelled) return;
                if (html || text) {
                    setHtmlContent(html);
                    setContent(text);
                    window.dispatchEvent(new CustomEvent('tome-master-editor-hydrate', {
                        detail: { content: text, html }
                    }));
                    if (toc && toc.length) setChapters(toc);
                    if (reports) setAgentReports(reports);
                    if (arc && arc.length) setArcData(arc);

                    // Persist the recovered draft into the project file so the
                    // migration is permanent and the legacy store can be retired.
                    if (migratedFromLegacy) {
                        saveProjectState(activeFolderPath, {
                            draft_html: html, draft_text: text,
                            draft_toc: toc || [], draft_reports: reports || {},
                            draft_arc: arc || [], draft_ts: Date.now(),
                        });
                    }
                }
            } catch (err) {
                console.error("Draft hydration failed:", err);
            } finally {
                if (!cancelled) draftHydratedRef.current = true;
            }
        })();
        return () => { cancelled = true; };
    }, [activeFolderPath, activeFilePath]);

    const editorState: EditorState = {
        content, htmlContent, wordCount, chapters, agentReports, arcData, activePage, currentChapterId,
        currentParagraphText, misspelledCount, selectedText
    };

    const editorActions: EditorActions = {
        setContent, setHtmlContent, setChapters, setAgentReports, setArcData,
        setActivePage, setCurrentChapterId, setCurrentParagraphText, setMisspelledCount, setWordCount,
        setSelectedText, processTextParallel
    };

    return (
        <EditorStateContext.Provider value={editorState}>
            <EditorActionsContext.Provider value={editorActions}>
                {children}
            </EditorActionsContext.Provider>
        </EditorStateContext.Provider>
    );
};

export const useEditorState = () => {
    const context = useContext(EditorStateContext);
    if (!context) throw new Error("useEditorState must be used within EditorProvider");
    return context;
};

export const useEditorActions = () => {
    const context = useContext(EditorActionsContext);
    if (!context) throw new Error("useEditorActions must be used within EditorProvider");
    return context;
};
