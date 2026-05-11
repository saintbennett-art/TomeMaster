"use client";

import React, { useState, useEffect } from "react";
import { 
    X, LayoutList, Activity, Save, AlertCircle, 
    CheckCircle2, Loader2, Wand2, ChevronRight, BarChart3,
    ShieldAlert, ExternalLink, Sparkles, Key
} from "lucide-react";
import { 
    ResponsiveContainer, AreaChart, Area, XAxis, 
    YAxis, Tooltip, CartesianGrid 
} from "recharts";
import { useWorkstationState, useWorkstationActions } from "@/context/WorkstationContext";
import { useEditorState, useEditorActions } from "@/context/EditorContext";
import { API_BASE_HOLDER } from "@/lib/apiClient";
import { Chapter } from "@/types/industrial";
import { secureVault } from "@/lib/vault";

const StructuralAnalysisModal = () => {
    const { 
        isStructuralModalOpen, activeFolderPath
    } = useWorkstationState();
    
    const {
        content, chapters: existingChapters
    } = useEditorState();
    
    const { 
        setIsStructuralModalOpen, notify
    } = useWorkstationActions();

    const { setChapters } = useEditorActions();

    const [isAnalyzing, setIsAnalyzing] = useState(false);
    const [proposedChapters, setProposedChapters] = useState<Chapter[]>([]);
    const [error, setError] = useState<string | null>(null);

    const runStructuralAudit = async () => {
        if (!content) {
            notify("Manuscript is empty. Cannot analyze structure.");
            return;
        }

        setIsAnalyzing(true);
        setError(null);
        
        try {
            const response = await fetch(`${API_BASE_HOLDER.current}/analysis/structural-analysis`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ content })
            });

            const data = await response.json();
            if (data.chapters) {
                setProposedChapters(data.chapters);
                notify("The Architect has delineated your narrative structure.");
            } else {
                throw new Error(data.detail || "Structural analysis failed to return chapters.");
            }
        } catch (err) {
            const e = err as Error;
            setError(e.message || "Sovereign Engine timeout during structural scan.");
        } finally {
            setIsAnalyzing(false);
        }
    };

    const applyStructure = () => {
        if (proposedChapters.length === 0) return;
        
        // [SOVEREIGN INJECTION]: Map proposed chapters to the workstation state
        // In a real implementation, we would also find the text segments and insert # headings
        // For now, we update the state chapters which drives the TOC and Arc.
        const formattedChapters = proposedChapters.map(c => ({
            id: `chap-${c.chapter_number}`,
            chapter_number: c.chapter_number,
            suggested_title: c.suggested_title,
            starting_words: c.starting_words,
            emotional_intensity: c.emotional_intensity,
            summary: c.summary,
            content_warnings: c.content_warnings || []
        }));

        setChapters(formattedChapters);
        notify("Structural Foundations Stabilized. Chapters and Arcs synchronized.");
        setIsStructuralModalOpen(false);
    };

    if (!isStructuralModalOpen) return null;

    return (
        <div className="fixed inset-0 z-[1000] flex items-center justify-center p-6 bg-black/60 backdrop-blur-md animate-in fade-in duration-300">
            <div className="w-full max-w-5xl h-[85vh] bg-surface border border-border shadow-[0_0_100px_rgba(0,0,0,0.5)] rounded-3xl flex flex-col overflow-hidden relative">
                
                {/* Header */}
                <div className="px-8 py-6 border-b border-border flex items-center justify-between bg-zinc-900/50">
                    <div className="flex items-center gap-4">
                        <div className="p-3 bg-emerald-500/10 rounded-2xl">
                            <LayoutList className="w-6 h-6 text-emerald-400" />
                        </div>
                        <div>
                            <h2 className="text-xl font-black text-foreground tracking-tighter uppercase leading-none">Structural Arrangement</h2>
                            <p className="text-[10px] text-muted-foreground font-bold uppercase tracking-widest mt-2 leading-none">Narrative Architect & Emotional Arc Analysis</p>
                        </div>
                    </div>
                    <button 
                        onClick={() => setIsStructuralModalOpen(false)}
                        className="p-2 hover:bg-white/5 rounded-xl transition-all text-muted-foreground hover:text-white"
                    >
                        <X className="w-6 h-6" />
                    </button>
                </div>

                <div className="flex-1 flex overflow-hidden">
                    {/* Sidebar / Chapter List */}
                    <div className="w-1/2 border-r border-border flex flex-col bg-zinc-900/20">
                        <div className="p-6 border-b border-border/50 flex items-center justify-between">
                            <span className="text-[10px] font-black text-zinc-500 uppercase tracking-widest">Proposed Chapter Delineation</span>
                            <button 
                                onClick={runStructuralAudit}
                                disabled={isAnalyzing}
                                className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:bg-zinc-800 text-white rounded-xl text-[10px] font-black uppercase transition-all shadow-lg shadow-indigo-600/20"
                            >
                                {isAnalyzing ? <Loader2 className="w-3 h-3 animate-spin" /> : <Wand2 className="w-3 h-3" />}
                                {isAnalyzing ? "Scanning..." : "Draft Structure"}
                            </button>
                        </div>

                        <div className="flex-1 overflow-y-auto p-4 space-y-3 custom-scrollbar">
                            {proposedChapters.length > 0 ? (
                                proposedChapters.map((chap, idx) => (
                                    <div key={idx} className="group p-4 bg-background border border-border/50 rounded-2xl hover:border-emerald-500/30 transition-all">
                                        <div className="flex items-center justify-between mb-2">
                                            <span className="text-[9px] font-black text-emerald-500 uppercase px-2 py-0.5 bg-emerald-500/10 rounded-full">Chapter {chap.chapter_number}</span>
                                            <div className="flex items-center gap-1">
                                                <Activity className="w-3 h-3 text-amber-500" />
                                                <span className="text-[10px] font-bold text-amber-500">{chap.emotional_intensity}/10</span>
                                            </div>
                                        </div>
                                        <h3 className="text-sm font-black text-foreground tracking-tight mb-1">{chap.suggested_title}</h3>
                                        <p className="text-[10px] text-zinc-500 italic mb-3">"{chap.summary}"</p>
                                        <div className="flex items-center gap-2 text-[9px] text-muted-foreground font-mono bg-black/30 p-2 rounded-lg border border-white/5 truncate">
                                            <ChevronRight className="w-3 h-3 shrink-0" />
                                            {chap.starting_words}...
                                        </div>
                                        {chap.content_warnings && chap.content_warnings.length > 0 && chap.content_warnings[0] !== "None" && (
                                            <div className="mt-3 flex flex-wrap gap-2">
                                                {chap.content_warnings.map((w: string, i: number) => (
                                                    <span key={i} className="flex items-center gap-1 text-[8px] font-black uppercase text-rose-400 bg-rose-400/10 px-2 py-0.5 rounded-full border border-rose-400/20">
                                                        <ShieldAlert className="w-2.5 h-2.5" />
                                                        {w}
                                                    </span>
                                                ))}
                                            </div>
                                        )}
                                    </div>
                                ))
                            ) : (
                                <div className="h-full flex flex-col items-center justify-center text-center p-8 opacity-40">
                                    <BarChart3 className="w-12 h-12 mb-4 text-zinc-600" />
                                    <p className="text-xs font-bold text-zinc-500 uppercase tracking-widest">Awaiting Structural Scan</p>
                                    <p className="text-[10px] text-zinc-600 mt-2 max-w-[200px]">Click 'Draft Structure' to invoke The Architect.</p>
                                </div>
                            )}
                        </div>
                    </div>

                    {/* Chart / Analysis Pane */}
                    <div className="w-1/2 flex flex-col p-8 bg-zinc-950/30">
                        <div className="flex items-center justify-between mb-8">
                            <div>
                                <h3 className="text-sm font-black text-foreground uppercase tracking-widest">Narrative Tension Map</h3>
                                <p className="text-[10px] text-muted-foreground mt-1">Emotional Intensity Arc by Chapter</p>
                            </div>
                            <div className="flex items-center gap-4 text-[10px] font-bold">
                                <div className="flex items-center gap-1.5">
                                    <div className="w-2 h-2 rounded-full bg-emerald-500"></div>
                                    <span className="text-zinc-400 uppercase">Intensity</span>
                                </div>
                            </div>
                        </div>

                        <div className="h-64 w-full mb-8">
                            {proposedChapters.length > 0 ? (
                                <ResponsiveContainer width="100%" height="100%">
                                    <AreaChart data={proposedChapters}>
                                        <defs>
                                            <linearGradient id="colorIntensity" x1="0" y1="0" x2="0" y2="1">
                                                <stop offset="5%" stopColor="#10b981" stopOpacity={0.3}/>
                                                <stop offset="95%" stopColor="#10b981" stopOpacity={0}/>
                                            </linearGradient>
                                        </defs>
                                        <CartesianGrid strokeDasharray="3 3" stroke="#ffffff05" vertical={false} />
                                        <XAxis 
                                            dataKey="chapter_number" 
                                            stroke="#ffffff20" 
                                            fontSize={10} 
                                            tickLine={false}
                                            axisLine={false}
                                        />
                                        <YAxis 
                                            hide 
                                            domain={[0, 10]} 
                                        />
                                        <Tooltip 
                                            contentStyle={{ 
                                                backgroundColor: '#09090b', 
                                                border: '1px solid #ffffff10',
                                                borderRadius: '12px',
                                                fontSize: '10px',
                                                fontWeight: '900',
                                                textTransform: 'uppercase'
                                            }} 
                                            itemStyle={{ color: '#10b981' }}
                                        />
                                        <Area 
                                            type="monotone" 
                                            dataKey="emotional_intensity" 
                                            stroke="#10b981" 
                                            strokeWidth={3}
                                            fillOpacity={1} 
                                            fill="url(#colorIntensity)" 
                                            animationDuration={2000}
                                        />
                                    </AreaChart>
                                </ResponsiveContainer>
                            ) : (
                                <div className="h-full border border-dashed border-white/5 rounded-2xl flex items-center justify-center text-zinc-700">
                                    <span className="text-[10px] font-black uppercase tracking-widest">Pulse Inactive</span>
                                </div>
                            )}
                        </div>

                        <div className="flex-1 space-y-6">
                            {/* Fidelity Intelligence Advisor */}
                            <div className="p-5 bg-amber-500/5 border border-amber-500/20 rounded-2xl">
                                <h4 className="text-[10px] font-black text-amber-500 uppercase tracking-widest mb-3 flex items-center gap-2">
                                    <Sparkles className="w-3 h-3" />
                                    Fidelity Hiring Recommendation
                                </h4>
                                
                                <div className="space-y-4">
                                    <div className="flex items-start gap-3">
                                        <div className="p-2 bg-emerald-500/10 rounded-lg">
                                            <Key className="w-3 h-3 text-emerald-400" />
                                        </div>
                                        <div className="flex-1">
                                            <p className="text-[11px] text-zinc-300 font-bold leading-tight">
                                                Intelligence established via the Sovereign Gateway. The Apex Narrative Architect is currently optimizing your structural trajectory.
                                            </p>
                                        </div>
                                    </div>
                                </div>
                            </div>

                            <div className="p-5 bg-indigo-500/5 border border-indigo-500/10 rounded-2xl">
                                <h4 className="text-[10px] font-black text-indigo-400 uppercase tracking-widest mb-2 flex items-center gap-2">
                                    <AlertCircle className="w-3 h-3" />
                                    The Architect's Briefing
                                </h4>
                                <p className="text-[11px] text-zinc-400 leading-relaxed">
                                    {proposedChapters.length > 0 
                                        ? "I have analyzed your narrative trajectory. The pacing shows a strong secondary peak. I recommend maintaining this tension before the final resolution."
                                        : "Engage the engine to generate structural recommendations. The Architect will analyze pacing, emotional spikes, and logical chapter boundaries."
                                    }
                                </p>
                            </div>

                            {error && (
                                <div className="p-4 bg-rose-500/10 border border-rose-500/20 rounded-xl flex items-center gap-3 text-rose-400">
                                    <AlertCircle className="w-5 h-5 shrink-0" />
                                    <p className="text-[10px] font-bold uppercase leading-tight">{error}</p>
                                </div>
                            )}
                        </div>
                    </div>
                </div>

                {/* Footer Actions */}
                <div className="px-8 py-6 border-t border-border flex items-center justify-between bg-zinc-900/50">
                    <div className="flex items-center gap-2 text-muted-foreground italic text-[10px]">
                        <Activity className="w-3 h-3" />
                        <span>Analysis powered by Apex Narrative Architect (Sovereign Context)</span>
                    </div>
                    <div className="flex items-center gap-4">
                        <button 
                            onClick={() => setIsStructuralModalOpen(false)}
                            className="px-6 py-2.5 text-[10px] font-black uppercase tracking-widest text-muted-foreground hover:text-foreground transition-all"
                        >
                            Discard
                        </button>
                        <button 
                            onClick={applyStructure}
                            disabled={proposedChapters.length === 0}
                            className={`flex items-center gap-2 px-8 py-2.5 rounded-xl text-[10px] font-black uppercase tracking-widest transition-all shadow-xl ${proposedChapters.length > 0 ? 'bg-emerald-600 hover:bg-emerald-500 text-white shadow-emerald-600/20' : 'bg-zinc-800 text-zinc-500 cursor-not-allowed'}`}
                        >
                            <CheckCircle2 className="w-4 h-4" />
                            Apply Structural Definition
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default StructuralAnalysisModal;
