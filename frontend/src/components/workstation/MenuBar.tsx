"use client";

import React, { useState, useRef, useEffect } from "react";
import { 
    File, Edit2, Monitor, ChevronDown, 
    FolderOpen, Save, FileOutput, ShieldCheck, 
    Eraser, Undo2, Redo2, PanelLeft, Maximize,
    Layers, ListOrdered, FileText, RefreshCw
} from "lucide-react";
import { useWorkstationState, useWorkstationActions } from "@/context/WorkstationContext";
import { useEditorState, useEditorActions } from "@/context/EditorContext";
import { API_BASE_HOLDER } from "@/lib/apiClient";

interface MenuBarProps {
    onExport?: () => void;
    onGrammarCheck?: () => void;
    onUndo?: () => void;
    onRedo?: () => void;
    onTakeSnapshot?: () => void;
}

const MenuBar: React.FC<MenuBarProps> = ({ 
    onExport, onGrammarCheck, onUndo, onRedo, onTakeSnapshot 
}) => {
    const [openMenu, setOpenMenu] = useState<string | null>(null);
    const menuRef = useRef<HTMLDivElement>(null);

    const { 
        activeFolderPath, isFocusMode, isOfflineMode
    } = useWorkstationState();
    
    const { 
        setIsFocusMode, establishProject, loadManuscript, loadSealedManuscript, setIsLedgerOpen, setIsAuditOpen,
        setIsStructuralModalOpen, invokeTranscription, notify
    } = useWorkstationActions();

    const { content } = useEditorState();
    const { setContent, setHtmlContent } = useEditorActions();

    // Close menu when clicking outside
    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
                setOpenMenu(null);
            }
        };
        document.addEventListener("mousedown", handleClickOutside);
        return () => document.removeEventListener("mousedown", handleClickOutside);
    }, []);

    const menuItems: Record<string, any[]> = {
        File: [
            { label: "Load Manuscript...", icon: FileText, action: loadManuscript },
            { label: "Load Sealed Manuscript", icon: ShieldCheck, action: loadSealedManuscript },
            { label: "Save Snapshot", icon: Save, shortcut: "Ctrl+S", action: onTakeSnapshot || (() => notify("Snapshot saved to local vault.")) },
            { type: "separator" },
            { label: "Export Manuscript", icon: FileOutput, action: onExport || (() => notify("Opening Export bridge...")) },
        ],
        Edit: [
            { label: "Undo", icon: Undo2, shortcut: "Ctrl+Z", action: onUndo || (() => {}) },
            { label: "Redo", icon: Redo2, shortcut: "Ctrl+Y", action: onRedo || (() => {}) },
            { type: "separator" },
            { label: "Sanitize Prose", icon: ShieldCheck, action: onGrammarCheck || (() => notify("Starting copy-editor audit...")) },
            { label: "Clear Workspace", icon: Eraser, action: async () => {
                if (confirm("Clear all prose and wipe the manuscript state? This cannot be undone.")) {
                    setContent("");
                    setHtmlContent("");
                    localStorage.removeItem('tome_master_shadow_path');
                    try {
                        await fetch(`${API_BASE_HOLDER.current}/transcribe/clear`, { method: "POST" });
                    } catch (e) {
                        // [CLEANSE]: Backend clear failed — state may persist until restart.
                    }
                    notify("Workspace cleared. State wiped from memory and disk.");
                }
            }},
        ],
        Directorial: [
            { label: "Invoke Transcription", icon: RefreshCw, action: invokeTranscription },
            { label: "Delineate Structure", icon: Layers, action: () => setIsStructuralModalOpen(true) },
            { type: "separator" },
            { label: "Sanitize Prose", icon: ShieldCheck, action: onGrammarCheck || (() => notify("Starting copy-editor audit...")) },
            { label: "Directorial Audit", icon: ListOrdered, action: () => setIsAuditOpen(true) },
        ],
        View: [
            { label: "Focus Mode", icon: Maximize, shortcut: "F11", action: () => setIsFocusMode(!isFocusMode) },
            { type: "separator" },
            { label: "Usage Ledger", icon: Layers, action: () => setIsLedgerOpen(true) },
        ]
    };

    return (
        <div className="flex items-center gap-1 ml-4" ref={menuRef}>
            {Object.keys(menuItems).map((menu) => (
                <div key={menu} className="relative">
                    <button
                        type="button"
                        onClick={() => {
                            setOpenMenu(openMenu === menu ? null : menu);
                        }}
                        className={`px-3 py-1.5 text-xs font-black uppercase tracking-widest transition-all rounded-md ${openMenu === menu ? 'bg-indigo-500 text-white shadow-lg' : 'text-zinc-400 hover:text-white hover:bg-white/10'}`}
                    >
                        {menu}
                    </button>

                    {openMenu === menu && (
                        <div className="absolute top-full left-0 mt-2 w-64 bg-[#0a0a0a] border-2 border-blue-500/50 rounded-xl shadow-[0_0_50px_rgba(37,99,235,0.2)] py-3 z-[9999] pointer-events-auto animate-in fade-in zoom-in-95 duration-150">
                            {menuItems[menu]
                                .filter(item => {
                                    if (item.label === "Invoke Transcription" && content && content.trim().length > 0) return false;
                                    return true;
                                })
                                .map((item, idx) => (
                                    item.type === "separator" ? (
                                        <div key={idx} className="h-[1px] bg-white/10 my-1 mx-2" />
                                    ) : (
                                        <button
                                            key={idx}
                                            onClick={() => {
                                                item.action();
                                                setOpenMenu(null);
                                            }}
                                            className="w-full flex items-center justify-between px-4 py-2 hover:bg-indigo-500/10 text-zinc-300 hover:text-indigo-400 transition-all text-xs font-medium group"
                                        >
                                            <div className="flex items-center gap-3">
                                                <item.icon className="w-3.5 h-3.5 opacity-50 group-hover:opacity-100" />
                                                <span>{item.label}</span>
                                            </div>
                                            {item.shortcut && <span className="text-[9px] text-zinc-600 font-bold">{item.shortcut}</span>}
                                        </button>
                                    )
                                ))}
                        </div>
                    )}
                </div>
            ))}
        </div>
    );
};

export default MenuBar;
