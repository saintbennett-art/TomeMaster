"use client";

import { useEffect, useState } from "react";
import { Lock, X } from "lucide-react";

interface Toast {
    id: number;
    message: string;
    feature?: string;
}

export default function TomeToast() {
    const [toasts, setToasts] = useState<Toast[]>([]);

    useEffect(() => {
        const handleToast = (e: any) => {
            const { message, feature } = e.detail || {};
            const id = Date.now();
            
            // Format the message specifically as requested by the user if it's a "locked" type
            const finalMessage = feature 
                ? `The ${feature} is locked and will be unlocked once licensed.`
                : message;

            setToasts(prev => [...prev, { id, message: finalMessage, feature }]);

            // Auto-dismiss after 4 seconds
            setTimeout(() => {
                setToasts(prev => prev.filter(t => t.id !== id));
            }, 4000);
        };

        window.addEventListener('tome_master-toast', handleToast);
        return () => window.removeEventListener('tome_master-toast', handleToast);
    }, []);

    const removeToast = (id: number) => {
        setToasts(prev => prev.filter(t => t.id !== id));
    };

    if (toasts.length === 0) return null;

    return (
        <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-[9999] flex flex-col gap-3 w-full max-w-md px-4 pointer-events-none">
            {toasts.map((toast) => (
                <div 
                    key={toast.id}
                    className="pointer-events-auto bg-[#1a1a1a]/95 backdrop-blur-md border border-indigo-500/30 rounded-xl px-4 py-3 shadow-[0_10px_40px_rgba(0,0,0,0.5)] flex items-center gap-4 animate-in slide-in-from-bottom-4 fade-in duration-300 group"
                >
                    <div className="w-10 h-10 bg-indigo-500/10 rounded-lg flex items-center justify-center border border-indigo-500/20 shrink-0">
                        <Lock className="w-5 h-5 text-indigo-400 group-hover:scale-110 transition-transform" />
                    </div>
                    
                    <div className="flex-1">
                        <p className="text-[12px] font-bold text-zinc-100 leading-tight">
                            {toast.message}
                        </p>
                    </div>

                    <button 
                        onClick={() => removeToast(toast.id)}
                        className="p-1 text-zinc-600 hover:text-zinc-300 transition-colors"
                    >
                        <X className="w-4 h-4" />
                    </button>
                </div>
            ))}
        </div>
    );
}
