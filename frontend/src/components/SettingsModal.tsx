"use client";

import React, { useState, useEffect } from "react";
import { X, Sparkles, Activity, ShieldCheck, Cpu, Database, Zap, Lock, Settings, FileText, Key, Info, Check, Loader2 } from "lucide-react";
import { MASTER_PROVIDER_LIBRARY } from "../lib/ai_config";
import { validateAiKey, API_BASE_HOLDER } from "../lib/apiClient";
import { ProviderSettingsCard } from "./workstation/settings/ProviderSettingsCard";
import { VaultDashboard } from "./workstation/settings/VaultDashboard";

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
    
    const [cloudModels, setCloudModels] = useState({});
    const [cloudModelStatus, setCloudModelStatus] = useState({});

    useEffect(() => {
        if (isOpen) {
            setLocalKeys(keys);
            
            // [SOVEREIGN HYDRATION]: Restore discovered models from Vault
            const savedModels = localStorage.getItem('tome_master_cloud_models');
            if (savedModels) {
                try {
                    const parsed = JSON.parse(savedModels);
                    setCloudModels(parsed);
                    // Mark as success if we have models and a key
                    Object.keys(parsed).forEach(provId => {
                        if (keys[provId]) {
                            setValStatus(prev => ({ ...prev, [provId]: "success" }));
                            setValMessages(prev => ({ ...prev, [provId]: "Vault Restored" }));
                            setCloudModelStatus(prev => ({ ...prev, [provId]: 'success' }));
                        }
                    });
                } catch (e) { console.error("Vault Restoration Failed", e); }
            }

            // [AUTO HANDSHAKE]: Test all connections immediately upon opening
            PROVIDERS.forEach(p => {
                if (keys[p.id]) {
                    testConnection(p.id, keys[p.id]);
                }
            });

            if (activeTab === "usage") fetchUsageLedger();
        }
    }, [isOpen]); // Only trigger on open

    const fetchUsageLedger = async () => {
        try {
            const res = await fetch(`${API_BASE_HOLDER.current}/analysis/usage`);
            const data = await res.json();
            if (data.history) {
                setLedgerEntries(data.history);
                setTotalTokens(data.history.reduce((acc, curr) => acc + (curr.metrics?.total_tokens || 0), 0));
            }
        } catch (e) { console.error("Ledger fetch failed", e); }
    };

    const handleKeyChange = (provider, value) => {
        setLocalKeys(prev => ({ ...prev, [provider]: value }));
        setSaved(false);
    };

    const testConnection = async (provider, keyOverride = null) => {
        const apiKey = keyOverride || localKeys[provider];
        if (!apiKey) return;

        setValStatus(prev => ({ ...prev, [provider]: "checking" }));
        try {
            const result = await validateAiKey(provider, apiKey);
            if (result.success) {
                fetchCloudModels(provider, apiKey);
                setValStatus(prev => ({ ...prev, [provider]: "success" }));
                setValMessages(prev => ({ ...prev, [provider]: "Verified" }));
            } else {
                setValStatus(prev => ({ ...prev, [provider]: "error" }));
                setValMessages(prev => ({ ...prev, [provider]: result.message }));
            }
        } catch (e) {
            setValStatus(prev => ({ ...prev, [provider]: "error" }));
            setValMessages(prev => ({ ...prev, [provider]: "Connection Failed" }));
        }
    };

    const fetchCloudModels = async (provider, keyOverride = null) => {
        const apiKey = keyOverride || localKeys[provider];
        if (!apiKey) return;
        
        setCloudModelStatus(prev => ({ ...prev, [provider]: 'fetching' }));
        try {
            const res = await fetch(`${API_BASE_HOLDER.current}/ai/models?provider=${provider}&api_key=${apiKey}`);
            const data = await res.json();
            if (data.success) {
                const updatedModels = { ...cloudModels, [provider]: data.models };
                setCloudModels(updatedModels);
                localStorage.setItem('tome_master_cloud_models', JSON.stringify(updatedModels));
                setCloudModelStatus(prev => ({ ...prev, [provider]: 'success' }));
            } else {
                setCloudModelStatus(prev => ({ ...prev, [provider]: 'error' }));
            }
        } catch (e) {
            setCloudModelStatus(prev => ({ ...prev, [provider]: 'error' }));
        }
    };

    const saveAll = () => {
        setKeys(localKeys);
        localStorage.setItem("tome_master_vault", JSON.stringify(localKeys));
        clearShadow(); // [SHADOW RELEASE]: State is now persistent
        setSaved(true);
        setTimeout(() => setSaved(false), 2000);
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
                            <div className="space-y-4">
                                {PROVIDERS.map(p => (
                                    <ProviderSettingsCard 
                                        key={p.id} provider={p} localKeys={localKeys} handleKeyChange={handleKeyChange} 
                                        testConnection={testConnection} valStatus={valStatus} valMessages={valMessages} 
                                        activeProvider={activeProvider} setActiveProvider={setActiveProvider} 
                                        cloudModels={cloudModels} cloudModelStatus={cloudModelStatus} fetchCloudModels={fetchCloudModels}
                                    />
                                ))}
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
                                            <p className="text-[8px] text-zinc-500 font-black uppercase tracking-widest mb-1">Active Project Anchor</p>
                                            <div className="flex items-center gap-3">
                                                <div className="flex-1 bg-black/40 border border-white/5 rounded-xl px-4 py-3 text-[10px] text-zinc-300 font-mono truncate">
                                                    {activeFolderPath || "No Project Anchored"}
                                                </div>
                                                <button 
                                                    onClick={() => window.dispatchEvent(new CustomEvent('tome-master-anchor-request'))}
                                                    className="px-4 py-3 bg-white/5 hover:bg-white/10 border border-white/5 rounded-xl text-[8px] font-black uppercase tracking-widest text-zinc-400 hover:text-white transition-all"
                                                >
                                                    Re-Anchor
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
                        {JSON.stringify(localKeys) === JSON.stringify(keys) ? (
                            <button className="px-8 py-2.5 rounded-xl text-[10px] font-black uppercase bg-emerald-500/10 border border-emerald-500/20 text-emerald-500 cursor-default flex items-center gap-2">
                                <ShieldCheck size={14} />
                                Vault Sealed
                            </button>
                        ) : (
                            <button onClick={saveAll} className="px-8 py-2.5 rounded-xl text-[10px] font-black uppercase bg-indigo-500 text-white hover:bg-indigo-400 transition-all shadow-[0_0_20px_rgba(99,102,241,0.3)]">
                                Seal Vault
                            </button>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
};

export default SettingsModal;
