import React, { useState, useEffect } from 'react';
import { Activity, Cpu, Zap } from 'lucide-react';
import { API_BASE_HOLDER } from '@/lib/apiClient';

export default function NerveCenter({ isLeftSidebarOpen = true }: { isLeftSidebarOpen?: boolean }) {
    const [load, setLoad] = useState(0);
    const [history, setHistory] = useState<number[]>(new Array(15).fill(0));
    const [status, setStatus] = useState<'online' | 'offline'>('offline');
    const [position, setPosition] = useState({ x: 0, y: 162 }); // Default top
    const [isDragging, setIsDragging] = useState(false);
    const [rel, setRel] = useState({ x: 0, y: 0 });

    useEffect(() => {
        // Initial position logic: far right
        setPosition({ x: window.innerWidth - 220, y: 162 });
    }, []);

    const onMouseDown = (e: React.MouseEvent) => {
        if (e.button !== 0) return;
        setIsDragging(true);
        const ref = e.currentTarget.getBoundingClientRect();
        setRel({
            x: e.pageX - ref.left,
            y: e.pageY - ref.top
        });
        e.stopPropagation();
        e.preventDefault();
    };

    useEffect(() => {
        const onMouseMove = (e: MouseEvent) => {
            if (!isDragging) return;
            setPosition({
                x: e.pageX - rel.x,
                y: e.pageY - rel.y
            });
            e.stopPropagation();
            e.preventDefault();
        };
        const onMouseUp = () => setIsDragging(false);

        if (isDragging) {
            window.addEventListener('mousemove', onMouseMove);
            window.addEventListener('mouseup', onMouseUp);
        }
        return () => {
            window.removeEventListener('mousemove', onMouseMove);
            window.removeEventListener('mouseup', onMouseUp);
        };
    }, [isDragging, rel]);

    useEffect(() => {
        const eventSource = new EventSource(`${API_BASE_HOLDER.current}/analysis/pulse`);
        // ... (rest of the pulse logic)
        
        eventSource.onmessage = (event) => {
            const data = JSON.parse(event.data);
            if (data.pulse === 'active') {
                setStatus('online');
                const newLoad = data.neural_load || 0;
                setLoad(newLoad);
                setHistory(prev => [...prev.slice(1), newLoad]);
            }
        };

        eventSource.onerror = () => {
            setStatus('offline');
            eventSource.close();
        };

        return () => eventSource.close();
    }, []);

    const [message, setMessage] = useState<string>("");
    const [actionEventName, setActionEventName] = useState<string | null>(null);

    useEffect(() => {
        const handleSpeak = (e: any) => {
            if (e.detail?.text) {
                setMessage(e.detail.text);
                setActionEventName(e.detail.actionEventName || null);
            }
        };
        window.addEventListener('tome-master-guide-speak', handleSpeak);
        return () => window.removeEventListener('tome-master-guide-speak', handleSpeak);
    }, []);

    return (
        <div 
            onMouseDown={onMouseDown}
            className={`fixed z-[150] group transition-all ${isDragging ? 'duration-0 scale-105 shadow-indigo-500/20' : 'duration-500'}`}
            style={{ 
                left: `${position.x}px`, 
                top: `${position.y}px`,
                width: message ? '380px' : '180px',
                cursor: isDragging ? 'grabbing' : 'grab'
            }}
        >
            <div className="bg-black/90 backdrop-blur-3xl border border-white/10 rounded-xl px-3 py-2 shadow-2xl flex flex-col gap-1 hover:border-indigo-500/30 transition-all duration-500">
                {/* Line 1: Label and Status */}
                <div className="flex items-center justify-between pointer-events-none">
                    <div className="flex items-center gap-1.5">
                        <Cpu className={`w-3 h-3 ${status === 'online' ? 'text-indigo-400' : 'text-rose-400'}`} />
                        <span className="text-[9px] font-black text-white uppercase tracking-widest leading-none">Nerve Center</span>
                    </div>
                    <div className={`w-1.5 h-1.5 rounded-full ${status === 'online' ? 'bg-emerald-500 animate-pulse' : 'bg-rose-500'}`} />
                </div>
                
                {/* Line 2: Telemetry Data + Message */}
                <div className="flex items-start justify-between gap-3 pointer-events-none">
                    <div className="flex flex-col gap-1">
                        <div className="flex items-baseline gap-1">
                            <span className="text-sm font-mono text-white leading-none">{Math.round(load)}</span>
                            <span className="text-[8px] text-zinc-500 font-bold uppercase">%</span>
                        </div>
                        <div className="flex items-end gap-0.5 h-3 w-12">
                            {history.map((h, i) => (
                                <div 
                                    key={i} 
                                    className="flex-1 bg-indigo-500/40 rounded-full transition-all duration-500"
                                    style={{ height: `${Math.max(20, h)}%`, opacity: 0.2 + (i / 15) * 0.8 }}
                                />
                            ))}
                        </div>
                    </div>
                    
                    {message && (
                        <div 
                            className={`flex-1 border-l border-white/5 pl-3 py-0.5 animate-in fade-in slide-in-from-right-2 duration-500 ${actionEventName ? 'pointer-events-auto cursor-pointer hover:bg-white/5 rounded-r-md transition-colors' : ''}`}
                            onClick={(e) => {
                                if (actionEventName) {
                                    e.stopPropagation();
                                    window.dispatchEvent(new CustomEvent(actionEventName));
                                }
                            }}
                            title={actionEventName ? "Click to execute action" : undefined}
                        >
                            <p className="text-[10px] text-zinc-300 font-medium leading-relaxed italic line-clamp-2">
                                {message}
                            </p>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}