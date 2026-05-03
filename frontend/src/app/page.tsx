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
import { performMasterMigration } from "@/lib/migration_gate";
import { useWorkstationState, useWorkstationActions } from "@/context/WorkstationContext";

export default function Home() {
  const { 
    isFocusMode, chapters, arcData, bookTitle, authorName, coverImage,
    activeProvider, activeModel, isOfflineMode, isActivated, activeFolderPath
  } = useWorkstationState();

  const { 
    setIsFocusMode, setChapters, setArcData, setBookTitle, setAuthorName, 
    setCoverImage, setIsOfflineMode, setActiveProvider, notify, syncTableOfContents,
    anchorProject
  } = useWorkstationActions();

  // Local UI-only states for the Shell
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

  // [FIX #8]: Cloud gate state
  const [cloudGate, setCloudGate] = useState<{isOpen: boolean, feature: string, onConfirm?: () => void}>({
      isOpen: false, feature: ''
  });

  // 🛡️ MIGRATION GATE
  useEffect(() => {
    performMasterMigration();
  }, []);

  // Detect first load for onboarding
  useEffect(() => {
    if (typeof window !== 'undefined') {
        const hasOnboarded = localStorage.getItem('tome_master_onboarded');
        if (!hasOnboarded) setIsOnboardingOpen(true);
    }
  }, []);

  // Load vault keys on mount
  useEffect(() => {
    if (typeof window !== 'undefined') {
        const savedKeys = localStorage.getItem('tome_master_vault');
        if (savedKeys) {
            setKeysState(JSON.parse(savedKeys));
        } else {
            import('@/lib/apiClient').then(async (api) => {
                const recovered = await api.fetchVaultSync();
                if (Object.keys(recovered).length > 0) {
                    setKeysState(prev => {
                        const updated = { ...recovered, ...prev };
                        localStorage.setItem('tome_master_vault', JSON.stringify(updated));
                        return updated;
                    });
                }
            });
        }
        setForcePrimary(localStorage.getItem('tome_master_force_primary') === 'true');
        setLocalMode(localStorage.getItem('tome_master_local_mode') === 'true');
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

  // Listen for anchor requests
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const handleAnchor = () => anchorProject();
      window.addEventListener('tome-master-anchor-request', handleAnchor);
      return () => window.removeEventListener('tome-master-anchor-request', handleAnchor);
    }
  }, [anchorProject]);

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
    localStorage.setItem('tome_master_vault', JSON.stringify(newKeys));
    window.dispatchEvent(new CustomEvent('tome-master-settings-changed'));
  };

  // [FIX #9]: Full onboarding completion logic
  const handleOnboardingComplete = (provider: string) => {
    localStorage.setItem('tome_master_onboarded', 'true');
    localStorage.setItem('tome_master_provider', provider);
    setActiveProvider(provider);
    setIsOnboardingOpen(false);
    
    if (provider === 'ollama') {
        localStorage.setItem('tome_master_model', 'gemma4:e2b');
    } else if (provider === 'gemini') {
        localStorage.setItem('tome_master_model', 'models/gemini-1.5-flash');
    }
    window.dispatchEvent(new CustomEvent('tome-master-settings-changed'));
  };

  const triggerCloudGate = (feature: string, onConfirm: () => void) => {
      setCloudGate({ isOpen: true, feature, onConfirm });
  };

  const handleCloudConfirm = () => {
      const { onConfirm } = cloudGate;
      setCloudGate({ isOpen: false, feature: '' });
      setIsOfflineMode(false);
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
          onAnalysisClick={() => setAnalysisTrigger(prev => prev + 1)}
          onSyncClick={() => setSyncTrigger(prev => prev + 1)}
          isOfflineMode={isOfflineMode}
          activeProvider={activeProvider}
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
        setActiveProvider={(p) => {
            setActiveProvider(p);
        }}
        activeFolderPath={activeFolderPath}
        keys={keys}
        setKeys={handleSetKeys}
        forcePrimary={forcePrimary}
        setForcePrimary={(v) => {
            setForcePrimary(v);
            localStorage.setItem('tome_master_force_primary', String(v));
        }}
        localMode={localMode}
        setLocalMode={(v) => {
            setLocalMode(v);
            localStorage.setItem('tome_master_local_mode', String(v));
        }}
      />
      
      <NerveCenter isLeftSidebarOpen={isLeftSidebarOpen} />
      <StructuralAnalysisModal />
      <AiEnhancementHub />
    </div>
  );
}
