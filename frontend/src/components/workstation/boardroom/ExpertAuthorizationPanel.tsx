import React from 'react';
import { ShieldCheck, Sparkles } from 'lucide-react';
import { useShadowSave } from '@/hooks/useShadowSave';
import { STANDARD_AGENTS } from "./SpecialistRegistry";

export const ExpertAuthorizationPanel = ({ authModal, dynamicModels, getFidelityPortfolioForExpert }) => {
    const [selectedModel, setSelectedModel] = React.useState(authModal.model);
    const [customPrompt, setCustomPrompt] = useShadowSave("boardroom_directive", authModal.prompt);
    const [handshakeStatus, setHandshakeStatus] = React.useState("idle"); // idle, checking, success, fail
    const portfolio = getFidelityPortfolioForExpert(authModal.persona, dynamicModels);

    const specialistData = STANDARD_AGENTS.find(a => a.id === authModal.persona);

    const verifyHandshake = async () => {
        setHandshakeStatus("checking");
        try {
            const baseUrl = typeof window !== 'undefined' ? (window.location.origin.includes('localhost') ? 'http://127.0.0.1:8080/api/v1' : '/api/v1') : '/api/v1';
            
            // Industrial Handshake: Verify the general gateway health
            const res = await fetch(`${baseUrl}/ai/status`);
            const data = await res.json();
            
            if (data.status === "online") {
                setHandshakeStatus("success");
            } else {
                setHandshakeStatus("fail");
            }
        } catch (e) {
            setHandshakeStatus("fail");
        }
    };

    return (
        <div className="fixed inset-0 z-[130] flex items-center justify-center p-6 bg-black/80 backdrop-blur-2xl animate-in fade-in duration-300">
            <div className="bg-[#0b0b0b] border border-indigo-500/30 rounded-[2.5rem] p-10 w-full max-w-xl shadow-2xl relative overflow-y-auto max-h-[90vh]">
                <div className="flex items-center gap-4 mb-8">
                    <div className="p-4 bg-indigo-500/10 rounded-2xl border border-indigo-500/20"><ShieldCheck className="w-8 h-8 text-indigo-400" /></div>
                    <div>
                        <h3 className="text-2xl font-black text-white uppercase tracking-tighter">Directorial Oversight</h3>
                        <p className="text-[10px] text-zinc-500 font-bold uppercase tracking-widest mt-1">Specialist: {authModal.persona}</p>
                    </div>
                </div>
                
                <div className="space-y-6">
                    {specialistData?.guidance && (
                        <div className="p-4 bg-indigo-500/5 border border-indigo-500/20 rounded-2xl">
                            <p className="text-[10px] text-indigo-300 font-bold leading-relaxed">
                                <span className="text-indigo-500 mr-2 uppercase tracking-widest">Guidance:</span>
                                {specialistData.guidance}
                            </p>
                        </div>
                    )}

                    <div>
                        <label className="text-[9px] font-black text-zinc-500 uppercase tracking-widest block mb-3">Narrative Directive</label>
                        <textarea value={customPrompt} onChange={(e) => setCustomPrompt(e.target.value)} className="w-full bg-black/40 border border-[#222] rounded-2xl p-5 text-xs text-zinc-300 min-h-[100px] focus:border-indigo-500/30 outline-none" />
                    </div>

                    {/* Fidelity Hiring Recommendation */}
                    <div className="p-5 bg-amber-500/5 border border-amber-500/20 rounded-2xl">
                        <div className="flex justify-between items-start mb-3">
                            <h4 className="text-[10px] font-black text-amber-500 uppercase tracking-widest flex items-center gap-2">
                                <Sparkles className="w-3 h-3" />
                                Specialist Hiring Advisor
                            </h4>
                            <button 
                                onClick={verifyHandshake}
                                disabled={handshakeStatus === "checking"}
                                className={`text-[8px] font-black uppercase px-3 py-1 rounded-full border transition-all ${
                                    handshakeStatus === "success" ? "bg-green-500/20 border-green-500/50 text-green-400" :
                                    handshakeStatus === "fail" ? "bg-red-500/20 border-red-500/50 text-red-400" :
                                    "bg-amber-500/10 border-amber-500/30 text-amber-500 hover:bg-amber-500/20"
                                }`}
                            >
                                {handshakeStatus === "checking" ? "Verifying..." : 
                                 handshakeStatus === "success" ? "Handshake Valid" : 
                                 handshakeStatus === "fail" ? "Handshake Failed" : 
                                 "Verify Handshake"}
                            </button>
                        </div>
                        <div className="space-y-3">
                            <p className="text-[10px] text-zinc-400 font-bold leading-relaxed italic">
                                {specialistData?.recommendedModels ? `Recommended for this persona: ${specialistData.recommendedModels.map(m => m.split('-').slice(0, 2).join(' ')).join(', ')}` : "Select a high-fidelity model to proceed."}
                            </p>
                        </div>
                    </div>

                    <div>
                        <label className="text-[9px] font-black text-zinc-500 uppercase tracking-widest block mb-3">Industrial Gateway Selection</label>
                        <div className="grid grid-cols-1 gap-2 max-h-[150px] overflow-y-auto pr-2">
                            {portfolio.map(m => (
                                <button key={m} onClick={() => { setSelectedModel(m); setHandshakeStatus("idle"); }} className={`px-4 py-3 rounded-xl border text-[10px] font-black uppercase text-left transition-all ${selectedModel === m ? "bg-indigo-500 border-indigo-400 text-white shadow-lg" : "bg-black/40 border-white/5 text-zinc-500 hover:border-white/10"}`}>
                                    {m.includes("/") ? m.split("/").pop() : m}
                                </button>
                            ))}
                        </div>
                    </div>
                </div>
                <div className="flex gap-4 mt-10">
                    <button onClick={authModal.onTerminate} className="flex-1 py-4 bg-zinc-900 text-zinc-500 rounded-2xl font-black uppercase text-[11px]">Veto</button>
                    <button onClick={() => authModal.onAuthorize(customPrompt, selectedModel)} className="flex-1 py-4 bg-indigo-600 text-white rounded-2xl font-black uppercase text-[11px] shadow-lg shadow-indigo-600/20">Authorize Dispatch</button>
                </div>
            </div>
        </div>
    );
};
