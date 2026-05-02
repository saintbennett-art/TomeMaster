"use client";

import React from "react";
import { 
    Download, ShieldCheck, Globe, GlobeLock, RefreshCw, 
    PanelRightClose, PanelRightOpen, Layers, ListOrdered, Camera, Mic, Volume2,
    Layout, Sparkles
} from "lucide-react";
import { useWorkstationState, useWorkstationActions } from "@/context/WorkstationContext";
import CreativeMuse from "@/components/CreativeMuse";
import ThemeToggle from "@/components/ThemeToggle";
import MenuBar from "./MenuBar";

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
    onUndo,
    onRedo
}) => {
    const { 
        activeFolderPath, isOfflineMode, activeProvider, activeModel, 
        isActivated, bookTitle, authorName, content, currentChapterId,
        currentParagraphText, agentReports, chapters, selectedText
    } = useWorkstationState();
    
    const { 
        setIsOfflineMode, anchorProject, invokeTranscription, 
        setIsLedgerOpen, setIsAuditOpen, notify,
        setIsStructuralModalOpen, setIsEnhancementHubOpen
    } = useWorkstationActions();

    return (
        <header className={`min-h-[3.5rem] py-1 border-b border-border flex items-center px-6 shrink-0 bg-surface transition-all duration-300 ${isLiaisonSpeaking ? 'ring-2 ring-indigo-500/20' : ''}`}>
          <div className="flex items-center gap-4 flex-wrap w-full">
            <div className="flex items-center gap-2 mr-4">
              <div className="p-2 bg-accent/10 rounded-lg">
                <Globe className="w-5 h-5 text-accent" />
              </div>
              <div className="flex flex-col">
                <span className="text-xs font-black text-foreground tracking-tighter uppercase leading-none">Sovereign Workstation</span>
                <span className="text-[9px] text-muted-foreground font-bold uppercase tracking-widest mt-1 leading-none">
                    {isOfflineMode ? "Isolated Logic" : "Cloud Augmented"}
                </span>
              </div>

            <MenuBar 
                onExport={onExportDocx} 
                onGrammarCheck={onGrammarCheck} 
                onUndo={onUndo}
                onRedo={onRedo}
                onTakeSnapshot={onTakeSnapshot}
            />
            </div>

            <div className="flex items-center gap-1 bg-background/50 p-1 rounded-lg border border-border/50">
              <button 
                onClick={() => setIsOfflineMode(true)}
                className={`px-3 py-1.5 rounded-md text-[10px] font-black uppercase tracking-widest transition-all ${isOfflineMode ? 'bg-accent text-accent-foreground shadow-lg' : 'text-muted-foreground hover:text-foreground'}`}
              >
                Local
              </button>
              <button 
                onClick={() => setIsOfflineMode(false)}
                className={`px-3 py-1.5 rounded-md text-[10px] font-black uppercase tracking-widest transition-all ${!isOfflineMode ? 'bg-indigo-600 text-white shadow-lg' : 'text-muted-foreground hover:text-foreground'}`}
              >
                Global
              </button>
            </div>

            <div className="h-6 w-[1px] bg-border mx-2"></div>

            <div className="flex items-center gap-2">
              <button 
                onClick={anchorProject}
                title="Anchor Project to Local Filesystem"
                className={`flex items-center gap-2 text-sm font-bold transition-all px-3 py-1.5 rounded-md border ${activeFolderPath ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' : 'bg-zinc-900 text-zinc-400 border-zinc-800 hover:text-white hover:border-zinc-700'}`}
              >
                <ShieldCheck className="w-4 h-4" /> 
                <span className="hidden sm:inline">{activeFolderPath ? "Anchored" : "Anchor Project"}</span>
              </button>

              <button 
                onClick={invokeTranscription}
                title="Invoke Transcription Engine"
                className={`flex items-center gap-2 text-sm font-bold transition-all px-4 py-1.5 rounded-md border shadow-lg bg-indigo-600 hover:bg-indigo-500 text-white border-indigo-400 shadow-indigo-500/20`}
              >
                <RefreshCw className="w-4 h-4" /> 
                <span className="hidden sm:inline">Transcribe</span>
              </button>

              <button 
                onClick={() => setIsStructuralModalOpen(true)}
                title="Delineate Chapters and Analyze Narrative Arc"
                className={`flex items-center gap-2 text-sm font-bold transition-all px-4 py-1.5 rounded-md border shadow-lg bg-emerald-600 hover:bg-emerald-500 text-white border-emerald-400 shadow-emerald-500/20`}
              >
                <Layers className="w-4 h-4" /> 
                <span className="hidden sm:inline">Structure</span>
              </button>

              <div className="h-6 w-[1px] bg-border mx-2"></div>

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

            <div className="flex items-center gap-2">
              <button 
                onClick={onGrammarCheck}
                className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-all px-3 py-1.5 rounded-md border border-border bg-surface"
                title="Perform Copy Editor Audit"
              >
                <ShieldCheck className="w-4 h-4" /> <span className="hidden lg:inline">Sanitize</span>
              </button>
              
              <button 
                onClick={() => setIsAuditOpen(true)} 
                disabled={!activeFolderPath}
                title="Verify Pagination Audit Trail"
                className={`flex items-center gap-2 text-sm transition-all px-3 py-1.5 rounded-md border ${activeFolderPath ? 'text-muted-foreground hover:text-indigo-400 bg-surface border-border' : 'text-muted border-border/50 opacity-50 cursor-not-allowed'}`}
              >
                <ListOrdered className="w-4 h-4" /> <span className="hidden lg:inline">Audit</span>
              </button>

              <div className="h-6 w-[1px] bg-border mx-2"></div>

              {activeFolderPath && (
                <>
                    <button 
                        onClick={() => setIsEnhancementHubOpen(true)}
                        className="flex items-center gap-2 px-4 py-2 bg-amber-600 hover:bg-amber-500 text-white rounded-xl text-[10px] font-black uppercase transition-all shadow-lg shadow-amber-600/20"
                    >
                        <Sparkles className="w-3.5 h-3.5" />
                        Enhancements
                    </button>
                </>
              )}

              {activeFolderPath && (
                <button 
                  onClick={() => setIsLedgerOpen(true)} 
                  className={`flex items-center gap-2 text-sm transition-all px-3 py-1.5 rounded-md border text-muted-foreground hover:text-accent bg-surface border-border`}
                  title="View AI Usage Ledger"
                >
                  <Layers className="w-4 h-4" /> <span className="hidden lg:inline">Ledger</span>
                </button>
              )}

              <CreativeMuse 
                content={content} 
                selectedText={selectedText} 
                currentChapterId={currentChapterId} 
                currentParagraphText={currentParagraphText}
                agentReports={agentReports} 
                onAmbientNotify={notify}
              />
              
              <ThemeToggle />
            </div>
          </div>
        </header>
    );
};

export default WorkstationHeader;
