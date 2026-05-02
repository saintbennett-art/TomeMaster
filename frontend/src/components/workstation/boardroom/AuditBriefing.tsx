"use client";
import React from "react";
import { Activity, Users, Info } from "lucide-react";

export const AuditBriefing = ({ data, onConfirm, onCancel }) => (
    <div className="fixed inset-0 z-[110] flex items-center justify-center p-6 bg-black/80 backdrop-blur-xl animate-in fade-in duration-500">
        <div className="bg-[#0c0c0c] border border-indigo-500/30 rounded-3xl p-8 w-full max-w-2xl shadow-2xl relative overflow-hidden">
            <div className="flex items-center gap-3 mb-6">
                <Activity className="w-6 h-6 text-indigo-400" />
                <h3 className="text-[12px] font-black text-white uppercase tracking-[0.3em]">Logistics Briefing</h3>
            </div>
            <div className="grid grid-cols-2 gap-4 mb-8">
                <div className="bg-zinc-900/50 border border-[#222] p-4 rounded-2xl">
                    <span className="text-[9px] font-black text-zinc-500">Narrative Displacement</span>
                    <span className="text-xl font-mono text-white">{(data.weight / 1000).toFixed(1)}k Words</span>
                </div>
                <div className="bg-indigo-500/5 border border-indigo-500/20 p-4 rounded-2xl">
                    <span className="text-[9px] font-black text-indigo-300">Intelligence Inventory</span>
                    <span className="text-xl font-mono text-indigo-400">{data.assignments.filter(a => a.funded).length} / {data.assignments.length} Ready</span>
                </div>
            </div>
            <div className="flex gap-4">
                <button onClick={onCancel} className="flex-1 py-4 bg-zinc-900 text-zinc-500 rounded-2xl">Abstain</button>
                <button onClick={onConfirm} className="flex-1 py-4 bg-indigo-600 text-white rounded-2xl shadow-lg shadow-indigo-600/20">Exert Multi-Cloud Crunch</button>
            </div>
        </div>
    </div>
);
