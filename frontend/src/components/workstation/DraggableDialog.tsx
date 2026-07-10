"use client";

import React, { useState, useRef, useEffect, useCallback, createContext, useContext } from 'react';
import { loadPreferences, getLayout, setLayout } from '@/lib/preferences';

interface DraggableLockState {
    isLocked: boolean;
    hasMoved: boolean;
    toggleLock: () => void;
}

// Lets a dialog's children render the lock control INSIDE the bar, so it stays
// reachable even when the bar is docked at the very top of the screen (a tab
// floating above the bar gets clipped off-screen there).
export const DraggableDialogContext = createContext<DraggableLockState | null>(null);
export const useDraggableDialog = () => useContext(DraggableDialogContext);

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
    // [FILES-ONLY]: position/lock come from vault preferences (ui_layout.dialog_<id>).
    const layoutId = `dialog_${headerId}`;
    const [position, setPosition] = useState(() => getLayout(layoutId).pos || { x: initialX, y: initialY });
    const [isDragging, setIsDragging] = useState(false);
    const [hasMoved, setHasMoved] = useState(() => !!getLayout(layoutId).pos);
    const [isLocked, setIsLocked] = useState(() => getLayout(layoutId).locked === true);
    const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
    const dialogRef = useRef<HTMLDivElement>(null);

    // Re-hydrate once vault preferences finish loading (cache may be empty at first render).
    useEffect(() => {
        (async () => {
            await loadPreferences();
            const saved = getLayout(layoutId);
            if (saved.pos) { setPosition(saved.pos); setHasMoved(true); }
            if (typeof saved.locked === 'boolean') setIsLocked(saved.locked);
        })();
    }, [layoutId]);

    // [PERSIST]: remember this dialog's position + lock across restarts (vault, keyed by headerId).
    useEffect(() => {
        if (hasMoved) setLayout(layoutId, { pos: position });
    }, [position, hasMoved, layoutId]);
    useEffect(() => {
        setLayout(layoutId, { locked: isLocked });
    }, [isLocked, layoutId]);

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
            {/* Lock control is rendered by the children INSIDE the bar header (via context),
                so it stays clickable even when the bar is docked at the top of the screen. */}
            <DraggableDialogContext.Provider value={{ isLocked, hasMoved, toggleLock: () => setIsLocked(prev => !prev) }}>
                {children}
            </DraggableDialogContext.Provider>
        </div>
    );
};
