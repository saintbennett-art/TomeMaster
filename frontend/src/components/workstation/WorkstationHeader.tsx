"use client";

import React from "react";
import { 
    Download, ShieldCheck, Globe, GlobeLock, RefreshCw, 
    PanelRightClose, PanelRightOpen, Layers, ListOrdered, Camera, Mic, Volume2,
    Layout, Sparkles, FileText
} from "lucide-react";
import { useWorkstationState, useWorkstationActions } from "@/context/WorkstationContext";
import { useEditorState } from "@/context/EditorContext";
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
        activeFolderPath,
        isActivated, bookTitle, authorName
    } = useWorkstationState();

    const {
        content, currentChapterId, currentParagraphText, agentReports, chapters, selectedText
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
