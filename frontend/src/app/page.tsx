"use client";

import React, { useState, useEffect } from "react";
import MainEditor from "@/components/MainEditor";
import Sidebar from "@/components/Sidebar";
import CloudServiceGate from "@/components/CloudServiceGate";
import HelpCenter from "@/components/HelpCenter";
import OnboardingModal from "@/components/OnboardingModal";
import SettingsModal from "@/components/SettingsModal";
import NerveCenter from "@/components/NerveCenter";
import StructuralAnalysisModal from "@/components/workstation/StructuralAnalysisModal";
import AiEnhancementHub from "@/components/workstation/AiEnhancementHub";
import { PanelLeftClose, PanelLeftOpen } from "lucide-react";
import { purgeLegacyBrowserStorage } from "@/lib/migration_gate";
import { loadPreferences, getPref, setPref } from "@/lib/preferences";
import { useWorkstationState, useWorkstationActions } from "@/context/WorkstationContext";
import { useEditorState } from "@/context/EditorContext";

export default function Home() {
  const { 
    isFocusMode, bookTitle, authorName, coverImage, activeFolderPath
  } = useWorkstationState();

  const { chapters, arcData } = useEditorState();

  const {
    setIsFocusMode, setBookTitle, setAuthorName,
    setCoverImage, notify, establishProject, setIsReportOpen
  } = useWorkstationActions();

  const [isLeftSidebarOpen, setIsLeftSidebarOpen] = useState(true);
  const [scrollToText, setScrollToText] = useState<string | null>(null);
  const [analysisTrigger, setAnalysisTrigger] = useState(0);
  const [syncTrigger, setSyncTrigger] = useState(0);
  const [isHelpOpen, setIsHelpOpen] = useState(false);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [isOnboardingOpen, setIsOnboardingOpen] = useState(false);

  // [FIX #7]: Settings state - keys and toggles managed here for SettingsModal
  const [keys, setKeysState] = useState<Record<string, string>>({});
  const [forcePrimary, setForcePrimary] = useState(false);
  const [localMode, setLocalMode] = useState(false);
  const [activeProvider, setActiveProvider] = useState('slot_primary');

  // [FIX #8]: Cloud gate state
  const [cloudGate, setCloudGate] = useState<{isOpen: boolean, feature: string, onConfirm?: () => void}>({
      isOpen: false, feature: ''
  });

  // 🛡️ [FILES-ONLY]: purge any legacy browser-stored keys/vault/shadow on load.
  useEffect(() => {
    purgeLegacyBrowserStorage();
  }, []);

  // [FILES-ONLY]: load global preferences from the vault, then derive onboarding /
  // mode flags from them (no browser localStorage).
  useEffect(() => {
    (async () => {
        await loadPreferences();
        if (!getPref<boolean>('onboarded', false)) setIsOnboardingOpen(true);
        setForcePrimary(getPref<boolean>('force_primary', false));
        setLocalMode(getPref<boolean>('local_mode', false));
    })();
  }, []);

  // Load vault presence on mount — keys live in backend .env, not in browser
  useEffect(() => {
    if (typeof window !== 'undefined') {
        import('@/lib/apiClient').then(async (api) => {
            const presence = await api.fetchVaultSync();
            // presence = { gemini: true/false, openai: true/false, ... }
            // We mark slots as '***SEALED***' so the UI shows the key is present
            const masked: Record<string, string> = {};
            for (const [provider, isPresent] of Object.entries(presence)) {
                if (isPresent) masked[provider] = '***SEALED***';
            }
            if (Object.keys(masked).length > 0) {
                setKeysState(masked);
            }

            // [SETUP GATE]: if no cloud key is configured and the user isn't in local
            // (Sovereign) mode, surface the startup setup screen so the app is usable.
            const hasAnyKey = ['gemini', 'openai', 'anthropic', 'groq'].some(p => masked[p]);
            await loadPreferences();
            if (!hasAnyKey && getPref<boolean>('local_mode', false) !== true) {
                setIsOnboardingOpen(true);
            }

            // [REMOVED]: the background validate-and-prune deleted VALID keys
            // (the /models check false-negatives on some keys). SEALED now reflects
            // vault presence only; the user manages keys manually. Never auto-delete.
        });
    }
  }, []);

  // Listen for settings-open events
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const handleOpenSettings = () => setIsSettingsOpen(true);
      window.addEventListener('tome-master-open-settings', handleOpenSettings);
      return () => window.removeEventListener('tome-master-open-settings', handleOpenSettings);
    }
  }, []);

  // Allow re-opening the AI setup / path-choice screen on demand.
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const handleOpenOnboarding = () => setIsOnboardingOpen(true);
      window.addEventListener('tome-master-open-onboarding', handleOpenOnboarding);
      return () => window.removeEventListener('tome-master-open-onboarding', handleOpenOnboarding);
    }
  }, []);

  // Listen for target requests
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const handleTarget = () => establishProject();
      window.addEventListener('tome-master-target-request', handleTarget);
      return () => window.removeEventListener('tome-master-target-request', handleTarget);
    }
  }, [establishProject]);

  // Listen for Nerve Center analysis invocation
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const handleInvokeAnalysis = () => setAnalysisTrigger(prev => prev + 1);
      window.addEventListener('tome-master-invoke-analysis', handleInvokeAnalysis);
      return () => window.removeEventListener('tome-master-invoke-analysis', handleInvokeAnalysis);
    }
  }, []);

  const handleSetKeys = (newKeys: Record<string, string>) => {
    setKeysState(newKeys);
    window.dispatchEvent(new CustomEvent('tome-master-settings-changed'));
  };

  // [SOVEREIGN]: Onboarding completion logic
  const handleOnboardingComplete = () => {
    setPref('onboarded', true);
    setIsOnboardingOpen(false);
    window.dispatchEvent(new CustomEvent('tome-master-settings-changed'));
    notify("Industrial Architecture Established.");
  };

  const triggerCloudGate = (feature: string, onConfirm: () => void) => {
      setCloudGate({ isOpen: true, feature, onConfirm });
  };

  const handleCloudConfirm = () => {
      const { onConfirm } = cloudGate;
      setCloudGate({ isOpen: false, feature: '' });
      if (onConfirm) onConfirm();
  };

  const handleChapterClick = (startingWords: string) => setScrollToText(startingWords);

  // Cover upload handler
  const handleCoverUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (event) => {
      const base64 = event.target?.result as string;
      setCoverImage(base64);
    };
    reader.readAsDataURL(file);
  };

  return (
    <div className="flex h-screen w-full bg-[#0a0a0a] text-zinc-100 overflow-hidden font-[family-name:var(--font-geist-sans)]" style={{ paddingTop: 'var(--safe-top, 0px)' }}>
      
      {/* Left Sidebar */}
      {!isFocusMode && isLeftSidebarOpen && (
        <Sidebar
          chapters={chapters}
          onChapterClick={handleChapterClick}
          onAnalysisClick={() => setIsReportOpen(true)}
          onSyncClick={() => setSyncTrigger(prev => prev + 1)}
          isOfflineMode={localMode}
          coverImage={coverImage}
          onCoverUpload={handleCoverUpload}
          bookTitle={bookTitle}
          onTitleChange={setBookTitle}
          authorName={authorName}
          onAuthorChange={setAuthorName}
          onOpenHelp={() => setIsHelpOpen(true)}
          arcData={arcData}
        />
      )}

      {/* Left sidebar toggle */}
      {!isFocusMode && (
        <button
          onClick={() => setIsLeftSidebarOpen(v => !v)}
          className="fixed left-0 top-1/2 -translate-y-1/2 z-30 w-5 h-14 bg-[#1a1a1a] hover:bg-[#252525] border-r border-t border-b border-[#333] rounded-r-lg flex items-center justify-center text-zinc-500 hover:text-indigo-400 transition-all shadow-sm"
          style={{ left: isLeftSidebarOpen ? '20rem' : '0px' }}
        >
          {isLeftSidebarOpen ? <PanelLeftClose className="w-4 h-4" /> : <PanelLeftOpen className="w-4 h-4" />}
        </button>
      )}

      {/* Main content area */}
      <div className="flex-1 h-full min-w-0 flex flex-col">
        <MainEditor
          scrollToText={scrollToText}
          onScrollComplete={() => setScrollToText(null)}
          onPreviewChapter={handleChapterClick}
          onCoverUpload={handleCoverUpload}
          syncTrigger={syncTrigger}
        />
      </div>

      <CloudServiceGate 
        isOpen={cloudGate.isOpen}
        featureName={cloudGate.feature}
        onClose={() => setCloudGate({ isOpen: false, feature: '' })}
        onConfirm={handleCloudConfirm}
      />

      <HelpCenter isOpen={isHelpOpen} onClose={() => setIsHelpOpen(false)} />
      
      <OnboardingModal 
        isOpen={isOnboardingOpen} 
        onClose={handleOnboardingComplete} 
      />

      <SettingsModal 
        isOpen={isSettingsOpen} 
        onClose={() => setIsSettingsOpen(false)}
        activeProvider={activeProvider}
        setActiveProvider={setActiveProvider}
        activeFolderPath={activeFolderPath}
        keys={keys}
        setKeys={handleSetKeys}
      />
      
      {/* Hide the Nerve Center bar while the path-choice / onboarding page is up. */}
      {!isOnboardingOpen && <NerveCenter isLeftSidebarOpen={isLeftSidebarOpen} />}
      <StructuralAnalysisModal />
      <AiEnhancementHub />
    </div>
  );
}
