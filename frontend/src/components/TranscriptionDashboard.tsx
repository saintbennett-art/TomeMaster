import React, { useEffect, useRef } from 'react';
import { Book, Zap, Search, Loader2, CheckCircle2, AlertCircle, Layers, GitMerge } from 'lucide-react';

type TranscriptionPhase = 'idle' | 'running' | 'indexing' | 'sewing' | 'stitching' | 'complete' | 'error' | 'audit';

interface TranscriptionDashboardProps {
    // The backend emits free-form phase strings; unknown phases fall back to idle styling.
    status: string;
    processedPages: number;
    totalPageGoal: number;
    isTranscribing: boolean;
    onStart: () => void;
    errorMessage?: string;
    providerName?: string;
    modelName?: string;
    currentImageB64?: string | null;
    missingPagesCount?: number;
}

const STATUS_CONFIG: Record<TranscriptionPhase, { label: string; color: string; icon: React.ReactNode; pulse: boolean }> = {
    idle:     { label: 'Awaiting Launch',   color: 'zinc',    icon: <Zap className="w-3 h-3" />,       pulse: false },
    indexing: { label: 'Scanning Artifacts', color: 'amber',  icon: <Search className="w-3 h-3" />,     pulse: true  },
    running:  { label: 'Digitizing',         color: 'indigo', icon: <Loader2 className="w-3 h-3" />,    pulse: true  },
    sewing:   { label: 'Assembling',         color: 'violet', icon: <Layers className="w-3 h-3" />,     pulse: true  },
    stitching:{ label: 'Injecting Pages',    color: 'cyan',   icon: <GitMerge className="w-3 h-3" />,   pulse: true  },
    complete: { label: 'Complete',           color: 'emerald',icon: <CheckCircle2 className="w-3 h-3" />,pulse: false },
    error:    { label: 'Error',              color: 'red',    icon: <AlertCircle className="w-3 h-3" />, pulse: false },
    audit:    { label: 'Audit Required',     color: 'orange', icon: <AlertCircle className="w-3 h-3" />, pulse: true  },
};

const COLOR_MAP: Record<string, { pill: string; bar: string; text: string }> = {
    zinc:    { pill: 'bg-zinc-800 text-zinc-400 border-zinc-700',           bar: 'bg-zinc-500',    text: 'text-zinc-400'   },
    amber:   { pill: 'bg-amber-500/10 text-amber-400 border-amber-500/20',  bar: 'bg-amber-500',   text: 'text-amber-400'  },
    indigo:  { pill: 'bg-indigo-500/10 text-indigo-400 border-indigo-500/20',bar: 'bg-indigo-500', text: 'text-indigo-400' },
    violet:  { pill: 'bg-violet-500/10 text-violet-400 border-violet-500/20',bar: 'bg-violet-500', text: 'text-violet-400' },
    cyan:    { pill: 'bg-cyan-500/10 text-cyan-400 border-cyan-500/20',     bar: 'bg-cyan-500',    text: 'text-cyan-400'   },
    emerald: { pill: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',bar:'bg-emerald-500',text:'text-emerald-400'},
    red:     { pill: 'bg-red-500/10 text-red-400 border-red-500/20',        bar: 'bg-red-500',     text: 'text-red-400'    },
    orange:  { pill: 'bg-orange-500/10 text-orange-400 border-orange-500/20',bar:'bg-orange-500',  text: 'text-orange-400' },
};

export function TranscriptionDashboard({
    status,
    processedPages,
    totalPageGoal,
    isTranscribing,
    onStart,
    errorMessage,
    providerName,
    modelName,
    currentImageB64,
    missingPagesCount = 0,
}: TranscriptionDashboardProps) {
    const cfg = STATUS_CONFIG[status as TranscriptionPhase] ?? STATUS_CONFIG.idle;
    const colors = COLOR_MAP[cfg.color];
    const percentage = totalPageGoal > 0 ? Math.round((processedPages / totalPageGoal) * 100) : 0;
    const remaining = Math.max(0, (totalPageGoal || 0) - (processedPages || 0));

    // Auto-scroll the status ticker to the latest message
    const tickerRef = useRef<HTMLDivElement>(null);
    useEffect(() => {
        if (tickerRef.current) tickerRef.current.scrollTop = tickerRef.current.scrollHeight;
    }, [errorMessage]);

    const isActive = status !== 'idle' && status !== 'complete' && status !== 'error';

    return (
        <div className="bg-zinc-950/90 backdrop-blur-xl border border-white/10 rounded-3xl p-5 w-[22rem] shadow-2xl flex flex-col gap-4">

            {/* Header */}
            <div className="flex items-center gap-3">
                <div className="p-2.5 bg-indigo-500/10 rounded-2xl border border-indigo-500/20 shrink-0">
                    <Book className="w-5 h-5 text-indigo-400" />
                </div>
                <div className="min-w-0">
                    <h2 className="text-white font-black text-[11px] tracking-tighter uppercase leading-none">Ingestion Engine</h2>
                    <p className="text-[9px] text-zinc-500 font-bold uppercase tracking-widest mt-0.5">
                        {providerName ? `${providerName.toUpperCase()}${modelName ? ` · ${modelName}` : ''}` : 'Manuscript Digitization'}
                    </p>
                </div>
                <div className="ml-auto shrink-0">
                    <div className={`px-2.5 py-1 rounded-full text-[8px] font-black uppercase tracking-widest flex items-center gap-1.5 border ${colors.pill} ${cfg.pulse ? 'animate-pulse' : ''}`}>
                        <span className={cfg.pulse ? 'animate-spin' : ''}>{cfg.icon}</span>
                        {cfg.label}
                    </div>
                </div>
            </div>

            {/* Progress numbers */}
            <div className="flex justify-between items-end">
                <div>
                    <span className="text-5xl font-black text-white tracking-tighter leading-none">{processedPages}</span>
                    <span className="text-[9px] text-zinc-500 font-bold uppercase ml-2 tracking-widest">Pages Done</span>
                </div>
                <div className="text-right">
                    <span className={`text-lg font-black tracking-tighter ${colors.text}`}>{percentage}%</span>
                    <p className="text-[8px] text-zinc-600 font-black uppercase tracking-widest">of {totalPageGoal || '?'}</p>
                </div>
            </div>

            {/* Progress bar */}
            <div className="h-1.5 bg-white/5 rounded-full overflow-hidden border border-white/5">
                <div
                    className={`h-full ${colors.bar} transition-all duration-700 ease-out ${isActive && percentage === 0 ? 'animate-pulse w-full opacity-30' : ''}`}
                    style={isActive && percentage === 0 ? {} : { width: `${percentage}%` }}
                />
            </div>

            {/* Stats row */}
            <div className="grid grid-cols-3 gap-2">
                <div className="p-2 bg-white/[0.02] border border-white/5 rounded-xl flex flex-col items-center">
                    <span className="text-[10px] font-mono text-zinc-300 font-bold">{totalPageGoal || '—'}</span>
                    <span className="text-[7px] text-zinc-600 font-black uppercase tracking-wide mt-0.5">Total</span>
                </div>
                <div className="p-2 bg-white/[0.02] border border-white/5 rounded-xl flex flex-col items-center">
                    <span className="text-[10px] font-mono text-zinc-300 font-bold">{processedPages}</span>
                    <span className="text-[7px] text-zinc-600 font-black uppercase tracking-wide mt-0.5">Done</span>
                </div>
                <div className="p-2 bg-white/[0.02] border border-white/5 rounded-xl flex flex-col items-center">
                    <span className={`text-[10px] font-mono font-bold ${missingPagesCount > 0 ? 'text-orange-400' : 'text-zinc-300'}`}>{missingPagesCount}</span>
                    <span className="text-[7px] text-zinc-600 font-black uppercase tracking-wide mt-0.5">Missing</span>
                </div>
            </div>

            {/* [FIDELITY]: Sequence Disruption Alert */}
            {missingPagesCount > 0 && (
                <div className="bg-orange-500/10 border border-orange-500/20 rounded-2xl px-4 py-3 flex items-center gap-3">
                    <AlertCircle className="w-4 h-4 text-orange-400 shrink-0" />
                    <div className="min-w-0">
                        <p className="text-[9px] text-orange-300 font-black uppercase tracking-widest leading-none">Sequence Disrupted</p>
                        <p className="text-[8px] text-orange-400/60 font-bold mt-1 uppercase tracking-tighter">
                            {missingPagesCount} disruption(s) detected in the manuscript.
                        </p>
                    </div>
                </div>
            )}

            {/* Live page thumbnail — shows the actual manuscript page being digitized */}
            {currentImageB64 && status === 'running' && (
                <div className="relative rounded-xl overflow-hidden border border-white/10 bg-black/40">
                    <img
                        src={`data:image/jpeg;base64,${currentImageB64}`}
                        alt="Page being digitized"
                        className="w-full object-contain max-h-36 opacity-80"
                    />
                    <div className="absolute bottom-0 left-0 right-0 px-2 py-1 bg-black/70 flex items-center gap-1.5">
                        <Loader2 className={`w-2.5 h-2.5 ${colors.text} animate-spin shrink-0`} />
                        <span className={`text-[8px] font-black uppercase tracking-widest ${colors.text}`}>
                            Scanning live
                        </span>
                    </div>
                </div>
            )}

            {/* Live status ticker — always shown when there's a message */}
            {errorMessage && (
                <div
                    ref={tickerRef}
                    className="bg-black/40 border border-white/5 rounded-xl px-3 py-2 max-h-16 overflow-y-auto"
                >
                    <p className={`text-[9px] font-mono leading-relaxed break-words ${isActive ? colors.text : 'text-zinc-500'}`}>
                        {isActive && <span className="inline-block w-1.5 h-1.5 rounded-full bg-current mr-1.5 mb-0.5 animate-pulse" />}
                        {errorMessage}
                    </p>
                </div>
            )}

            {/* Action area */}
            {status === 'complete' ? (
                <div className="w-full py-2.5 bg-emerald-500/10 text-emerald-400 text-[9px] font-black uppercase tracking-[0.3em] rounded-2xl border border-emerald-500/20 text-center">
                    Transcription Complete
                </div>
            ) : (
                <button
                    onClick={onStart}
                    disabled={isTranscribing}
                    className={`w-full py-3.5 rounded-2xl font-black text-[10px] uppercase tracking-[0.2em] transition-all flex items-center justify-center gap-2.5 ${
                        isTranscribing
                            ? `${colors.pill} border cursor-not-allowed`
                            : 'bg-indigo-600 hover:bg-indigo-500 text-white shadow-lg shadow-indigo-500/20 hover:scale-[1.02] active:scale-[0.98]'
                    }`}
                >
                    {isTranscribing ? (
                        <>
                            <Loader2 className="w-3.5 h-3.5 animate-spin" />
                            {cfg.label}...
                        </>
                    ) : (
                        <>
                            <Zap className="w-3.5 h-3.5" />
                            Start Industrial Transcription
                        </>
                    )}
                </button>
            )}
        </div>
    );
}
