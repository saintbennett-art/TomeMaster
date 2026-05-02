"use client";
import React, { useState, useEffect } from 'react';
import { FileText, Settings, BarChart2, Scroll, RefreshCw, HelpCircle, Activity } from "lucide-react";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, ResponsiveContainer } from 'recharts';
import { checkSystemHealth } from '@/lib/apiClient';

interface SidebarProps {
  chapters: any[];
  onChapterClick?: (startingWords: string) => void;
  onAnalysisClick?: () => void;
  onSyncClick?: () => void;
  isOfflineMode?: boolean;
  activeProvider?: string;
  coverImage?: string | null;
  onCoverUpload?: (e: React.ChangeEvent<HTMLInputElement>) => void;
  bookTitle?: string;
  onTitleChange?: (val: string) => void;
  authorName?: string;
  onAuthorChange?: (val: string) => void;
  onOpenHelp?: () => void;
  onAmbientNotify?: (text: string) => void;
  arcData?: any[];
}

function Sidebar({ 
  chapters = [], onChapterClick, onAnalysisClick, onSyncClick, isOfflineMode, activeProvider = 'simulator',
  coverImage, onCoverUpload, bookTitle = "Manuscript", onTitleChange, authorName = "Author", onAuthorChange, onOpenHelp,
  onAmbientNotify,
  arcData = []
}: SidebarProps) {
  const [activeTab, setActiveTab] = useState<'manuscript' | 'project'>('manuscript');
  const [health, setHealth] = useState({ backend: false, vault: false, ollama: false });

  const ambientNotify = onAmbientNotify || ((text: string, actionEventName?: string) => {
    window.dispatchEvent(new CustomEvent('tome-master-guide-speak', { detail: { text, actionEventName } }));
  });

  useEffect(() => {
    let isMounted = true;
    const pollHealth = async () => {
        if (!isMounted) return;
        try {
            const status = await checkSystemHealth();
            if (isMounted) setHealth(status);
        } catch (e) {}
    };
    pollHealth();
    const interval = setInterval(pollHealth, 15000); // [HUSHED HEARTBEAT]: 15s interval to reduce noise
    return () => {
        isMounted = false;
        clearInterval(interval);
    };
  }, []);

  const healthScore = (health.backend ? 1 : 0) + (health.vault ? 1 : 0);

  return (
    <>
      <aside className="w-80 border-r border-border bg-background flex flex-col h-full min-h-0 shrink-0">
        <div className="h-14 flex items-center px-6 border-b border-border">
          <div className="flex items-center gap-3">
            <Scroll className="w-5 h-5 text-accent" />
            <h1 className="font-semibold text-foreground tracking-wide">Tome-Master</h1>
          </div>
          <div className="ml-auto flex gap-1.5">
             <div className={`w-1.5 h-1.5 rounded-full ${health.backend ? 'bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.3)]' : 'bg-rose-500'}`} title={health.backend ? "Backend Active" : "Backend Offline: Run Start_TomeMaster.bat"} />
             <div className={`w-1.5 h-1.5 rounded-full ${health.vault ? 'bg-indigo-500 shadow-[0_0_8px_rgba(99,102,241,0.3)]' : 'bg-amber-500'}`} title={health.vault ? "Vault Loaded" : "Vault Empty: Configure Settings"} />
          </div>
        </div>
        
        <div className="flex-1 py-4 px-4 flex flex-col min-h-0">
          <div className="flex gap-2 mb-6">
            <button 
                onClick={() => setActiveTab('manuscript')}
                onMouseEnter={() => ambientNotify("Manuscript Chamber: Here you audit your story's high-level architecture, navigation anchors, and live structural pacing.")}
                className={`flex-1 flex items-center justify-center gap-2 py-2 rounded-lg border text-[10px] font-black uppercase tracking-widest transition-all ${activeTab === 'manuscript' ? 'bg-accent/20 border-accent/40 text-accent shadow-lg shadow-accent/5' : 'bg-surface border-border text-muted hover:text-foreground'}`}
            >
                <FileText className="w-3.5 h-3.5" />
                Manuscript
            </button>
            <button 
                onClick={() => setActiveTab('project')}
                onMouseEnter={() => ambientNotify("Project Branding: Define your narrative's visual identity, cover aesthetics, and metadata anchoring for professional distribution.")}
                className={`flex-1 flex items-center justify-center gap-2 py-2 rounded-lg border text-[10px] font-black uppercase tracking-widest transition-all ${activeTab === 'project' ? 'bg-accent/20 border-accent/40 text-accent shadow-lg shadow-accent/5' : 'bg-surface border-border text-muted hover:text-foreground'}`}
            >
                <BarChart2 className="w-3.5 h-3.5" />
                Project
            </button>
          </div>

          <div className="flex flex-col gap-2 mb-4">
            <button 
                onMouseEnter={() => ambientNotify("Narrative Archive: Your active drafting environment where prose is synthesized into reality.")}
                className="flex items-center gap-3 px-3 py-2.5 rounded-md bg-accent/20 text-accent font-medium transition-colors hover:bg-accent/30"
            >
              <FileText className="w-4 h-4" />
              Editor
            </button>
            <button 
               onMouseEnter={() => ambientNotify(chapters.length === 0 ? "Strategic Alert: No structural segments identified. Connect the specialists to synthesize your chapter breaks." : "Boardroom Convention: Trigger a deep-tissue manuscript audit across all specialized directorial agents.")}
               className={`flex items-center gap-3 px-3 py-2.5 rounded-md transition-colors ${isOfflineMode ? 'text-muted cursor-not-allowed opacity-50' : 'text-blue-400 hover:text-white hover:bg-blue-600/20'}`} 
               onClick={isOfflineMode ? undefined : onAnalysisClick}
               title={isOfflineMode ? "Internet Access Required for Cloud Analysis" : `Quick Full Manuscript Analysis: Run a high-level Boardroom summary on the entire book via ${activeProvider.charAt(0).toUpperCase() + activeProvider.slice(1)}`}
            >
              {isOfflineMode ? <div className="relative"><BarChart2 className="w-4 h-4" /><div className="absolute -top-1 -right-1 bg-background rounded-full"><Settings className="w-2 h-2 text-muted" /></div></div> : <BarChart2 className="w-4 h-4 text-blue-500" />}
              Analysis {isOfflineMode && <span className="text-[10px] bg-surface-hover px-1 rounded ml-auto tracking-tighter">OFFLINE</span>}
            </button>
          </div>

          <div className="flex-1 min-h-0 flex flex-col overflow-hidden">
            {activeTab === 'project' ? (
                <div className="flex-1 overflow-y-auto px-1 animate-in fade-in slide-in-from-left-2 duration-300">
                    <div className="mt-2 mb-4 px-2 flex flex-col gap-3">
                        <span className="text-[10px] font-black text-zinc-600 uppercase tracking-[0.2em]">Visual Branding</span>
                        <div 
                            onMouseEnter={() => ambientNotify("Cover Archive: Anchors your project's visual identity.")}
                            className="relative group aspect-[2/3] w-full bg-[#151515] rounded-xl border border-[#2a2a2a] overflow-hidden hover:border-indigo-500/50 transition-all flex flex-col items-center justify-center cursor-pointer shadow-xl"
                        >
                            {coverImage ? (
                                <>
                                    <img src={coverImage} alt="Project Cover" className="w-full h-full object-cover opacity-80 group-hover:opacity-100 transition-opacity" />
                                    <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity flex items-end justify-center p-4">
                                        <span className="text-[10px] text-zinc-300 font-bold tracking-widest uppercase mb-2">Change Cover Image</span>
                                    </div>
                                </>
                            ) : (
                                <div className="flex flex-col items-center gap-2 text-zinc-600 group-hover:text-zinc-400 transition-colors">
                                    <div className="w-12 h-12 rounded-full border-2 border-dashed border-zinc-800 flex items-center justify-center">
                                        <Scroll className="w-6 h-6 opacity-30" />
                                    </div>
                                    <span className="text-[10px] font-black tracking-widest uppercase">Upload Cover Page</span>
                                </div>
                            )}
                            <input 
                                type="file" 
                                accept="image/*" 
                                onChange={onCoverUpload} 
                                className="absolute inset-0 opacity-0 cursor-pointer" 
                                title="Upload or Change Project Cover Image"
                            />
                        </div>

                        <div className="flex flex-col gap-4 mt-4">
                            <div className="flex flex-col gap-1.5" onMouseEnter={() => ambientNotify("Author Identity: Define your pen name and manuscript title for metadata anchoring.")}>
                                <label htmlFor="book-title" className="text-[9px] text-muted font-black uppercase tracking-widest pl-1">Manuscript Title</label>
                                <input 
                                    id="book-title"
                                    type="text" 
                                    value={bookTitle} 
                                    onChange={(e) => onTitleChange?.(e.target.value)}
                                    placeholder="Book Title"
                                    className="w-full bg-surface border border-border rounded-lg px-4 py-2.5 text-xs text-foreground focus:outline-none focus:border-accent/50 transition-colors font-medium"
                                />
                            </div>
                        </div>
                    </div>
                </div>
            ) : (
                <div className="flex-1 flex flex-col min-h-0 animate-in fade-in slide-in-from-right-2 duration-300">
                    <div className="mt-2 mb-2 px-2 flex items-center justify-between">
                        <span className="text-[10px] font-black text-zinc-600 uppercase tracking-[0.2em]">Table of Contents</span>
                        <button 
                            onClick={onSyncClick} 
                            onMouseEnter={() => ambientNotify("Sync: Synchronizes Heading tags from the editor into your structured Table of Contents.")}
                            className="p-1 hover:bg-indigo-500/10 rounded-md text-zinc-500 hover:text-indigo-400 transition-colors" 
                            title="Sync live headings from Editor"
                        >
                            <RefreshCw className="w-3.5 h-3.5" />
                        </button>
                    </div>
                    <div className="flex-1 overflow-y-auto overflow-x-hidden pr-2 pb-4 bright-scrollbar min-h-0">
                        {chapters.length > 0 ? (
                        chapters
                            .filter((chap: any, i: number) => {
                                const title = (chap.original_heading || chap.suggested_title || "").toLowerCase();
                                if (title.includes('epilogue') || title.includes('prologue') || title.includes('prelude')) return true;
                                if ((chap.chapter_word_count || 0) < 30) return false;
                                if (i < 2 && (chap.chapter_word_count || 0) < 250) return false;
                                return true;
                            })
                            .map((chap: any, i: number) => (
                            <div 
                                key={i} 
                                onMouseEnter={() => ambientNotify(`Scrolling to ${chap.suggested_title || 'Chapter'}. Duration: ${chap.reading_time_mins || 1} minutes.`)}
                                onClick={(e) => {
                                    onChapterClick?.(chap.starting_words);
                                    e.currentTarget.scrollIntoView({ behavior: 'smooth', block: 'start' });
                                }}
                                className="text-xs py-2.5 pl-3 border-l-2 border-[#1a1a1a] hover:border-indigo-500/50 text-zinc-400 hover:text-zinc-100 cursor-pointer ml-2 transition-all mt-1 flex justify-between items-start pr-3 group hover:bg-white/5 rounded-r-md"
                            >
                                <div className="flex flex-col min-w-0 pr-4">
                                    <span className="font-medium truncate block">{(chap.suggested_title || "").replace(/^Chapter\s*\d+\s*[:\-]?\s*/i, '').trim()}</span>
                                    <span className="text-[10px] text-zinc-500 mt-0.5 opacity-80">
                                        {chap.reading_time_mins || 1} min • {chap.chapter_word_count?.toLocaleString() || 0} words
                                    </span>
                                </div>
                            </div>
                            ))
                        ) : (
                            <div 
                                onClick={onAnalysisClick}
                                onMouseEnter={() => ambientNotify("The manuscript archive is empty. Click here to summon the specialists and synthesize your chapter breaks.", "tome-master-invoke-analysis")}
                                className="text-xs py-4 px-2 text-muted-foreground hover:text-accent hover:border-accent/40 bg-surface/50 hover:bg-accent/5 italic border border-dashed border-border rounded-xl text-center mx-2 mt-4 cursor-pointer transition-all group"
                            >
                                <div className="mb-2 flex justify-center opacity-30 group-hover:opacity-100 transition-opacity"><BarChart2 className="w-5 h-5 text-accent" /></div>
                                No chapters detected yet. <br/>
                                <span className="text-[10px] uppercase font-bold not-italic tracking-wider mt-2 block opacity-0 group-hover:opacity-100 transition-opacity">Invoke Synthesis Specialist</span>
                            </div>
                        )}
                    </div>

                    {/* NEW: Permanent Structural Cockpit (The Arc Chart) */}
                    {arcData.length > 0 && (
                        <div 
                            className="mt-4 pt-4 border-t border-[#222] animate-in fade-in slide-in-from-bottom-4 duration-700"
                            onMouseEnter={() => ambientNotify("Master Story Arc: Operational view of narrative tension and emotional rhythm.")}
                        >
                            <div className="flex items-center justify-between mb-3 px-1">
                                <span className="text-[10px] font-black text-indigo-400 uppercase tracking-[0.2em] flex items-center gap-2">
                                    <Activity className="w-3 h-3" /> Master Story Arc
                                </span>
                                <span className="text-[8px] text-zinc-600 font-bold uppercase">Dynamic Rhythm</span>
                            </div>
                            <div className="h-28 w-full bg-surface-hover/30 rounded-xl border border-border p-2 hover:border-accent/30 transition-colors cursor-crosshair">
                                <ResponsiveContainer width="100%" height="100%">
                                    <LineChart data={arcData.filter((d, i) => (d.chapter_word_count || 0) > 30)}>
                                        <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
                                        <XAxis dataKey="segment" hide />
                                        <YAxis domain={[0, 10]} hide />
                                        <RechartsTooltip 
                                            contentStyle={{ backgroundColor: 'var(--background)', border: '1px solid var(--border)', borderRadius: '8px', fontSize: '10px' }}
                                            itemStyle={{ color: 'var(--accent)', fontWeight: 'bold' }}
                                            labelStyle={{ color: 'var(--muted)', marginBottom: '4px' }}
                                        />
                                        <Line 
                                            type="monotone" 
                                            dataKey="score" 
                                            stroke="#6366f1" 
                                            strokeWidth={3} 
                                            dot={{ r: 2, fill: '#818cf8', strokeWidth: 0 }} 
                                            activeDot={{ r: 4, fill: '#fff' }}
                                            animationDuration={1500}
                                        />
                                    </LineChart>
                                </ResponsiveContainer>
                            </div>
                        </div>
                    )}
                </div>
            )}
          </div>
        </div>
        
        <div className="p-4 border-t border-border flex flex-col gap-2">
          <button 
            onClick={onOpenHelp}
            onMouseEnter={() => ambientNotify("Tactical Support: Access the instruction manual and system documentation.")}
            className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-surface hover:bg-surface-hover border border-border rounded-md text-sm text-foreground transition-colors"
          >
            <HelpCircle className="w-4 h-4" />
            Help Center
          </button>
          <button 
            onClick={() => window.dispatchEvent(new CustomEvent('tome-master-open-settings'))}
            onMouseEnter={() => ambientNotify("Intelligence Command: Configure your specialist vaults and directorial voice personas.")}
            className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-surface hover:bg-surface-hover border border-border rounded-md text-sm text-foreground transition-colors"
          >
            <Settings className="w-4 h-4" />
            Settings
          </button>
        </div>
      </aside>
    </>
  );
}

export default React.memo(Sidebar);
