"use client";
import React from "react";
import { Activity, Clock } from "lucide-react";

export const IntelligencePulse = ({ isAnalyzing, elapsedSeconds, pulseData }) => {
    if (!isAnalyzing) return null;
    return (
        <div className="p-4 bg-black/40 border border-indigo-500/20 rounded-2xl space-y-3 animate-in fade-in duration-500">
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                    <Activity className="w-3 h-3 text-indigo-400 animate-pulse" />
                    <span className="text-[9px] font-black text-indigo-400 uppercase tracking-widest">Active Intelligence Cycle</span>
                </div>
                <div className="flex items-center gap-1.5">
                    <Clock className="w-3 h-3 text-zinc-600" />
                    <span className="text-[10px] font-mono text-zinc-400">{Math.floor(elapsedSeconds / 60)}m {elapsedSeconds % 60}s</span>
                </div>
            </div>
            <div className="space-y-1">
                {Object.entries(pulseData).map(([persona, data]: [any, any]) => (
                    <div key={persona} className="flex items-center justify-between text-[8px] font-bold uppercase tracking-tighter">
                        <span className="text-zinc-500">{persona}</span>
                        <span className="text-emerald-500">{data.status}</span>
                    </div>
                ))}
            </div>
        </div>
    );
};
