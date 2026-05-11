"use client";

import React, { useState } from 'react';
import { 
    Eye, 
    EyeOff, 
    Check, 
    AlertCircle, 
    ExternalLink,
    RefreshCw,
    Loader2,
    Zap,
    Sparkles,
    Shield,
    Clipboard
} from 'lucide-react';
import { isVisionModel, Provider } from '../../../lib/ai_config';
import { SystemAudit } from '@/types/industrial';

interface ProviderSettingsCardProps {
    provider: Provider;
    localKeys: Record<string, string>;
    handleKeyChange: (id: string, val: string) => void;
    testConnection: (id: string) => void;
    valStatus: Record<string, string>;
    valMessages: Record<string, string>;
    activeProvider: string;
    setActiveProvider: (id: string) => void;
    cloudModels: Record<string, string[]>;
    cloudModelStatus: Record<string, string>;
    fetchCloudModels: (id: string) => void;
    systemAudit?: SystemAudit | null;
}

export const ProviderSettingsCard: React.FC<ProviderSettingsCardProps> = ({
    provider,
    localKeys,
    handleKeyChange,
    testConnection,
    valStatus,
    valMessages,
    activeProvider,
    setActiveProvider,
    cloudModels,
    cloudModelStatus,
    fetchCloudModels,
    systemAudit
}) => {
    const [showKey, setShowKey] = useState(false);
    const isOllama = provider.id === 'ollama';
    const hasEnoughRam = systemAudit?.ram_total >= 15.5; // 16GB threshold
    const isGated = isOllama && !hasEnoughRam;
    
    const status = valStatus[provider.id] || 'idle';
    const message = valMessages[provider.id] || '';
    const mStatus = cloudModelStatus[provider.id] || 'idle';

    return (
        <div key={provider.id} className={`p-4 rounded-2xl border ${isGated ? "opacity-40 grayscale pointer-events-none" : ""} transition-all duration-300 ${activeProvider === provider.id ? 'bg-indigo-500/5 border-indigo-500/30 ring-1 ring-indigo-500/20' : 'bg-black/20 border-white/5 hover:border-white/10'}`}>
            
            {isGated && (
                <div className="absolute inset-0 z-10 flex flex-col items-center justify-center bg-black/60 rounded-2xl backdrop-blur-sm p-4 text-center">
                    <AlertCircle className="w-8 h-8 text-rose-500 mb-2 animate-pulse" />
                    <p className="text-[10px] font-black uppercase text-white tracking-widest">Hardware Stewardship Active</p>
                    <p className="text-[8px] text-zinc-400 uppercase font-bold mt-1">16GB RAM Required for Local Intelligence</p>
                    <p className="text-[7px] text-zinc-600 mt-2 italic">Perform "System Audit" in Vault Usage to verify.</p>
                </div>
            )}
    
            <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-3">
                    <div className={`p-2 rounded-xl bg-black/40 border border-white/5 ${provider.color}`}>
                        <span className="text-xs font-black uppercase tracking-tighter">{provider.name.split(' ')[0]}</span>
                    </div>
                    <div>
                        <h4 className="text-xs font-black text-foreground uppercase tracking-tight">{provider.name}</h4>
                        <p className="text-[8px] text-zinc-500 font-bold uppercase tracking-widest">{provider.id === 'ollama' ? 'Local Handshake' : 'Cloud Intelligence'}</p>
                    </div>
                </div>
                {status === 'success' && <Check className="w-3 h-3 text-emerald-500 shadow-[0_0_10px_rgba(16,185,129,0.4)]" />}
                {status === 'error' && <AlertCircle className="w-3 h-3 text-rose-500 animate-pulse" />}
            </div>

            <div className="space-y-3">
                <div className="relative group">
                    <input 
                        type={showKey ? "text" : "password"} 
                        value={localKeys[provider.id] || ''} 
                        onChange={(e) => handleKeyChange(provider.id, e.target.value)} 
                        placeholder={provider.placeholder} 
                        className="w-full bg-black/40 border border-[#222] rounded-xl py-2.5 px-4 pr-16 text-[10px] text-zinc-300 font-mono focus:border-indigo-500/50 outline-none transition-all placeholder:text-zinc-800 group-hover:border-white/10" 
                    />
                    <div className="absolute right-3 top-1/2 -translate-y-1/2 flex items-center gap-2">
                        <button 
                            onClick={async () => {
                                try {
                                    const text = await navigator.clipboard.readText();
                                    handleKeyChange(provider.id, text);
                                } catch (e) {
                                    console.error("Clipboard access denied", e);
                                }
                            }}
                            className="text-zinc-600 hover:text-indigo-400 transition-colors"
                            title="Paste from Clipboard"
                        >
                            <Clipboard size={12} />
                        </button>
                        <button 
                            onClick={() => setShowKey(!showKey)}
                            className="text-zinc-600 hover:text-zinc-400 transition-colors"
                            title="Toggle Visibility"
                        >
                            {showKey ? <EyeOff size={12} /> : <Eye size={12} />}
                        </button>
                    </div>
                </div>

                <div className="flex gap-2 items-center px-1 mb-1">
                    <span className="text-[7px] text-zinc-500 font-bold uppercase tracking-widest flex items-center gap-1">
                        <Clipboard size={8} className="text-zinc-600" /> Tip: Press <kbd className="px-1 py-0.5 rounded bg-zinc-800 text-zinc-400 font-mono text-[6px]">Win + V</kbd> to open Clipboard History
                    </span>
                </div>

                <div className="flex gap-2">
                    <div className="flex-1">
                        {provider.id === 'gemini' ? (
                            <div className="flex flex-col gap-1.5">
                                <select 
                                    value={localKeys[`model_${provider.id}`] || provider.defaultModel || ''} 
                                    onChange={(e) => handleKeyChange(`model_${provider.id}`, e.target.value)} 
                                    className="w-full bg-black/60 border border-indigo-500/30 rounded-xl py-2.5 px-3 text-[10px] text-indigo-400 font-bold font-mono focus:border-indigo-500/50 outline-none transition-all appearance-none cursor-pointer shadow-[0_0_15px_rgba(99,102,241,0.1)]"
                                >
                                    {cloudModels[provider.id] && cloudModels[provider.id].length > 0 ? (
                                        cloudModels[provider.id].map(m => {
                                            const isTrans = localKeys.provider_transcribe === provider.id && localKeys.model_transcribe === m;
                                            const isBoard = localKeys.provider_boardroom === provider.id && localKeys.model_boardroom === m;
                                            const isVision = isVisionModel(m);
                                            return (
                                                <option key={m} value={m}>
                                                    {m.toUpperCase()} 
                                                    {isTrans ? ' (TRANSCRIPTION LEAD)' : ''}
                                                    {isBoard ? ' (BOARDROOM LEAD)' : ''}
                                                    {isVision ? ' [VISION]' : ''}
                                                </option>
                                            );
                                        })
                                    ) : (
                                        <option value="">[HANDSHAKE REQUIRED]</option>
                                    )}
                                </select>
                                <p className="text-[7px] text-indigo-500/60 font-black uppercase tracking-widest pl-1">Sovereign Directorial Standard</p>
                            </div>
                        ) : provider.id === 'openai' ? (
                            <div className="flex flex-col gap-1.5">
                                <select 
                                    value={localKeys[`model_${provider.id}`] || provider.defaultModel || ''} 
                                    onChange={(e) => handleKeyChange(`model_${provider.id}`, e.target.value)} 
                                    className="w-full bg-black/60 border border-emerald-500/30 rounded-xl py-2.5 px-3 text-[10px] text-emerald-400 font-bold font-mono focus:border-emerald-500/50 outline-none transition-all appearance-none cursor-pointer shadow-[0_0_15px_rgba(16,185,129,0.1)]"
                                >
                                    {cloudModels[provider.id] && cloudModels[provider.id].length > 0 ? (
                                        cloudModels[provider.id].map(m => {
                                            const isTrans = localKeys.provider_transcribe === provider.id && localKeys.model_transcribe === m;
                                            const isBoard = localKeys.provider_boardroom === provider.id && localKeys.model_boardroom === m;
                                            const isVision = isVisionModel(m);
                                            return (
                                                <option key={m} value={m}>
                                                    {m.toUpperCase()} 
                                                    {isTrans ? ' (TRANSCRIPTION LEAD)' : ''}
                                                    {isBoard ? ' (BOARDROOM LEAD)' : ''}
                                                    {isVision ? ' [VISION]' : ''}
                                                </option>
                                            );
                                        })
                                    ) : (
                                        <option value="">[HANDSHAKE REQUIRED]</option>
                                    )}
                                </select>
                                <p className="text-[7px] text-emerald-500/60 font-black uppercase tracking-widest pl-1">Sovereign OpenAI Quota Authorized</p>
                            </div>
                        ) : provider.id === 'anthropic' ? (
                            <div className="flex flex-col gap-1.5">
                                <select 
                                    value={localKeys[`model_${provider.id}`] || provider.defaultModel || ''} 
                                    onChange={(e) => handleKeyChange(`model_${provider.id}`, e.target.value)} 
                                    className="w-full bg-black/60 border border-orange-500/30 rounded-xl py-2.5 px-3 text-[10px] text-orange-400 font-bold font-mono focus:border-orange-500/50 outline-none transition-all appearance-none cursor-pointer shadow-[0_0_15px_rgba(249,115,22,0.1)]"
                                >
                                    {cloudModels[provider.id] && cloudModels[provider.id].length > 0 ? (
                                        cloudModels[provider.id].map(m => {
                                            const isTrans = localKeys.provider_transcribe === provider.id && localKeys.model_transcribe === m;
                                            const isBoard = localKeys.provider_boardroom === provider.id && localKeys.model_boardroom === m;
                                            const isVision = isVisionModel(m);
                                            return (
                                                <option key={m} value={m}>
                                                    {m.toUpperCase()} 
                                                    {isTrans ? ' (TRANSCRIPTION LEAD)' : ''}
                                                    {isBoard ? ' (BOARDROOM LEAD)' : ''}
                                                    {isVision ? ' [VISION]' : ''}
                                                </option>
                                            );
                                        })
                                    ) : (
                                        <option value="">[HANDSHAKE REQUIRED]</option>
                                    )}
                                </select>
                                <p className="text-[7px] text-orange-500/60 font-black uppercase tracking-widest pl-1">Style Mirror Calibration Active</p>
                            </div>
                        ) : provider.id === 'groq' ? (
                            <div className="flex flex-col gap-1.5">
                                <select 
                                    value={localKeys[`model_${provider.id}`] || provider.defaultModel || ''} 
                                    onChange={(e) => handleKeyChange(`model_${provider.id}`, e.target.value)} 
                                    className="w-full bg-black/60 border border-rose-500/30 rounded-xl py-2.5 px-3 text-[10px] text-rose-400 font-bold font-mono focus:border-rose-500/50 outline-none transition-all appearance-none cursor-pointer shadow-[0_0_15px_rgba(244,63,94,0.1)]"
                                >
                                    {cloudModels[provider.id] && cloudModels[provider.id].length > 0 ? (
                                        cloudModels[provider.id].map(m => {
                                            const isTrans = localKeys.provider_transcribe === provider.id && localKeys.model_transcribe === m;
                                            const isBoard = localKeys.provider_boardroom === provider.id && localKeys.model_boardroom === m;
                                            const isVision = isVisionModel(m);
                                            
                                            // [EXPERT GUIDANCE]: Hard-established recommendations for the user
                                            const isTranscriptionApex = provider.id === 'groq' && m.includes('llama-3.2-11b');
                                            const isBoardroomApex = provider.id === 'gemini' && m.includes('3.1-pro');
                                            const isProseApex = provider.id === 'anthropic' && m.includes('sonnet');
                                            
                                            return (
                                                <option key={m} value={m} className="bg-black text-zinc-300">
                                                    {m.toUpperCase()} 
                                                    {isTranscriptionApex ? ' ⭐ [BEST FOR TRANSCRIPTION]' : ''}
                                                    {isBoardroomApex ? ' ⭐ [BEST FOR LOGIC/BOARDROOM]' : ''}
                                                    {isProseApex ? ' ⭐ [BEST FOR CREATIVE PROSE]' : ''}
                                                    {isTrans ? ' (ACTIVE TRANSCRIBER)' : ''}
                                                    {isBoard ? ' (ACTIVE BOARDROOM)' : ''}
                                                </option>
                                            );
                                        })
                                    ) : (
<option value="">[HANDSHAKE REQUIRED]</option>
                                    )}
                                </select>
                                <p className="text-[7px] text-rose-500/60 font-black uppercase tracking-widest pl-1">LPU Velocity Quota Authorized</p>
                            </div>
                        ) : (
                            <input 
                                type="text" 
                                value={localKeys[`model_${provider.id}`] || ''} 
                                onChange={(e) => handleKeyChange(`model_${provider.id}`, e.target.value)} 
                                placeholder={`Override Model (e.g. ${provider.model.split('/').pop()})`} 
                                className="w-full bg-black/40 border border-[#222] rounded-xl py-2 px-4 text-[10px] text-zinc-400 font-mono focus:border-indigo-500/50 outline-none transition-all placeholder:text-zinc-800" 
                            />
                        )}

                    </div>
                    <button 
                        onClick={() => testConnection(provider.id)} 
                        disabled={status === 'checking'}
                        className={`px-4 rounded-xl border text-[10px] font-black uppercase transition-all flex items-center gap-2 ${status === 'checking' ? 'bg-zinc-900 border-zinc-800 text-zinc-600' : 'bg-black/60 border-white/5 text-zinc-400 hover:border-white/20 hover:text-white active:scale-95'}`}
                    >
                        {status === 'checking' ? <Loader2 className="w-3 h-3 animate-spin" /> : <RefreshCw className={`w-3 h-3 ${status === 'success' ? 'text-emerald-500' : ''}`} />}
                        {status === 'checking' ? 'Testing' : 'Test'}
                    </button>
                </div>

                {/* [MISSION ALLOCATION]: High-Contrast Mission Controls - Now in a single efficient line */}
                <div className="flex gap-1.5 mt-1 p-1.5 bg-black/40 rounded-xl border border-white/5">
                    <button 
                        onClick={() => {
                            if (!isVisionModel(localKeys[`model_${provider.id}`] || provider.defaultModel)) return;
                            handleKeyChange('provider_transcribe', provider.id);
                            handleKeyChange('model_transcribe', localKeys[`model_${provider.id}`] || provider.defaultModel);
                        }} 
                        disabled={!isVisionModel(localKeys[`model_${provider.id}`] || provider.defaultModel)}
                        className={`flex-1 flex flex-col items-center justify-center py-2.5 rounded-lg transition-all border gap-1 ${!isVisionModel(localKeys[`model_${provider.id}`] || provider.defaultModel) ? 'opacity-20 cursor-not-allowed bg-zinc-950 border-white/5' : localKeys.provider_transcribe === provider.id ? 'bg-amber-500 border-amber-400 text-white shadow-[0_0_15px_rgba(245,158,11,0.3)]' : 'text-zinc-400 bg-zinc-900/50 border-white/5 hover:text-white hover:border-white/10'}`}
                        title={!isVisionModel(localKeys[`model_${provider.id}`] || provider.defaultModel) ? "Engine is Blind: Vision Model required for Transcription" : "Assign to Transcription Engine"}
                    >
                        {!isVisionModel(localKeys[`model_${provider.id}`] || provider.defaultModel) ? <EyeOff size={12} /> : <Eye size={12} className={localKeys.provider_transcribe === provider.id ? 'animate-pulse' : ''} />}
                        <span className="text-[6px] font-black uppercase tracking-widest leading-none">
                            {localKeys.provider_transcribe === provider.id ? 'Active' : 'Transcribe'}
                        </span>
                    </button>

                    <button 
                        onClick={() => {
                            handleKeyChange('provider_boardroom', provider.id);
                            handleKeyChange('model_boardroom', localKeys[`model_${provider.id}`] || provider.defaultModel);
                        }} 
                        className={`flex-1 flex flex-col items-center justify-center py-2.5 rounded-lg transition-all border gap-1 ${localKeys.provider_boardroom === provider.id ? 'bg-indigo-500 border-indigo-400 text-white shadow-[0_0_15px_rgba(99,102,241,0.3)]' : 'text-zinc-400 bg-zinc-900/50 border-white/5 hover:text-white hover:border-white/10'}`}
                        title="Assign to Boardroom Engine"
                    >
                        <Zap size={12} />
                        <span className="text-[6px] font-black uppercase tracking-widest leading-none">{localKeys.provider_boardroom === provider.id ? 'Active' : 'Boardroom'}</span>
                    </button>

                    <button 
                        onClick={() => {
                            handleKeyChange('provider_fallback', provider.id);
                            handleKeyChange('model_fallback', localKeys[`model_${provider.id}`] || provider.defaultModel);
                        }} 
                        className={`flex-1 flex flex-col items-center justify-center py-2.5 rounded-lg transition-all border gap-1 ${localKeys.provider_fallback === provider.id ? 'bg-zinc-700 border-zinc-600 text-white shadow-[0_0_15px_rgba(63,63,70,0.3)]' : 'text-zinc-400 bg-zinc-900/50 border-white/5 hover:text-white hover:border-white/10'}`}
                        title="Assign as Failover Fallback"
                    >
                        <Shield size={12} />
                        <span className="text-[6px] font-black uppercase tracking-widest leading-none">{localKeys.provider_fallback === provider.id ? 'Active' : 'Fallback'}</span>
                    </button>
                </div>
                
                {message && (
                    <p className={`text-[8px] font-bold uppercase tracking-tighter px-1 ${status === 'success' ? 'text-emerald-500/80' : 'text-rose-500/80 animate-pulse'}`}>{message}</p>
                )}

                {/* [DIRECTORIAL ADVISORY]: Real-time engine guidance */}
                <div className="mt-3 p-2 bg-indigo-500/5 rounded-xl border border-indigo-500/10">
                    <p className="text-[7px] text-indigo-400 font-black uppercase tracking-widest mb-1 flex items-center gap-1">
                        <Sparkles size={8} /> Directorial Advisory
                    </p>
                    <p className="text-[8px] text-zinc-400 leading-tight">
                        {provider.id === 'groq' ? "Llama-3.2-11B Vision is the apex choice for 400-page manuscript resurrection due to its low-latency LPU architecture." :
                         provider.id === 'gemini' ? "Gemini 3.1 Pro is the mandatory logic foundation for boardroom audits and deep-context narrative analysis." :
                         provider.id === 'anthropic' ? "Claude 3.5 Sonnet provides the most symmetrical prose mirror for creative style audits." :
                         "Select an engine to synchronize this provider with your active mission objectives."}
                    </p>
                </div>
            </div>

            <div className="flex items-center justify-between mt-4 pt-4 border-t border-white/5">
                <div className="flex flex-col gap-1">
                    <p className="text-[10px] text-foreground font-black uppercase tracking-tight leading-none">{provider.description}</p>
                    <div className="flex items-center gap-2 mt-1">
                        <a href={provider.link} target="_blank" rel="noopener noreferrer" className="text-[8px] font-black text-indigo-400 uppercase hover:text-indigo-300 transition-colors tracking-tighter flex items-center gap-1">
                            {provider.linkLabel}
                            <ExternalLink size={8} />
                        </a>
                        {isVisionModel(localKeys[`model_${provider.id}`]) && (
                            <div className="flex items-center gap-1 px-1.5 py-0.5 rounded bg-emerald-500/10 border border-emerald-500/20">
                                <Eye className="w-2 h-2 text-emerald-500" />
                                <span className="text-[6px] font-black text-emerald-500 uppercase tracking-widest">Vision Ready</span>
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
};
