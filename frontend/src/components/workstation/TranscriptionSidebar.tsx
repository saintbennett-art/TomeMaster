"use client";

import React from "react";
import { useWorkstationState, useWorkstationActions } from "@/context/WorkstationContext";
import { useEditorState, useEditorActions } from "@/context/EditorContext";
import ResurrectionDashboard from "@/components/ResurrectionDashboard";


interface ResurrectionSidebarProps {
    isOpen: boolean;
    activeTab: string;
    setActiveTab: (tab: string) => void;
    selectedAgents: string[];
    setSelectedAgents: (agents: string[]) => void;
    customAgents: string[];
    setCustomAgents: (agents: string[]) => void;
    onApplySuggestion: (suggestion: string) => void;
    isAnalyzing: boolean;
    localAnalysisTrigger: number;
}

const ResurrectionSidebar: React.FC<ResurrectionSidebarProps> = ({
    isOpen,
    activeTab,
    setActiveTab,
    selectedAgents,
    setSelectedAgents,
    customAgents,
    setCustomAgents,
    onApplySuggestion,
    isAnalyzing,
    localAnalysisTrigger
}) => {
    const { 
        transcriptionStatus, isTranscribing, processedPageCount
    } = useWorkstationState();

    const {
        content, arcData, chapters, agentReports
    } = useEditorState();
    
    const { setAgentReports } = useEditorActions();

    if (!isOpen) return null;

    return (
        <aside className="w-0 border-none bg-transparent pointer-events-none flex flex-col shrink-0 animate-in slide-in-from-right duration-300">
            <div className="flex-1 overflow-y-auto">
                {/* Nerve Center Evacuated */}
                
                
            </div>
        </aside>
    );
};

export default ResurrectionSidebar;
