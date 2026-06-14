"use client";
import React, { useState, useEffect, useCallback } from 'react';
import { ShieldCheck, Cpu, Globe, Rocket, Check, ArrowRight, Download, Info, Eye, RefreshCw, Loader2, ExternalLink, AlertTriangle } from 'lucide-react';
import { fetchLocalEngines, type LocalEngine } from '../lib/apiClient';
import { isVisionModel } from '../lib/ai_config';

interface OnboardingModalProps {
    isOpen: boolean;
    onClose: () => void;
}

function CmdRow({ cmd }: { cmd: string }) {
    return (
        <code className="block w-full bg-black/60 border border-[#222] rounded-lg px-3 py-2 text-[11px] text-emerald-300 font-mono select-all my-1 break-all">
            {cmd}
        </code>
    );
}

/** Explicit, capability-annotated local-engine install guide (shown when the
 *  Sovereign path lacks the engines/models needed to run all AI features). */
function SovereignInstallGuide({ hasEngine, hasVision }: { hasEngine: boolean; hasVision: boolean }) {
    return (
        <div className="space-y-4">
            {!hasEngine && (
                <div className="p-4 bg-amber-500/5 border border-amber-500/20 rounded-xl">
                    <p className="text-sm font-bold text-amber-400 flex items-center gap-2 mb-1">
                        <AlertTriangle className="w-4 h-4" /> No local engine detected
                    </p>
                    <p className="text-[12px] text-zinc-400 mb-3">
                        Sovereign mode needs a local model server. <span className="text-white font-bold">Ollama</span> is the simplest — free, one installer.
                    </p>
                    <a href="https://ollama.com/download" target="_blank" rel="noopener noreferrer"
                        className="inline-flex items-center gap-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-500 rounded-lg text-white text-[11px] font-bold transition-all">
                        <Download className="w-3.5 h-3.5" /> Install Ollama <ExternalLink className="w-3 h-3" />
                    </a>
                    <p className="text-[10px] text-zinc-600 mt-2">After installing, it runs on <code className="text-zinc-400">localhost:11434</code>. Pull the models below, then press Rescan.</p>
                </div>
            )}

            {/* VISION model — required for OCR/transcription */}
            <div className="p-4 bg-[#111] border border-[#222] rounded-xl">
                <p className="text-sm font-bold text-white flex items-center gap-2 mb-1">
                    <Eye className="w-4 h-4 text-indigo-400" /> Transcription / OCR — needs a VISION model
                    {hasVision && <span className="text-emerald-400 text-[10px] uppercase">✓ present</span>}
                </p>
                <p className="text-[12px] text-zinc-400 mb-2">
                    OCR must <span className="text-white">see</span> the page — a text-only model physically can't transcribe a scan. Choose by hardware:
                </p>
                <p className="text-[10px] text-zinc-500">• Light (~1.8B, fast, basic OCR for clean print):</p>
                <CmdRow cmd="ollama pull moondream" />
                <p className="text-[10px] text-zinc-500 mt-2">• Standard (~7B, better quality, ~8GB RAM/VRAM):</p>
                <CmdRow cmd="ollama pull llava" />
                <div className="flex flex-wrap gap-3 mt-2">
                    <a href="https://ollama.com/library/moondream" target="_blank" rel="noopener noreferrer" className="text-[10px] text-indigo-400 hover:text-indigo-300 inline-flex items-center gap-1">moondream <ExternalLink className="w-2.5 h-2.5" /></a>
                    <a href="https://ollama.com/library/llava" target="_blank" rel="noopener noreferrer" className="text-[10px] text-indigo-400 hover:text-indigo-300 inline-flex items-center gap-1">llava <ExternalLink className="w-2.5 h-2.5" /></a>
                    <a href="https://ollama.com/search?c=vision" target="_blank" rel="noopener noreferrer" className="text-[10px] text-indigo-400 hover:text-indigo-300 inline-flex items-center gap-1">all vision models <ExternalLink className="w-2.5 h-2.5" /></a>
                </div>
            </div>

            {/* TEXT model — analysis / editing / boardroom */}
            <div className="p-4 bg-[#111] border border-[#222] rounded-xl">
                <p className="text-sm font-bold text-white flex items-center gap-2 mb-1">
                    <Cpu className="w-4 h-4 text-sky-400" /> Analysis / editing / boardroom — a TEXT model
                </p>
                <p className="text-[12px] text-zinc-400 mb-2">Powers structure, grammar, and the boardroom specialists.</p>
                <p className="text-[10px] text-zinc-500">• Light (~2B):</p>
                <CmdRow cmd="ollama pull gemma2:2b" />
                <p className="text-[10px] text-zinc-500 mt-2">• Standard (~8B, stronger reasoning):</p>
                <CmdRow cmd="ollama pull llama3.1" />
                <a href="https://ollama.com/library" target="_blank" rel="noopener noreferrer" className="text-[10px] text-sky-400 hover:text-sky-300 inline-flex items-center gap-1 mt-2">browse the full model library <ExternalLink className="w-2.5 h-2.5" /></a>
            </div>

            {/* Hardware reality */}
            <div className="flex items-start gap-3 p-3 bg-amber-500/5 border border-amber-500/20 rounded-xl">
                <Info className="w-5 h-5 text-amber-500 shrink-0 mt-0.5" />
                <p className="text-[11px] text-amber-500/80 leading-relaxed">
                    Hardware: text-only roles run on ~8&nbsp;GB RAM; vision/OCR wants ~12–16&nbsp;GB RAM or a GPU with 4–8&nbsp;GB VRAM (a GPU is dramatically faster). CPU-only works but is slow per page. Full tiers in <span className="text-amber-400 font-mono">LOCAL_SOVEREIGNTY.md</span>.
                </p>
            </div>
        </div>
    );
}

export default function OnboardingModal({ isOpen, onClose }: OnboardingModalProps) {
    const [step, setStep] = useState(1);
    const [selectedPath, setSelectedPath] = useState<'cloud' | 'sovereign' | null>(null);

    // [SOVEREIGN READINESS]: live local-engine detection for the Sovereign path
    const [engines, setEngines] = useState<LocalEngine[]>([]);
    const [scanState, setScanState] = useState<'idle' | 'scanning' | 'done'>('idle');

    const scanEngines = useCallback(async () => {
        setScanState('scanning');
        const found = await fetchLocalEngines();
        setEngines(found);
        setScanState('done');
    }, []);

    // Auto-scan when the user lands on the Sovereign setup step.
    useEffect(() => {
        if (isOpen && step === 2 && selectedPath === 'sovereign') {
            scanEngines();
        }
    }, [isOpen, step, selectedPath, scanEngines]);

    if (!isOpen) return null;

    // Readiness: OCR needs a vision model; other AI needs any (text) model.
    const allModels = engines.flatMap(e => e.models);
    const hasEngine = engines.length > 0;
    const hasVision = allModels.some(m => isVisionModel(m));
    const hasText = allModels.length > 0;
    const sovereignReady = hasEngine && hasVision && hasText;

    const handleSelectPath = (path: 'cloud' | 'sovereign') => {
        setSelectedPath(path);
        setStep(2);
    };

    const finalize = () => {
        // Persist the chosen path so the app actually runs in that mode.
        if (selectedPath === 'sovereign') localStorage.setItem('tome_master_local_mode', 'true');
        else if (selectedPath === 'cloud') localStorage.setItem('tome_master_local_mode', 'false');
        onClose();
    };

    return (
        <div className="fixed inset-0 z-[300] flex items-center justify-center p-4">
            {/* Opaque, above the Nerve Center (z-150) + Agent Manager bars so they
                never hover over the path-choice page. */}
            <div className="absolute inset-0 bg-[#050505] backdrop-blur-md" />
            
            <div className="relative z-10 w-full max-w-2xl bg-[#0a0a0a] border border-[#222] rounded-3xl shadow-2xl overflow-hidden animate-in fade-in zoom-in duration-300">
                
                {/* Visual Accent */}
                <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-indigo-500 via-sky-500 to-emerald-500" />
                
                <div className="p-8 md:p-12">
                    {step === 1 ? (
                        <div className="flex flex-col items-center text-center">
                            <div className="w-20 h-20 bg-indigo-500/10 rounded-2xl flex items-center justify-center mb-6 border border-indigo-500/20">
                                <Rocket className="w-10 h-10 text-indigo-400" />
                            </div>
                            
                            <h1 className="text-3xl md:text-4xl font-black text-white mb-4 tracking-tight">Choose Your Writing Path</h1>
                            <p className="text-zinc-400 text-lg mb-10 max-w-lg leading-relaxed">
                                Welcome to <span className="text-white font-bold">Tome-Master</span>. Before we open your manuscript, how would you like to power your AI?
                            </p>

                            <div className="grid md:grid-cols-2 gap-6 w-full">
                                {/* Option A: Industrial Gateway */}
                                <button 
                                    onClick={() => handleSelectPath('cloud')}
                                    className="group relative flex flex-col items-start p-6 rounded-2xl border border-[#222] bg-[#111] hover:border-sky-500/40 hover:bg-sky-500/5 transition-all text-left"
                                >
                                    <div className="w-12 h-12 rounded-xl bg-sky-500/10 flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
                                        <Globe className="w-6 h-6 text-sky-400" />
                                    </div>
                                    <h3 className="text-xl font-bold text-white mb-2">Industrial Path</h3>
                                    <p className="text-zinc-500 text-sm leading-relaxed mb-4">
                                        High-velocity deployment. Uses industrial-grade Sovereign Gateways for massive context analysis.
                                    </p>
                                    <div className="mt-auto flex items-center gap-2 text-sky-400 font-bold text-xs uppercase tracking-widest">
                                        Select Industrial Track <ArrowRight className="w-4 h-4" />
                                    </div>
                                </button>

                                {/* Option B: Local Sovereign */}
                                <button 
                                    onClick={() => handleSelectPath('sovereign')}
                                    className="group relative flex flex-col items-start p-6 rounded-2xl border border-[#222] bg-[#111] hover:border-emerald-500/40 hover:bg-emerald-500/5 transition-all text-left"
                                >
                                    <div className="w-12 h-12 rounded-xl bg-emerald-500/10 flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
                                        <ShieldCheck className="w-6 h-6 text-emerald-400" />
                                    </div>
                                    <h3 className="text-xl font-bold text-white mb-2">Sovereign Path</h3>
                                    <p className="text-zinc-500 text-sm leading-relaxed mb-4">
                                        100% Private. 100% Offline. Uses local industrial engines. Your manuscript never leaves this machine.
                                    </p>
                                    <div className="mt-auto flex items-center gap-2 text-emerald-400 font-bold text-xs uppercase tracking-widest">
                                        Select Privacy Path <ArrowRight className="w-4 h-4" />
                                    </div>
                                </button>
                            </div>
                        </div>
                    ) : (
                        <div className="flex flex-col items-start">
                            {selectedPath === 'cloud' ? (
                                <>
                                    <h2 className="text-2xl font-bold text-white mb-2">Industrial Path Selected</h2>
                                    <p className="text-zinc-400 mb-8 leading-relaxed">
                                        Establish your links via the Sovereign Gateway Registry to enable Boardroom specialist features.
                                    </p>
                                    <div className="bg-[#111] border border-[#222] rounded-xl p-5 mb-8 w-full">
                                        <ul className="space-y-3">
                                            <li className="flex items-start gap-3 text-sm text-zinc-300">
                                                <Check className="w-5 h-5 text-emerald-500 shrink-0" />
                                                <span>Access to high-fidelity Apex Gateways</span>
                                            </li>
                                            <li className="flex items-start gap-3 text-sm text-zinc-300">
                                                <Check className="w-5 h-5 text-emerald-500 shrink-0" />
                                                <span>Industrial-grade multi-agent orchestration</span>
                                            </li>
                                            <li className="flex items-start gap-3 text-sm text-zinc-300">
                                                <Check className="w-5 h-5 text-emerald-500 shrink-0" />
                                                <span>Secure credential-based handshakes</span>
                                            </li>
                                        </ul>
                                    </div>
                                </>
                            ) : (
                                <>
                                    <h2 className="text-2xl font-bold text-white mb-2 flex items-center gap-3">
                                        <ShieldCheck className="w-7 h-7 text-emerald-400" />
                                        Sovereign Mode Setup
                                    </h2>
                                    <p className="text-zinc-400 mb-6 leading-relaxed">
                                        Sovereign mode runs every AI role on a local engine — your manuscript never leaves this machine. Let's confirm the engines for transcription (OCR) and analysis are present.
                                    </p>

                                    <div className="w-full mb-8 max-h-[46vh] overflow-y-auto custom-scrollbar pr-1">
                                        <div className="flex items-center justify-between mb-3">
                                            <span className="text-[10px] font-black text-zinc-500 uppercase tracking-widest">Local Engine Scan</span>
                                            <button onClick={scanEngines} disabled={scanState === 'scanning'}
                                                className="flex items-center gap-1.5 px-3 py-1.5 bg-[#111] border border-[#222] rounded-lg text-[9px] font-black uppercase tracking-widest text-zinc-400 hover:text-white hover:border-white/15 transition-all">
                                                {scanState === 'scanning' ? <Loader2 size={10} className="animate-spin" /> : <RefreshCw size={10} />}
                                                {scanState === 'scanning' ? 'Scanning' : 'Rescan'}
                                            </button>
                                        </div>

                                        {scanState === 'scanning' ? (
                                            <div className="p-4 bg-[#111] border border-[#222] rounded-xl text-[12px] text-zinc-500">Scanning localhost for engines…</div>
                                        ) : sovereignReady ? (
                                            <div className="p-4 bg-emerald-500/5 border border-emerald-500/20 rounded-xl">
                                                <p className="text-sm font-bold text-emerald-400 flex items-center gap-2 mb-2"><Check className="w-4 h-4" /> Sovereign engines ready — all AI features can run locally</p>
                                                {engines.map(e => (
                                                    <div key={e.base} className="text-[11px] text-zinc-400 mb-1">
                                                        <span className="text-emerald-300 font-bold uppercase">{e.name}</span> — {e.models.length} model(s)
                                                        {e.models.some(isVisionModel) && <span className="ml-2 text-emerald-400">✓ vision / OCR</span>}
                                                    </div>
                                                ))}
                                            </div>
                                        ) : (
                                            <SovereignInstallGuide hasEngine={hasEngine} hasVision={hasVision} />
                                        )}
                                    </div>
                                </>
                            )}

                            <div className="flex w-full gap-4">
                                <button 
                                    onClick={() => setStep(1)}
                                    className="flex-1 py-4 px-6 rounded-2xl border border-[#222] text-zinc-400 font-bold hover:bg-[#151515] transition-all"
                                >
                                    Go Back
                                </button>
                                <button 
                                    onClick={finalize}
                                    className={`flex-[2] py-4 px-6 rounded-2xl font-bold text-white transition-all shadow-xl shadow-indigo-500/10 ${selectedPath === 'cloud' ? 'bg-sky-600 hover:bg-sky-500' : 'bg-emerald-600 hover:bg-emerald-500'}`}
                                >
                                    Activate {selectedPath === 'cloud' ? 'Cloud Path' : 'Sovereign Path'}
                                </button>
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
