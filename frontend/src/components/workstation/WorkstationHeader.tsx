"use client";

import React, { useState, useRef, useEffect } from "react";
import {
    Download, ShieldCheck, Globe, GlobeLock, RefreshCw,
    PanelRightClose, PanelRightOpen, Layers, ListOrdered, Camera, Mic, Volume2,
    Layout, Sparkles, FileText, Check, Loader2
} from "lucide-react";
import { useWorkstationState, useWorkstationActions } from "@/context/WorkstationContext";
import { useEditorState } from "@/context/EditorContext";
import { EXPORT_FORMATS } from "@/lib/apiClient";
import CreativeMuse from "@/components/CreativeMuse";
import ThemeToggle from "@/components/ThemeToggle";
import MenuBar from "./MenuBar";

/**
 * MULTI-SELECT BATCH EXPORT
 * Popover with a checkbox per format (data-driven from EXPORT_FORMATS). "Export
 * selected" spins off every checked format at once — each triggers its own save.
 */
const BatchExportControl: React.FC<{
    htmlContent: string;
    chapters: ReturnType<typeof useEditorState>["chapters"];
    bookTitle: string;
    authorName: string;
    coverImage: string | null;
    notify: (msg: string) => void;
}> = ({ htmlContent, chapters, bookTitle, authorName, coverImage, notify }) => {
    const [open, setOpen] = useState(false);
    // Default selection: Word, PDF, EPUB checked (the canonical book formats).
    const [selected, setSelected] = useState<Record<string, boolean>>({
        docx: true, pdf: true, epub: true,
    });
    const [progress, setProgress] = useState<{ done: number; total: number } | null>(null);
    const ref = useRef<HTMLDivElement>(null);

    useEffect(() => {
        const onClickOutside = (e: MouseEvent) => {
            if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
        };
        document.addEventListener("mousedown", onClickOutside);
        return () => document.removeEventListener("mousedown", onClickOutside);
    }, []);

    const toggle = (id: string) =>
        setSelected(prev => ({ ...prev, [id]: !prev[id] }));

    const chosen = EXPORT_FORMATS.filter(f => selected[f.id]);

    const runBatch = async () => {
        if (!htmlContent || htmlContent.trim().length === 0) {
            notify("Nothing to export — the manuscript is empty.");
            return;
        }
        if (chosen.length === 0) {
            notify("Select at least one format to export.");
            return;
        }
        setOpen(false);
        setProgress({ done: 0, total: chosen.length });
        notify(`Exporting ${chosen.length} format${chosen.length === 1 ? "" : "s"}…`);

        let ok = 0;
        const failed: string[] = [];
        // Sequential so each format's native Save dialog (saveBlobWithSovereignty)
        // doesn't collide with the next — parallel pickers can't all open at once.
        for (const fmt of chosen) {
            try {
                await fmt.run(htmlContent, chapters, bookTitle || "Manuscript", authorName, "chicago", coverImage || undefined);
                ok += 1;
            } catch (e) {
                failed.push(fmt.label);
            }
            setProgress(prev => prev ? { ...prev, done: prev.done + 1 } : prev);
        }
        setProgress(null);
        if (failed.length === 0) {
            notify(`Exported ${ok} format${ok === 1 ? "" : "s"}.`);
        } else {
            notify(`Exported ${ok}; failed: ${failed.join(", ")}.`);
        }
    };

    return (
        <div className="relative" ref={ref}>
            <button
                onClick={() => setOpen(o => !o)}
                title="Export manuscript (choose one or more formats)"
                disabled={!!progress}
                className="flex items-center gap-2 p-2 rounded-lg border transition-all bg-surface border-border text-muted-foreground hover:text-indigo-400 disabled:opacity-60"
            >
                {progress
                    ? <Loader2 className="w-4 h-4 animate-spin" />
                    : <Download className="w-4 h-4" />}
                <span className="hidden sm:inline text-xs font-bold">
                    {progress ? `Exporting ${progress.done}/${progress.total}…` : "Export"}
                </span>
            </button>

            {open && (
                <div className="absolute top-full right-0 mt-2 w-60 bg-[#0a0a0a] border-2 border-blue-500/50 rounded-xl shadow-[0_0_50px_rgba(37,99,235,0.2)] py-3 z-[9999] animate-in fade-in zoom-in-95 duration-150">
                    <div className="px-4 pb-2 text-[10px] font-black uppercase tracking-widest text-zinc-500">
                        Export formats
                    </div>
                    {EXPORT_FORMATS.map(fmt => (
                        <button
                            key={fmt.id}
                            onClick={() => toggle(fmt.id)}
                            className="w-full flex items-center gap-3 px-4 py-2 hover:bg-indigo-500/10 text-zinc-300 hover:text-indigo-300 transition-all text-xs font-medium"
                        >
                            <span className={`w-4 h-4 rounded border flex items-center justify-center shrink-0 ${selected[fmt.id] ? "bg-indigo-500 border-indigo-400" : "border-zinc-600"}`}>
                                {selected[fmt.id] && <Check className="w-3 h-3 text-white" />}
                            </span>
                            <span>{fmt.label}</span>
                        </button>
                    ))}
                    <div className="h-[1px] bg-white/10 my-2 mx-2" />
                    <div className="px-3">
                        <button
                            onClick={runBatch}
                            disabled={chosen.length === 0}
                            className="w-full px-3 py-2 rounded-md bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 disabled:hover:bg-indigo-600 text-white text-xs font-bold transition-all"
                        >
                            Export selected ({chosen.length})
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
};

interface WorkstationHeaderProps {
    isRightSidebarOpen: boolean;
    setIsRightSidebarOpen: (val: boolean) => void;
    onExportMenuToggle: () => void;
    isExportMenuOpen: boolean;
    onTakeSnapshot: () => void;
    onGrammarCheck: () => void;
    onClearFailedReports: () => void;
    isLiaisonSpeaking: boolean;
    isListening?: boolean;
    toggleListening?: () => void;
    onReadManuscript?: () => void;
    isSpeaking?: boolean;
    onExportDocx?: () => void;
    onExportPdf?: () => void;
    onExportEpub?: () => void;
    onUndo?: () => void;
    onRedo?: () => void;
}

const WorkstationHeader: React.FC<WorkstationHeaderProps> = ({
    isRightSidebarOpen,
    setIsRightSidebarOpen,
    onExportMenuToggle,
    isExportMenuOpen,
    onTakeSnapshot,
    onGrammarCheck,
    onClearFailedReports,
    isLiaisonSpeaking,
    isListening = false,
    toggleListening = () => {},
    onReadManuscript = () => {},
    isSpeaking = false,
    onExportDocx,
    onExportPdf,
    onExportEpub,
    onUndo,
    onRedo
}) => {
    const {
        activeFolderPath,
        isActivated, bookTitle, authorName, coverImage
    } = useWorkstationState();

    const {
        content, htmlContent, currentChapterId, currentParagraphText, agentReports, chapters, selectedText
    } = useEditorState();

    const {
        setIsOfflineMode, establishProject, loadManuscript, invokeTranscription,
        setIsLedgerOpen, setIsAuditOpen, notify,
        setIsStructuralModalOpen, setIsEnhancementHubOpen
    } = useWorkstationActions();

    return (
        <header className={`min-h-[3.5rem] py-1 border-b border-border flex items-center px-6 shrink-0 bg-surface transition-all duration-300 ${isLiaisonSpeaking ? 'ring-2 ring-indigo-500/20' : ''}`}>
          <div className="flex items-center gap-4 w-full">
            <MenuBar
                onExport={onExportDocx}
                onExportPdf={onExportPdf}
                onExportEpub={onExportEpub}
                onGrammarCheck={onGrammarCheck}
                onUndo={onUndo}
                onRedo={onRedo}
                onTakeSnapshot={onTakeSnapshot}
            />
            
            <div className="flex-1" />

            {/* [SOVEREIGN]: Transcribe only appears when the workstation is empty. */}
            {(!content || content.trim().length === 0) && (
              <button 
                onClick={invokeTranscription}
                title="Invoke Transcription Engine"
                className="flex items-center gap-2 text-sm font-bold transition-all px-4 py-1.5 rounded-md border shadow-lg bg-indigo-600 hover:bg-indigo-500 text-white border-indigo-400 shadow-indigo-500/20 mr-4 animate-in fade-in zoom-in duration-300"
              >
                <RefreshCw className="w-4 h-4" /> 
                <span className="hidden sm:inline">Transcribe</span>
              </button>
            )}

            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2">
                <button 
                  onClick={toggleListening}
                  title="Toggle Voice Activation / Dictation"
                  className={`p-2 rounded-lg border transition-all ${isListening ? 'bg-red-500/20 border-red-500/40 text-red-400 animate-pulse' : 'bg-surface border-border text-muted-foreground hover:text-indigo-400'}`}
                >
                  <Mic className="w-4 h-4" />
                </button>

                <button 
                  onClick={onReadManuscript}
                  title="Read Manuscript (Selection or Cursor)"
                  className={`p-2 rounded-lg border transition-all ${isSpeaking ? 'bg-amber-500/20 border-amber-500/40 text-amber-400' : 'bg-surface border-border text-muted-foreground hover:text-amber-400'}`}
                >
                  <Volume2 className="w-4 h-4" />
                </button>
              </div>

              <div className="h-6 w-[1px] bg-border" />

              <div className="flex items-center gap-2">
                <BatchExportControl
                  htmlContent={htmlContent}
                  chapters={chapters}
                  bookTitle={bookTitle}
                  authorName={authorName}
                  coverImage={coverImage}
                  notify={notify}
                />
                <ThemeToggle />
                <button
                  onClick={() => setIsRightSidebarOpen(!isRightSidebarOpen)}
                  className={`p-2 rounded-lg border transition-all ${isRightSidebarOpen ? 'bg-indigo-500/20 border-indigo-500/40 text-indigo-400' : 'bg-surface border-border text-muted-foreground hover:text-indigo-400'}`}
                >
                  {isRightSidebarOpen ? <PanelRightClose className="w-4 h-4" /> : <PanelRightOpen className="w-4 h-4" />}
                </button>
              </div>
            </div>
          </div>
        </header>
    );
};

export default WorkstationHeader;
