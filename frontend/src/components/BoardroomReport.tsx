"use client";
import React, { useState } from 'react';
import { X, CheckCircle, RefreshCcw, Save, Maximize2, Minimize2, LayoutList, Pen, Users, Megaphone, Film, Sparkles, AlertTriangle, ArrowRight, Volume2, VolumeX, BookOpen } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import ReactMarkdown from 'react-markdown';
import { useTextToSpeech } from '@/hooks/useTextToSpeech';
import { exportDocx } from '@/lib/apiClient';

interface Suggestion {
    id: string;
    type: 'replace' | 'insert' | 'metadata';
    label?: string;
    original?: string;
    suggestion?: string;
    content?: string;
    reason: string;
}

interface AgentReport {
    feedback: string;
    suggestions: Suggestion[];
    raw_edits?: any[];
    _accounting?: {
        model_audit: string;
        credits_consumed: number;
        unit: string;
        succeeded: boolean;
    };
}

interface BoardroomReportProps {
    isOpen: boolean;
    onClose: () => void;
    arcData: any[];
    chapters: any[];
    agentReports: Record<string, AgentReport>;
    onApplySuggestion: (suggestion: Suggestion) => void;
    onRegenerate?: () => void;
    isAnalyzing?: boolean;
    selectedAgents?: string[];
}

const AGENT_META: Record<string, any> = {
    'Developmental Editor': { icon: LayoutList, color: 'text-indigo-400', bg: 'bg-indigo-500/10', border: 'border-indigo-500/30' },
    'Copy Editor': { icon: Pen, color: 'text-blue-400', bg: 'bg-blue-500/10', border: 'border-blue-500/30' },
    'Sensitivity Reader': { icon: Users, color: 'text-amber-400', bg: 'bg-amber-500/10', border: 'border-amber-500/30' },
    'Marketing Executive': { icon: Megaphone, color: 'text-emerald-400', bg: 'bg-emerald-500/10', border: 'border-emerald-500/30' },
    'Hollywood Screenwriter': { icon: Film, color: 'text-purple-400', bg: 'bg-purple-500/10', border: 'border-purple-500/30' },
    'TomeMaster Guide': { icon: BookOpen, color: 'text-indigo-400', bg: 'bg-indigo-500/10', border: 'border-indigo-500/30' },
};

export default function BoardroomReport({ isOpen, onClose, arcData, chapters, agentReports, onApplySuggestion, onRegenerate, isAnalyzing }: BoardroomReportProps) {
    const [activeAgent, setActiveAgent] = useState(Object.keys(agentReports)[0] || 'Developmental Editor');
    const [appliedIds, setAppliedIds] = useState<Set<string>>(new Set());
    const [isExporting, setIsExporting] = useState(false);
    const [viewMode, setViewMode] = useState<'critique' | 'audit'>('critique');
    const [isMaximized, setIsMaximized] = useState(false);
    const { speak, stop, isPlaying: isSpeakingCritique } = useTextToSpeech();

    // Update active agent if reports change and current one is gone
    const agents = Object.keys(agentReports);
    if (isOpen && agents.length > 0 && !agents.includes(activeAgent)) {
        setActiveAgent(agents[0]);
    }

    if (!isOpen) return null;

    const currentReport = agentReports[activeAgent];
    const meta = AGENT_META[activeAgent] || { icon: Sparkles, color: 'text-zinc-400', bg: 'bg-zinc-500/10', border: 'border-zinc-500/30' };

    const handleApply = (s: Suggestion) => {
        onApplySuggestion(s);
        setAppliedIds(prev => {
            const next = new Set(prev);
            next.add(s.id);
            return next;
        });
    };

    const handleExportFullAudit = async () => {
        setIsExporting(true);
        try {
            let md = "# Tome-Master Boardroom Audit Report\n\n";
            
            // Using the synchronized high-sensitivity cleaning logic
            const cleanse = (text: string) => {
                if (!text) return "";
                // Split jammed headings (OldTitleNewTitle) into 'Old Title : New Title'
                let cleaned = text.replace(/([a-z])([A-Z])/g, '$1 : $2').trim();
                // Strip structural boilerplate: Chapter, Prologue, etc.
                cleaned = cleaned.replace(/^(Chapter|Prologue|Epilogue|Part|Scene|Section)\s*(\d+|[IVXLCDM]+)?\s*[:\-]?\s*/i, '').trim();
                return cleaned;
            };

            md += "## Structural Rhythm & Pacing Map\n";
            md += "| Chapter Heading | Reading Time | Status |\n";
            md += "| :--- | :--- | :--- |\n";
            chapters.forEach((c, i) => {
                const title = (c.suggested_title || c.cleaned_anchor || `Break ${i+1}`).substring(0, 60);
                const isFrontMatter = /Prelude|Forward|Title Page|Dedication|Table of Contents|Front Matter/i.test(title);
                if ((c.chapter_word_count || 0) < 250 || isFrontMatter) return;
                
                const mins = c.reading_time_mins || 1;
                const status = mins > 20 ? "⚠️ RHYTHM VIOLATION" : "✅ OK";
                md += `| ${title} | ${mins} mins | ${status} |\n`;
            });
            md += "\n\n";

            md += "## Chapter Breakdown & Narrative Anchors\n";
            md += "| Chapter Heading | Duration | Narrative Anchor (First 15 Words of Prose) |\n";
            md += "| :--- | :--- | :--- |\n";
            chapters.forEach((c, i) => {
                const title = c.suggested_title || "Untitled Break";
                const isFrontMatter = /Prelude|Forward|Title Page|Dedication|Table of Contents|Front Matter/i.test(title);
                if ((c.chapter_word_count || 0) < 250 || isFrontMatter) return;
                
                // The anchor is now decoupled from the title and contains actual narrative text
                const anchor = c.cleaned_anchor || c.starting_words || "No narrative detected";
                const mins = c.reading_time_mins || 1;
                md += `| ${title} | ${mins}m | "${anchor}..." |\n`;
            });
            md += "\n\n";

            md += "## Emotional Tension & Visual Arc Map\n";
            md += "| Chapter Heading | Duration | Visual Tension | Score | Content Advisories |\n";
            md += "| :--- | :--- | :--- | :--- | :--- |\n";
            arcData.forEach((d, i) => {
                const title = (d.name || d.cleaned_anchor || `Point ${i+1}`).substring(0, 60);
                const isFrontMatter = /Prelude|Forward|Title Page|Dedication|Table of Contents|Front Matter/i.test(title);
                if ((d.chapter_word_count || 0) < 250 || isFrontMatter) return;
                
                const score = d.score || 5;
                const visual = "▓".repeat(Math.round(score)) + "░".repeat(10 - Math.round(score));
                const warnings = (d.warnings || []).map((w:any) => typeof w === 'string' ? w : w.label).join(", ") || "None";
                const duration = d.reading_time || 1;
                md += `| ${title} | ${duration}m | ${visual} | ${score}/10 | ${warnings} |\n`;
            });
            md += "\n\n";

            // Add each agent's feedback
            Object.entries(agentReports).forEach(([agent, report]) => {
                md += `## ${agent} Insight\n`;
                md += `${report.feedback}\n\n`;
            });

            // Use the centralized, hardened export bridge (now with native OS Picker support)
            await exportDocx(md, [], `Tome-Master_Audit_Report_${new Date().toISOString().split('T')[0]}`, "Tome-Master AI");
        } catch (err) {
            console.error(err);
            alert("Failed to connect to the Sovereign Engine for export. Is the backend running?");
        } finally {
            setIsExporting(false);
        }
    };

    return (
        <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 md:p-8">
            {/* Backdrop */}
            <div className="absolute inset-0 bg-background/90 backdrop-blur-xl transition-opacity animate-in fade-in duration-500" onClick={onClose} />
            
            {/* Main Dashboard */}
            <div className={`relative z-10 bg-background border border-border rounded-3xl shadow-2xl flex flex-col overflow-hidden transition-all duration-500 ease-in-out ${isMaximized ? 'w-full h-full' : 'w-full h-full max-w-7xl max-h-[90vh]'} animate-in zoom-in-95 fade-in`}>
                
                {/* Header Area */}
                <div className="flex items-center justify-between p-6 border-b border-border bg-surface/50 backdrop-blur-md">
                    <div className="flex items-center gap-4">
                        <div>
                            <h1 className="text-2xl font-black text-foreground tracking-tight">Boardroom Insight Report</h1>
                            <div className="flex items-center gap-4 mt-1">
                                <button 
                                    onClick={() => setViewMode('critique')}
                                    className={`text-xs font-bold uppercase tracking-widest transition-all ${viewMode === 'critique' ? 'text-accent' : 'text-muted hover:text-foreground'}`}
                                >
                                    Agent Critique
                                </button>
                                <div className="w-1 h-1 rounded-full bg-border-strong" />
                                <button 
                                    onClick={() => setViewMode('audit')}
                                    className={`text-xs font-bold uppercase tracking-widest transition-all ${viewMode === 'audit' ? 'text-accent' : 'text-muted hover:text-foreground'}`}
                                >
                                    Structural Audit
                                </button>
                            </div>
                        </div>
                    </div>
                    
                    <div className="flex items-center gap-3">
                        {onRegenerate && (
                            <button 
                                onClick={onRegenerate}
                                disabled={isAnalyzing}
                                className="flex items-center gap-2 px-4 py-2 bg-indigo-600/10 hover:bg-indigo-600/20 text-indigo-400 disabled:opacity-50 rounded-xl border border-indigo-500/30 transition-all text-sm font-bold shadow-[0_0_15px_rgba(129,140,248,0.1)]"
                                title="Run a brand new analysis with current manuscript edits"
                            >
                                <RefreshCcw className={`w-4 h-4 ${isAnalyzing ? 'animate-spin' : ''}`} />
                                {isAnalyzing ? "Analyzing..." : "Refresh Analysis"}
                            </button>
                        )}
                        <button
                            onClick={handleExportFullAudit}
                            disabled={isExporting}
                            className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-[12px] font-black uppercase tracking-widest transition-all shadow-lg shadow-indigo-500/20 flex items-center justify-center gap-3"
                        >
                            {isExporting ? <RefreshCcw className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                            {isExporting ? "Generating..." : "Export"}
                        </button>
                        
                        <div className="h-8 w-[1px] bg-border mx-1"></div>

                        <button 
                            onClick={() => setIsMaximized(!isMaximized)}
                            title={isMaximized ? "Restore Window" : "Maximize Window"}
                            className="p-2.5 bg-surface hover:bg-indigo-500/10 text-muted hover:text-indigo-400 rounded-xl transition-all border border-border"
                        >
                            {isMaximized ? <Minimize2 className="w-5 h-5" /> : <Maximize2 className="w-5 h-5" />}
                        </button>

                        <button 
                            onClick={onClose}
                            title="Close Report"
                            className="p-2.5 bg-surface hover:bg-rose-500/20 text-muted hover:text-rose-400 rounded-xl transition-all border border-border hover:border-rose-500/30"
                        >
                            <X className="w-5 h-5" />
                        </button>
                    </div>
                </div>

                <div className="flex-1 flex overflow-hidden">
                    
                    {/* Left Navigation: Agents & Emotional Arc Summary */}
                    <div className="w-80 border-r border-border flex flex-col bg-background/50">
                        <div className="p-6">
                            <h2 className="text-[10px] font-black text-muted-foreground uppercase tracking-[0.2em] mb-4">Board of Directors</h2>
                            <div className="space-y-2">
                                {agents.map(agent => {
                                    const m = AGENT_META[agent] || { icon: Sparkles, color: 'text-muted-foreground' };
                                    return (
                                        <button
                                            key={agent}
                                            onClick={() => setActiveAgent(agent)}
                                            className={`w-full flex items-center gap-3 p-3.5 rounded-2xl transition-all border ${activeAgent === agent ? 'bg-accent/10 border-accent/30 text-foreground' : 'border-transparent text-muted hover:bg-surface-hover hover:text-foreground'}`}
                                        >
                                            <m.icon className={`w-5 h-5 ${activeAgent === agent ? m.color : 'text-muted-foreground'}`} />
                                            <span className="text-sm font-bold tracking-tight">{agent}</span>
                                            {activeAgent === agent && <div className="ml-auto w-1.5 h-1.5 rounded-full bg-accent shadow-[0_0_8px_rgba(16,185,129,0.8)]" />}
                                        </button>
                                    );
                                })}
                            </div>
                        </div>

                        <div className="mt-auto p-6 border-t border-border bg-surface/30">
                            <div className="flex items-center justify-between mb-4">
                                <h3 className="text-[10px] font-black text-muted-foreground uppercase tracking-[0.2em]">Emotional Tension</h3>
                                {arcData.length > 0 && <span className="text-[10px] font-bold text-accent bg-accent/10 px-2 py-0.5 rounded-full border border-accent/20">LIVE ARC</span>}
                            </div>
                            <div className="h-32 w-full">
                                {arcData.length > 0 ? (
                                    <ResponsiveContainer width="100%" height="100%">
                                        <LineChart data={arcData}>
                                            <Line type="monotone" dataKey="score" stroke="var(--accent)" strokeWidth={3} dot={false} />
                                        </LineChart>
                                    </ResponsiveContainer>
                                ) : (
                                    <div className="h-full border border-dashed border-border rounded-xl flex items-center justify-center text-[10px] text-muted font-bold uppercase italic">No Arc Data</div>
                                )}
                            </div>
                            <p className="text-[10px] text-muted mt-4 leading-relaxed font-medium">Emotional waypoints are calibrated based on prose density and narrative beats.</p>
                        </div>
                    </div>

                    {/* Main Content Area */}
                    <div className="flex-1 flex flex-col bg-background">
                        
                        {viewMode === 'critique' ? (
                            /* Report & Suggestions Grid */
                            <div key="critique-view" className="flex-1 overflow-y-auto p-8 lg:p-12 space-y-12 scrollbar-none hover:scrollbar-thin scrollbar-thumb-indigo-500/20">
                                
                                {/* Agent Persona Header */}
                                <div className="flex items-start gap-6">
                                    <div className={`p-5 ${meta.bg} ${meta.border} border rounded-3xl`}>
                                        <meta.icon className={`w-8 h-8 ${meta.color}`} />
                                    </div>
                                    <div>
                                        <div className="flex items-center gap-3 mb-1">
                                            <h2 className="text-3xl font-black text-foreground tracking-tighter">{activeAgent}</h2>
                                            {currentReport && (
                                                <button 
                                                    onClick={() => isSpeakingCritique ? stop() : speak(currentReport.feedback)}
                                                    className={`p-2 rounded-xl transition-all ${isSpeakingCritique ? 'bg-indigo-500/20 text-indigo-400' : 'bg-zinc-800 text-zinc-400 hover:text-indigo-400'}`}
                                                    title={isSpeakingCritique ? "Stop Reading" : "Listen to Critique"}
                                                >
                                                    {isSpeakingCritique ? <VolumeX className="w-5 h-5" /> : <Volume2 className="w-5 h-5" />}
                                                </button>
                                            )}
                                        </div>
                                        <div className="flex items-center gap-3">
                                            <span className="text-xs font-bold text-indigo-400 bg-indigo-500/10 px-3 py-1 rounded-full border border-indigo-500/20 tracking-wider">CRITIQUE COMPLETE</span>
                                            <span className="text-xs font-bold text-emerald-400 bg-emerald-500/10 px-3 py-1 rounded-full border border-emerald-500/20 tracking-wider">100% PRIVATE</span>
                                        </div>
                                    </div>
                                </div>

                                {/* Two Column Layout: Detailed Report vs Actionable Items */}
                                <div className="grid grid-cols-1 lg:grid-cols-5 gap-12">
                                    
                                    {/* Left: Detailed Markdown Report */}
                                    <div className="lg:col-span-3">
                                        <div className="prose prose-invert prose-indigo max-w-none prose-headings:text-foreground prose-p:text-muted prose-p:leading-relaxed prose-strong:text-foreground prose-li:text-muted prose-blockquote:border-accent/50 prose-blockquote:bg-accent/5 prose-blockquote:py-1 prose-blockquote:rounded-r-lg">
                                            <ReactMarkdown>{currentReport?.feedback || "Generating in-depth narrative audit..."}</ReactMarkdown>
                                        </div>

                                        {/* Sovereign Accounting Seal: Visible Transparency for Failover logic */}
                                        {currentReport?._accounting && (
                                            <div className="mt-12 p-6 rounded-3xl bg-surface/50 border border-border flex items-center justify-between group hover:border-accent/30 transition-all border-dashed">
                                                <div className="flex items-center gap-4">
                                                    <div className="w-10 h-10 rounded-full bg-accent/10 border border-accent/20 flex items-center justify-center text-accent">
                                                        <CheckCircle className="w-5 h-5" />
                                                    </div>
                                                    <div>
                                                        <h4 className="text-[10px] font-black text-muted-foreground uppercase tracking-widest mb-1">Architectural Handshake Approved</h4>
                                                        <p className="text-sm font-bold text-foreground">Audit Engine: <span className="text-accent">{currentReport._accounting.model_audit}</span></p>
                                                    </div>
                                                </div>
                                                <div className="text-right">
                                                    <h4 className="text-[10px] font-black text-muted-foreground uppercase tracking-widest mb-1">Credit Impact</h4>
                                                    <p className="text-sm font-black text-foreground">{currentReport._accounting.credits_consumed} <span className="text-muted-foreground font-bold">{currentReport._accounting.unit}</span></p>
                                                </div>
                                            </div>
                                        )}
                                    </div>

                                    {/* Right: Actionable Suggestions */}
                                    <div className="lg:col-span-2 space-y-6">
                                        <h3 className="text-[10px] font-black text-muted-foreground uppercase tracking-[0.2em] mb-6 flex items-center gap-2">
                                            <Sparkles className="w-3 h-3 text-emerald-400" /> Actionable Improvements
                                        </h3>
                                        
                                        <div className="space-y-4">
                                            {currentReport?.suggestions && currentReport.suggestions.length > 0 ? (
                                                currentReport.suggestions.map((s, idx) => (
                                                    <div 
                                                        key={s.id || `suggest-${idx}`} 
                                                        className={`group p-6 rounded-3xl border transition-all ${appliedIds.has(s.id) ? 'bg-surface border-border opacity-60' : 'bg-surface border-border hover:border-accent/50 hover:shadow-2xl shadow-black/50'}`}
                                                    >
                                                        <div className="flex items-center justify-between mb-4">
                                                            <div className="flex items-center gap-2">
                                                                <div className={`p-1.5 rounded-lg ${s.type === 'replace' ? 'bg-accent/20 text-accent' : 'bg-emerald-500/20 text-emerald-400'}`}>
                                                                    {s.type === 'replace' ? <RefreshCcw className="w-3 h-3" /> : <Sparkles className="w-3 h-3" />}
                                                                </div>
                                                                <span className="text-[10px] font-black text-muted uppercase tracking-widest">{s.type === 'replace' ? 'Stylistic Edit' : 'New Content'}</span>
                                                            </div>
                                                            {appliedIds.has(s.id) && <span className="text-[10px] font-bold text-emerald-400 flex items-center gap-1"><CheckCircle className="w-3 h-3" /> Applied</span>}
                                                        </div>

                                                        <h4 className="text-sm font-bold text-foreground mb-2 leading-snug">{s.label || (s.type === 'replace' ? 'Refine Passage' : 'Insert Component')}</h4>
                                                        <p className="text-xs text-muted leading-relaxed font-medium line-clamp-2 mb-4 italic">"{s.reason}"</p>

                                                        <button 
                                                            onClick={() => handleApply(s)}
                                                            disabled={appliedIds.has(s.id)}
                                                            title={appliedIds.has(s.id) ? "Already applied" : "Apply this suggestion to your manuscript"}
                                                            className={`w-full py-3 rounded-2xl font-black text-[10px] uppercase tracking-widest transition-all flex items-center justify-center gap-2 ${appliedIds.has(s.id) ? 'bg-background text-muted' : 'bg-accent hover:bg-emerald-600 text-white shadow-lg'}`}
                                                        >
                                                            {appliedIds.has(s.id) ? 'Integrated Into MS' : 'Modify Manuscript'} <ArrowRight className="w-3.5 h-3.5" />
                                                        </button>
                                                    </div>
                                                ))
                                            ) : (
                                                <div className="p-8 border border-dashed border-border rounded-3xl flex flex-col items-center justify-center text-center gap-3">
                                                    <AlertTriangle className="w-5 h-5 text-muted" />
                                                    <p className="text-[10px] font-black text-muted uppercase tracking-widest">No Direct Edits Found</p>
                                                    <p className="text-xs text-muted-foreground font-medium leading-relaxed italic px-6">The agent has provided macro-level structural feedback instead of line-level edits.</p>
                                                </div>
                                            )}
                                        </div>
                                    </div>
                                </div>
                            </div>
                        ) : (
                            /* Structural Audit Mode: PURIFIED LIVE VIEW */
                            <div key="audit-view" className="flex-1 overflow-y-auto p-8 lg:p-16 scrollbar-none hover:scrollbar-thin scrollbar-thumb-indigo-500/20">
                                <div className="max-w-5xl mx-auto space-y-16 animate-in slide-in-from-bottom-4 duration-700">
                                    <div className="flex items-end justify-between border-b border-border pb-8">
                                        <div>
                                            <h2 className="text-4xl font-black text-foreground tracking-tighter mb-3">Structural Audit</h2>
                                            <div className="flex items-center gap-3">
                                                <span className="text-[10px] font-black text-accent bg-accent/10 px-3 py-1 rounded-full border border-accent/20 tracking-[0.2em] uppercase">Purity Level: High</span>
                                                <span className="text-[10px] font-black text-emerald-400 bg-emerald-500/10 px-3 py-1 rounded-full border border-emerald-500/20 tracking-[0.2em] uppercase">Front-Matter Scrubbed</span>
                                            </div>
                                        </div>
                                        <div className="flex flex-col items-end">
                                            <span className="text-[10px] font-black text-muted uppercase tracking-[0.2em]">Net Word Count</span>
                                            <span className="text-2xl font-black text-foreground">{chapters.filter(c => (c.chapter_word_count||0) >= 250).reduce((acc, c) => acc + (c.chapter_word_count || 0), 0).toLocaleString()}</span>
                                        </div>
                                    </div>

                                    <div className="overflow-hidden border border-border rounded-[40px] bg-surface shadow-2xl">
                                        <table className="w-full text-left border-collapse">
                                            <thead>
                                                <tr className="bg-background border-b border-border">
                                                    <th className="px-8 py-5 text-[10px] font-black text-muted uppercase tracking-widest">Chapter Heading</th>
                                                    <th className="px-8 py-5 text-[10px] font-black text-muted uppercase tracking-widest">Reader Pacing</th>
                                                    <th className="px-8 py-5 text-[10px] font-black text-muted uppercase tracking-widest">Narrative Anchor (Live Story Prose)</th>
                                                </tr>
                                            </thead>
                                            <tbody className="divide-y divide-border/50">
                                                {chapters.map((c, i) => {
                                                    const title = c.suggested_title || "Untitled Break";
                                                    const isFrontMatter = /Prelude|Forward|Title Page|Dedication|Table of Contents|Front Matter/i.test(title);
                                                    if ((c.chapter_word_count || 0) < 250 || isFrontMatter) return null;

                                                    const mins = c.reading_time_mins || 1;
                                                    // Strictly pull from the prose-purified anchor
                                                    const anchor = c.cleaned_anchor || "Searching for story beats...";

                                                    return (
                                                        <tr key={c.id || `chapter-${i}`} className="group hover:bg-accent/[0.02] transition-colors">
                                                            <td className="px-8 py-8">
                                                                <div className="font-black text-lg text-foreground group-hover:text-accent transition-colors tracking-tight">
                                                                    {title}
                                                                </div>
                                                            </td>
                                                            <td className="px-8 py-8">
                                                                <div className={`inline-flex items-center gap-2 px-3 py-1 rounded-full text-[10px] font-black border tracking-widest ${mins > 20 ? 'bg-rose-500/10 text-rose-400 border-rose-500/20' : 'bg-surface text-foreground border-border'}`}>
                                                                    {mins}M {mins > 20 && <div className="w-1.5 h-1.5 rounded-full bg-rose-500 animate-pulse" />}
                                                                </div>
                                                            </td>
                                                            <td className="px-8 py-8 max-w-sm">
                                                                <p className="text-[11px] text-muted font-medium italic leading-relaxed group-hover:text-foreground transition-colors">
                                                                    "{anchor.length > 120 ? anchor.substring(0, 120) + '...' : anchor}..."
                                                                </p>
                                                            </td>
                                                        </tr>
                                                    );
                                                })}
                                            </tbody>
                                        </table>
                                    </div>
                                    
                                    <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
                                        <div className="group p-8 bg-surface border border-border rounded-[32px] hover:border-accent/30 transition-all">
                                            <h4 className="text-[10px] font-black text-muted uppercase tracking-widest mb-6">Story Chapters</h4>
                                            <p className="text-5xl font-black text-foreground tabular-nums tracking-tighter">{chapters.filter(c => (c.chapter_word_count||0) >= 250).length}</p>
                                        </div>
                                        <div className="group p-8 bg-accent/10 border border-accent/20 rounded-[32px] hover:border-accent/40 transition-all">
                                            <h4 className="text-[10px] font-black text-accent uppercase tracking-widest mb-6">Synthesis Forecast</h4>
                                            <p className="text-5xl font-black text-foreground tabular-nums tracking-tighter">
                                                {(currentReport?._accounting as any)?.processing_time || `${Math.max(15, Math.round(chapters.reduce((acc, c) => acc + (c.chapter_word_count || 0), 0) / 2000) + 10)}s`}
                                            </p>
                                        </div>
                                        <div className="group p-8 bg-emerald-500/10 border border-emerald-500/20 rounded-[32px] hover:border-emerald-500/40 transition-all">
                                            <h4 className="text-[10px] font-black text-emerald-400 uppercase tracking-widest mb-6">Data Purity</h4>
                                            <p className="text-5xl font-black text-foreground tabular-nums tracking-tighter">100<span className="text-xl ml-1 text-emerald-400/50">%</span></p>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        )}

                        {/* Status Bar */}
                        <div className="p-6 border-t border-border bg-background flex items-center justify-between">
                            <div className="flex items-center gap-4">
                                <div className="flex -space-x-2">
                                    {agents.map(a => {
                                        const m = AGENT_META[a] || { icon: Sparkles, color: 'text-muted-foreground' };
                                        return <div key={a} className={`w-8 h-8 rounded-full border-2 border-background flex items-center justify-center bg-surface ${m.color}`}><m.icon className="w-3.5 h-3.5" /></div>;
                                    })}
                                </div>
                                <span className="text-[10px] font-black text-muted-foreground uppercase tracking-widest leading-none">Tome-Master Intelligence System <span className="text-accent ml-2">V2.4.0</span></span>
                            </div>
                            <div className="flex items-center gap-1.5">
                                <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                                <span className="text-[10px] font-bold text-muted-foreground uppercase">System Ready</span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}

// Shorthand for icon addition in the dynamic sections
function Plus({ className }: { className?: string }) {
    return (
        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" className={className}>
            <path d="M5 12h14" /><path d="M12 5v14" />
        </svg>
    );
}
