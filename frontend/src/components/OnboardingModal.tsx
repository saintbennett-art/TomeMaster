"use client";
import React, { useState } from 'react';
import { ShieldCheck, Cpu, Globe, Rocket, Check, ArrowRight, Download, Info } from 'lucide-react';

interface OnboardingModalProps {
    isOpen: boolean;
    onClose: () => void;
}

export default function OnboardingModal({ isOpen, onClose }: OnboardingModalProps) {
    const [step, setStep] = useState(1);
    const [selectedPath, setSelectedPath] = useState<'cloud' | 'sovereign' | null>(null);

    if (!isOpen) return null;

    const handleSelectPath = (path: 'cloud' | 'sovereign') => {
        setSelectedPath(path);
        setStep(2);
    };

    const finalize = () => {
        onClose();
    };

    return (
        <div className="fixed inset-0 z-[100] flex items-center justify-center p-4">
            <div className="absolute inset-0 bg-[#050505]/95 backdrop-blur-md" />
            
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
                                        To run industrial AI locally, establish a connection to your local Sovereign Gateway.
                                    </p>
                                    
                                    <div className="space-y-4 w-full mb-8">
                                        <div className="bg-[#111] border border-[#222] rounded-xl p-4 flex gap-4 items-center">
                                            <div className="w-8 h-8 rounded-full bg-[#222] text-zinc-300 flex items-center justify-center font-bold text-sm">1</div>
                                            <div className="flex-1">
                                                <p className="text-sm font-bold text-white">Initialize Sovereign Engine</p>
                                                <p className="text-xs text-zinc-500">Ensure your local gateway is active and listening for handshakes.</p>
                                            </div>
                                            <div className="p-2 bg-zinc-800 text-zinc-400 rounded-lg">
                                                <Download className="w-4 h-4" />
                                            </div>
                                        </div>
                                        
                                        <div className="bg-[#111] border border-[#222] rounded-xl p-4 flex gap-4 items-center">
                                            <div className="w-8 h-8 rounded-full bg-[#222] text-zinc-300 flex items-center justify-center font-bold text-sm">2</div>
                                            <div className="flex-1">
                                                <p className="text-sm font-bold text-white">Establish Gateway Link</p>
                                                <p className="text-xs text-zinc-500">Enter your local gateway URL in the Discovery Pulse.</p>
                                            </div>
                                            <div className="p-2 text-zinc-600">
                                                <Cpu className="w-4 h-4" />
                                            </div>
                                        </div>

                                        <div className="flex items-start gap-3 p-3 bg-amber-500/5 border border-amber-500/20 rounded-xl">
                                            <Info className="w-5 h-5 text-amber-500 shrink-0 mt-0.5" />
                                            <p className="text-[11px] text-amber-500/80 leading-relaxed">
                                                Sovereign mode requires a dedicated graphics card (GPU) or at least 16GB of RAM for the best experience.
                                            </p>
                                        </div>
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
