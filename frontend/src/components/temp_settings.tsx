"use client";

import React, { useState, useEffect } from 'react';
import { 
    X, 
    Sparkles, 
    Activity, 
    ShieldCheck, 
    Cpu, 
    Database,
    Zap,
    Lock,
    Settings,
    FileText,
    Key,
    Info,
    Check,
    Loader2
} from 'lucide-react';
import { MASTER_PROVIDER_LIBRARY } from '../lib/ai_config';
import { validateAiKey, API_BASE_HOLDER } from '../lib/apiClient';
import { ProviderSettingsCard } from './workstation/settings/ProviderSettingsCard';
import { VaultDashboard } from './workstation/settings/VaultDashboard';

const PROVIDERS = MASTER_PROVIDER_LIBRARY;

interface SettingsModalProps {
    isOpen: boolean;
    onClose: () => void;
    activeProvider: string;
    setActiveProvider: (provider: string) => void;
    keys: Record<string, string>;
    setKeys: (keys: Record<string, string>) => void;
}

interface LedgerEntry {
    agent_id: string;
    timestamp: string;
    metrics?: {
        total_tokens?: number;
    };
}

const SettingsModal: React.FC<SettingsModalProps> = ({ 
    isOpen, 
    onClose, 
    activeProvider, 
    setActiveProvider,
    keys,
    setKeys
}) => {
    const [activeTab, setActiveTab] = useState<'keys' | 'usage'>('keys');
    const [saved, setSaved] = useState(false);
    const [valStatus, setValStatus] = useState<Record<string, string>>({});
    const [valMessages, setValMessages] = useState<Record<string, string>>({});
    const [ledgerEntries, setLedgerEntries] = useState<LedgerEntry[]>([]);
    const [totalTokens, setTotalTokens] = useState(0);
    const [localKeys, setLocalKeys] = useState<Record<string, string>>(keys);

    useEffect(() => {
        if (isOpen) {
            setLocalKeys(keys);
            if (activeTab === 'usage') fetchUsageLedger();
        }
    }, [isOpen, activeTab, keys]);

    const fetchUsageLedger = async () => {
        try {
            const res = await fetch(`${API_BASE_HOLDER.current}/analysis/usage`);
            const data = await res.json();
            if (data.history) {
                setLedgerEntries(data.history);
                setTotalTokens(data.history.reduce((acc: number, curr: LedgerEntry) => acc + (curr.metrics?.total_tokens || 0), 0));
            }
        } catch (e) { }
    };

    const handleKeyChange = (provider: string, value: string) => {
        setLocalKeys(prev => ({ ...prev, [provider]: value }));
        setSaved(false);
    };

    const testConnection = async (provider: string) => {
        setValStatus(prev => ({ ...prev, [provider]: 'checking' }));
        try {
            const result = await validateAiKey(provider, localKeys[provider]);
            if (result.success) {
                setValStatus(prev => ({ ...prev, [provider]: 'success' }));
                setValMessages(prev => ({ ...prev, [provider]: 'Verified' }));
            } else {
                setValStatus(prev => ({ ...prev, [provider]: 'error' }));
                setValMessages(prev => ({ ...prev, [provider]: result.message }));
            }
        } catch (e) {
            setValStatus(prev => ({ ...prev, [provider]: 'error' }));
            setValMessages(prev => ({ ...prev, [provider]: 'Connection Failed' }));
        }
    };

    const saveAll = () => {
        setKeys(localKeys);
        localStorage.setItem('tome_master_vault', JSON.stringify(localKeys));
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
                        <h2 className="text-lg font-black text-white uppercase tracking-tighter">Command Center</h2>
                    </div>
                    <button onClick={onClose} className="p-2 hover:bg-white/5 rounded-xl transition-colors text-zinc-500 hover:text-white">
                        <X size={20} />
                    </button>
                </div>

                <div className="flex-1 flex overflow-hidden">
                    <div className="w-48 border-r border-white/5 p-4 space-y-2 bg-black/20">
                        {( [
                            { id: 'keys', icon: Key, label: 'Intelligence' },
                            { id: 'usage', icon: Activity, label: 'Vault Usage' }
                        ] as const).map(tab => (
                            <button 
                                key={tab.id}
                                onClick={() => setActiveTab(tab.id)}
                                className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl text-[10px] font-black uppercase transition-all ${activeTab === tab.id ? 'bg-indigo-500 text-white shadow-lg shadow-indigo-500/20' : 'text-zinc-500 hover:text-zinc-300 hover:bg-white/5'}`}
                            >
                                <tab.icon size={14} />
                                {tab.label}
                            </button>
                        ))}
                    </div>

                    <div className="flex-1 overflow-y-auto p-8 custom-scrollbar">
                        {activeTab === 'keys' && (
                            <div className="space-y-4">
                                {PROVIDERS.map(p => (
                                    <ProviderSettingsCard 
                                        key={p.id}
                                        provider={p}
                                        localKeys={localKeys}
                                        handleKeyChange={handleKeyChange}
                                        testConnection={testConnection}
                                        valStatus={valStatus}
                                        valMessages={valMessages}
                                        activeProvider={activeProvider}
                                        setActiveProvider={setActiveProvider}
                                        cloudModels={{}}
                                        cloudModelStatus={{}}
                                        fetchCloudModels={() => {}}
                                    />
                                ))}
                            </div>
                        )}

                        {activeTab === 'usage' && (
                            <VaultDashboard 
                                ledgerEntries={ledgerEntries}
                                totalTokens={totalTokens}
                                expenditure={{}}
                                startingBalances={{}}
                                systemAudit={null}
                                isAuditLoading={false}
                                triggerKillSwitch={() => {}}
                                isKilling={false}
                            />
                        )}
                    </div>
                </div>

                <div className="p-6 border-t border-white/5 bg-black/40 flex items-center justify-between">
                    <div className="flex items-center gap-2 text-emerald-500/50">
                        <Lock size={12} />
                        <span className="text-[8px] font-black uppercase">Sovereign Encryption Active</span>
                    </div>
                    <div className="flex gap-3">
                        <button onClick={onClose} className="px-6 py-2.5 rounded-xl text-[10px] font-black uppercase text-zinc-500 hover:text-white transition-colors">Cancel</button>
                        <button 
                            onClick={saveAll}
                            className={`px-8 py-2.5 rounded-xl text-[10px] font-black uppercase transition-all flex items-center gap-2 ${saved ? 'bg-emerald-500 text-white' : 'bg-indigo-500 text-white'}`}
                        >
                            {saved ? <Check size={14} /> : <Database size={14} />}
                            {saved ? 'Vault Sealed' : 'Seal Vault'}
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default SettingsModal;
