"use client";
import React, { useState } from 'react';
import { X, HelpCircle, ChevronDown, ChevronRight, BookOpen, Cpu, Mic, ShieldCheck, Scroll, Star, BarChart3, Activity } from 'lucide-react';

interface AccordionSectionProps {
    title: string;
    icon: React.ElementType;
    isOpen: boolean;
    onToggle: () => void;
    children: React.ReactNode;
}

const AccordionSection = ({ title, icon: Icon, isOpen, onToggle, children }: AccordionSectionProps) => (
    <div className="border-b border-[#2a2a2a] last:border-b-0">
        <button 
            onClick={onToggle}
            className="w-full flex items-center justify-between py-4 px-2 hover:bg-white/5 transition-colors text-left"
        >
            <div className="flex items-center gap-3">
                <div className={`p-2 rounded-lg ${isOpen ? 'bg-indigo-500/20 text-indigo-400' : 'bg-zinc-800 text-zinc-400'}`}>
                    <Icon className="w-4 h-4" />
                </div>
                <span className={`font-semibold text-sm ${isOpen ? 'text-white' : 'text-zinc-300'}`}>{title}</span>
            </div>
            {isOpen ? <ChevronDown className="w-4 h-4 text-zinc-500" /> : <ChevronRight className="w-4 h-4 text-zinc-500" />}
        </button>
        {isOpen && (
            <div className="px-14 pb-6 pt-2 text-sm text-zinc-400 leading-relaxed space-y-4">
                {children}
            </div>
        )}
    </div>
);

interface HelpCenterProps {
    isOpen: boolean;
    onClose: () => void;
}

export default function HelpCenter({ isOpen, onClose }: HelpCenterProps) {
    const [openSection, setOpenSection] = useState<string | null>('getting-started');

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 z-[100] flex items-center justify-center">
            {/* Backdrop */}
            <div className="absolute inset-0 bg-black/80 backdrop-blur-md" onClick={onClose} />
            
            {/* Modal */}
            <div className="relative z-10 w-full max-w-2xl bg-[#111] border border-[#2a2a2a] rounded-2xl shadow-2xl flex flex-col max-h-[85vh] overflow-hidden mx-4">
                
                {/* Header */}
                <div className="flex items-center justify-between p-6 border-b border-[#2a2a2a] bg-[#151515]">
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-xl bg-indigo-500/10 flex items-center justify-center border border-indigo-500/20">
                            <HelpCircle className="w-6 h-6 text-indigo-400" />
                        </div>
                        <div>
                            <h2 className="text-xl font-bold text-white leading-tight">Help Center</h2>
                            <p className="text-xs text-zinc-500 font-medium tracking-wide uppercase">Tome-Master Support & Documentation</p>
                        </div>
                    </div>
                    <button onClick={onClose} className="p-2 rounded-lg text-zinc-500 hover:text-white hover:bg-[#222] transition-all">
                        <X className="w-5 h-5" />
                    </button>
                </div>

                {/* Content - Scrollable */}
                <div className="flex-1 overflow-y-auto custom-scrollbar">
                    
                    {/* Engineering Credits Hook */}
                    <div className="p-6 bg-gradient-to-br from-indigo-500/10 via-transparent to-transparent border-b border-[#2a2a2a]">
                         <div className="flex items-start gap-4">
                            <div className="mt-1">
                                <Star className="w-5 h-5 text-amber-400 fill-amber-400/20" />
                            </div>
                            <div>
                                <h3 className="text-sm font-bold text-white mb-2">Platform Credits & Engineering</h3>
                                <p className="text-xs text-zinc-400 italic leading-relaxed">
                                    Designed, Engineered, Programmed and Security Hardened by High Level Software development engines overseen by <strong>Trent Bennett</strong> the President of <strong>Bennett Consulting</strong> since 1992.
                                </p>
                            </div>
                         </div>
                    </div>

                    <div className="p-4">
                        <AccordionSection 
                            title="Getting Started & Setup" 
                            icon={BookOpen}
                            isOpen={openSection === 'getting-started'}
                            onToggle={() => setOpenSection(openSection === 'getting-started' ? null : 'getting-started')}
                        >
                            <p>Tome-Master is a local-first workstation. All your work is stored safely on your machine in a private database (IndexedDB).</p>
                            <div className="bg-[#1a1a1a] p-4 rounded-xl border border-[#222] space-y-3">
                                <p className="text-white font-bold text-xs uppercase tracking-widest">To use the AI Boardroom:</p>
                                <ol className="list-decimal pl-4 space-y-2 text-xs">
                                    <li>Visit <a href="https://aistudio.google.com/app/apikey" target="_blank" className="text-indigo-400 underline">Google AI Studio</a> to get a Gemini 3.1 API Key.</li>
                                    <li>Open <strong>Settings (Gear Icon)</strong> in the sidebar.</li>
                                    <li>Select your provider and paste your key.</li>
                                </ol>
                            </div>
                        </AccordionSection>

                        {/* [SOVEREIGN ENGINE MASTERCLASS] */}
                        <AccordionSection 
                            title="AI Orchestration Masterclass (v8.0)" 
                            icon={Cpu}
                            isOpen={openSection === 'ai-masterclass'}
                            onToggle={() => setOpenSection(openSection === 'ai-masterclass' ? null : 'ai-masterclass')}
                        >
                            <div className="space-y-4">
                                <div>
                                    <h4 className="text-white font-bold text-xs uppercase tracking-widest mb-1 flex items-center gap-2">
                                        <ShieldCheck className="w-3 h-3 text-indigo-400" /> 1. The Handshake Protocol
                                    </h4>
                                    <p className="text-xs leading-relaxed">
                                        Enter your API Key in the Vault (Settings) and click <strong>Test Connection</strong>. A successful handshake instantly populates the active model list for that provider.
                                    </p>
                                </div>

                                <div>
                                    <h4 className="text-white font-bold text-xs uppercase tracking-widest mb-1 flex items-center gap-2">
                                        <Activity className="w-3 h-3 text-emerald-400" /> 2. Mission Alignment
                                    </h4>
                                    <p className="text-xs leading-relaxed mb-2">
                                        Assign your commissioned models to specific tasks:
                                    </p>
                                    <ul className="list-disc pl-4 space-y-1 text-[10px]">
                                        <li><strong>Transcription Lead:</strong> Ocular scanning & OCR (Recommended: <em>Groq Llama-3.2</em>).</li>
                                        <li><strong>Boardroom Lead:</strong> Narrative analysis & logic (Recommended: <em>Gemini 3.1 Pro</em>).</li>
                                        <li><strong>Creative Prose:</strong> Symmetrical style mirroring (Recommended: <em>Claude 3.5 Sonnet</em>).</li>
                                    </ul>
                                </div>

                                <div className="bg-indigo-500/10 p-3 rounded-xl border border-indigo-500/20">
                                    <h4 className="text-indigo-400 font-bold text-xs uppercase tracking-widest mb-1 flex items-center gap-2">
                                        <BarChart3 className="w-3 h-3" /> 3. Spectrum Failover
                                    </h4>
                                    <p className="text-[11px] leading-relaxed italic text-zinc-300">
                                        The final defensive layer. Assign a <strong>Fallback Gear</strong> in Settings. If your primary engine (e.g., Groq) hits a rate limit, the system instantly "Shifts Gears" to the fallback (e.g., Gemini Flash) to prevent mission failure.
                                    </p>
                                </div>

                                <p className="text-[10px] text-zinc-500 italic flex items-center gap-2 border-t border-white/5 pt-3">
                                    <Star className="w-3 h-3 text-amber-500" /> Always follow the ⭐ EXPERT CHOICE badges for optimal manuscript resurrection.
                                </p>
                            </div>
                        </AccordionSection>

                        <AccordionSection 
                            title="The AI Boardroom" 
                            icon={Cpu}
                            isOpen={openSection === 'boardroom'}
                            onToggle={() => setOpenSection(openSection === 'boardroom' ? null : 'boardroom')}
                        >
                            <p>The Boardroom features specialized AI agents who critique your narrative structure, pacing, and style.</p>
                            <ul className="space-y-3">
                                <li className="flex gap-2">
                                    <strong className="text-indigo-300 min-w-[120px]">Developmental:</strong>
                                    <span>Analyzes story rhythm and structural integrity.</span>
                                </li>
                                <li className="flex gap-2">
                                    <strong className="text-blue-300 min-w-[120px]">Copy Editor:</strong>
                                    <span>Checks grammar, tone, and prose consistency.</span>
                                </li>
                                <li className="flex gap-2">
                                    <strong className="text-amber-300 min-w-[120px]">Sensitivity:</strong>
                                    <span>Identifies tropes and cultural authenticity.</span>
                                </li>
                            </ul>
                        </AccordionSection>

                        <AccordionSection 
                            title="Voice Control & Accessibility" 
                            icon={Mic}
                            isOpen={openSection === 'voice'}
                            onToggle={() => setOpenSection(openSection === 'voice' ? null : 'voice')}
                        >
                            <p>Tome-Master supports 100% hands-free dictation and system commands.</p>
                            <div className="space-y-4">
                                <div className="p-3 bg-zinc-900 rounded-lg border border-[#222]">
                                    <span className="text-[10px] font-bold text-zinc-500 uppercase block mb-1">Wake Word</span>
                                    <code className="text-indigo-400 text-sm">"Computer..."</code> or <code className="text-indigo-400 text-sm">"System..."</code>
                                </div>
                                <ul className="list-disc pl-4 space-y-1 text-xs">
                                    <li><em>"Computer, Run Analysis"</em> — Triggers agents.</li>
                                    <li><em>"Computer, Magic Wand"</em> — Instantly syncs TOC.</li>
                                    <li><em>"Computer, Export PDF"</em> — Begins download.</li>
                                </ul>
                            </div>
                        </AccordionSection>

                        <AccordionSection 
                            title="Security & Data Sovereignty" 
                            icon={ShieldCheck}
                            isOpen={openSection === 'security'}
                            onToggle={() => setOpenSection(openSection === 'security' ? null : 'security')}
                        >
                            <p>Your Creative Intellectual Property is protected by our local-first architecture.</p>
                            <ul className="list-disc pl-4 space-y-2">
                                <li><strong>No Cloud Storage:</strong> Manuscripts are not stored on our servers.</li>
                                <li><strong>In-Memory Processing:</strong> AI analysis is performed in volatile RAM and purged instantly.</li>
                                <li><strong>Local Data Vault:</strong> All drafts are saved on your physical hardware only.</li>
                            </ul>
                        </AccordionSection>

                        <AccordionSection 
                            title="Budget & Expenditure Tracking" 
                            icon={BarChart3}
                            isOpen={openSection === 'accounting'}
                            onToggle={() => setOpenSection(openSection === 'accounting' ? null : 'accounting')}
                        >
                            <p>Tome-Master provides real-time estimates of your AI expenditure calculated directly from your local token logs.</p>
                            <div className="space-y-4">
                                <div className="p-3 bg-zinc-900 rounded-lg border border-[#222]">
                                    <span className="text-xs font-bold text-white block mb-1">Local Fidelity</span>
                                    <p className="text-[11px] text-zinc-300 leading-relaxed font-medium">
                                        Since providers do not expose financial balances via inference keys, Tome-Master subtracts your actual token consumption from your <strong>Starting Balance</strong> to provide a high-fidelity estimate of remaining funds.
                                    </p>
                                </div>
                                <ul className="list-disc pl-4 space-y-1 text-xs">
                                    <li><strong>Starting Balance:</strong> Enter your current provider credit amount in Settings.</li>
                                    <li><strong>Precision:</strong> Costs are calculated based on current industry-standard rates.</li>
                                    <li><strong>Privacy:</strong> Your financial settings are stored 100% locally in your browser.</li>
                                </ul>
                            </div>
                        </AccordionSection>

                        <AccordionSection 
                            title="Manuscript Typography Standards" 
                            icon={Star}
                            isOpen={openSection === 'typography'}
                            onToggle={() => setOpenSection(openSection === 'typography' ? null : 'typography')}
                        >
                            <p>Tome-Master enforces professional publishing standards to ensure your work is ready for submission to agents and editors.</p>
                            <div className="space-y-4">
                                <div className="p-3 bg-zinc-900 rounded-lg border border-[#222]">
                                    <span className="text-xs font-bold text-white block mb-1">Standard Ordinals (16th, 21st)</span>
                                    <p className="text-[11px] text-zinc-300 font-medium leading-relaxed">
                                        Following the <strong>Chicago Manual of Style (CMS 9.6)</strong>, ordinals are kept "flat" on the line. Automatic superscripting is a word-processor artifact that most professional publishers prefer to avoid for clean, even line spacing.
                                    </p>
                                </div>
                                <ul className="list-disc pl-4 space-y-1 text-xs">
                                    <li><strong>Smart Quotes:</strong> Automatically converted to "curly" variants.</li>
                                    <li><strong>Em-Dashes:</strong> Use two hyphens (--) to auto-convert to an em-dash (—).</li>
                                    <li><strong>Ellipses:</strong> Standardized for professional spacing.</li>
                                </ul>
                            </div>
                        </AccordionSection>

                        <AccordionSection 
                            title="Troubleshooting & Engineering Diagnostics" 
                            icon={Activity}
                            isOpen={openSection === 'troubleshooting'}
                            onToggle={() => setOpenSection(openSection === 'troubleshooting' ? null : 'troubleshooting')}
                        >
                            <p>Tome-Master includes real-time system health monitoring via the **Sidebar Pulse Icons** (Top Right).</p>
                            <div className="space-y-4">
                                <div className="p-3 bg-zinc-900 rounded-lg border border-[#222]">
                                    <div className="flex items-center gap-2 mb-2">
                                        <div className="w-2 h-2 rounded-full bg-rose-500" />
                                        <span className="text-xs font-bold text-white uppercase">Backend Engine Offline</span>
                                    </div>
                                    <p className="text-[11px] text-zinc-400 leading-relaxed italic">
                                        Cause: The local Python server has stopped or been blocked.<br/>
                                        <strong>Fix:</strong> Ensure the Tome-Master terminal window is open and active. If using the Desktop App, check your firewall for Port 8080.
                                    </p>
                                </div>
                                <div className="p-3 bg-zinc-900 rounded-lg border border-[#222]">
                                    <div className="flex items-center gap-2 mb-2">
                                        <div className="w-2 h-2 rounded-full bg-amber-500" />
                                        <span className="text-xs font-bold text-white uppercase">Intelligence Vault Empty</span>
                                    </div>
                                    <p className="text-[11px] text-zinc-400 leading-relaxed italic">
                                        Cause: No API keys detected in your local storage.<br/>
                                        <strong>Fix:</strong> Open Settings (Gear Icon) and provide a key for your preferred provider.
                                    </p>
                                </div>
                                <div className="p-3 bg-zinc-900 rounded-lg border border-[#222]">
                                    <div className="flex items-center gap-2 mb-2">
                                        <div className="w-2 h-2 rounded-full bg-indigo-500" />
                                        <span className="text-xs font-bold text-white uppercase">Handshake Timeout</span>
                                    </div>
                                    <p className="text-[11px] text-zinc-400 leading-relaxed italic">
                                        Cause: AI provider took too long to respond (25s+).<br/>
                                        <strong>Fix:</strong> Contact the Sovereign Liaison (Shield Icon) for a Diagnostic Pulse or verify your internet stability.
                                    </p>
                                </div>
                            </div>
                        </AccordionSection>

                        <AccordionSection 
                            title="Advanced Publishing Control" 
                            icon={Scroll}
                            isOpen={openSection === 'publishing'}
                            onToggle={() => setOpenSection(openSection === 'publishing' ? null : 'publishing')}
                        >
                            <p>Finalize your manuscript using industry-standard formatting.</p>
                            <div className="grid grid-cols-2 gap-3">
                                <div className="p-3 bg-zinc-900 rounded-lg border border-[#222]">
                                    <span className="text-xs font-bold text-white block mb-1">DOCX</span>
                                    <span className="text-[10px] text-zinc-500 leading-tight">High-quality Chicago Manual of Style submission format.</span>
                                </div>
                                <div className="p-3 bg-zinc-900 rounded-lg border border-[#222]">
                                    <span className="text-xs font-bold text-white block mb-1">EPUB</span>
                                    <span className="text-[10px] text-zinc-500 leading-tight">Kindle-ready with embedded metadata and artwork.</span>
                                </div>
                            </div>
                        </AccordionSection>
                    </div>
                </div>

                {/* Footer Credits */}
                <div className="p-4 border-t border-[#2a2a2a] bg-[#0c0c0c] flex items-center justify-between">
                    <span className="text-[10px] text-zinc-600 font-mono">Build: TM-2026-XQ9-ULTRA</span>
                    <span className="text-[10px] text-zinc-500 font-bold uppercase tracking-tighter">© 2026 Bennett Consulting</span>
                </div>
            </div>
        </div>
    );
}
