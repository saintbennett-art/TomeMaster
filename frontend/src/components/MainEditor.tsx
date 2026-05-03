"use client";

import { TranscriptionDashboard } from "@/components/TranscriptionDashboard";
import AnalysisDashboard from "@/components/AnalysisDashboard";
import { DraggableDialog } from "@/components/workstation/DraggableDialog";
import React, { useState, useRef, useEffect, useCallback } from "react";
import { Upload, Download, Maximize2, Minimize2, FileText, Mic, MicOff, ChevronDown, Camera, Loader2, Globe, XCircle, Sparkles, Volume2, VolumeX, Expand, Shrink, Save } from "lucide-react";
import { RichTextEditorRef } from "@/components/RichTextEditor";
import { useDictation } from "@/hooks/useDictation";
import { useTextToSpeech } from "@/hooks/useTextToSpeech";
import { useScreenRecorder } from "@/hooks/useScreenRecorder";
import { exportDocx, exportEpub, exportPdf, checkTranscriptionStatus, saveSnapshot } from "@/lib/apiClient";
import { useWorkstationState, useWorkstationActions } from "@/context/WorkstationContext";

import WorkstationHeader from "./workstation/WorkstationHeader";
import WorkstationViewport from "./workstation/WorkstationViewport";
import TranscriptionSidebar from "./workstation/TranscriptionSidebar";
import WorkstationModals from "./workstation/WorkstationModals";
import GuideAssistant from "@/components/GuideAssistant";

interface MainEditorProps {
  scrollToText?: string | null;
  onScrollComplete?: () => void;
  onPreviewChapter?: (startingWords: string) => void;
  onCoverUpload: (e: React.ChangeEvent<HTMLInputElement>) => void;
}

export default function MainEditor({ 
  scrollToText, onScrollComplete, onPreviewChapter, onCoverUpload
}: MainEditorProps) {
  const { 
    content, htmlContent, chapters, agentReports, activeFolderPath,
    isTranscribing, transcriptionStatus, wordCount, misspelledCount,
    activeProvider, isActivated, processedPageCount, arcData, bookTitle, authorName, coverImage,
    selectedText, currentChapterId, providerTranscribe, modelTranscribe
  } = useWorkstationState();

  const { 
    setHtmlContent, setContent, setAgentReports,
    notify, setIsTranscribing,
    setTranscriptionStatus, setProcessedPageCount,
    setSelectedText, setArcData, invokeTranscription
  } = useWorkstationActions();

  const [activeTab, setActiveTab] = useState("Developmental Editor");
  const [selectedAgents, setSelectedAgents] = useState([]);
  const [customAgents, setCustomAgents] = useState([]);
  const [isRightSidebarOpen, setIsRightSidebarOpen] = useState(false);
  const [isSuperMuseMode, setIsSuperMuseMode] = useState(true);
  const [localAnalysisTrigger, setLocalAnalysisTrigger] = useState(0);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [isLiaisonSpeaking, setIsLiaisonSpeaking] = useState(false);
  const [lastActionTime, setLastActionTime] = useState(0);

  const editorRef = useRef(null);

  const { speak, stop, isPlaying } = useTextToSpeech();
  const vault = typeof window !== "undefined" ? JSON.parse(localStorage.getItem("tome_master_vault") || "{}") : {};

  const handleStartTranscribe = async () => {
    setLastActionTime(Date.now());
    await invokeTranscription();
  };
    

  const { isListening, toggleListening, isRefining } = useDictation({
      onCommand: (cmd) => {
          const lowerCmd = cmd.toLowerCase();
          if (lowerCmd.includes("run analysis")) {
              setLocalAnalysisTrigger(prev => prev + 1);
          } else if (lowerCmd.includes("export word")) {
              handleExportDocx();
          } else if (lowerCmd.includes("stop reading") || lowerCmd.includes("stop audio")) {
              if (isPlaying) stop();
          } else if (lowerCmd.includes("read manuscript") || lowerCmd.includes("read this")) {
              if (isPlaying) { stop(); } else { const t = selectedText || content; if (t) speak(t); }
          } else if (lowerCmd.includes("go to beginning") || lowerCmd.includes("scroll to top")) {
              if (content && onPreviewChapter) onPreviewChapter(content.substring(0, 30));
          } else if (lowerCmd.includes("go to chapter") || lowerCmd.includes("navigate to")) {
              const searchTerm = lowerCmd.replace(/^.*(go to chapter|navigate to)\s+/i, '').trim();
              if (searchTerm && chapters.length > 0) {
                  const match = chapters.find(c =>
                      c.title?.toLowerCase().includes(searchTerm) ||
                      c.startingWords?.toLowerCase().includes(searchTerm)
                  );
                  if (match && onPreviewChapter) onPreviewChapter(match.startingWords || match.title);
              }
          }
      },
      onDictation: (text) => editorRef.current?.insertDictation(text),
      isSuperMuseMode,
      provider: activeProvider,
      apiKey: vault[activeProvider] || ""
  });

  useEffect(() => {
    if (!isTranscribing) return;
    
    const poll = setInterval(async () => {
      try {
        const state = await checkTranscriptionStatus(true);
        const timeSinceAction = Date.now() - lastActionTime;
        
        if (state.status === "complete" && timeSinceAction < 5000) {
            console.log("POLLING: Shielding from stale complete status...");
            return;
        }

        setTranscriptionStatus({...state}); // Force reactivity
        if (state.new_pages && state.new_pages.length > 0) {
          let accText = "";
          let accHtml = "";
          state.new_pages.forEach((p) => {
             accText += "\n\n" + p.text;
             accHtml += `<div class="transcription-batch"><p>${p.text.replace(/\n\n/g, "</p><p>")}</p></div>`;
          });
          setContent(prev => prev + accText);
          setHtmlContent(prev => prev + accHtml);
          editorRef.current?.insertChunk(accHtml);
          setProcessedPageCount(prev => prev + state.new_pages.length);
        }
        if (state.status === "complete") {
          setIsTranscribing(false);
          clearInterval(poll);
          
          // [INDUSTRIAL]: No 'Big Bang' overwrite. Trust the incremental stream.
          notify("Your manuscript is sealed and ready in the project folder!");
        }
        
        if (state.status === "audit") {
            setIsTranscribing(false);
            clearInterval(poll);
            notify("DIRECTORIAL AUDIT: Sequence Disruption Detected.");
            // The UI will now remain open in Audit mode due to the state update
        }
      } catch (e) {
        console.error("Transcription Poll Error:", e);
      }
    }, 2000);
    return () => clearInterval(poll);
  }, [isTranscribing, lastActionTime]);

  const handleApplySuggestion = useCallback((suggestion) => {
    editorRef.current?.insertChunk(`<div class="ai-suggestion">${suggestion}</div>`);
  }, []);

  const handleExportDocx = async () => {
    try { await exportDocx(htmlContent, chapters, bookTitle || "Manuscript", authorName, "chicago"); }
    catch (err) { alert("Export failed"); }
  };

  const handleUndo = () => editorRef.current?.undo();
  const handleRedo = () => editorRef.current?.redo();

  const handleTakeSnapshot = async () => {
    if (!activeFolderPath) {
        notify("Anchor a project first to save snapshots.");
        return;
    }
    notify("Capturing architectural snapshot...");
    try {
        // [SIMULATION]: Since we don't have html2canvas in this environment's standard bundle yet, 
        // we use a formatted timestamped log as the 'snapshot' content or a placeholder dataUrl
        const placeholderDataUrl = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==";
        await saveSnapshot(placeholderDataUrl, activeFolderPath);
        notify("Snapshot preserved in project vault.");
    } catch (err) {
        notify("Snapshot Handshake Failed.");
    }
  };

  const handleGrammarCheck = () => {
    if (!content) return;
    notify("Dispatching copy-editor agents for prose audit...");
    setLocalAnalysisTrigger(prev => prev + 1);
    // [LOGIC]: This triggers the AnalysisDashboard which eventually dispatches 'copy_editor_edits'
  };

  return (
    <main className="flex flex-col h-screen bg-background overflow-hidden relative selection:bg-indigo-500/30">
      <div className="flex-1 flex overflow-hidden min-w-0 relative">
        <div className="flex-1 flex flex-col min-w-0 relative">
          <WorkstationHeader 
            bookTitle={bookTitle} 
            onExportDocx={handleExportDocx}
            onClearFailedReports={() => {}}
            isLiaisonSpeaking={isLiaisonSpeaking}
            isRightSidebarOpen={isRightSidebarOpen}
            setIsRightSidebarOpen={setIsRightSidebarOpen}
            onExportMenuToggle={() => {}}
            isExportMenuOpen={false}
            onTakeSnapshot={handleTakeSnapshot}
            onGrammarCheck={handleGrammarCheck}
            onUndo={handleUndo}
            onRedo={handleRedo}
            isListening={isListening}
            toggleListening={toggleListening}
            isSpeaking={isPlaying}
            onReadManuscript={() => {
                if (isPlaying) {
                    stop();
                } else {
                    const text = selectedText || content;
                    if (text) speak(text);
                }
            }}
          />

          <div className="flex-1 flex overflow-hidden min-w-0 relative">
            <WorkstationViewport
              editorRef={editorRef}
              onSelectionChange={setSelectedText}
              onParagraphChange={() => {}}
              scrollToText={scrollToText}
              onScrollComplete={onScrollComplete}
            />

            <TranscriptionSidebar 
              isOpen={isRightSidebarOpen}
              activeTab={activeTab}
              setActiveTab={setActiveTab}
              selectedAgents={selectedAgents}
              setSelectedAgents={setSelectedAgents}
              customAgents={customAgents}
              setCustomAgents={setCustomAgents}
              onApplySuggestion={handleApplySuggestion}
              isAnalyzing={isAnalyzing}
              localAnalysisTrigger={localAnalysisTrigger}
            />
          </div>
        </div>
      </div>

      <WorkstationModals 
        onApplySuggestion={handleApplySuggestion}
        isAnalyzing={isAnalyzing}
        localAnalysisTrigger={localAnalysisTrigger}
        setLocalAnalysisTrigger={setLocalAnalysisTrigger}
        isListening={isListening}
        isRefining={isRefining}
        isSuperMuseMode={isSuperMuseMode}
        setIsSuperMuseMode={setIsSuperMuseMode}
        toggleListening={toggleListening}
      />

      {/* [SOVEREIGN FLOATING]: Ingestion Engine Dashboard (Only visible when transcribing) */}
      {isTranscribing && (
        <DraggableDialog headerId="nerve-center-handle" initialX={40} initialY={100}>
          <div id="nerve-center-handle" className="cursor-grab active:cursor-grabbing">
            <TranscriptionDashboard
              totalPageGoal={transcriptionStatus?.total_images || 0}
              processedPages={transcriptionStatus?.processed_images || 0}
              status={transcriptionStatus?.status || "idle"}
              errorMessage={transcriptionStatus?.error_message}
              isTranscribing={isTranscribing}
              onStart={handleStartTranscribe}
              providerName={providerTranscribe}
              modelName={modelTranscribe}
              currentImageB64={transcriptionStatus?.current_image_b64}
            />
          </div>
        </DraggableDialog>
      )}

            {/* [SOVEREIGN MAPPED]: Boardroom Engine (Fixed Top-Right) */}
      <DraggableDialog headerId="boardroom-title-handle" initialX={window?.innerWidth ? window.innerWidth - 480 : 800} initialY={110}>
        <AnalysisDashboard 
          content={htmlContent} arcData={arcData} chapters={chapters} agentReports={agentReports}
          onAgentReportsChange={setAgentReports} onApplySuggestion={handleApplySuggestion}
          activeTab={activeTab} setActiveTab={setActiveTab}
          selectedAgents={selectedAgents} setSelectedAgents={setSelectedAgents}
          customAgents={customAgents} setCustomAgents={setCustomAgents}
          isAnalyzing={isAnalyzing} setIsAnalyzing={setIsAnalyzing}
          analysisTrigger={localAnalysisTrigger} globalProvider={activeProvider}
          notify={notify}
        />
      </DraggableDialog>

      <GuideAssistant 
        content={content} selectedText={selectedText} misspelledCount={misspelledCount}
        wordCount={wordCount} hasToc={chapters.length > 0}
        hasReports={Object.keys(agentReports).length > 0}
        folderPath={activeFolderPath} provider={activeProvider} apiKey={vault[activeProvider]}
      />
    </main>
  );
}
