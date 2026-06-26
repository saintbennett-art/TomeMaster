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

interface EngineOption { provider: string; model: string; trait?: string; quality?: number }

// [SMART DEFAULTS]: the trait tier best suited to each specialist's analysis, in
// priority order. We auto-pick the highest-quality discovered model matching the
// first available tier, so each board member defaults to the right kind of model.
export const AGENT_TRAIT_PREFERENCE: Record<string, string[]> = {
    "Developmental Editor": ['Thinking', 'Analysis'],          // deep structural reasoning
    "Copy Editor": ['Analysis', 'Fast'],                       // precise line work
    "Sensitivity Reader": ['Thinking', 'Analysis'],            // nuanced judgment
    "Marketing Executive": ['Analysis', 'Thinking'],           // strong creative judgment
    "Cinematic Screenplay Specialist": ['Thinking', 'Analysis'],
    "Directorial Bridge": ['Thinking', 'Analysis'],            // top-tier synthesis
};
const DEFAULT_PREF = ['Analysis', 'Thinking', 'Visual', 'Fast', 'General'];

/** The recommended model for an agent: highest-quality discovered model whose trait
 *  matches the agent's preferred tier (falling through the full trait order). */
export function recommendedModelFor(agentId: string, engineOptions: EngineOption[]): EngineOption | null {
    if (!engineOptions || engineOptions.length === 0) return null;
    const prefs = AGENT_TRAIT_PREFERENCE[agentId] || DEFAULT_PREF;
    const order = [...prefs, ...DEFAULT_PREF.filter(t => !prefs.includes(t))];
    for (const trait of order) {
        const matches = engineOptions.filter(o => o.trait === trait);
        if (matches.length) {
            return matches.reduce((best, o) => ((o.quality ?? 0) > (best.quality ?? 0) ? o : best));
        }
    }
    return engineOptions[0];
}

interface SpecialistRegistryProps {
    selectedAgents: string[];
    setSelectedAgents: (agents: string[]) => void;
    customAgents: string[];
    setCustomAgents: (agents: string[]) => void;
    // [PER-AGENT MODEL]: the discovered models + each agent's override (absent = default).
    engineOptions?: EngineOption[];
    agentModels?: Record<string, { provider: string; model: string }>;
    setAgentModel?: (agentId: string, provider: string, model: string) => void;
    defaultEngine?: { provider: string; model: string } | null;
    // [PER-AGENT TONE]: harden/soften each critique (absent = 'balanced').
    agentIntensities?: Record<string, 'soft' | 'balanced' | 'hard'>;
    setAgentIntensity?: (agentId: string, intensity: 'soft' | 'balanced' | 'hard') => void;
}

export const SpecialistRegistry: React.FC<SpecialistRegistryProps> = ({
    selectedAgents, setSelectedAgents, customAgents, setCustomAgents,
    engineOptions = [], agentModels = {}, setAgentModel, defaultEngine = null,
    agentIntensities = {}, setAgentIntensity,
}) => {
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

    // Per-agent model dropdown. Empty value = "use the default Boardroom Engine".
    const defaultLabel = defaultEngine ? `Default — ${defaultEngine.model}` : "Default engine";
    // Render function (not a nested component) so the native <select> isn't remounted
    // on every parent re-render, which would close it mid-interaction.
    const renderAgentPicker = (agentId: string) => {
        if (!setAgentModel) return null;
        const cur = agentModels[agentId];
        const rec = recommendedModelFor(agentId, engineOptions);
        // When the user hasn't overridden, the recommended best-for-role model is what
        // runs — surface it as the selected default so they only change it deliberately.
        const recommendedLabel = rec
            ? `★ Recommended: ${rec.model}${rec.trait ? `  [${rec.trait}]` : ''}`
            : defaultLabel;
        return (
            <select
                value={cur ? `${cur.provider}|${cur.model}` : ''}
                onClick={(e) => e.stopPropagation()}
                onChange={(e) => { e.stopPropagation(); const [p, m] = e.target.value.split('|'); setAgentModel(agentId, p || '', m || ''); }}
                title="Model for this specialist. Defaults to the best model for its analysis; change only if you prefer another."
                className={`mt-2 w-full bg-black/60 border rounded-lg py-1 px-2 text-[8px] font-mono focus:border-amber-500/40 outline-none cursor-pointer ${cur ? 'border-amber-500/30 text-amber-300' : 'border-white/10 text-zinc-300'}`}
            >
                <option value="">{recommendedLabel}</option>
                {engineOptions.map((o) => {
                    const isRec = rec && o.provider === rec.provider && o.model === rec.model;
                    return (
                        <option key={`${o.provider}|${o.model}`} value={`${o.provider}|${o.model}`}>
                            {isRec ? '★ ' : ''}{o.model}{o.trait ? `  [${o.trait}]` : ''}
                        </option>
                    );
                })}
            </select>
        );
    };

    // Per-agent critique tone: Gentle / Balanced / Blunt (absent = balanced).
    const TONES: Array<{ key: 'soft' | 'balanced' | 'hard'; label: string }> = [
        { key: 'soft', label: 'Gentle' }, { key: 'balanced', label: 'Balanced' }, { key: 'hard', label: 'Blunt' },
    ];
    const renderTonePicker = (agentId: string) => {
        if (!setAgentIntensity) return null;
        const cur = agentIntensities[agentId] || 'balanced';
        return (
            <div className="mt-1.5 flex items-center gap-0.5 bg-black/40 border border-white/10 rounded-lg p-0.5" onClick={(e) => e.stopPropagation()}>
                {TONES.map(t => (
                    <button
                        key={t.key}
                        onClick={(e) => { e.stopPropagation(); setAgentIntensity(agentId, t.key); }}
                        title={t.key === 'soft' ? 'Encouraging, diplomatic' : t.key === 'hard' ? 'Blunt, rigorous, exhaustive' : 'Default professional tone'}
                        className={`flex-1 py-1 rounded-md text-[7px] font-black uppercase tracking-widest transition-colors ${cur === t.key ? (t.key === 'hard' ? 'bg-rose-500/20 text-rose-300' : t.key === 'soft' ? 'bg-emerald-500/20 text-emerald-300' : 'bg-indigo-500/20 text-indigo-300') : 'text-zinc-600 hover:text-zinc-300'}`}
                    >
                        {t.label}
                    </button>
                ))}
            </div>
        );
    };

    return (
        <div className="space-y-4">
            <h4 className="text-[10px] font-black text-zinc-500 uppercase tracking-widest px-1">Boardroom Specialists</h4>
            <div className="grid grid-cols-2 gap-2">
                {STANDARD_AGENTS.map(agent => {
                    const sel = selectedAgents.includes(agent.id);
                    return (
                        <div key={agent.id} className={`flex flex-col gap-2 p-3 rounded-2xl border transition-all text-left ${sel ? "bg-indigo-500/10 border-indigo-500/30" : "bg-black/40 border-white/5 hover:border-white/10"}`}>
                            <button onClick={() => toggleAgent(agent.id)} title={sel ? 'Active — click to turn off' : 'Inactive — click to turn on'} className="flex flex-col gap-2 text-left w-full">
                                <div className="flex items-center justify-between w-full">
                                    <agent.icon className={`w-4 h-4 ${sel ? "text-indigo-400" : "text-zinc-600"}`} />
                                    <span className={`px-2 py-0.5 rounded-full text-[7px] font-black uppercase tracking-widest border ${sel ? 'bg-indigo-500/20 text-indigo-300 border-indigo-500/40' : 'bg-zinc-800/60 text-zinc-500 border-white/10'}`}>
                                        {sel ? 'On' : 'Off'}
                                    </span>
                                </div>
                                <div>
                                    <p className={`text-[10px] font-black uppercase tracking-tighter leading-none ${sel ? 'text-white' : 'text-zinc-400'}`}>{agent.id}</p>
                                    <p className="text-[7px] text-zinc-500 font-bold uppercase mt-1 leading-tight">{agent.desc}</p>
                                </div>
                            </button>
                            {sel && renderAgentPicker(agent.id)}
                            {sel && renderTonePicker(agent.id)}
                        </div>
                    );
                })}
            </div>
            {customAgents.length > 0 && (
                <div className="space-y-2">
                    <h5 className="text-[8px] font-black text-zinc-600 uppercase tracking-widest px-1">Ad-hoc Specialists</h5>
                    {customAgents.map(name => (
                        <div key={name} className="flex flex-col gap-1 p-2.5 rounded-xl border border-white/5 bg-black/40">
                            <div className="flex items-center justify-between gap-2">
                                <span className="text-[9px] font-black text-white uppercase tracking-tighter truncate">{name}</span>
                                <button onClick={() => { setCustomAgents(customAgents.filter(a => a !== name)); setSelectedAgents(selectedAgents.filter(a => a !== name)); }} className="text-zinc-600 hover:text-rose-400 shrink-0"><XCircle size={13} /></button>
                            </div>
                            {renderAgentPicker(name)}
                            {renderTonePicker(name)}
                        </div>
                    ))}
                </div>
            )}
            <div className="flex gap-2 pt-2">
                <input type="text" value={newAgent} onChange={(e) => setNewAgent(e.target.value)} placeholder="Ad-hoc Specialist" className="flex-1 bg-black/40 border border-[#222] rounded-xl px-4 py-2 text-[10px] text-zinc-400 outline-none" />
                <button onClick={addCustom} className="p-2 bg-zinc-900 border border-zinc-800 rounded-xl text-zinc-500"><Plus size={16} /></button>
            </div>
        </div>
    );
};
