"use client";

import React from "react";
import { 
    X, Sparkles, ShieldCheck, Activity, Eye, 
    Zap, Ghost, Layers, TrendingUp, Info, 
    ArrowRight, DollarSign, Clock, Calendar, 
    BarChart2, CheckCircle2, ShieldAlert
} from "lucide-react";
import { useWorkstationState, useWorkstationActions } from "@/context/WorkstationContext";

const ENHANCEMENTS = [
    {
        id: "continuity_sentinel",
        name: "Continuity Sentinel",
        icon: ShieldCheck,
        description: "Background logic monitoring for narrative consistency (eye color, dates, character ages).",
        engine: "GPT-4o",
        rationale: "Deep reasoning and long-term memory retrieval required for logic-fault detection.",
        costPerHour: 0.12,
        costPerWeek: 4.80,
        costPerMonth: 19.20,
        fidelity: "High"
    },
    {
        id: "narrative_heatmap",
        name: "Narrative Heatmap",
        icon: Activity,
        description: "Real-time pacing density and narrative tension visualization in the editor gutter.",
        engine: "Gemini 1.5 Flash",
        rationale: "Low-latency streaming analysis optimized for speed and high-frequency updates.",
        costPerHour: 0.02,
        costPerWeek: 0.80,
        costPerMonth: 3.20,
        fidelity: "Medium"
    },
    {
        id: "style_mirror",
        name: "Style Mirroring",
        icon: Ghost,
        description: "Voice-matched prose suggestions that mirror your specific authorial style.",
        engine: "Claude 3.5 Sonnet",
        rationale: "Unrivaled linguistic nuance and creative prose replication capabilities.",
        costPerHour: 0.25,
        costPerWeek: 10.00,
        costPerMonth: 40.00,
        fidelity: "Extreme"
    },
    {
        id: "autonomous_moodboard",
        name: "Autonomous Moodboarding",
        icon: Layers,
        description: "Automatic visual scene generation and soundscape suggestions as you write.",
        engine: "Gemini 3.1 Pro",
        rationale: "Superior vision-to-language mapping for atmospheric scene translation.",
        costPerHour: 0.15,
        costPerWeek: 6.00,
        costPerMonth: 24.00,
        fidelity: "High"
    },
    {
        id: "boardroom_ocr",
        name: "Boardroom OCR Voting",
        icon: ShieldAlert,
        description: "Multi-model ensemble voting for resolving smudged or illegible manuscript text.",
        engine: "Sovereign Ensemble",
        rationale: "Triple-check validation (Gemini/Claude/GPT) for 99.9% industrial accuracy.",
        costPerHour: 0.08,
        costPerWeek: 3.20,
        costPerMonth: 12.80,
        fidelity: "Industrial"
    },
    {
        id: "dynamic_arc_manipulation",
        name: "Dynamic Arc Manipulation",
        icon: TrendingUp,
        description: "Interactive emotional arc dragging with real-time plot-point recommendations.",
        engine: "Gemini 3.1 Pro",
        rationale: "Large context window allows for structural repositioning of narrative weight.",
        costPerHour: 0.18,
        costPerWeek: 7.20,
        costPerMonth: 28.80,
        fidelity: "High"
    }
];

const AiEnhancementHub = () => {
    const { isEnhancementHubOpen, activeEnhancements } = useWorkstationState();
    const { setIsEnhancementHubOpen, toggleEnhancement, notify } = useWorkstationActions();

    if (!isEnhancementHubOpen) return null;

    const totalMonthlyCost = ENHANCEMENTS
        .filter(e => activeEnhancements.includes(e.id))
        .reduce((sum, e) => sum + e.costPerMonth, 0);

    return (
        <div className="fixed inset-0 z-[1500] flex items-center justify-center p-6 bg-black/70 backdrop-blur-xl animate-in fade-in duration-300">
            <div className="w-full max-w-6xl h-[85vh] bg-surface border border-border shadow-[0_0_100px_rgba(0,0,0,0.6)] rounded-[2.5rem] flex flex-col overflow-hidden relative">
                
                {/* Header */}
                <div className="px-10 py-8 border-b border-border flex items-center justify-between bg-zinc-900/40">
                    <div className="flex items-center gap-5">
                        <div className="p-4 bg-indigo-500/10 rounded-2xl border border-indigo-500/20">
                            <Sparkles className="w-8 h-8 text-indigo-400" />
                        </div>
                        <div>
                            <h2 className="text-2xl font-black text-white uppercase tracking-tighter leading-none">AI Enhancement Hub</h2>
                            <p className="text-[10px] text-zinc-500 font-bold uppercase tracking-widest mt-3 flex items-center gap-2">
                                <ShieldCheck className="w-3 h-3" /> Sovereign Specialist Recruitment & Hiring
                            </p>
                        </div>
                    </div>
                    <button 
                        onClick={() => setIsEnhancementHubOpen(false)}
                        className="p-3 bg-white/5 hover:bg-white/10 rounded-2xl transition-all text-zinc-500 hover:text-white"
                    >
                        <X className="w-6 h-6" />
                    </button>
                </div>

                <div className="flex-1 flex overflow-hidden">
                    {/* Enhancement List */}
                    <div className="flex-1 overflow-y-auto p-10 space-y-6 custom-scrollbar bg-black/20">
                        <div className="grid grid-cols-2 gap-6">
                            {ENHANCEMENTS.map((enh) => {
                                const isActive = activeEnhancements.includes(enh.id);
                                return (
                                    <div 
                                        key={enh.id} 
                                        className={`group relative p-6 rounded-3xl border transition-all duration-500 ${isActive ? 'bg-indigo-500/5 border-indigo-500/30 ring-1 ring-indigo-500/20 shadow-xl' : 'bg-zinc-900/40 border-white/5 hover:border-white/10'}`}
                                    >
                                        <div className="flex items-start justify-between mb-4">
                                            <div className={`p-3 rounded-2xl ${isActive ? 'bg-indigo-500 text-white' : 'bg-black/40 text-zinc-500 group-hover:text-zinc-300'} transition-all`}>
                                                <enh.icon className="w-6 h-6" />
                                            </div>
                                            <div 
                                                onClick={() => {
                                                    toggleEnhancement(enh.id);
                                                    notify(isActive ? `${enh.name} De-selected.` : `${enh.name} Hired.`);
                                                }}
                                                className="flex items-center gap-3 cursor-pointer group/check"
                                            >
                                                <span className={`text-[10px] font-black uppercase tracking-widest ${isActive ? 'text-indigo-400' : 'text-zinc-600'}`}>Hire</span>
                                                <div className={`w-6 h-6 rounded-lg border-2 flex items-center justify-center transition-all ${isActive ? 'bg-indigo-500 border-indigo-400' : 'border-zinc-700 bg-transparent group-hover/check:border-zinc-500'}`}>
                                                    {isActive && <CheckCircle2 className="w-4 h-4 text-white" />}
                                                </div>
                                            </div>
                                        </div>

                                        <h3 className="text-base font-black text-white uppercase tracking-tight mb-2">{enh.name}</h3>
                                        <p className="text-[11px] text-zinc-500 leading-relaxed mb-6 h-10 overflow-hidden line-clamp-2">{enh.description}</p>
                                        
                                        <div className="space-y-4 p-4 bg-black/40 rounded-2xl border border-white/5">
                                            <div className="flex items-center justify-between">
                                                <span className="text-[9px] font-black text-zinc-600 uppercase tracking-widest">Optimal Hire</span>
                                                <span className="text-[10px] font-bold text-indigo-400 uppercase">{enh.engine}</span>
                                            </div>
                                            <div className="flex items-center justify-between">
                                                <span className="text-[9px] font-black text-zinc-600 uppercase tracking-widest">Fidelity Tier</span>
                                                <span className={`text-[10px] font-bold uppercase ${enh.fidelity === 'Extreme' ? 'text-amber-500' : 'text-emerald-500'}`}>{enh.fidelity}</span>
                                            </div>
                                            <div className="pt-3 border-t border-white/5">
                                                <p className="text-[9px] text-zinc-500 leading-tight">
                                                    <span className="font-black text-zinc-400 uppercase tracking-tighter mr-1">Rationale:</span>
                                                    {enh.rationale}
                                                </p>
                                            </div>
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                    </div>

                    {/* Cost & Comparison Panel */}
                    <div className="w-[380px] border-l border-border bg-zinc-950/30 p-10 flex flex-col">
                        <div className="mb-10">
                            <h3 className="text-sm font-black text-white uppercase tracking-widest mb-2 flex items-center gap-2">
                                <DollarSign className="w-4 h-4 text-emerald-500" />
                                Project Cost Projections
                            </h3>
                            <p className="text-[10px] text-zinc-500 uppercase font-bold tracking-tighter">Estimated Token Consumption & Billing</p>
                        </div>

                        <div className="space-y-4 mb-10">
                            <div className="p-5 bg-black/40 border border-white/5 rounded-2xl flex items-center justify-between">
                                <div className="flex items-center gap-3">
                                    <Clock className="w-4 h-4 text-zinc-500" />
                                    <span className="text-[10px] font-black text-zinc-400 uppercase">Hourly Run-Rate</span>
                                </div>
                                <span className="text-sm font-mono font-black text-white">${ENHANCEMENTS.filter(e => activeEnhancements.includes(e.id)).reduce((s, e) => s + e.costPerHour, 0).toFixed(2)}</span>
                            </div>
                            <div className="p-5 bg-black/40 border border-white/5 rounded-2xl flex items-center justify-between">
                                <div className="flex items-center gap-3">
                                    <Calendar className="w-4 h-4 text-zinc-500" />
                                    <span className="text-[10px] font-black text-zinc-400 uppercase">Weekly Retainer</span>
                                </div>
                                <span className="text-sm font-mono font-black text-white">${ENHANCEMENTS.filter(e => activeEnhancements.includes(e.id)).reduce((s, e) => s + e.costPerWeek, 0).toFixed(2)}</span>
                            </div>
                            <div className="p-8 bg-indigo-600/10 border border-indigo-500/30 rounded-3xl flex flex-col items-center justify-center shadow-2xl shadow-indigo-600/10">
                                <span className="text-[10px] font-black text-indigo-400 uppercase tracking-[0.2em] mb-4">Total Monthly Operational Cost</span>
                                <div className="flex items-baseline gap-1">
                                    <span className="text-4xl font-black text-white tracking-tighter">${totalMonthlyCost.toFixed(2)}</span>
                                    <span className="text-xs text-indigo-400/50 font-bold uppercase">USD/mo</span>
                                </div>
                            </div>
                        </div>

                        <div className="flex-1 space-y-6">
                            <div className="p-6 bg-zinc-900/50 border border-white/5 rounded-2xl">
                                <h4 className="text-[10px] font-black text-zinc-400 uppercase tracking-widest mb-4 flex items-center gap-2">
                                    <BarChart2 className="w-3 h-3" /> Hire Comparison
                                </h4>
                                <div className="space-y-3">
                                    <div className="flex items-center justify-between text-[9px] uppercase font-bold">
                                        <span className="text-zinc-600">Flash (Low Cost)</span>
                                        <span className="text-emerald-500">92% Savings</span>
                                    </div>
                                    <div className="w-full h-1 bg-black rounded-full overflow-hidden">
                                        <div className="w-full h-full bg-emerald-500/20" />
                                    </div>
                                    <div className="flex items-center justify-between text-[9px] uppercase font-bold">
                                        <span className="text-zinc-600">Pro (Standard)</span>
                                        <span className="text-amber-500">Balanced Fidelity</span>
                                    </div>
                                    <div className="w-full h-1 bg-black rounded-full overflow-hidden">
                                        <div className="w-[60%] h-full bg-amber-500" />
                                    </div>
                                    <div className="flex items-center justify-between text-[9px] uppercase font-bold">
                                        <span className="text-zinc-600">Elite (Extreme)</span>
                                        <span className="text-rose-500">Peak Performance</span>
                                    </div>
                                    <div className="w-full h-1 bg-black rounded-full overflow-hidden">
                                        <div className="w-[20%] h-full bg-rose-500" />
                                    </div>
                                </div>
                            </div>
                        </div>

                        <div className="mt-auto">
                            <button 
                                onClick={() => setIsEnhancementHubOpen(false)}
                                className="w-full py-4 bg-white/5 hover:bg-white/10 border border-white/10 rounded-2xl text-[11px] font-black uppercase tracking-widest text-zinc-400 hover:text-white transition-all flex items-center justify-center gap-3"
                            >
                                <CheckCircle2 className="w-4 h-4" />
                                Confirm Deployments
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default AiEnhancementHub;
