"use client";
import React from "react";
import { Pen, Users, LayoutList, Megaphone, Film, ShieldCheck, Plus, XCircle } from "lucide-react";

export const STANDARD_AGENTS = [
    { 
        id: "Developmental Editor", 
        icon: LayoutList, 
        desc: "Structure & Pacing Specialist",
        guidance: "Ideal for deep-manuscript logic and character arcs. Requires massive context window.",
        recommendedModels: ["gemini-1.5-pro", "gemini-1.5-flash", "slot_primary"]
    },
    { 
        id: "Copy Editor", 
        icon: Pen, 
        desc: "Grammar & Tone Specialist",
        guidance: "Specializes in prose fluidity and linguistic nuance. Prefers models with high literary fidelity.",
        recommendedModels: ["claude-3-5-sonnet-20241022", "gpt-4o", "slot_specialist"]
    },
    { 
        id: "Sensitivity Reader", 
        icon: Users, 
        desc: "Demographic Tropes & Representation",
        guidance: "Audit for cultural nuance and stereotypical pitfalls. Requires high reasoning stability.",
        recommendedModels: ["claude-3-5-sonnet-20241022", "slot_specialist"]
    },
    { 
        id: "Marketing Executive", 
        icon: Megaphone, 
        desc: "Pitch & High-Concept Expert",
        guidance: "Focused on hooks, taglines, and marketability. Requires models with punchy, creative output.",
        recommendedModels: ["gpt-4o", "gemini-1.5-pro", "slot_primary"]
    },
    { 
        id: "Cinematic Screenplay Specialist", 
        icon: Film, 
        desc: "Cinematic & TV Adaptation",
        guidance: "Transforms prose into visual beats and scene headings. Requires high-fidelity structural logic.",
        recommendedModels: ["gpt-4o", "gemini-1.5-pro", "slot_primary"]
    },
    { 
        id: "Directorial Bridge", 
        icon: ShieldCheck, 
        desc: "System Workflow Coordinator",
        guidance: "Coordinates multi-agent workflows and enforces project consistency.",
        recommendedModels: ["gemini-1.5-flash", "slot_primary"]
    }
];

interface SpecialistRegistryProps {
    selectedAgents: string[];
    setSelectedAgents: (agents: string[]) => void;
    customAgents: string[];
    setCustomAgents: (agents: string[]) => void;
}

export const SpecialistRegistry: React.FC<SpecialistRegistryProps> = ({ selectedAgents, setSelectedAgents, customAgents, setCustomAgents }) => {
    const [newAgent, setNewAgent] = React.useState("");
    const toggleAgent = (id: string) => {
        if (selectedAgents.includes(id)) setSelectedAgents(selectedAgents.filter(a => a !== id));
        else setSelectedAgents([...selectedAgents, id]);
    };
    const addCustom = () => {
        if (!newAgent.trim()) return;
        setCustomAgents([...customAgents, newAgent.trim()]);
        setSelectedAgents([...selectedAgents, newAgent.trim()]);
        setNewAgent("");
    };
    return (
        <div className="space-y-4">
            <h4 className="text-[10px] font-black text-zinc-500 uppercase tracking-widest px-1">Boardroom Specialists</h4>
            <div className="grid grid-cols-2 gap-2">
                {STANDARD_AGENTS.map(agent => (
                    <button key={agent.id} onClick={() => toggleAgent(agent.id)} className={`flex flex-col gap-2 p-3 rounded-2xl border transition-all text-left ${selectedAgents.includes(agent.id) ? "bg-indigo-500/10 border-indigo-500/30" : "bg-black/40 border-white/5 hover:border-white/10"}`}>
                        <agent.icon className={`w-4 h-4 ${selectedAgents.includes(agent.id) ? "text-indigo-400" : "text-zinc-600"}`} />
                        <div>
                            <p className="text-[10px] font-black text-white uppercase tracking-tighter leading-none">{agent.id}</p>
                            <p className="text-[7px] text-zinc-500 font-bold uppercase mt-1 leading-tight">{agent.desc}</p>
                        </div>
                    </button>
                ))}
            </div>
            <div className="flex gap-2 pt-2">
                <input type="text" value={newAgent} onChange={(e) => setNewAgent(e.target.value)} placeholder="Ad-hoc Specialist" className="flex-1 bg-black/40 border border-[#222] rounded-xl px-4 py-2 text-[10px] text-zinc-400 outline-none" />
                <button onClick={addCustom} className="p-2 bg-zinc-900 border border-zinc-800 rounded-xl text-zinc-500"><Plus size={16} /></button>
            </div>
        </div>
    );
};
