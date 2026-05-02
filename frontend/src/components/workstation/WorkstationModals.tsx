"use client";

import React from "react";
import { useWorkstationState, useWorkstationActions } from "@/context/WorkstationContext";
import BoardroomReport from "@/components/BoardroomReport";
import ProjectLedger from "@/components/ProjectLedger";
import { Mic, Sparkles, XCircle, ListOrdered, ShieldCheck, RefreshCw } from "lucide-react";

interface WorkstationModalsProps {
    onApplySuggestion: (suggestion: string) => void;
    isAnalyzing: boolean;
    localAnalysisTrigger: number;
    setLocalAnalysisTrigger: React.Dispatch<React.SetStateAction<number>>;
    isListening: boolean;
    isRefining: boolean;
    isSuperMuseMode: boolean;
    setIsSuperMuseMode: (val: boolean) => void;
    toggleListening: () => void;
}

const WorkstationModals: React.FC<WorkstationModalsProps> = ({
    onApplySuggestion,
    isAnalyzing,
    localAnalysisTrigger,
    setLocalAnalysisTrigger,
    isListening,
    isRefining,
    isSuperMuseMode,
    setIsSuperMuseMode,
    toggleListening
}) => {
    const { 
        isReportOpen, arcData, chapters, agentReports,
        isLedgerOpen, activeFolderPath, isAuditOpen
    } = useWorkstationState();

    // [FIX #4]: Audit-specific local state (not needed globally)
    const [auditPageInput, setAuditPageInput] = React.useState("");
    const [applyOffset, setApplyOffset] = React.useState(false);
    
    const { 
        setIsReportOpen, setIsLedgerOpen, setIsAuditOpen,
        notify 
    } = useWorkstationActions();

    return (
        <>
            <BoardroomReport 
                isOpen={isReportOpen}
                onClose={() => setIsReportOpen(false)}
                arcData={arcData}
                chapters={chapters}
                agentReports={agentReports}
                onApplySuggestion={onApplySuggestion}
                onRegenerate={() => setLocalAnalysisTrigger(v => v + 1)}
                isAnalyzing={isAnalyzing}
            />

            {isLedgerOpen && activeFolderPath && (
                <ProjectLedger 
                    folderPath={activeFolderPath} 
                    onClose={() => setIsLedgerOpen(false)} 
                />
            )}

            {/* [ARCHITECTURE]: AUDIT WORKSPACE MODAL */}
            {isAuditOpen && (
                <div className="fixed inset-0 z-[200] bg-black/95 backdrop-blur-2xl flex flex-col p-8 animate-in fade-in zoom-in duration-300">
                    <div className="flex items-center justify-between mb-8">
                        <div className="flex items-center gap-4">
                            <div className="p-3 bg-indigo-500/10 rounded-2xl border border-indigo-500/20">
                                <ListOrdered className="w-8 h-8 text-indigo-400" />
                            </div>
                            <div>
                                <h2 className="text-3xl font-black text-white tracking-tighter uppercase">Directorial Audit</h2>
                                <p className="text-zinc-500 font-bold uppercase tracking-widest text-[10px] mt-1">Sovereign Pagination Verification & Re-Sorting</p>
                            </div>
                        </div>
                        <button 
                            onClick={() => setIsAuditOpen(false)}
                            className="p-4 bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 rounded-2xl text-zinc-400 hover:text-white transition-all shadow-xl"
                        >
                            <XCircle className="w-8 h-8" />
                        </button>
                    </div>

                    <div className="flex-1 flex gap-8 min-h-0">
                        {/* Audit specific logic would go here - placeholder for now */}
                        <div className="flex-1 bg-zinc-900/50 border border-zinc-800 rounded-3xl flex items-center justify-center p-12">
                            <div className="max-w-md text-center">
                                <ShieldCheck className="w-16 h-16 text-zinc-700 mx-auto mb-6" />
                                <h3 className="text-xl font-bold text-zinc-300 mb-2">Audit Synchronization Active</h3>
                                <p className="text-zinc-500 text-sm mb-8">Verifying logical manuscript sequence against cached directorial state.</p>
                                <button 
                                    className="px-8 py-4 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl font-black text-sm uppercase tracking-widest transition-all"
                                >
                                    Force Full Sync
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            )}

            {/* [ARCHITECTURE]: LISTENING OVERLAY */}
            {isListening && (
                <div className="fixed bottom-24 left-1/2 -translate-x-1/2 z-[150] animate-in fade-in slide-in-from-bottom-4 duration-500">
                    <div className="bg-black/90 backdrop-blur-3xl border border-indigo-500/30 rounded-3xl p-5 shadow-[0_0_60px_rgba(99,102,241,0.2)] flex items-center gap-8">
                        <div className="relative">
                            <div className="w-14 h-14 rounded-full bg-red-500/10 flex items-center justify-center border border-red-500/20">
                                <Mic className={`w-7 h-7 text-red-500 ${isListening ? 'animate-pulse' : ''}`} />
                            </div>
                            {isRefining && (
                                <div className="absolute inset-0 rounded-full border-2 border-indigo-500 animate-ping opacity-60"></div>
                            )}
                        </div>

                        <div className="flex flex-col gap-1">
                            <div className="flex items-center gap-2">
                                <span className="text-[10px] font-black text-white uppercase tracking-[0.2em]">Super Muse Active</span>
                                <div className="w-1.5 h-1.5 rounded-full bg-red-500 animate-pulse"></div>
                            </div>
                            <div className="flex items-center gap-3">
                                <button 
                                    onClick={() => setIsSuperMuseMode(!isSuperMuseMode)}
                                    className={`flex items-center gap-2 px-3 py-1 rounded-full border transition-all duration-300 ${isSuperMuseMode ? 'bg-indigo-500/20 border-indigo-500/40 text-indigo-400' : 'bg-zinc-800 border-zinc-700 text-zinc-500'}`}
                                >
                                    <Sparkles className="w-3 h-3" />
                                    <span className="text-[8px] font-black uppercase tracking-widest">{isSuperMuseMode ? 'Smoothing Active' : 'Raw Input'}</span>
                                </button>
                                {isRefining && (
                                    <span className="text-[9px] font-black text-emerald-400 uppercase animate-pulse tracking-tighter italic">Refining The Author's Voice...</span>
                                )}
                            </div>
                        </div>

                        <button 
                            onClick={toggleListening}
                            className="p-4 bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 rounded-2xl text-zinc-400 hover:text-white transition-all shadow-xl"
                        >
                            <XCircle className="w-6 h-6" />
                        </button>
                    </div>
                </div>
            )}
        </>
    );
};

export default WorkstationModals;
