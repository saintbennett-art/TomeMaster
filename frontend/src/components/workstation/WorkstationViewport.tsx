"use client";

import React from "react";
import { Loader2 } from "lucide-react";
import { useWorkstationState, useWorkstationActions } from "@/context/WorkstationContext";
import RichTextEditor, { RichTextEditorRef } from "@/components/RichTextEditor";

interface WorkstationViewportProps {
    editorRef: React.RefObject<RichTextEditorRef | null>;
    onSelectionChange: (text: string) => void;
    onParagraphChange: (text: string) => void;
    scrollToText?: string | null;
    onScrollComplete?: () => void;
}

const WorkstationViewport: React.FC<WorkstationViewportProps> = ({
    editorRef,
    onSelectionChange,
    onParagraphChange,
    scrollToText,
    onScrollComplete
}) => {
    const { 
        htmlContent, isTranscribing, transcriptionStatus, isActivated, 
        activePage, wordCount, misspelledCount 
    } = useWorkstationState();
    
    const { setHtmlContent, setContent } = useWorkstationActions();

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
                            {transcriptionStatus.missing_pages_count > 0 && (
                                <div className="flex flex-col items-end px-3 border-r border-zinc-800">
                                    <span className="text-[10px] font-black text-amber-500 leading-none">{transcriptionStatus.missing_pages_count}</span>
                                    <span className="text-[7px] text-zinc-500 uppercase font-bold tracking-tighter mt-1 italic">Sequence Gaps</span>
                                </div>
                            )}
                            <div className="flex flex-col items-end">
                                <span className="text-[10px] font-black text-white leading-none">{transcriptionStatus.processed_images} / {transcriptionStatus.total_images || '?'}</span>
                                <span className="text-[7px] text-zinc-500 uppercase font-bold tracking-tighter mt-1">Transcribed Pages</span>
                            </div>
                            <div className="w-24 h-1 bg-zinc-800 rounded-full overflow-hidden">
                                <div 
                                    className="h-full bg-indigo-500 transition-all duration-500" 
                                    style={{ width: `${(transcriptionStatus.processed_images / Math.max(1, transcriptionStatus.total_images)) * 100}%` }}
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
                    }}
                    onSelectionChange={onSelectionChange}
                    onParagraphChange={onParagraphChange}
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
