import React from 'react';
import { Book, Zap, Search } from 'lucide-react';

interface TranscriptionDashboardProps {
    status: 'idle' | 'running' | 'indexing' | 'sewing' | 'complete' | 'error';
    processedPages: number;
    totalPageGoal: number;
    isTranscribing: boolean;
    onStart: () => void;
}

export function TranscriptionDashboard({ 
    status, 
    processedPages, 
    totalPageGoal, 
    isTranscribing,
    onStart 
}: TranscriptionDashboardProps) {
    const percentage = totalPageGoal > 0 ? Math.round((processedPages / totalPageGoal) * 100) : 0;
    
    return (
        <div className="bg-zinc-950/80 backdrop-blur-xl border border-white/10 rounded-3xl p-6 w-80 shadow-2xl flex flex-col gap-6">
            <div className="flex items-center gap-4">
                <div className="p-3 bg-indigo-500/10 rounded-2xl border border-indigo-500/20">
                    <Book className="w-6 h-6 text-indigo-400" />
                </div>
                <div>
                    <h2 className="text-white font-black text-sm tracking-tighter uppercase">Transcription Progress</h2>
                    <p className="text-[10px] text-zinc-500 font-bold uppercase tracking-widest">Manuscript Fidelity Track</p>
                </div>
                <div className="ml-auto">
                    <div className={`px-3 py-1 rounded-full text-[8px] font-black uppercase tracking-widest flex items-center gap-2 ${
                        isTranscribing ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 animate-pulse' : 'bg-zinc-800 text-zinc-500'
                    }`}>
                        <div className={`w-1.5 h-1.5 rounded-full ${isTranscribing ? 'bg-emerald-400' : 'bg-zinc-600'}`} />
                        {status === 'complete' ? 'Complete' : isTranscribing ? 'Engine Active' : 'Standby'}
                    </div>
                </div>
            </div>

            <div className="space-y-4">
                <div className="flex justify-between items-end">
                    <div>
                        <span className="text-4xl font-black text-white tracking-tighter">{processedPages}</span>
                        <span className="text-[10px] text-zinc-500 font-bold uppercase ml-2 tracking-widest">Pages Digitized</span>
                    </div>
                    <div className="text-right">
                        <span className="text-sm font-black text-indigo-400 tracking-tighter">{percentage}%</span>
                        <p className="text-[8px] text-zinc-600 font-black uppercase tracking-widest">Completion</p>
                    </div>
                </div>

                <div className="h-2 bg-white/5 rounded-full overflow-hidden border border-white/5">
                    <div 
                        className="h-full bg-indigo-500 transition-all duration-1000 ease-out"
                        style={{ width: `${percentage}%` }}
                    />
                </div>

                <div className="grid grid-cols-2 gap-3">
                    <div className="p-3 bg-white/[0.02] border border-white/5 rounded-2xl flex flex-col items-center">
                        <Book className="w-4 h-4 mb-1 text-zinc-600" />
                        <span className="text-xs font-mono text-zinc-300">{totalPageGoal}</span>
                        <span className="text-[7px] text-zinc-600 font-black uppercase">Goal</span>
                    </div>
                    <div className="p-3 bg-white/[0.02] border border-white/5 rounded-2xl flex flex-col items-center">
                        <Zap className={`w-4 h-4 mb-1 ${status === 'error' ? 'text-red-500/50' : 'text-indigo-500/50'}`} />
                        <span className="text-xs font-mono text-zinc-300">{(totalPageGoal || 0) - (processedPages || 0)}</span>
                        <span className="text-[7px] text-zinc-600 font-black uppercase">Remaining</span>
                    </div>
                </div>
            </div>

            <div className="mt-6 flex flex-col gap-3">
                {status === 'complete' ? (
                    <div className="w-full py-3 bg-emerald-500/10 text-emerald-400 text-[10px] font-black uppercase tracking-[0.3em] rounded-2xl border border-emerald-500/20 text-center">
                        Transcription Complete
                    </div>
                ) : (
                    <button 
                        onClick={onStart}
                        disabled={isTranscribing}
                        className={`w-full py-4 rounded-2xl font-black text-xs uppercase tracking-[0.2em] transition-all flex items-center justify-center gap-3 ${
                            isTranscribing 
                                ? 'bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 cursor-not-allowed' 
                                : 'bg-indigo-600 hover:bg-indigo-500 text-white shadow-lg shadow-indigo-500/20 hover:scale-[1.02] active:scale-[0.98]'
                        }`}
                    >
                        {isTranscribing ? (
                            <>
                                <Search className="w-4 h-4 animate-spin" />
                                Processing Artifacts...
                            </>
                        ) : (
                            <>
                                <Zap className="w-4 h-4" />
                                Start Industrial Transcription
                            </>
                        )}
                    </button>
                )}
                
                <p className="text-[8px] text-zinc-500 font-bold uppercase text-center tracking-tighter leading-relaxed">
                    Accuracy and Speed are the Apex Standard.
                </p>
            </div>
        </div>
    );
}
