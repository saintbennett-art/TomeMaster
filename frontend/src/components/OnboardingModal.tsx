"use client";
import React, { useState, useEffect, useCallback } from 'react';
import { ShieldCheck, Cpu, Globe, Rocket, Check, ArrowRight, Download, Info, Eye, RefreshCw, Loader2, ExternalLink, AlertTriangle, Gift, KeyRound } from 'lucide-react';
import { fetchLocalEngines, saveVaultToEnv, fetchVaultSync, type LocalEngine } from '../lib/apiClient';
import { isVisionModel, MASTER_PROVIDER_LIBRARY, type Provider } from '../lib/ai_config';
import { setPref } from '../lib/preferences';

interface OnboardingModalProps {
    isOpen: boolean;
    onClose: () => void;
}

type Path = 'free' | 'premium' | 'sovereign';

const GEMINI = MASTER_PROVIDER_LIBRARY.find(p => p.id === 'gemini')!;
const PAID_PROVIDERS = MASTER_PROVIDER_LIBRARY.filter(p => ['openai', 'anthropic', 'groq'].includes(p.id));

function CmdRow({ cmd }: { cmd: string }) {
    return (
        <code className="block w-full bg-black/60 border border-[#222] rounded-lg px-3 py-2 text-[11px] text-emerald-300 font-mono select-all my-1 break-all">
            {cmd}
        </code>
    );
}

/** Inline key entry: get-key link + masked input + Save, writing straight to the
 *  encrypted vault. Shows a sealed state for keys already configured. */
function ProviderKeyRow({ provider, sealed, onSaved, onChange }: { provider: Provider; sealed: boolean; onSaved: (id: string) => void; onChange: (id: string, value: string) => void }) {
    const [val, setVal] = useState('');
    const [state, setState] = useState<'idle' | 'saving' | 'saved' | 'error'>(sealed ? 'saved' : 'idle');
    const [msg, setMsg] = useState('');

    const setValue = (v: string) => { setVal(v); onChange(provider.id, v); };

    const save = async () => {
        const k = val.trim();
        if (!k) return;
        setState('saving'); setMsg('');
        const ok = await saveVaultToEnv({ [provider.id]: k });
        if (ok) { setState('saved'); setVal(''); onChange(provider.id, ''); onSaved(provider.id); }
        else { setState('error'); setMsg('Save failed — re-check the key.'); }
    };

    return (
        <div className="p-3 bg-black/30 border border-white/5 rounded-xl">
            <div className="flex items-center justify-between mb-2">
                <span className={`text-[11px] font-black uppercase tracking-widest ${provider.color}`}>{provider.name}</span>
                <a href={provider.link} target="_blank" rel="noopener noreferrer"
                    className="inline-flex items-center gap-1 text-[10px] text-indigo-400 hover:text-indigo-300 font-bold">
                    {provider.linkLabel} <ExternalLink className="w-2.5 h-2.5" />
                </a>
            </div>
            {state === 'saved' ? (
                <div className="flex items-center justify-between gap-2">
                    <span className="text-[11px] text-emerald-400 font-bold flex items-center gap-1.5">
                        <Check className="w-3.5 h-3.5" /> Key saved — ready to use
                    </span>
                    <button onClick={() => setState('idle')} className="text-[9px] text-zinc-500 hover:text-zinc-300 uppercase font-black tracking-widest">Replace</button>
                </div>
            ) : (
                <div className="flex items-center gap-2">
                    <input
                        type="password"
                        value={val}
                        onChange={e => setValue(e.target.value)}
                        onKeyDown={e => { if (e.key === 'Enter') save(); }}
                        placeholder={provider.placeholder}
                        className="flex-1 bg-black/50 border border-white/10 rounded-lg px-3 py-2 text-[11px] text-white font-mono outline-none focus:border-indigo-500/50"
                    />
                    <button
                        onClick={save}
                        disabled={state === 'saving' || !val.trim()}
                        className="px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-[10px] font-black uppercase tracking-widest disabled:opacity-30 disabled:cursor-not-allowed flex items-center gap-1.5"
                    >
                        {state === 'saving' ? <Loader2 className="w-3 h-3 animate-spin" /> : <KeyRound className="w-3 h-3" />} Save
                    </button>
                </div>
            )}
            {msg && <p className="text-[9px] text-rose-400 font-bold mt-1">{msg}</p>}
        </div>
    );
}

/** Explicit, capability-annotated local-engine install guide (Sovereign path). */
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
    const [selectedPath, setSelectedPath] = useState<Path | null>(null);
    const [preferGemini, setPreferGemini] = useState(true);

    // Which providers already have a key in the vault (so we show "saved" not an empty field).
    const [sealed, setSealed] = useState<Record<string, boolean>>({});
    const markSealed = (id: string) => {
        setSealed(prev => ({ ...prev, [id]: true }));
        // Tell the rest of the app a key changed so the boardroom re-reads its model list.
        window.dispatchEvent(new CustomEvent('tome-master-settings-changed'));
    };
    // Typed-but-not-yet-saved key inputs, so the footer button can flush them (no lost keys).
    const [pending, setPending] = useState<Record<string, string>>({});
    const setPendingKey = (id: string, value: string) => setPending(prev => ({ ...prev, [id]: value }));

    // Live local-engine detection for the Sovereign path.
    const [engines, setEngines] = useState<LocalEngine[]>([]);
    const [scanState, setScanState] = useState<'idle' | 'scanning' | 'done'>('idle');

    const scanEngines = useCallback(async () => {
        setScanState('scanning');
        setEngines(await fetchLocalEngines());
        setScanState('done');
    }, []);

    useEffect(() => {
        if (isOpen) fetchVaultSync().then(p => setSealed(p as unknown as Record<string, boolean>));
    }, [isOpen]);

    useEffect(() => {
        if (isOpen && step === 2 && selectedPath === 'sovereign') scanEngines();
    }, [isOpen, step, selectedPath, scanEngines]);

    if (!isOpen) return null;

    const allModels = engines.flatMap(e => e.models);
    const hasEngine = engines.length > 0;
    const hasVision = allModels.some(m => isVisionModel(m));
    const sovereignReady = hasEngine && hasVision && allModels.length > 0;

    const choose = (path: Path) => {
        setSelectedPath(path);
        setPreferGemini(path !== 'premium');   // free path defaults Gemini ON; premium defaults OFF
        setStep(2);
    };

    const finalize = async () => {
        // [NO LOST KEYS]: flush any pasted-but-unsaved key inputs before closing, so the
        // prominent footer button works even if the user didn't click each row's Save.
        const toSave = Object.fromEntries(
            Object.entries(pending).filter(([id, v]) => v.trim() && !sealed[id]).map(([id, v]) => [id, v.trim()])
        );
        if (Object.keys(toSave).length > 0) {
            await saveVaultToEnv(toSave);
            window.dispatchEvent(new CustomEvent('tome-master-settings-changed'));
        }

        if (selectedPath === 'sovereign') {
            setPref('local_mode', true);
        } else {
            setPref('local_mode', false);
            if (preferGemini) {
                // Soft default: make Gemini the default engine (free). Per-agent smart
                // defaults still surface the best model once premium keys are added.
                setPref('default_provider', 'gemini');
                setPref('boardroom_provider', 'gemini');
                setPref('boardroom_model', GEMINI.defaultModel);
            }
        }
        onClose();
    };

    return (
        <div className="fixed inset-0 z-[300] flex items-center justify-center p-4">
            <div className="absolute inset-0 bg-[#050505] backdrop-blur-md" />

            <div className="relative z-10 w-full max-w-2xl bg-[#0a0a0a] border border-[#222] rounded-3xl shadow-2xl overflow-hidden animate-in fade-in zoom-in duration-300">
                <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-indigo-500 via-sky-500 to-emerald-500" />

                <div className="p-8 md:p-12">
                    {step === 1 ? (
                        <div className="flex flex-col items-center text-center">
                            <div className="w-20 h-20 bg-indigo-500/10 rounded-2xl flex items-center justify-center mb-6 border border-indigo-500/20">
                                <Rocket className="w-10 h-10 text-indigo-400" />
                            </div>
                            <h1 className="text-3xl md:text-4xl font-black text-white mb-3 tracking-tight">Choose How to Power Your AI</h1>
                            <p className="text-zinc-400 text-base mb-8 max-w-lg leading-relaxed">
                                Welcome to <span className="text-white font-bold">Tome-Master</span>. Pick a starting point — you can add or change engines anytime in Settings.
                            </p>

                            <div className="grid md:grid-cols-3 gap-4 w-full">
                                {/* FREE — recommended */}
                                <button onClick={() => choose('free')}
                                    className="group relative flex flex-col items-start p-5 rounded-2xl border border-emerald-500/40 bg-emerald-500/5 hover:bg-emerald-500/10 transition-all text-left">
                                    <span className="absolute -top-2.5 left-4 px-2 py-0.5 rounded-full bg-emerald-500 text-black text-[8px] font-black uppercase tracking-widest">Recommended</span>
                                    <Gift className="w-7 h-7 text-emerald-400 mb-3" />
                                    <h3 className="text-base font-bold text-white mb-1">Free — Gemini</h3>
                                    <p className="text-zinc-500 text-[11px] leading-relaxed mb-3">Google's free API tier runs the whole app at no cost. Best place to start.</p>
                                    <span className="mt-auto flex items-center gap-1 text-emerald-400 font-bold text-[10px] uppercase tracking-widest">Start free <ArrowRight className="w-3 h-3" /></span>
                                </button>

                                {/* PREMIUM */}
                                <button onClick={() => choose('premium')}
                                    className="group relative flex flex-col items-start p-5 rounded-2xl border border-[#222] bg-[#111] hover:border-sky-500/40 hover:bg-sky-500/5 transition-all text-left">
                                    <Globe className="w-7 h-7 text-sky-400 mb-3" />
                                    <h3 className="text-base font-bold text-white mb-1">Premium Keys</h3>
                                    <p className="text-zinc-500 text-[11px] leading-relaxed mb-3">Add paid OpenAI / Claude / Groq keys to unlock the most capable models per role.</p>
                                    <span className="mt-auto flex items-center gap-1 text-sky-400 font-bold text-[10px] uppercase tracking-widest">Add keys <ArrowRight className="w-3 h-3" /></span>
                                </button>

                                {/* SOVEREIGN */}
                                <button onClick={() => choose('sovereign')}
                                    className="group relative flex flex-col items-start p-5 rounded-2xl border border-[#222] bg-[#111] hover:border-indigo-500/40 hover:bg-indigo-500/5 transition-all text-left">
                                    <ShieldCheck className="w-7 h-7 text-indigo-400 mb-3" />
                                    <h3 className="text-base font-bold text-white mb-1">Sovereign — Local</h3>
                                    <p className="text-zinc-500 text-[11px] leading-relaxed mb-3">100% offline on your own hardware. No keys, no bills — your manuscript never leaves this machine.</p>
                                    <span className="mt-auto flex items-center gap-1 text-indigo-400 font-bold text-[10px] uppercase tracking-widest">Go offline <ArrowRight className="w-3 h-3" /></span>
                                </button>
                            </div>
                        </div>
                    ) : selectedPath === 'sovereign' ? (
                        <div className="flex flex-col items-start">
                            <h2 className="text-2xl font-bold text-white mb-2 flex items-center gap-3">
                                <ShieldCheck className="w-7 h-7 text-indigo-400" /> Sovereign Mode Setup
                            </h2>
                            <p className="text-zinc-400 mb-6 leading-relaxed">
                                Every AI role runs on a local engine — your manuscript never leaves this machine. Let's confirm the engines for transcription (OCR) and analysis are present.
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
                            <FooterButtons onBack={() => setStep(1)} onActivate={finalize} label="Activate Sovereign Path" color="bg-indigo-600 hover:bg-indigo-500" />
                        </div>
                    ) : (
                        /* CLOUD setup (free + premium) */
                        <div className="flex flex-col items-start">
                            <h2 className="text-2xl font-bold text-white mb-2">Connect an AI Engine</h2>
                            <p className="text-zinc-400 mb-6 leading-relaxed text-sm">
                                Paste a key below and you're ready — no extra steps. You can change engines anytime in Settings.
                            </p>

                            <div className="w-full max-h-[52vh] overflow-y-auto custom-scrollbar pr-1 space-y-5">
                                {/* FREE — Gemini */}
                                <div className="p-4 rounded-2xl border border-emerald-500/30 bg-emerald-500/5">
                                    <div className="flex items-center gap-2 mb-2">
                                        <Gift className="w-4 h-4 text-emerald-400" />
                                        <h3 className="text-sm font-black text-emerald-400 uppercase tracking-widest">Free to start</h3>
                                    </div>
                                    <p className="text-[12px] text-zinc-400 mb-3">
                                        <span className="text-white font-bold">Google Gemini</span> has a genuinely free API tier — grab a key (takes a minute) and the whole app runs at <span className="text-emerald-400 font-bold">no cost</span>.
                                    </p>
                                    <ProviderKeyRow provider={GEMINI} sealed={!!sealed.gemini} onSaved={markSealed} onChange={setPendingKey} />
                                    <label className="flex items-center gap-2 mt-3 cursor-pointer select-none">
                                        <input type="checkbox" checked={preferGemini} onChange={e => setPreferGemini(e.target.checked)}
                                            className="w-4 h-4 accent-emerald-500" />
                                        <span className="text-[11px] text-zinc-300">Make Gemini the default engine (free). You can still override any specialist later.</span>
                                    </label>
                                </div>

                                {/* Billing reality */}
                                <div className="flex items-start gap-3 p-3 bg-sky-500/5 border border-sky-500/20 rounded-xl">
                                    <Info className="w-5 h-5 text-sky-400 shrink-0 mt-0.5" />
                                    <p className="text-[11px] text-sky-300/80 leading-relaxed">
                                        <span className="text-white font-bold">A Claude or ChatGPT subscription is NOT an API key.</span> Those plans only work inside their own apps. Apps like this use a separate, pay-as-you-go <span className="text-white">API key</span>. Gemini and Groq offer free API tiers; OpenAI and Anthropic are paid.
                                    </p>
                                </div>

                                {/* PREMIUM */}
                                <div className="p-4 rounded-2xl border border-[#222] bg-[#0f0f0f]">
                                    <h3 className="text-sm font-black text-zinc-300 uppercase tracking-widest mb-1">Go further — premium models (paid)</h3>
                                    <p className="text-[12px] text-zinc-500 mb-3">
                                        Add any of these to unlock the strongest model per specialist (e.g. deep-reasoning models for structural audits). Groq also has a free tier. Optional — skip and add later anytime.
                                    </p>
                                    <div className="space-y-2">
                                        {PAID_PROVIDERS.map(p => (
                                            <ProviderKeyRow key={p.id} provider={p} sealed={!!sealed[p.id]} onSaved={markSealed} onChange={setPendingKey} />
                                        ))}
                                    </div>
                                </div>
                            </div>

                            <div className="w-full mt-6">
                                <FooterButtons onBack={() => setStep(1)} onActivate={finalize}
                                    label={(['gemini', 'openai', 'anthropic', 'groq'].some(id => sealed[id]) || Object.values(pending).some(v => v.trim()))
                                        ? 'Save & Enter Tome-Master' : 'Skip for now'}
                                    color="bg-emerald-600 hover:bg-emerald-500" />
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}

function FooterButtons({ onBack, onActivate, label, color }: { onBack: () => void; onActivate: () => void; label: string; color: string }) {
    return (
        <div className="flex w-full gap-4">
            <button onClick={onBack} className="flex-1 py-4 px-6 rounded-2xl border border-[#222] text-zinc-400 font-bold hover:bg-[#151515] transition-all">Go Back</button>
            <button onClick={onActivate} className={`flex-[2] py-4 px-6 rounded-2xl font-bold text-white transition-all shadow-xl shadow-indigo-500/10 ${color}`}>{label}</button>
        </div>
    );
}
