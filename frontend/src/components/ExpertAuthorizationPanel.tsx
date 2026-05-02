"use client";
import React, { useState, useEffect } from 'react';
import { ShieldCheck, Cpu, Zap, X, Terminal, FileCode, Users } from 'lucide-react';

interface ExpertAuthorizationPanelProps {
    isOpen: boolean;
    onClose: () => void;
    onAuthorize: (editedPrompt: string, selectedModel: string) => void;
    onTerminate?: () => void;
    persona: string;
    defaultPrompt: string;
    defaultModel: string;
    availableModels: string[];
}

const ExpertAuthorizationPanel: React.FC<ExpertAuthorizationPanelProps> = ({
    isOpen,
    onClose,
    onAuthorize,
    onTerminate,
    persona,
    defaultPrompt,
    defaultModel,
    availableModels
}) => {
    const [editedPrompt, setEditedPrompt] = useState(defaultPrompt);
    const [selectedModel, setSelectedModel] = useState(defaultModel);

    useEffect(() => {
        if (isOpen) {
            setEditedPrompt(defaultPrompt);
            setSelectedModel(defaultModel);
        }
    }, [defaultPrompt, defaultModel, isOpen]);

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 z-[150] flex items-center justify-center p-4 py-8 pointer-events-auto overflow-hidden">
            <div className="absolute inset-0 bg-black/80 backdrop-blur-md" onClick={onClose} />
            
            <div className="relative w-full max-w-3xl bg-background border border-accent/30 rounded-[2.5rem] shadow-2xl flex flex-col max-h-full overflow-hidden animate-in fade-in zoom-in-95 duration-300 shadow-black">
                <div className="p-8 pb-4 flex items-center justify-between shrink-0 border-b border-border relative">
                    <div className="absolute top-0 left-1/4 right-1/4 h-[1px] bg-gradient-to-r from-transparent via-indigo-500/50 to-transparent" />
                    
                    <div className="flex items-center gap-5">
                        <div className="w-14 h-14 rounded-2xl bg-indigo-500/10 flex items-center justify-center border border-indigo-500/20 shadow-inner">
                            <ShieldCheck className="w-7 h-7 text-indigo-400" />
                        </div>
                        <div>
                            <div className="flex items-center gap-3">
                                <h2 className="text-xl font-black text-foreground uppercase tracking-widest leading-none">Directorial Authorization</h2>
                                <span className="px-3 py-1 rounded-full bg-emerald-500/20 border border-emerald-500/30 text-[10px] font-black text-emerald-400 uppercase tracking-tighter">Handshake Ready</span>
                            </div>
                            <p className="text-[12px] text-muted font-bold uppercase mt-2 tracking-tighter">Specialist: <span className="text-foreground">{persona}</span></p>
                        </div>
                    </div>

                    <button 
                        onClick={onClose}
                        className="p-2 hover:bg-surface-hover rounded-full transition-colors text-muted hover:text-foreground"
                    >
                        <X className="w-5 h-5" />
                    </button>
                </div>

                <div className="p-8 pt-6 flex-1 overflow-hidden flex flex-col gap-6">
                    <div className="flex items-center justify-between p-5 bg-accent/[0.03] border border-accent/10 rounded-2xl">
                        <div className="flex items-center gap-3">
                            <Cpu className="w-5 h-5 text-accent" />
                            <div>
                                <p className="text-[12px] font-black text-accent uppercase tracking-widest">Model Calibration</p>
                                <div className="flex items-center gap-2 mt-1">
                                    <p className="text-[10px] text-muted font-bold uppercase leading-none">Select intelligence tier</p>
                                    <span className="px-1.5 py-0.5 rounded bg-emerald-500/10 border border-emerald-500/20 text-[7px] font-black text-emerald-400 uppercase tracking-widest">⭐ Specialist Optimization Active</span>
                                </div>
                            </div>
                        </div>
                        <select 
                            value={selectedModel}
                            onChange={(e) => setSelectedModel(e.target.value)}
                            className="bg-background border border-border rounded-xl py-2 px-4 text-sm font-mono text-accent outline-none focus:border-accent/50 transition-all cursor-pointer appearance-none min-w-[220px]"
                        >
                            {availableModels.map(m => {
                                let displayName = m.split('/').pop() || m;
                                const isBest = m === defaultModel;
                                
                                // [SOVEREIGN NOMENCLATURE]: Mapping technical IDs to Public Directorial Standards
                                if (displayName.includes('gemini-1.5-pro') || displayName.includes('gemini-2.0-pro') || displayName.includes('gemini-3.1-pro')) {
                                    displayName = 'GEMINI 3.1 PRO (NARRATIVE APEX)';
                                } else if (displayName.includes('gemini-1.5-flash') || displayName.includes('gemini-2.0-flash') || displayName.includes('gemini-3.1-flash')) {
                                    displayName = 'GEMINI 3.1 FLASH (STABILITY OPTIMIZED)';
                                } else if (displayName.includes('claude-3-5-sonnet') || displayName.includes('claude-3.5-sonnet')) {
                                    displayName = 'CLAUDE 3.5 SONNET (PROSE SPECIALIST)';
                                } else if (displayName.includes('claude-3-5-haiku') || displayName.includes('claude-3.5-haiku')) {
                                    displayName = 'CLAUDE 3.5 HAIKU (VELOCITY SPECIALIST)';
                                } else if (displayName.includes('deep-research')) {
                                    displayName = 'DEEP RESEARCH PRO (STRUCTURAL AUDIT)';
                                }

                                if (isBest && !displayName.toLowerCase().includes('mini')) {
                                    displayName = `⭐ [APEX CHOICE] ${displayName}`;
                                }

                                return (
                                    <option key={m} value={m} className={isBest ? 'font-black text-emerald-400' : ''}>
                                        {displayName}
                                    </option>
                                );
                            })}
                        </select>
                    </div>

                    <div className="flex-1 flex flex-col gap-3 min-h-0">
                        <div className="flex items-center justify-between px-2">
                            <div className="flex items-center gap-3">
                                <Terminal className="w-4 h-4 text-muted" />
                                <h3 className="text-[12px] font-black text-muted-foreground uppercase tracking-widest">Specialist Instruction Ledger</h3>
                            </div>
                            <span className="text-[10px] text-muted font-bold uppercase tracking-tighter italic">Read-Write Enabled</span>
                        </div>
                        
                        <div className="flex-1 relative group">
                            <textarea 
                                value={editedPrompt}
                                onChange={(e) => setEditedPrompt(e.target.value)}
                                className="w-full h-full bg-surface/40 border border-border rounded-3xl p-6 text-sm text-foreground font-mono leading-relaxed focus:border-accent/30 outline-none transition-all resize-none bright-scrollbar group-hover:bg-surface/60 shadow-inner"
                                placeholder="Enter specialist instructions..."
                            />
                            <div className="absolute bottom-4 right-6 opacity-40 group-hover:opacity-100 transition-opacity">
                                <div className="flex items-center gap-2 px-3 py-1 bg-surface/80 border border-border rounded-full backdrop-blur-sm">
                                    <FileCode className="w-3.5 h-3.5 text-accent" />
                                    <span className="text-[10px] font-black text-muted uppercase">Tokens: {Math.ceil(editedPrompt.length / 4)}</span>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <div className="p-8 pt-6 bg-surface/30 border-t border-border flex items-center justify-between gap-6">
                    <div className="flex items-center gap-4">
                        <Users className="w-5 h-5 text-muted" />
                        <p className="text-[11px] text-muted-foreground uppercase font-bold leading-tight max-w-[320px]">
                            Dispatching high-fidelity instructions to the <span className="text-foreground">{persona}</span>. Handshake requires directorial sign-off.
                        </p>
                    </div>

                    <div className="flex items-center gap-5">
                        <button 
                            onClick={onClose}
                            className="px-6 py-3 rounded-2xl text-[12px] font-black text-muted uppercase tracking-widest hover:text-foreground transition-all hover:bg-surface-hover"
                            title="Skip this specialist and proceed to the next Handshake"
                        >
                            Veto Specialist
                        </button>
                        {onTerminate && (
                            <button 
                                onClick={onTerminate}
                                className="px-6 py-3 bg-rose-500/10 hover:bg-rose-500/20 text-rose-500 rounded-2xl text-[12px] font-black uppercase tracking-widest transition-all border border-rose-500/20"
                                title="Abort the entire Boardroom convention for troubleshooting"
                            >
                                Terminate All
                            </button>
                        )}
                        <button 
                            onClick={() => onAuthorize(editedPrompt, selectedModel)}
                            className="px-10 py-4 bg-accent hover:bg-emerald-600 text-white rounded-2xl text-[12px] font-black uppercase tracking-[0.2em] shadow-xl shadow-accent/20 transition-all flex items-center gap-2 group active:scale-95"
                        >
                            <Zap className="w-4 h-4 group-hover:fill-current" />
                            Authorize Dispatch
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default ExpertAuthorizationPanel;
