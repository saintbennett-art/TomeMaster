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
import { exportDocx, exportEpub, exportPdf, checkTranscriptionStatus, saveProjectState } from "@/lib/apiClient";
import { useWorkstationState, useWorkstationActions } from "@/context/WorkstationContext";
import { useEditorState, useEditorActions } from "@/context/EditorContext";

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
  onMisspelledCountChange?: (count: number) => void;
  syncTrigger?: number;
}

export default function MainEditor({
  scrollToText, onScrollComplete, onPreviewChapter, onCoverUpload, onMisspelledCountChange, syncTrigger
}: MainEditorProps) {
  const { 
    activeFolderPath, isTranscribing, transcriptionStatus,
    isActivated, processedPageCount, bookTitle, authorName, coverImage
  } = useWorkstationState();

  const {
    notify, setIsTranscribing, setTranscriptionStatus, setProcessedPageCount, invokeTranscription, abortTranscription, setIsReportOpen
  } = useWorkstationActions();

  const {
    content, htmlContent, chapters, agentReports, wordCount, misspelledCount,
    arcData, selectedText, currentChapterId, currentParagraphText
  } = useEditorState();

  const {
    setHtmlContent, setContent, setAgentReports, setSelectedText, setArcData,
    setChapters, setCurrentParagraphText, setMisspelledCount
  } = useEditorActions();

  const [activeTab, setActiveTab] = useState("Developmental Editor");
  const [selectedAgents, setSelectedAgents] = useState<string[]>([]);
  const [customAgents, setCustomAgents] = useState<string[]>([]);
  const [isRightSidebarOpen, setIsRightSidebarOpen] = useState(false);
  const [isSuperMuseMode, setIsSuperMuseMode] = useState(true);
  const [localAnalysisTrigger, setLocalAnalysisTrigger] = useState(0);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [isLiaisonSpeaking, setIsLiaisonSpeaking] = useState(false);
  const [lastActionTime, setLastActionTime] = useState(0);

  const editorRef = useRef<RichTextEditorRef | null>(null);

  const { speak, stop, isPlaying } = useTextToSpeech();

  // [SYNC HEADINGS]: the sidebar "Sync" button bumps syncTrigger. Build the
  // chapter list / TOC from the document's headings (client-side, no AI).
  useEffect(() => {
    if (!syncTrigger) return;
    const toc = editorRef.current?.generateTOC?.();
    if (toc && toc.length > 0) {
      setChapters(toc);
      notify(`Synced ${toc.length} chapter${toc.length === 1 ? '' : 's'} from headings.`);
    } else {
      notify("No chapter headings found to sync. Load a document with headings, or run Delineate Structure.");
    }
  }, [syncTrigger]); // eslint-disable-line react-hooks/exhaustive-deps

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
                  const target = match && (match.startingWords || match.title);
                  if (target && onPreviewChapter) onPreviewChapter(target);
              }
          }
      },
      onDictation: (text) => editorRef.current?.insertDictation(text),
      isSuperMuseMode
  });

  useEffect(() => {
    if (!isTranscribing) return;
    
    const poll = setInterval(async () => {
      try {
        const state = await checkTranscriptionStatus(true);
        const timeSinceAction = Date.now() - lastActionTime;
        
        if (state.status === "complete" && timeSinceAction < 5000) {
            return;
        }

        setTranscriptionStatus({...state}); // Force reactivity
        const newPages = state.new_pages;
        if (newPages && newPages.length > 0) {
          let accText = "";
          let accHtml = "";
          newPages.forEach((p) => {
             accText += "\n\n" + p.text;
             accHtml += `<div class="transcription-batch"><p>${p.text.replace(/\n\n/g, "</p><p>")}</p></div>`;
          });
          setContent(prev => prev + accText);
          setHtmlContent(prev => prev + accHtml);
          editorRef.current?.insertChunk(accHtml);
          setProcessedPageCount(prev => prev + newPages.length);
        }
        if (state.status === "complete") {
          setIsTranscribing(false);
          clearInterval(poll);
          notify("Your manuscript is sealed and ready in the project folder!");
        }
        
        if (state.status === "error") {
          setIsTranscribing(false);
          clearInterval(poll);
          const msg = state.error_message || "Transcription engine encountered an error.";
          notify(`ENGINE FAULT: ${msg}`);
        }
        
        if (state.status === "audit") {
            setIsTranscribing(false);
            clearInterval(poll);
            notify("DIRECTORIAL AUDIT: Sequence Disruption Detected.");
        }
      } catch (e) {
        notify("Transcription Pulse Weakened: Re-connecting...");
      }
    }, 2000);
    return () => clearInterval(poll);
  }, [isTranscribing, lastActionTime]);

  const handleApplySuggestion = useCallback((suggestion: string | { suggestion?: string; content?: string }) => {
    // Suggestion objects carry the replacement text in .suggestion/.content;
    // plain strings are inserted as-is.
    const text = typeof suggestion === 'string'
        ? suggestion
        : (suggestion.suggestion ?? suggestion.content ?? '');
    if (!text) return;
    editorRef.current?.insertChunk(`<div class="ai-suggestion">${text}</div>`);
  }, []);

  const handleExportDocx = async () => {
    try { await exportDocx(htmlContent, chapters, bookTitle || "Manuscript", authorName, "chicago", coverImage || undefined); }
    catch (err) { alert("Export failed"); }
  };

  const handleExportPdf = async () => {
    try { await exportPdf(htmlContent, chapters, bookTitle || "Manuscript", authorName, "chicago", coverImage || undefined); }
    catch (err) { alert("Export failed"); }
  };

  const handleExportEpub = async () => {
    try { await exportEpub(htmlContent, chapters, bookTitle || "Manuscript", authorName, "chicago", coverImage || undefined); }
    catch (err) { alert("Export failed"); }
  };

  const handleUndo = () => editorRef.current?.undo();
  const handleRedo = () => editorRef.current?.redo();

  const handleTakeSnapshot = async () => {
    // [SAVE PROJECT]: flush the live draft to the project file (same store autosave uses).
    const ok = await saveProjectState(activeFolderPath, {
        draft_html: htmlContent,
        draft_text: content,
        draft_toc: chapters,
        draft_reports: agentReports,
        draft_arc: arcData,
        draft_ts: Date.now(),
    });
    notify(ok
        ? `Project saved at ${new Date().toLocaleTimeString()}.`
        : "Save failed — could not write the project file.");
  };

  // [SHORTCUT]: Ctrl/Cmd+S → Save Project (and suppress the browser Save dialog).
  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 's') {
        e.preventDefault();
        handleTakeSnapshot();
      }
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [content, htmlContent, chapters, agentReports, arcData]);

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
            onExportDocx={handleExportDocx}
            onExportPdf={handleExportPdf}
            onExportEpub={handleExportEpub}
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
              onParagraphChange={setCurrentParagraphText}
              onMisspelledCountChange={(count) => {
                setMisspelledCount(count);
                onMisspelledCountChange?.(count);
              }}
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
              missingPagesCount={transcriptionStatus?.missing_pages_count || 0}
              status={transcriptionStatus?.status || "idle"}
              errorMessage={transcriptionStatus?.error_message}
              isTranscribing={isTranscribing}
              onStart={handleStartTranscribe}
              onAbort={() => abortTranscription('current')}
              providerName="Sovereign Gateway"
              modelName="Apex Vision"
              currentImageB64={transcriptionStatus?.current_image_b64}
            />
          </div>
        </DraggableDialog>
      )}

            {/* [SOVEREIGN MAPPED]: Boardroom Engine (Fixed Top-Right) */}
      <DraggableDialog headerId="boardroom-title-handle" initialX={window?.innerWidth ? window.innerWidth - 480 : 800} initialY={110}>
        <AnalysisDashboard 
          editorContent={htmlContent} 
          arcData={arcData} 
          setArcData={setArcData}
          chapters={chapters} 
          setChapters={setChapters}
          agentReports={agentReports}
          setAgentReports={setAgentReports} 
          onApplySuggestion={handleApplySuggestion}
          activeTab={activeTab} 
          setActiveTab={setActiveTab}
          selectedAgents={selectedAgents} 
          setSelectedAgents={setSelectedAgents}
          customAgents={customAgents} 
          setCustomAgents={setCustomAgents}
          isAnalyzing={isAnalyzing}
          setIsAnalyzing={setIsAnalyzing}
          analysisTrigger={localAnalysisTrigger}
          projectFolder={activeFolderPath}
          onCompletion={() => { notify("Boardroom Consensus Established."); setIsReportOpen(true); }}
          notify={notify}
        />
      </DraggableDialog>

      <GuideAssistant 
        content={content} selectedText={selectedText} misspelledCount={misspelledCount}
        wordCount={wordCount} hasToc={(chapters?.length || 0) > 0}
        hasReports={Object.keys(agentReports || {}).length > 0}
        folderPath={activeFolderPath}
      />
    </main>
  );
}
