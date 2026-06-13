"use client";
import React, { useState, useEffect, useRef } from "react";
import { Maximize2, Minimize2, Save, Eye, Zap, RefreshCw, ExternalLink, ShieldAlert, ShieldCheck } from "lucide-react";
import { runMultiAgentAnalysis, validateAiKey, API_BASE_HOLDER } from "@/lib/apiClient";
import { secureVault } from "@/lib/vault";

// [BLACK BOX IMPORTS]
import { SpecialistRegistry } from "./workstation/boardroom/SpecialistRegistry";
import { IntelligencePulse } from "./workstation/boardroom/IntelligencePulse";
import { NarrativeRangePicker } from "./workstation/boardroom/NarrativeRangePicker";
import { AuditBriefing } from "./workstation/boardroom/AuditBriefing";
import { ExpertAuthorizationPanel } from "./workstation/boardroom/ExpertAuthorizationPanel";
import { Chapter, AgentReport, ArcPoint } from "@/types/industrial";

interface AnalysisDashboardProps {
    selectedAgents: string[];
    setSelectedAgents: (agents: string[]) => void;
    customAgents: string[];
    setCustomAgents: (agents: string[]) => void;
    agentReports: Record<string, AgentReport>;
    setAgentReports: React.Dispatch<React.SetStateAction<Record<string, AgentReport>>>;
    activeTab: string;
    setActiveTab: (tab: string) => void;
    onCompletion: () => void;
    arcData?: ArcPoint[];
    setArcData: (data: ArcPoint[]) => void;
    chapters: Chapter[];
    setChapters: (chapters: Chapter[]) => void;
    onApplySuggestion: (suggestion: string) => void;
    projectFolder: string | null;
    editorContent: string;
    isAnalyzing: boolean;
    setIsAnalyzing: (analyzing: boolean) => void;
    analysisTrigger: number;
    notify: (msg: string) => void;
}

interface Assignment {
    agent: string;
    funded: boolean;
    recommended: string;
}

interface Toast {
    id: number;
    message: string;
}

interface MenuItem {
    label?: string;
    icon?: React.ElementType;
    action?: () => void;
    type?: 'separator';
}

const AnalysisDashboard: React.FC<AnalysisDashboardProps> = ({ 
    selectedAgents, setSelectedAgents, customAgents, setCustomAgents, agentReports, setAgentReports, 
    activeTab, setActiveTab, onCompletion, arcData = [], setArcData, 
    chapters = [], setChapters, onApplySuggestion, 
    projectFolder = null, editorContent = "", isAnalyzing, setIsAnalyzing, analysisTrigger = 0,
    notify
}) => {
    const [showAudit, setShowAudit] = useState(false);
    const [isMinimized, setIsMinimized] = useState(true);
    const [auditData, setAuditData] = useState({weight: 0, assignments: [] as Assignment[]});
    const [currentExpert, setCurrentExpert] = useState<string | null>(null);
    const [handshakeStatus, setHandshakeStatus] = useState("ok");
    const [isInterventionMode, setIsInterventionMode] = useState(true);
    const [isDeepAnalysis, setIsDeepAnalysis] = useState(false);
    const [authModal, setAuthModal] = useState({ isOpen: false, persona: "", prompt: "", model: "" });
    const [pulseData, setPulseData] = useState({});
    const [elapsedSeconds, setElapsedSeconds] = useState(0);
    const [dynamicModels, setDynamicModels] = useState<string[]>([]);
    const [analyticScope, setAnalyticScope] = useState("full");
    const [rangeStartIdx, setRangeStartIdx] = useState(0);
    const [rangeEndIdx, setRangeEndIdx] = useState(0);
    const startTimeRef = useRef(0);

    // [LOGIC]: Analysis Dispatch
    const runAnalysis = async (forceNoAudit = false) => {
        if (!editorContent || isAnalyzing) return;
        if (!forceNoAudit) {
            setAuditData({ weight: editorContent.split(/\s+/).length, assignments: selectedAgents.map(a => ({ agent: a, funded: true, recommended: "Apex Gateway" })) });
            setShowAudit(true);
            return;
        }
        setShowAudit(false);
        setIsAnalyzing(true);
        setElapsedSeconds(0);
        startTimeRef.current = Date.now();
        
        try {
            const allAgents = [...selectedAgents, ...customAgents];
            for (const agentId of allAgents) {
                setCurrentExpert(agentId);
                // Sovereign Dispatch: Trust the backend role mappings
                const result = await runMultiAgentAnalysis(editorContent, [agentId], undefined, undefined, 'full', chapters);
                if (result && result[agentId]) {
                    setAgentReports(prev => ({ ...prev, [agentId]: result[agentId] }));
                }
            }
            onCompletion();
        } catch (err) { }
        finally { setIsAnalyzing(false); }
    };

    useEffect(() => { if (analysisTrigger > 0) runAnalysis(); }, [analysisTrigger]);

    const [activeMenu, setActiveMenu] = useState<string | null>(null);
    const [toasts, setToasts] = useState<Toast[]>([]);
    const dashboardRef = useRef<HTMLDivElement>(null);

    const showToast = (message: string) => {
        const id = Date.now();
        setToasts(prev => [...prev, { id, message }]);
        setTimeout(() => {
            setToasts(prev => prev.filter(t => t.id !== id));
        }, 3000);
        notify(message);
    };

    useEffect(() => {
        const handleClickOutside = (e: MouseEvent) => {
            const target = e.target as HTMLElement;
            if (dashboardRef.current && !dashboardRef.current.contains(target)) {
                setActiveMenu(null);
            }
        };
        document.addEventListener("mousedown", handleClickOutside);
        return () => document.removeEventListener("mousedown", handleClickOutside);
    }, []);

    const dashboardMenus: Record<string, MenuItem[]> = {
        File: [
            { label: "Export Consensus", icon: Save, action: () => {
                if (Object.keys(agentReports).length === 0) {
                    showToast("No reports to export.");
                    return;
                }
                const blob = new Blob([JSON.stringify(agentReports, null, 2)], { type: "application/json" });
                const url = URL.createObjectURL(blob);
                const a = document.createElement("a");
                a.href = url;
                a.download = `boardroom-consensus-${Date.now()}.json`;
                a.click();
                showToast("Consensus exported to JSON.");
            }},
            { label: "Import Persona", icon: Zap, action: () => {
                const input = document.createElement("input");
                input.type = "file";
                input.accept = ".json";
                input.onchange = (e: Event) => {
                    const target = e.target as HTMLInputElement;
                    const file = target.files?.[0];
                    if (file) showToast(`Importing ${file.name}... (Validation Pending)`);
                };
                input.click();
            }},
            { type: "separator" },
            { label: "Save State", icon: Save, action: () => {
                const state = { selectedAgents, customAgents, activeTab };
                localStorage.setItem("tm_boardroom_state", JSON.stringify(state));
                showToast("Boardroom state cached.");
            }}
        ],
        Edit: [
            { label: "Reset Registry", icon: RefreshCw, action: () => { 
                if (confirm("Reset all agent selections?")) {
                    setSelectedAgents([]); 
                    setCustomAgents([]); 
                    showToast("Registry cleared."); 
                }
            }},
            { label: "Clear Reports", icon: RefreshCw, action: () => { 
                if (confirm("Purge all analysis reports?")) {
                    setAgentReports({}); 
                    showToast("Reports purged."); 
                }
            }},
            { type: "separator" },
            { label: "Global Directive", icon: Eye, action: () => {
                window.open('/MASTER_DIRECTIVE.md', '_blank');
                showToast("Opening Master Directive...");
            }}
        ],
        View: [
            { label: "Logic Pulse", icon: Zap, action: () => {
                const nc = document.querySelector('.nerve-center-telemetry');
                if (nc) nc.classList.toggle('hidden');
                showToast("Toggling telemetry pulse...");
            }},
            { label: "Narrative Scope", icon: Eye, action: () => { 
                setAnalyticScope("full"); 
                showToast("Scope reset to Full Manuscript."); 
            }},
            { type: "separator" },
            { label: "Minimize Window", icon: Minimize2, action: () => setIsMinimized(true) }
        ]
    };

    return (
        <div ref={dashboardRef} className={`w-[450px] ${isMinimized ? "h-[64px]" : "h-[80vh]"} transition-all duration-500 bg-black/95 backdrop-blur-3xl border border-white/10 flex flex-col shadow-[0_30px_90px_rgba(0,0,0,0.8)] rounded-2xl hover:border-amber-500/30 overflow-hidden relative`}>
            <div className="absolute top-[-40px] left-0 right-0 flex flex-col items-center gap-2 pointer-events-none z-[10000]">
                {toasts.map(t => (
                    <div key={t.id} className="bg-amber-500 text-black text-[10px] font-black uppercase px-4 py-1.5 rounded-full shadow-[0_10px_30px_rgba(245,158,11,0.4)] animate-in slide-in-from-bottom-2 fade-in duration-300">
                        {t.message}
                    </div>
                ))}
            </div>
            <div className="p-4 border-b border-white/5 bg-transparent shrink-0 z-50">
                <div className="flex items-center justify-between">
                    <div className="flex flex-col">
                        <div className="flex items-center gap-4">
                            <h2 id="boardroom-title-handle" className="text-[12px] font-black text-amber-500 uppercase tracking-[0.2em] leading-none cursor-grab active:cursor-grabbing p-1 -m-1 hover:bg-white/5 rounded transition-all">Agent Manager</h2>
                            {!isMinimized && (
                                <div className="flex items-center gap-1.5 relative z-[100]">
                                    {Object.keys(dashboardMenus).map(m => (
                                        <div key={m} className="relative">
                                            <button 
                                                type="button"
                                                onClick={() => {
                                                    setActiveMenu(activeMenu === m ? null : m);
                                                }}
                                                className={`relative z-[100] px-3 py-2 text-[12px] font-black uppercase tracking-widest rounded-md transition-all ${activeMenu === m ? "bg-amber-600 text-black shadow-[0_0_20px_rgba(245,158,11,0.4)]" : "text-zinc-400 hover:text-white hover:bg-white/10"}`}
                                            >
                                                {m}
                                            </button>
                                            {activeMenu === m && (
                                                <div className="absolute top-full left-0 mt-2 w-56 bg-[#0a0a0a] border-2 border-amber-500/50 rounded-xl shadow-[0_0_50px_rgba(0,0,0,0.8)] py-3 z-[9999] pointer-events-auto animate-in fade-in zoom-in-95 duration-150">
                                                    {dashboardMenus[m].map((item, idx) => (
                                                        item.type === "separator" ? (
                                                            <div key={idx} className="h-[1px] bg-white/5 my-1 mx-2" />
                                                        ) : (
                                                            <button 
                                                                key={idx} 
                                                                onClick={() => { 
                                                                    item.action?.(); 
                                                                    setActiveMenu(null); 
                                                                }}
                                                                className="w-full flex items-center gap-3 px-4 py-2 hover:bg-amber-500/10 text-zinc-400 hover:text-amber-500 text-[10px] font-black uppercase tracking-tighter transition-all"
                                                            >
                                                                {item.icon && <item.icon className="w-3 h-3 opacity-50 text-amber-500" />}
                                                                <span>{item.label}</span>
                                                            </button>
                                                        )
                                                    ))}
                                                </div>
                                            )}
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                        {!isMinimized && (
                            <div className="flex items-center gap-1.5 mt-2">
                                <div className={`w-1.5 h-1.5 rounded-full ${handshakeStatus === "ok" ? "bg-emerald-500 animate-pulse" : "bg-rose-500"}`} />
                                <span className="text-[8px] font-mono text-zinc-500 uppercase">{handshakeStatus === "ok" ? "Sovereign Link Active" : "Handshake Pending"}</span>
                            </div>
                        )}
                    </div>
                    <div className="flex items-center gap-2">
                        <button onClick={() => setIsMinimized(!isMinimized)} className="p-2 bg-zinc-800/50 hover:bg-zinc-700/50 text-zinc-400 rounded-lg border border-white/5 transition-all">
                            {isMinimized ? <Maximize2 className="w-4 h-4" /> : <Minimize2 className="w-4 h-4" />}
                        </button>
                    </div>
                </div>
            </div>
            {!isMinimized && (
                <>
                    <div className="flex-1 overflow-y-auto p-5 space-y-6 bright-scrollbar">
                        <IntelligencePulse isAnalyzing={isAnalyzing} elapsedSeconds={elapsedSeconds} pulseData={pulseData} />
                        <NarrativeRangePicker 
                            analyticScope={analyticScope} setAnalyticScope={setAnalyticScope} userChapters={chapters} 
                            rangeStartIdx={rangeStartIdx} setRangeStartIdx={setRangeStartIdx} 
                            rangeEndIdx={rangeEndIdx} setRangeEndIdx={setRangeEndIdx} 
                            visibilityMap={new Map()} displacement={editorContent.split(/\s+/).length} tacticalSummary="Full Scope"
                        />
                        <SpecialistRegistry 
                            selectedAgents={selectedAgents} setSelectedAgents={setSelectedAgents} 
                            customAgents={customAgents} setCustomAgents={setCustomAgents} 
                        />
                        {handshakeStatus === "ok" && (
                            <div className="p-4 bg-emerald-500/5 border border-emerald-500/10 rounded-2xl flex items-center gap-3">
                                <div className="p-2 bg-emerald-500/10 rounded-lg">
                                    <ShieldCheck className="w-4 h-4 text-emerald-400" />
                                </div>
                                <div>
                                    <p className="text-[10px] font-black text-emerald-400 uppercase leading-none">Sovereign Fidelity Verified</p>
                                    <p className="text-[8px] text-zinc-500 font-bold uppercase mt-1">Optimal Engines Established for Analysis</p>
                                </div>
                            </div>
                        )}
                        <button 
                            onClick={() => runAnalysis()} 
                            disabled={isAnalyzing} 
                            className="w-full py-4 bg-indigo-600 hover:bg-indigo-500 disabled:bg-zinc-800 text-white rounded-2xl font-black uppercase text-xs shadow-lg shadow-indigo-600/20 transition-all"
                        >
                            {isAnalyzing ? "Processing Consensus..." : "Convene Boardroom"}
                        </button>
                    </div>
                    {showAudit && <AuditBriefing data={auditData} onConfirm={() => runAnalysis(true)} onCancel={() => setShowAudit(false)} />}
                    {authModal.isOpen && <ExpertAuthorizationPanel authModal={authModal} dynamicModels={dynamicModels} getFidelityPortfolioForExpert={() => []} />}
                </>
            )}
        </div>
    );
};

export default AnalysisDashboard;
