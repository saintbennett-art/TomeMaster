"use client";

import React, { useState, useEffect } from "react";
import { X, Sparkles, Activity, ShieldCheck, Cpu, Database, Zap, Lock, Settings, FileText, Key, Info, Check, Loader2, ChevronDown } from "lucide-react";
import { autoConfigureGateway, API_BASE_HOLDER, fetchAvailableModels, saveVaultToEnv, type DiscoveredModel } from "../lib/apiClient";
import { VaultDashboard } from "./workstation/settings/VaultDashboard";
import { secureVault } from "../lib/vault";
import { MASTER_PROVIDER_LIBRARY } from "../lib/ai_config";

import { useShadowSave } from "../hooks/useShadowSave";

const PROVIDERS = MASTER_PROVIDER_LIBRARY;

const SettingsModal = ({ isOpen, onClose, activeProvider, setActiveProvider, activeFolderPath, keys, setKeys }) => {
    const [activeTab, setActiveTab] = useState("keys");
    const [saved, setSaved] = useState(false);
    const [valStatus, setValStatus] = useState({});
    const [valMessages, setValMessages] = useState({});
    const [ledgerEntries, setLedgerEntries] = useState([]);
    const [totalTokens, setTotalTokens] = useState(0);
    
    // [SOVEREIGN RESILIENCE]: Shadow-Save for volatile Vault inputs
    const [localKeys, setLocalKeys, clearShadow] = useShadowSave("vault_entry", keys);
    
    const [discoveryStatus, setDiscoveryStatus] = useState("idle");
    const [discoveryMessage, setDiscoveryMessage] = useState("");
    const [discoveredPortfolio, setDiscoveredPortfolio] = useState([]);
    const [sovereignSettings, setSovereignSettings] = useState(null);
    // [SOVEREIGN DISCOVERY]: Live models fetched from the provider using the saved key
    const [discoveredModels, setDiscoveredModels] = useState<Record<string, DiscoveredModel[]>>({});
    const [selectedModels, setSelectedModels] = useState<Record<string, string>>({});
    const [modelFetchStatus, setModelFetchStatus] = useState<Record<string, 'idle' | 'loading' | 'done' | 'error'>>({});

    const fetchSovereignSettingsLocal = async () => {
        try {
            const res = await fetch(`${API_BASE_HOLDER.current}/ai/status`);
            const data = await res.json();
            setSovereignSettings(data);
        } catch (e) { /* Silent */ }
    };

    useEffect(() => {
        if (isOpen) {
            setLocalKeys(keys);
            fetchSovereignSettingsLocal();
            if (activeTab === "usage") fetchUsageLedger();
        }
    }, [isOpen]);

    const fetchUsageLedger = async () => {
        try {
            const res = await fetch(`${API_BASE_HOLDER.current}/analysis/usage`);
            const data = await res.json();
            if (data.history) {
                setLedgerEntries(data.history);
                setTotalTokens(data.history.reduce((acc, curr) => acc + (curr.metrics?.total_tokens || 0), 0));
            }
        } catch (e) { /* Silent */ }
    };

    const handleGatewayDiscovery = async (key) => {
        if (!key || key.length < 10) return;
        
        setDiscoveryStatus("detecting");
        setDiscoveryMessage("Analyzing Signature...");
        
        try {
            const res = await fetch(`${API_BASE_HOLDER.current}/analysis/auto-configure`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ keys: { "discovery": key } })
            });
            const data = await res.json();
            
            if (data.success) {
                setDiscoveryStatus("success");
                const details = data.details[0]?.status;
                if (details?.success) {
                    setDiscoveryMessage(`Gateway Established: ${details.message}`);
                    setDiscoveredPortfolio(details.portfolio || []);
                    fetchSovereignSettingsLocal();
                } else {
                    setDiscoveryStatus("error");
                    setDiscoveryMessage(details?.message || "Discovery Failed");
                }
            } else {
                setDiscoveryStatus("error");
                setDiscoveryMessage("Handshake Refused");
            }
        } catch (e) {
            setDiscoveryStatus("error");
            setDiscoveryMessage("Connection Interrupted");
        }
    };

    const saveAll = async () => {
        // [MASK GUARD]: Strip display placeholders — never write '***SEALED***' to the vault
        const realKeys = Object.fromEntries(
            Object.entries(localKeys).filter(([, v]) => v && !v.includes('***') && v.trim().length > 5)
        );

        // [VAULT SEAL]: Persist real keys to backend .env first — must complete before discovery
        if (Object.keys(realKeys).length > 0) {
            await saveVaultToEnv(realKeys);
        }

        // Update React state and UI
        setKeys({ ...localKeys, ...realKeys });
        clearShadow();
        setSaved(true);
        setTimeout(() => setSaved(false), 2000);

        // [SOVEREIGN DISCOVERY]: Now that the key is sealed, query each provider's live model list
        // Only providers with a real key (not masked) trigger discovery
        const providers = PROVIDERS.filter(p => realKeys[p.id]);
        const allDiscovered: Record<string, DiscoveredModel[]> = {};

        for (const p of providers) {
            setModelFetchStatus(prev => ({ ...prev, [p.id]: 'loading' }));
            try {
                const models = await fetchAvailableModels(p.id);
                allDiscovered[p.id] = models;
                setDiscoveredModels(prev => ({ ...prev, [p.id]: models }));
                setModelFetchStatus(prev => ({ ...prev, [p.id]: 'done' }));
            } catch {
                setModelFetchStatus(prev => ({ ...prev, [p.id]: 'error' }));
            }
        }

        // [DYNAMIC ROUTING]: Tell the backend to set all roles to "auto" so it
        // queries the live model list and picks the best model for each role
        // dynamically. No hardcoded model names in the frontend.
        // The backend's _resolve_auto_model() handles the ranking per role.
        const preferred_models: Record<string, string> = {
            TRANSCRIBER_LEAD: "auto",
            NARRATIVE_ARCHITECT: "auto",
            COPY_EDITOR: "auto",
            MARKETING_ANALYST: "auto",
            SOVEREIGN_LIAISON: "auto",
            vision: "auto",
            logic: "auto",
            analysis: "auto",
        };

        try {
            const settingsRes = await fetch(`${API_BASE_HOLDER.current}/settings/update`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ preferred_models })
            });
            if (settingsRes.ok) {
                console.log("[VAULT]: Model routing set to dynamic auto-discovery.");
            }
        } catch { /* Silent — defaults remain in place */ }

        // [UI FEEDBACK]: Show what the backend actually resolved for display
        if (Object.keys(allDiscovered).length > 0) {
            try {
                const resolvedRes = await fetch(`${API_BASE_HOLDER.current}/settings/resolved-models`);
                if (resolvedRes.ok) {
                    const resolved = await resolvedRes.json();
                    setSelectedModels(resolved.models || {});
                }
            } catch { /* Silent */ }
        }
    };


    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 z-[2000] flex items-center justify-center p-4">
            <div className="absolute inset-0 bg-black/80 backdrop-blur-xl" onClick={onClose} />
            <div className="relative w-full max-w-4xl h-[85vh] bg-[#0a0a0a] border border-white/5 rounded-[2rem] shadow-[0_0_100px_rgba(0,0,0,1)] overflow-hidden flex flex-col">
                <div className="p-6 border-b border-white/5 flex items-center justify-between bg-black/40">
                    <div className="flex items-center gap-4">
                        <div className="w-10 h-10 rounded-2xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center">
                            <Settings className="text-indigo-400 w-5 h-5" />
                        </div>
                        <h2 className="text-xl font-black text-white uppercase tracking-tighter italic">Command Center</h2>
                    </div>
                    <div className="flex items-center gap-6">
                        <div className="flex flex-col items-end">
                            <span className="text-[8px] font-black text-zinc-500 uppercase tracking-widest">System Status</span>
                            <span className="text-[10px] font-bold text-emerald-500 uppercase">Operational</span>
                        </div>
                        <button onClick={onClose} className="p-2 bg-white/5 hover:bg-white/10 rounded-xl transition-all text-zinc-400 hover:text-white"><X size={18} /></button>
                    </div>
                </div>

                <div className="flex-1 flex overflow-hidden">
                    <div className="w-48 border-r border-white/5 p-4 space-y-2 bg-black/20">
                        {[
                            { id: "keys", icon: Key, label: "Intelligence" },
                            { id: "usage", icon: Activity, label: "Vault Usage" },
                            { id: "about", icon: Info, label: "System" }
                        ].map(tab => (
                            <button 
                                key={tab.id}
                                onClick={() => setActiveTab(tab.id)}
                                className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl text-[10px] font-black uppercase transition-all ${activeTab === tab.id ? "bg-indigo-600 text-white shadow-lg shadow-indigo-600/20" : "text-zinc-400 hover:bg-white/5 hover:text-zinc-200"}`}
                            >
                                <tab.icon size={14} />
                                {tab.label}
                            </button>
                        ))}
                    </div>

                    <div className="flex-1 overflow-y-auto p-8 custom-scrollbar">
                        {activeTab === "keys" && (
                            <div className="space-y-6">

                                {/* Per-provider key inputs */}
                                <div className="space-y-3">
                                    <h3 className="text-[9px] font-black text-zinc-500 uppercase tracking-[0.25em] flex items-center gap-2">
                                        <Key size={10} className="text-indigo-400" />
                                        Intelligence Gateway Keys
                                    </h3>
                                    {PROVIDERS.filter(p => p.id !== 'ollama').map(p => {
                                        const currentVal = localKeys[p.id] || '';
                                        const isSealed   = currentVal === '***SEALED***';
                                        return (
                                            <div key={p.id} className="p-4 bg-black/30 border border-white/5 rounded-2xl hover:border-white/10 transition-all">
                                                <div className="flex items-center justify-between mb-2">
                                                    <span className={`text-[9px] font-black uppercase tracking-widest ${p.color}`}>{p.name}</span>
                                                    {isSealed && (
                                                        <span className="flex items-center gap-1 text-[7px] font-black text-emerald-500 uppercase tracking-widest">
                                                            <ShieldCheck size={9} /> Sealed
                                                        </span>
                                                    )}
                                                </div>
                                                <div className="relative">
                                                    <input
                                                        id={`key-input-${p.id}`}
                                                        type="password"
                                                        placeholder={isSealed ? '••••••••••••••••••••' : p.placeholder}
                                                        value={isSealed ? '' : currentVal}
                                                        onChange={e => setLocalKeys(prev => ({ ...prev, [p.id]: e.target.value }))}
                                                        className="w-full bg-black/40 border border-white/5 rounded-xl px-4 py-3 text-[10px] text-white font-mono focus:outline-none focus:border-indigo-500/50 transition-all pr-10"
                                                    />
                                                    {isSealed && (
                                                        <button
                                                            onClick={() => setLocalKeys(prev => ({ ...prev, [p.id]: '' }))}
                                                            title="Replace key"
                                                            className="absolute right-3 top-1/2 -translate-y-1/2 text-zinc-600 hover:text-zinc-300 transition-colors text-[8px] font-black uppercase"
                                                        >
                                                            Replace
                                                        </button>
                                                    )}
                                                </div>
                                                <p className="text-[7px] text-zinc-600 mt-1.5">
                                                    <a href={p.link} target="_blank" rel="noopener noreferrer" className="hover:text-indigo-400 transition-colors">{p.linkLabel} ↗</a>
                                                </p>
                                            </div>
                                        );
                                    })}
                                </div>

                                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                    {sovereignSettings?.gateways && Object.entries(sovereignSettings.gateways).map(([name, config]: [string, any]) => (
                                        <div key={`gw-${name}`} className="p-4 bg-black/20 border border-white/5 rounded-2xl hover:border-indigo-500/20 transition-all group">
                                            <div className="flex items-center justify-between mb-3">
                                                <div className="flex items-center gap-2">
                                                    <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                                                    <span className="text-[10px] font-black text-white uppercase">{String(name).replace('_', ' ')}</span>
                                                </div>
                                                <span className="text-[8px] font-black text-zinc-600 uppercase tracking-widest">{String(config?.provider_type || 'unknown')}</span>
                                            </div>
                                            <div className="space-y-1">
                                                <p className="text-[8px] text-zinc-500 font-black uppercase tracking-widest">Gateway URL</p>
                                                <p className="text-[10px] text-zinc-400 font-mono truncate">{String(config?.url || 'n/a')}</p>
                                            </div>
                                        </div>
                                    ))}
                                </div>

                                {/* [COMMISSIONED INTELLIGENCE]: Auto-assigned model status per provider */}
                                {Object.keys(modelFetchStatus).length > 0 && (
                                    <div className="p-5 bg-black/30 border border-white/5 rounded-2xl space-y-3 animate-in fade-in duration-500">
                                        <h3 className="text-[9px] font-black text-zinc-500 uppercase tracking-[0.25em] flex items-center gap-2">
                                            <Cpu size={10} className="text-indigo-400" />
                                            Commissioned Intelligence
                                        </h3>
                                        <div className="space-y-2">
                                            {PROVIDERS.map(p => {
                                                const status = modelFetchStatus[p.id];
                                                if (!status) return null;
                                                const roleModel = selectedModels[`TRANSCRIBER_LEAD`] && p.id === 'gemini'
                                                    ? { transcriber: selectedModels['TRANSCRIBER_LEAD'], analysis: selectedModels['NARRATIVE_ARCHITECT'] }
                                                    : null;
                                                const models = discoveredModels[p.id] || [];
                                                return (
                                                    <div key={p.id} className="flex items-start gap-3 p-3 bg-white/[0.02] border border-white/5 rounded-xl">
                                                        {/* Status dot */}
                                                        <div className="mt-0.5 shrink-0">
                                                            {status === 'loading' && <Loader2 size={10} className="text-indigo-400 animate-spin" />}
                                                            {status === 'done'    && <Check size={10} className="text-emerald-500" />}
                                                            {status === 'error'   && <span className="text-[8px] text-red-400">✕</span>}
                                                        </div>
                                                        <div className="flex-1 min-w-0">
                                                            <div className="flex items-center justify-between">
                                                                <span className={`text-[9px] font-black uppercase tracking-wide ${p.color}`}>{p.name}</span>
                                                                <span className="text-[7px] text-zinc-600 font-bold uppercase">
                                                                    {status === 'loading' ? 'Querying...' : status === 'error' ? 'Failed' : `${models.length} models`}
                                                                </span>
                                                            </div>
                                                            {status === 'done' && roleModel && (
                                                                <div className="mt-1.5 space-y-1">
                                                                    <div className="flex items-center gap-2">
                                                                        <span className="text-[7px] text-zinc-600 font-black uppercase w-16 shrink-0">Transcriber</span>
                                                                        <span className="text-[8px] text-indigo-300 font-mono truncate">{roleModel.transcriber || '—'}</span>
                                                                    </div>
                                                                    <div className="flex items-center gap-2">
                                                                        <span className="text-[7px] text-zinc-600 font-black uppercase w-16 shrink-0">Architect</span>
                                                                        <span className="text-[8px] text-indigo-300 font-mono truncate">{roleModel.analysis || '—'}</span>
                                                                    </div>
                                                                </div>
                                                            )}
                                                            {status === 'done' && !roleModel && models.length > 0 && (
                                                                <div className="mt-1.5 flex items-center gap-2">
                                                                    <span className="text-[7px] text-zinc-600 font-black uppercase w-16 shrink-0">Assigned</span>
                                                                    <span className="text-[8px] text-indigo-300 font-mono truncate">
                                                                        {selectedModels[p.id] || models[0]?.id || '—'}
                                                                    </span>
                                                                </div>
                                                            )}
                                                        </div>
                                                    </div>
                                                );
                                            })}
                                        </div>
                                    </div>
                                )}

                                <div className="p-6 bg-black/20 border border-white/5 rounded-2xl">
                                    <h3 className="text-[10px] font-black text-zinc-500 uppercase tracking-[0.2em] mb-4">Industrial Role Mappings</h3>
                                    <div className="grid grid-cols-2 gap-2">
                                        {sovereignSettings?.role_mappings && Object.entries(sovereignSettings.role_mappings).map(([role, gateway]) => (
                                            <div key={`role-${role}`} className="flex items-center justify-between p-3 bg-white/5 rounded-xl border border-white/5">
                                                <div className="flex flex-col">
                                                    <span className="text-[8px] font-black text-zinc-500 uppercase">{String(role)}</span>
                                                    <span className="text-[10px] font-bold text-zinc-200">{String(gateway)}</span>
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            </div>
                        )}

                        {activeTab === "usage" && (
                            <VaultDashboard 
                                ledgerEntries={ledgerEntries} totalTokens={totalTokens} expenditure={{}} 
                                startingBalances={{}} systemAudit={null} isAuditLoading={false} 
                                triggerKillSwitch={()=>{}} isKilling={false}
                            />
                        )}

                        {activeTab === "about" && (
                            <div className="space-y-8 animate-in fade-in duration-500">
                                <div className="p-6 bg-indigo-500/5 border border-indigo-500/20 rounded-2xl relative overflow-hidden group">
                                    <div className="absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity">
                                        <Database size={80} className="text-indigo-500" />
                                    </div>
                                    <h3 className="text-[10px] font-black text-indigo-400 uppercase tracking-[0.2em] mb-4 flex items-center gap-2">
                                        <Database size={12} /> Project Infrastructure
                                    </h3>
                                    <div className="space-y-4 relative z-10">
                                        <div>
                                            <p className="text-[8px] text-zinc-500 font-black uppercase tracking-widest mb-1">Active Project Root</p>
                                            <div className="flex items-center gap-3">
                                                <div className="flex-1 bg-black/40 border border-white/5 rounded-xl px-4 py-3 text-[10px] text-zinc-300 font-mono truncate">
                                                    {activeFolderPath || "No Project Target Set"}
                                                </div>
                                                <button 
                                                    onClick={() => window.dispatchEvent(new CustomEvent('tome-master-target-request'))}
                                                    className="px-4 py-3 bg-white/5 hover:bg-white/10 border border-white/5 rounded-xl text-[8px] font-black uppercase tracking-widest text-zinc-400 hover:text-white transition-all"
                                                >
                                                    Update Path
                                                </button>
                                            </div>
                                        </div>
                                    </div>
                                </div>

                                <div className="p-6 bg-black/20 border border-white/5 rounded-2xl">
                                    <h3 className="text-[10px] font-black text-zinc-500 uppercase tracking-[0.2em] mb-4">System Telemetry</h3>
                                    <div className="grid grid-cols-2 gap-4">
                                        <div className="space-y-1">
                                            <p className="text-[8px] text-zinc-600 font-black uppercase tracking-widest">Handshake Integrity</p>
                                            <p className="text-[10px] text-zinc-300 font-bold uppercase tracking-tighter">
                                                {Object.values(valStatus).some(v => v === 'checking') ? "Engaging Specialists..." : 
                                                 Object.values(valStatus).every(v => v === 'success') ? "All Handshakes Verified" : 
                                                 "Handshake Required"}
                                            </p>
                                        </div>
                                        <div className="space-y-1 text-right">
                                            <p className="text-[8px] text-zinc-600 font-black uppercase tracking-widest">Version</p>
                                            <p className="text-[10px] text-indigo-400 font-black uppercase tracking-tighter italic">Industrial v1.4.2</p>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        )}
                    </div>
                </div>

                <div className="p-6 border-t border-white/5 bg-black/40 flex items-center justify-between">
                    <div className="flex items-center gap-2 text-emerald-500/50">
                        <Lock size={12} />
                        <span className="text-[8px] font-black uppercase">Sovereign Encryption Active</span>
                    </div>
                    <div className="flex gap-3">
                        <button onClick={onClose} className="px-6 py-2.5 text-[10px] font-black uppercase text-zinc-500">Cancel</button>
                        <button
                            onClick={saveAll}
                            className={`px-8 py-2.5 rounded-xl text-[10px] font-black uppercase transition-all flex items-center gap-2 ${
                                saved
                                    ? 'bg-emerald-500/10 border border-emerald-500/20 text-emerald-400'
                                    : 'bg-indigo-500 text-white hover:bg-indigo-400 shadow-[0_0_20px_rgba(99,102,241,0.3)]'
                            }`}
                        >
                            {saved ? <><ShieldCheck size={14} /> Sealed ✓</> : <><Lock size={14} /> Seal Vault</>}
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default SettingsModal;
