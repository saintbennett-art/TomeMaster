"use client";

import React, { useState, useRef, useEffect, useCallback } from 'react';
import { Lock, LockOpen } from 'lucide-react';

interface DraggableDialogProps {
    children: React.ReactNode;
    initialX?: number;
    initialY?: number;
    headerId: string;
}

const MOVED_THRESHOLD = 20; // pixels from start = considered "moved"

export const DraggableDialog: React.FC<DraggableDialogProps> = ({ 
    children, initialX = 20, initialY = 20, headerId
}) => {
    const [position, setPosition] = useState({ x: initialX, y: initialY });
    const [isDragging, setIsDragging] = useState(false);
    const [hasMoved, setHasMoved] = useState(false);
    const [isLocked, setIsLocked] = useState(false);
    const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
    const dialogRef = useRef<HTMLDivElement>(null);

    const onMouseDown = (e: React.MouseEvent) => {
        if (isLocked) return; // Locked — no dragging
        const target = e.target as HTMLElement;
        if (!target.closest(`#${headerId}`) || target.closest('button') || target.closest('a') || target.closest('input')) return;
        setIsDragging(true);
        setIsLocked(false); // Auto-unlock when user starts dragging
        setDragStart({ x: e.clientX - position.x, y: e.clientY - position.y });
        e.preventDefault();
    };

    useEffect(() => {
        const onMouseMove = (e: MouseEvent) => {
            if (!isDragging) return;
            const newX = Math.max(0, Math.min(window.innerWidth - 100, e.clientX - dragStart.x));
            const newY = Math.max(0, Math.min(window.innerHeight - 100, e.clientY - dragStart.y));
            setPosition({ x: newX, y: newY });
            if (Math.abs(newX - initialX) > MOVED_THRESHOLD || Math.abs(newY - initialY) > MOVED_THRESHOLD) {
                setHasMoved(true);
            }
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
    }, [isDragging, dragStart, initialX, initialY]);

    return (
        <div 
            ref={dialogRef}
            style={{ 
                position: 'fixed', 
                left: `${position.x}px`, 
                top: `${position.y}px`, 
                zIndex: 1000,
                cursor: isLocked ? 'default' : isDragging ? 'grabbing' : 'auto',
                transition: isDragging ? 'none' : 'left 0.2s ease-out, top 0.2s ease-out'
            }}
            onMouseDown={onMouseDown}
        >
            {/* LOCK BUTTON — appears after moved, vanishes once locked */}
            {hasMoved && !isLocked && (
                <button
                    onClick={() => setIsLocked(prev => !prev)}
                    title={isLocked ? "Unlock panel to move" : "Lock panel in place"}
                    style={{ position: 'absolute', top: '-26px', right: '0px', zIndex: 1001 }}
                    className={`flex items-center gap-1 px-2 py-1 text-[9px] font-black uppercase tracking-wider rounded-t-lg shadow-lg transition-all animate-in fade-in duration-200 cursor-pointer ${
                        isLocked 
                            ? 'bg-emerald-500/90 hover:bg-emerald-400 text-black' 
                            : 'bg-zinc-700/90 hover:bg-zinc-600 text-zinc-300'
                    }`}
                >
                    {isLocked 
                        ? <><Lock className="w-2.5 h-2.5" /> Locked</> 
                        : <><LockOpen className="w-2.5 h-2.5" /> Lock</>
                    }
                </button>
            )}
            {children}
        </div>
    );
};
