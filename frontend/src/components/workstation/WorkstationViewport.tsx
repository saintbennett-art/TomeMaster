"use client";

import React from "react";
import { Loader2 } from "lucide-react";
import { useWorkstationState, useWorkstationActions } from "@/context/WorkstationContext";
import { useEditorState, useEditorActions } from "@/context/EditorContext";
import RichTextEditor, { RichTextEditorRef } from "@/components/RichTextEditor";

interface WorkstationViewportProps {
    editorRef: React.RefObject<RichTextEditorRef | null>;
    onSelectionChange: (text: string) => void;
    onParagraphChange: (text: string) => void;
    scrollToText?: string | null;
    onScrollComplete?: () => void;
    onMisspelledCountChange?: (count: number) => void;
}

const WorkstationViewport: React.FC<WorkstationViewportProps> = ({
    editorRef,
    onSelectionChange,
    onParagraphChange,
    scrollToText,
    onScrollComplete,
    onMisspelledCountChange
}) => {
    const { 
        isTranscribing, transcriptionStatus, isActivated
    } = useWorkstationState();
    
    // Pull domain data from the Editor silo
    const { 
        htmlContent = "", activePage = 1, wordCount = 0, misspelledCount = 0 
    } = useEditorState();
    
    const { setHtmlContent, setContent, setWordCount } = useEditorActions();
    
    // [HYDRATION BRIDGE]: Listen for manual restoration events (e.g. Loading a Sealed Manuscript)
    React.useEffect(() => {
        const handleHydrate = (e: any) => {
            if (e.detail?.html && editorRef.current) {
                editorRef.current.setContent(e.detail.html);
                setHtmlContent(e.detail.html);
            }
            if (e.detail?.content) {
                setContent(e.detail.content);
            }
        };
        window.addEventListener('tome-master-editor-hydrate', handleHydrate);
        return () => window.removeEventListener('tome-master-editor-hydrate', handleHydrate);
    }, [setContent, setHtmlContent, editorRef]);

    return (
        <div className="flex-1 flex flex-col min-w-0 relative h-full" id="main-workstation-viewport">
            {isTranscribing && (
                <div className="bg-indigo-600/10 border-b border-indigo-500/20 px-6 py-2 flex items-center justify-between shrink-0 animate-in fade-in slide-in-from-top-4 z-30">
                    <div className="flex items-center gap-3">
                        <div className="p-1.5 bg-indigo-500/10 rounded-lg border border-indigo-500/20">
                            <Loader2 className="w-3 h-3 text-indigo-400 animate-spin" />
                        </div>
                        <div>
                            <span className="text-[9px] font-black text-indigo-400 uppercase tracking-widest block leading-none">Ingestion Protocol Active</span>
                            <span className="text-[8px] text-zinc-500 font-bold uppercase tracking-tight mt-1 block leading-none">{transcriptionStatus?.error_message || 'Initializing high-fidelity scanner...'}</span>
                        </div>
                    </div>
                            {transcriptionStatus?.missing_pages_count != null && transcriptionStatus.missing_pages_count > 0 && (
                                <div className="flex flex-col items-end px-3 border-r border-zinc-800">
                                    <span className="text-[10px] font-black text-amber-500 leading-none">{transcriptionStatus.missing_pages_count}</span>
                                    <span className="text-[7px] text-zinc-500 uppercase font-bold tracking-tighter mt-1 italic">Sequence Gaps</span>
                                </div>
                            )}
                            <div className="flex flex-col items-end">
                                <span className="text-[10px] font-black text-white leading-none">{transcriptionStatus?.processed_images ?? 0} / {transcriptionStatus?.total_images || '?'}</span>
                                <span className="text-[7px] text-zinc-500 uppercase font-bold tracking-tighter mt-1">Transcribed Pages</span>
                            </div>
                            <div className="w-24 h-1 bg-zinc-800 rounded-full overflow-hidden">
                                <div 
                                    className="h-full bg-indigo-500 transition-all duration-500" 
                                    style={{ width: `${((transcriptionStatus?.processed_images ?? 0) / Math.max(1, transcriptionStatus?.total_images ?? 1)) * 100}%` }}
                                />
                            </div>

                </div>
            )}

            <div className="flex-1 flex flex-col overflow-hidden relative bg-background min-h-0">
                <RichTextEditor
                    ref={editorRef}
                    content={htmlContent}
                    isActivated={isActivated}
                    onChange={(text, html, isEmpty) => {
                        setHtmlContent(html);
                        setContent(text);
                        // [LEXICAL MASS]: Calculate word count locally to avoid ghosting
                        const count = text.trim() ? text.trim().split(/\s+/).length : 0;
                        setWordCount(count);
                    }}
                    onSelectionChange={onSelectionChange}
                    onCurrentParagraphChange={onParagraphChange}
                    onMisspelledCountChange={onMisspelledCountChange}
                    scrollToText={scrollToText}
                    onScrollComplete={onScrollComplete}
                />
            </div>

            <footer className="h-10 border-t border-border bg-surface flex items-center justify-between px-6 shrink-0 z-20">
                <div className="flex items-center gap-6">
                    <div className="flex items-center gap-2">
                        <span className="text-[10px] font-black text-muted-foreground uppercase tracking-widest">Transcription Status:</span>
                        <span className="text-[10px] font-mono text-foreground font-bold">Page {activePage}</span>
                    </div>
                    <div className="h-3 w-[1px] bg-border" />
                    <div className="flex items-center gap-2">
                        <span className="text-[10px] font-black text-muted-foreground uppercase tracking-widest">Lexical Mass:</span>
                        <span className="text-[10px] font-mono text-foreground font-bold">{wordCount.toLocaleString()} Words</span>
                    </div>
                </div>

                <div className="flex items-center gap-4">
                    {misspelledCount > 0 && (
                        <div className="flex items-center gap-2 px-2 py-0.5 bg-rose-500/10 border border-rose-500/20 rounded text-rose-400 animate-pulse">
                            <span className="text-[9px] font-black uppercase tracking-tighter italic">{misspelledCount} Lexical Anomalies (Spelling)</span>
                        </div>
                    )}
                    <span className="text-[10px] text-muted-foreground font-medium uppercase tracking-[0.2em] opacity-50">Sovereign Encryption Active</span>
                </div>
            </footer>
        </div>
    );
};

export default WorkstationViewport;
