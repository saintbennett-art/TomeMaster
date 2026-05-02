"use client";
import { X, Globe, ShieldCheck, Zap, Info, FileText, Camera } from "lucide-react";

interface CloudServiceGateProps {
    isOpen: boolean;
    onClose: () => void;
    onConfirm: () => void;
    featureName: string;
}

export default function CloudServiceGate({ isOpen, onClose, onConfirm, featureName }: CloudServiceGateProps) {
    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 z-[200] flex items-center justify-center p-6">
            {/* Backdrop */}
            <div className="absolute inset-0 bg-black/80 backdrop-blur-md" onClick={onClose} />
            
            {/* Modal */}
            <div className="relative z-10 w-full max-w-lg bg-[#111] border border-[#2a2a2a] rounded-2xl shadow-2xl overflow-hidden flex flex-col animate-in fade-in zoom-in duration-300">
                
                {/* Header Gradient */}
                <div className="h-1.5 bg-gradient-to-r from-indigo-600 via-purple-600 to-indigo-600 w-full animate-pulse" />
                
                <div className="p-8">
                    <div className="flex items-center justify-between mb-6">
                        <div className="flex items-center gap-3">
                            <div className="p-2 bg-indigo-500/10 rounded-lg border border-indigo-500/20">
                                <Globe className="w-6 h-6 text-indigo-400" />
                            </div>
                            <div>
                                <h2 className="text-xl font-bold text-white tracking-tight">Internet Access Required</h2>
                                <p className="text-xs text-zinc-500 uppercase tracking-widest mt-1 font-semibold">{featureName} Service</p>
                            </div>
                        </div>
                        <button onClick={onClose} className="p-1.5 rounded-md text-zinc-500 hover:text-white hover:bg-[#222] transition-colors" title="Close modal">
                            <X className="w-5 h-5" />
                        </button>
                    </div>

                    <div className="space-y-6">
                         <div className="flex gap-4">
                            <div className="mt-1 shrink-0"><Zap className="w-5 h-5 text-amber-400" /></div>
                            <div>
                                <h3 className="text-sm font-bold text-zinc-200 mb-1">Why do we need the cloud?</h3>
                                <p className="text-xs text-zinc-500 leading-relaxed">
                                    {featureName.toLowerCase().includes('import') || featureName.toLowerCase().includes('transcribe') 
                                        ? "Precision OCR & Handwriting Analysis requires advanced Vision transformers that currently live in the cloud to ensure your original annotations are captured accurately."
                                        : "Deep Multi-Agent Critique uses high-parameter agents to analyze pace, structure, and demographic tropes — a process that requires extensive compute."
                                    }
                                </p>
                            </div>
                         </div>

                         <div className="flex gap-4">
                            <div className="mt-1 shrink-0"><ShieldCheck className="w-5 h-5 text-emerald-400" /></div>
                            <div>
                                <h3 className="text-sm font-bold text-zinc-200 mb-1">Your Privacy is Protected</h3>
                                <p className="text-xs text-zinc-500 leading-relaxed">
                                    tome_master is local-first. We only transmit text to the cloud for processing. Data is processed in-memory and **instantly purged** once your results are returned. We do not store your manuscript in the cloud.
                                </p>
                            </div>
                         </div>

                         <div className="flex gap-4">
                            <div className="mt-1 shrink-0"><Info className="w-5 h-5 text-indigo-400" /></div>
                            <div>
                                <h3 className="text-sm font-bold text-zinc-200 mb-1">What can I do offline?</h3>
                                <p className="text-xs text-zinc-500 leading-relaxed">
                                    Standard text-based imports (DOCX, TXT), PDF text extraction, and all manual editing features remain **100% Local**. Only Cloud AI features are currently locked.
                                </p>
                            </div>
                         </div>
                    </div>

                    <div className="mt-10 flex flex-col gap-3">
                        <button 
                            onClick={onConfirm}
                            className="w-full py-3.5 bg-indigo-600 hover:bg-indigo-500 text-white font-bold rounded-xl transition-all shadow-lg shadow-indigo-500/20 active:scale-[0.98] flex items-center justify-center gap-2"
                        >
                            <Globe className="w-4 h-4" />
                            Turn ON Internet & Continue
                        </button>
                        <button 
                            onClick={onClose}
                            className="w-full py-3.5 border border-[#333] hover:bg-[#1a1a1a] text-zinc-400 hover:text-white font-semibold rounded-xl transition-all active:scale-[0.98]"
                        >
                            Cancel & Stay Offline
                        </button>
                    </div>
                    
                    <p className="text-[10px] text-zinc-600 text-center mt-4 italic">
                        By enabling internet access, you confirm you agree to temporary cloud processing as outlined in your local-first agreement.
                    </p>
                </div>
            </div>
        </div>
    );
}

