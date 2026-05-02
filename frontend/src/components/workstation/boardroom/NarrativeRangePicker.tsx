"use client";
import React from "react";
import { BookOpen, Layers } from "lucide-react";

export const NarrativeRangePicker = ({ 
    analyticScope, setAnalyticScope, userChapters, 
    rangeStartIdx, setRangeStartIdx, rangeEndIdx, setRangeEndIdx, 
    visibilityMap, displacement, tacticalSummary 
}) => {
    return (
        <div className="space-y-4">
            <div className="flex items-center justify-between px-1">
                <h4 className="text-[10px] font-black text-zinc-500 uppercase tracking-widest">Narrative Scope</h4>
                <div className="flex bg-black/40 p-1 rounded-lg border border-white/5">
                    <button 
                        onClick={() => setAnalyticScope("full")} 
                        className={`px-3 py-1 text-[8px] font-black uppercase rounded-md transition-all ${analyticScope === "full" ? "bg-indigo-500 text-white" : "text-zinc-600 hover:text-zinc-400"}`}
                    >
                        Full
                    </button>
                    <button 
                        onClick={() => setAnalyticScope("range")} 
                        className={`px-3 py-1 text-[8px] font-black uppercase rounded-md transition-all ${analyticScope === "range" ? "bg-indigo-500 text-white" : "text-zinc-600 hover:text-zinc-400"}`}
                    >
                        Range
                    </button>
                </div>
            </div>

            {analyticScope === "range" && (
                <div className="grid grid-cols-2 gap-3 p-4 bg-indigo-500/5 border border-indigo-500/10 rounded-2xl animate-in zoom-in-95 duration-300">
                    <div>
                        <span className="text-[8px] font-black text-indigo-400 uppercase tracking-widest block mb-2">Entry Point</span>
                        <select 
                            value={rangeStartIdx} 
                            onChange={(e) => setRangeStartIdx(Number(e.target.value))} 
                            className="w-full bg-black/60 border border-white/5 rounded-xl py-2 px-3 text-[10px] text-zinc-300 font-bold focus:border-indigo-500/30 outline-none"
                        >
                            {userChapters.map((c, i) => (
                                <option key={c.id} value={i} disabled={!visibilityMap.get(c.id)}>{c.suggested_title || `Chapter ${i+1}`}</option>
                            ))}
                        </select>
                    </div>
                    <div>
                        <span className="text-[8px] font-black text-indigo-400 uppercase tracking-widest block mb-2">Exit Point</span>
                        <select 
                            value={rangeEndIdx} 
                            onChange={(e) => setRangeEndIdx(Number(e.target.value))} 
                            className="w-full bg-black/60 border border-white/5 rounded-xl py-2 px-3 text-[10px] text-zinc-300 font-bold focus:border-indigo-500/30 outline-none"
                        >
                            {userChapters.map((c, i) => (
                                <option key={c.id} value={i} disabled={i < rangeStartIdx || !visibilityMap.get(c.id)}>{c.suggested_title || `Chapter ${i+1}`}</option>
                            ))}
                        </select>
                    </div>
                </div>
            )}

            <div className="p-4 bg-black/20 border border-white/5 rounded-2xl flex items-center justify-between">
                <div className="flex flex-col">
                    <span className="text-[8px] font-black text-zinc-600 uppercase tracking-[0.2em] mb-1">Payload Weight</span>
                    <span className="text-xs font-mono text-white">{(displacement / 1000).toFixed(1)}k <span className="text-[10px] text-zinc-600 uppercase">Words</span></span>
                </div>
                <div className="text-right">
                    <span className="text-[8px] font-black text-zinc-600 uppercase tracking-[0.2em] mb-1">Targeting</span>
                    <span className="text-[9px] font-bold text-indigo-400 uppercase truncate max-w-[120px] block">{tacticalSummary}</span>
                </div>
            </div>
        </div>
    );
};
