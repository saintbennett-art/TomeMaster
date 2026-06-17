"use client";

import React, { createContext, useContext, useState, useEffect, useRef, useCallback } from "react";
import { Chapter, AgentReport, ArcPoint } from "@/types/industrial";
import { get, set } from "idb-keyval";
import { saveCompressed, loadCompressed } from "@/lib/storage_utils";

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

    // [AUTOSAVE]: Silent, debounced persistence of the live draft to IndexedDB.
    useEffect(() => {
        if (!htmlContent && !content) return;
        const timeout = setTimeout(async () => {
            try {
                await saveCompressed('tome_master_draft_html', htmlContent);
                await saveCompressed('tome_master_draft_text', content);
                await set('tome_master_draft_toc', chapters);
                await set('tome_master_draft_reports', agentReports);
                await set('tome_master_draft_arc', arcData);
                await set('tome_master_draft_ts', Date.now());
            } catch (err) {
                console.warn("Storage pressure detected. Auto-save failed.", err);
            }
        }, 2500);
        return () => clearTimeout(timeout);
    }, [htmlContent, content, chapters, agentReports, arcData]);

    // [RESTORE]: On mount, rehydrate the draft. An opened active file wins
    // (that path is owned by WorkstationContext.hydrate), so skip then.
    useEffect(() => {
        (async () => {
            try {
                const activeFile = await get<string>('tome_master_active_file');
                const ext = activeFile?.split('.').pop()?.toLowerCase();
                if (activeFile && ['md', 'markdown', 'txt'].includes(ext || '')) return;

                const html = await loadCompressed<string>('tome_master_draft_html');
                const text = await loadCompressed<string>('tome_master_draft_text');
                if (html || text) {
                    setHtmlContent(html || "");
                    setContent(text || "");
                    window.dispatchEvent(new CustomEvent('tome-master-editor-hydrate', {
                        detail: { content: text || "", html: html || "" }
                    }));
                    const toc = await get('tome_master_draft_toc');
                    if (Array.isArray(toc) && toc.length) setChapters(toc as Chapter[]);
                    const reports = await get('tome_master_draft_reports');
                    if (reports) setAgentReports(reports as Record<string, AgentReport>);
                    const arc = await get('tome_master_draft_arc');
                    if (Array.isArray(arc) && arc.length) setArcData(arc as ArcPoint[]);
                }
            } catch (err) {
                console.error("Draft hydration failed:", err);
            }
        })();
    }, []);

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
