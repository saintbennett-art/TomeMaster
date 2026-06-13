"use client";

import React from 'react';
import { 
    Activity, 
    ShieldCheck, 
    Cpu, 
    Database,
    Zap,
    Scroll,
    Loader2,
    Check,
    AlertCircle
} from 'lucide-react';
import { LedgerEntry, SystemAudit } from '@/types/industrial';

interface VaultDashboardProps {
    ledgerEntries: LedgerEntry[];
    totalTokens: number;
    expenditure: Record<string, number>;
    startingBalances: Record<string, number>;
    systemAudit: SystemAudit | null;
    isAuditLoading: boolean;
    triggerKillSwitch: () => void;
    isKilling: boolean;
}

export const VaultDashboard: React.FC<VaultDashboardProps> = ({
    ledgerEntries,
    totalTokens,
    expenditure,
    startingBalances,
    systemAudit,
    isAuditLoading,
    triggerKillSwitch,
    isKilling
}) => {
    return (
        <div className="space-y-6">
            {/* Credits & Consumption */}
            <div className="grid grid-cols-3 gap-3">
                <div className="bg-black/40 border border-white/5 rounded-2xl p-4">
                    <p className="text-[8px] font-black text-zinc-500 uppercase tracking-widest mb-1">Total Intelligence Flow</p>
                    <div className="flex items-end gap-2">
                        <span className="text-xl font-black text-indigo-400">{(totalTokens / 1000).toFixed(1)}k</span>
                        <span className="text-[10px] text-zinc-600 font-bold uppercase mb-1">Tokens</span>
                    </div>
                </div>
                <div className="bg-black/40 border border-white/5 rounded-2xl p-4">
                    <p className="text-[8px] font-black text-zinc-500 uppercase tracking-widest mb-1">Logged AI Calls</p>
                    <div className="flex items-end gap-2">
                        <span className="text-xl font-black text-emerald-400">
                            {ledgerEntries.length}
                        </span>
                        <span className="text-[10px] text-zinc-600 font-bold uppercase mb-1">Calls</span>
                    </div>
                </div>
                <div className="bg-black/40 border border-white/5 rounded-2xl p-4">
                    <p className="text-[8px] font-black text-zinc-500 uppercase tracking-widest mb-1">Vault Status</p>
                    <div className="flex items-center gap-2 mt-1">
                        <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse shadow-[0_0_10px_rgba(16,185,129,0.5)]" />
                        <span className="text-[10px] text-zinc-300 font-black uppercase">Sealed</span>
                    </div>
                </div>
            </div>

            {/* Hardware Audit */}
            <div className="bg-black/40 border border-white/5 rounded-2xl p-4">
                <div className="flex items-center justify-between mb-4">
                    <div className="flex items-center gap-2">
                        <Cpu className="w-4 h-4 text-indigo-400" />
                        <h4 className="text-xs font-black text-foreground uppercase tracking-tight">Directorial Hardware Audit</h4>
                    </div>
                    {isAuditLoading && <Loader2 className="w-3 h-3 animate-spin text-indigo-500" />}
                </div>
                
                {systemAudit ? (
                    <div className="grid grid-cols-2 gap-4">
                        <div className="space-y-2">
                            <div className="flex items-center justify-between">
                                <span className="text-[8px] font-bold text-zinc-500 uppercase">Architecture</span>
                                <span className="text-[10px] text-zinc-300 font-mono">{systemAudit.os || 'Unknown'}</span>
                            </div>
                            <div className="flex items-center justify-between">
                                <span className="text-[8px] font-bold text-zinc-500 uppercase">Memory Latency</span>
                                <span className={`text-[10px] font-mono ${systemAudit.ram_total > 15 ? 'text-emerald-400' : 'text-orange-400'}`}>
                                    {systemAudit.ram_total ? `${systemAudit.ram_total}GB` : 'Checking...'}
                                </span>
                            </div>
                        </div>
                        <div className="space-y-2">
                            <div className="flex items-center justify-between">
                                <span className="text-[8px] font-bold text-zinc-500 uppercase">Local Mode Capacity</span>
                                <span className={`text-[10px] font-black uppercase ${systemAudit.ram_total > 15 ? 'text-emerald-500' : 'text-rose-500'}`}>
                                    {systemAudit.ram_total > 15 ? 'Optimized' : 'Saturated'}
                                </span>
                            </div>
                            <div className="flex items-center justify-between">
                                <span className="text-[8px] font-bold text-zinc-500 uppercase">LPU Handshake</span>
                                <span className="text-[10px] text-emerald-400 font-black uppercase">Verified</span>
                            </div>
                        </div>
                    </div>
                ) : (
                    <p className="text-[9px] text-zinc-600 italic">Initiating hardware scan...</p>
                )}
            </div>

            {/* Recent Intelligence Log */}
            <div className="bg-black/20 border border-white/5 rounded-2xl overflow-hidden">
                <div className="p-4 border-b border-white/5 bg-black/20 flex items-center justify-between">
                    <div className="flex items-center gap-2">
                        <Scroll className="w-4 h-4 text-indigo-400" />
                        <h4 className="text-xs font-black text-foreground uppercase tracking-tight">Intelligence Ledger</h4>
                    </div>
                    <span className="text-[8px] font-black text-zinc-600 uppercase tracking-widest">{ledgerEntries.length} Operations logged</span>
                </div>
                <div className="max-h-[200px] overflow-y-auto custom-scrollbar">
                    {ledgerEntries.length > 0 ? (
                        <table className="w-full text-left border-collapse">
                            <thead>
                                <tr className="bg-black/40">
                                    <th className="p-3 text-[8px] font-black text-zinc-500 uppercase tracking-widest border-b border-white/5">Operation</th>
                                    <th className="p-3 text-[8px] font-black text-zinc-500 uppercase tracking-widest border-b border-white/5">Provider</th>
                                    <th className="p-3 text-[8px] font-black text-zinc-500 uppercase tracking-widest border-b border-white/5">Cost</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-white/5">
                                {ledgerEntries.slice(0, 50).map((entry, idx) => (
                                    <tr key={idx} className="hover:bg-white/5 transition-colors">
                                        <td className="p-3">
                                            <p className="text-[9px] text-zinc-300 font-bold uppercase truncate max-w-[120px]">{entry.action || 'Analysis'}</p>
                                            <p className="text-[7px] text-zinc-600 font-mono mt-0.5">{new Date((entry.timestamp ?? 0) * 1000).toLocaleTimeString()}</p>
                                        </td>
                                        <td className="p-3">
                                            <span className="text-[8px] font-black text-indigo-400 uppercase tracking-tighter bg-indigo-500/10 px-1.5 py-0.5 rounded border border-indigo-500/20">{entry.provider}</span>
                                        </td>
                                        <td className="p-3">
                                            <span className="text-[10px] text-zinc-400 font-mono">{((entry.metrics?.total_tokens ?? 0) / 1000).toFixed(1)}k</span>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    ) : (
                        <div className="p-10 text-center">
                            <Database className="w-8 h-8 text-zinc-800 mx-auto mb-3" />
                            <p className="text-[10px] text-zinc-600 font-bold uppercase">No intelligence history found in current vault.</p>
                        </div>
                    )}
                </div>
            </div>

            {/* Kill Switch */}
            <div className="pt-4 flex justify-center">
                <button 
                    onClick={triggerKillSwitch}
                    disabled={isKilling}
                    className="flex items-center gap-2 px-6 py-2 bg-rose-500/10 border border-rose-500/30 rounded-xl text-rose-500 text-[9px] font-black uppercase hover:bg-rose-500 hover:text-white transition-all group"
                >
                    <Zap className={`w-3 h-3 ${isKilling ? 'animate-spin' : 'group-hover:scale-125 transition-transform'}`} />
                    {isKilling ? 'Terminating Service...' : 'Execute Directorial Kill-Switch'}
                </button>
            </div>
        </div>
    );
};
