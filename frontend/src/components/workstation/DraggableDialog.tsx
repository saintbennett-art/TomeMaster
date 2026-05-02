"use client";

import React, { useState, useRef, useEffect } from 'react';

interface DraggableDialogProps {
    children: React.ReactNode;
    initialX?: number;
    initialY?: number;
    headerId: string; // The ID of the element that acts as the drag handle
}

export const DraggableDialog: React.FC<DraggableDialogProps> = ({ children, initialX = 20, initialY = 20, headerId }) => {
    const [position, setPosition] = useState({ x: initialX, y: initialY });
    const [isDragging, setIsDragging] = useState(false);
    const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
    const dialogRef = useRef<HTMLDivElement>(null);

    const onMouseDown = (e: React.MouseEvent) => {
        // Only drag if clicking the designated header
        const target = e.target as HTMLElement;
        if (!target.closest(`#${headerId}`) || target.closest('button') || target.closest('a') || target.closest('input')) return;

        setIsDragging(true);
        setDragStart({
            x: e.clientX - position.x,
            y: e.clientY - position.y
        });
        e.preventDefault();
    };

    useEffect(() => {
        const onMouseMove = (e: MouseEvent) => {
            if (!isDragging) return;
            
            // Boundary checks
            const newX = Math.max(0, Math.min(window.innerWidth - 100, e.clientX - dragStart.x));
            const newY = Math.max(0, Math.min(window.innerHeight - 100, e.clientY - dragStart.y));
            
            setPosition({ x: newX, y: newY });
        };

        const onMouseUp = () => {
            setIsDragging(false);
        };

        if (isDragging) {
            window.addEventListener('mousemove', onMouseMove);
            window.addEventListener('mouseup', onMouseUp);
        }

        return () => {
            window.removeEventListener('mousemove', onMouseMove);
            window.removeEventListener('mouseup', onMouseUp);
        };
    }, [isDragging, dragStart]);

    return (
        <div 
            ref={dialogRef}
            style={{ 
                position: 'fixed', 
                left: `${position.x}px`, 
                top: `${position.y}px`, 
                zIndex: 1000,
                cursor: isDragging ? 'grabbing' : 'auto',
                transition: isDragging ? 'none' : 'all 0.1s ease-out'
            }}
            onMouseDown={onMouseDown}
        >
            {children}
        </div>
    );
};
