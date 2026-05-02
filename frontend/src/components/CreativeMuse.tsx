"use client";
import { useState, useRef, useEffect } from 'react';
import { Sparkles, Image as ImageIcon, BookOpen, Volume2, ChevronDown, X, User, MapPin, Loader2, Play, Pause, Pen, Palette, Scroll, Feather } from 'lucide-react';
import { fetchMoodboard, checkWorldBible } from '@/lib/apiClient';

interface CreativeMuseProps {
    content: string;
    selectedText?: string;
    currentChapterId?: string | null;
    currentParagraphText?: string;
    agentReports?: Record<string, any>;
    onAmbientNotify?: (text: string) => void;
}

export default function CreativeMuse({ content, selectedText, currentChapterId, currentParagraphText, agentReports, onAmbientNotify }: CreativeMuseProps) {
    const [isOpen, setIsOpen] = useState(false);
    const [activeModal, setActiveModal] = useState<'moodboard' | 'bible' | null>(null);
    const [isLoading, setIsLoading] = useState(false);
    const [statusIndex, setStatusIndex] = useState(0);

    const MOODBOARD_STATUSES = [
        "Analyzing Authorial DNA...",
        "Mirroring The Author's Rhythms...",
        "Drafting Visual Directives...",
        "Synthesizing Cinematic Textures...",
        "Finalizing Moodboard Vision..."
    ];

    const BIBLE_STATUSES = [
        "Reading Between the Lines...",
        "Extracting Character Lore...",
        "Synchronizing World Elements...",
        "Indexing Geographical Atlas..."
    ];

    useEffect(() => {
        let interval: NodeJS.Timeout;
        if (isLoading) {
            interval = setInterval(() => {
                setStatusIndex(prev => prev + 1);
            }, 2500);
        } else {
            setStatusIndex(0);
        }
        return () => clearInterval(interval);
    }, [isLoading]);
    
    // Feature States
    const [moodboardData, setMoodboardData] = useState<any>(null);
    const [bibleData, setBibleData] = useState<any>(null);
    const [isPlayingAudio, setIsPlayingAudio] = useState(false);
    const [hoverDesc, setHoverDesc] = useState<string | null>(null);
    const [visualStyle, setVisualStyle] = useState<'cinematic' | 'lineart' | 'historical' | 'masterpiece'>('cinematic');
    
    const VISUAL_STYLES = [
        { id: 'cinematic', label: 'Cinematic', icon: Sparkles, directive: "cinematic film still, high fidelity, atmospheric lighting, moody, volumetric rays", loading: "Drafting Cinematic Vision..." },
        { id: 'lineart', label: 'Line Art', icon: Pen, directive: "detailed line art, black and white sketch, minimal shading, clean linework, professional paperback illustration", loading: "Drafting Production Line Art..." },
        { id: 'historical', label: 'Historical Plate', icon: Scroll, directive: "19th century historical engraving, vintage book plate, antique woodcut style, parchment texture", loading: "Engraving Historical Plate..." },
        { id: 'masterpiece', label: 'Masterpiece', icon: Palette, directive: "masterpiece oil painting, thick brushstrokes, rich textures, Renaissance style, gallery quality", loading: "Synthesizing Masterpiece..." }
    ];

    const dropdownRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
                setIsOpen(false);
            }
        };
        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, []);

    const getTargetText = () => {
        if (selectedText && selectedText.trim().length > 5) return selectedText;
        if (currentParagraphText && currentParagraphText.trim().length > 10) return currentParagraphText;
        
        // If we have a current chapter but no specific paragraph, try to slice it
        if (currentChapterId) {
            const index = content.indexOf(currentChapterId);
            if (index !== -1) {
                // Return a generous slice of the starting chapter text for context
                return content.substring(index, index + 3000);
            }
        }
        
        return content;
    };

    const getAnalysisScope = () => {
        if (selectedText && selectedText.trim().length > 5) return "Selected Text";
        if (currentParagraphText && currentParagraphText.trim().length > 10) return "Active Paragraph";
        if (currentChapterId) return "Current Chapter";
        return "Global Manuscript";
    };

    const handleGenerateMoodboard = async () => {
        setIsLoading(true);
        setActiveModal('moodboard');
        try {
            const currentStyle = VISUAL_STYLES.find(s => s.id === visualStyle);
            const styledText = `${getTargetText()} -- Style: ${currentStyle?.directive || ""}`;
            const data = await fetchMoodboard(styledText);
            setMoodboardData(data);
        } catch (e) {
            console.error(e);
        } finally {
            setIsLoading(false);
        }
    };

    const handleOpenBible = async () => {
        setIsLoading(true);
        setActiveModal('bible');
        try {
            const data = await checkWorldBible(getTargetText());
            setBibleData(data);
        } catch (e) {
            console.error(e);
        } finally {
            setIsLoading(false);
        }
    };

    const handleAudioBriefing = () => {
        if (isPlayingAudio) {
            window.speechSynthesis.cancel();
            setIsPlayingAudio(false);
            return;
        }

        const reports = Object.entries(agentReports || {})
            .map(([agent, data]) => `${agent} reports: ${data.feedback}`)
            .join(". ");
        
        if (!reports) {
            alert("No analysis reports available to brief. Run the Boardroom first!");
            return;
        }

        const cleanText = reports.replace(/[*#>`~]/g, '').substring(0, 3000);
        const utterance = new SpeechSynthesisUtterance(`Stand by for your Boardroom Audio Briefing. ${cleanText}`);
        utterance.rate = 1.0;
        utterance.onend = () => setIsPlayingAudio(false);
        
        window.speechSynthesis.speak(utterance);
        setIsPlayingAudio(true);
        setIsOpen(false);
    };

    return (
        <div className="relative" ref={dropdownRef}>
            <button 
                onClick={() => setIsOpen(!isOpen)}
                className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-indigo-600/20 to-fuchsia-600/20 border border-indigo-500/30 rounded-full hover:from-indigo-600/30 hover:to-fuchsia-600/30 transition-all group shadow-lg shadow-indigo-500/10"
            >
                <div className="flex items-center gap-1">
                    <Sparkles className="w-4 h-4 text-indigo-400 group-hover:rotate-12 transition-transform" />
                    <div className="flex flex-col items-start">
                        <span className="text-[10px] font-black text-white uppercase tracking-widest leading-none">Creative Muse</span>
                        <div className="flex items-center gap-1 mt-0.5">
                            <div className="w-1 h-1 rounded-full bg-emerald-500 animate-pulse shadow-[0_0_5px_rgba(16,185,129,0.5)]" />
                            <span className="text-[7px] font-black text-emerald-400 uppercase tracking-tighter">Mirroring The Author</span>
                        </div>
                    </div>
                </div>
                <ChevronDown className={`w-4 h-4 text-zinc-500 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
            </button>

            {isOpen && (
                <div className="absolute right-0 mt-2 w-64 bg-[#111]/95 backdrop-blur-xl border border-[#2a2a2a] rounded-2xl shadow-2xl z-[100] overflow-hidden animate-in fade-in slide-in-from-top-2 duration-200">
                    <div className="p-2 flex flex-col gap-1">
                        <div className="p-3">
                            <label className="text-[9px] font-black text-zinc-500 uppercase tracking-[0.2em] mb-3 block">Visual Paradigm</label>
                            <div className="grid grid-cols-4 gap-2 mb-4">
                                {VISUAL_STYLES.map(style => (
                                    <button
                                        key={style.id}
                                        onClick={() => setVisualStyle(style.id as any)}
                                        title={style.label}
                                        className={`flex flex-col items-center gap-1.5 p-2 rounded-xl transition-all border ${visualStyle === style.id ? 'bg-indigo-500/20 border-indigo-500/40 text-indigo-400' : 'bg-white/5 border-transparent text-zinc-500 hover:bg-white/10'}`}
                                    >
                                        <style.icon className="w-4 h-4" />
                                        <span className="text-[8px] font-bold uppercase">{style.label.split(' ')[0]}</span>
                                    </button>
                                ))}
                            </div>

                            <button 
                                onClick={handleGenerateMoodboard}
                                onMouseEnter={() => setHoverDesc(`Synthesizes a ${visualStyle} visualization of your active scene for production inspiration.`)}
                                onMouseLeave={() => setHoverDesc(null)}
                                className="flex items-center gap-3 w-full p-3 bg-gradient-to-r from-emerald-600/20 to-indigo-600/20 hover:from-emerald-600/30 hover:to-indigo-600/30 border border-emerald-500/20 rounded-xl transition-all text-left group"
                            >
                                <div className="p-2 bg-emerald-500/10 rounded-lg group-hover:bg-emerald-500/20 transition-colors">
                                    <ImageIcon className="w-4 h-4 text-emerald-400" />
                                </div>
                                <div>
                                    <div className="text-xs font-bold text-white uppercase tracking-wider">Generate Moodboard</div>
                                    <div className="text-[10px] text-zinc-500 italic">Visualizing: {getAnalysisScope()}</div>
                                </div>
                            </button>
                        </div>

                        <button 
                            onClick={handleOpenBible}
                            onMouseEnter={() => setHoverDesc("Continuously extracts character traits, roles, and locations to ensure your story stays consistent.")}
                            onMouseLeave={() => setHoverDesc(null)}
                            className="flex items-center gap-3 w-full p-3 hover:bg-white/5 rounded-xl transition-colors text-left group"
                        >
                            <div className="p-2 bg-blue-500/10 rounded-lg group-hover:bg-blue-500/20 transition-colors">
                                <BookOpen className="w-4 h-4 text-blue-400" />
                            </div>
                            <div>
                                <div className="text-xs font-bold text-white">Continuity Bible</div>
                                <div className="text-[10px] text-zinc-500">Sync characters and locations</div>
                            </div>
                        </button>

                        <button 
                            onClick={handleAudioBriefing}
                            onMouseEnter={() => setHoverDesc("Generates a podcast-style vocal walkthrough of your Boardroom reports using browser TTS.")}
                            onMouseLeave={() => setHoverDesc(null)}
                            className="flex items-center gap-3 w-full p-3 hover:bg-white/5 rounded-xl transition-colors text-left group border-t border-[#222] mt-1 pt-3"
                        >
                            <div className="p-2 bg-amber-500/10 rounded-lg group-hover:bg-amber-500/20 transition-colors">
                                {isPlayingAudio ? <Pause className="w-4 h-4 text-amber-400" /> : <Volume2 className="w-4 h-4 text-amber-400" />}
                            </div>
                            <div>
                                <div className="text-xs font-bold text-white">Audio Briefing</div>
                                <div className="text-[10px] text-zinc-500">Listen to Boardroom feedback</div>
                            </div>
                        </button>

                        {/* Hover Description Footer */}
                        <div className={`mt-2 p-3 bg-indigo-500/5 rounded-xl border border-indigo-500/10 transition-all duration-300 ${hoverDesc ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-1 pointer-events-none'}`}>
                            <p className="text-[10px] text-indigo-300 leading-tight italic">
                                {hoverDesc}
                            </p>
                        </div>
                    </div>
                </div>
            )}

            {/* Moodboard Modal */}
            {activeModal === 'moodboard' && (
                <div className="fixed inset-0 z-[110] flex items-center justify-center p-6">
                    <div className="absolute inset-0 bg-black/80 backdrop-blur-md" onClick={() => setActiveModal(null)} />
                    <div className="relative w-full max-w-4xl bg-[#0a0a0a] border border-[#2a2a2a] rounded-3xl shadow-3xl overflow-hidden flex flex-col md:flex-row h-[80vh] animate-in zoom-in-95 duration-300">
                        <div className="flex-1 bg-[#111] relative overflow-hidden group">
                           {isLoading ? (
                               <div className="absolute inset-0 flex flex-col items-center justify-center gap-4 bg-black/60 backdrop-blur-sm z-10 p-12 text-center">
                                   <div className="w-full max-w-xs space-y-6">
                                       <div className="relative flex justify-center">
                                           <Loader2 className="w-16 h-16 text-emerald-400 animate-spin opacity-20" />
                                           <Sparkles className="absolute inset-0 m-auto w-6 h-6 text-emerald-400 animate-pulse" />
                                       </div>
                                        <div className="space-y-2">
                                            <div className="text-[10px] font-black tracking-[0.3em] text-emerald-500/50 uppercase">TomeMaster Muse Engine</div>
                                            <div className="text-xl font-medium text-white tracking-tight h-8 transition-all duration-500">
                                                {MOODBOARD_STATUSES[statusIndex % MOODBOARD_STATUSES.length]}
                                            </div>
                                           <div className="text-[11px] text-zinc-500 italic mt-2">
                                               Analysis Scope: <span className="text-indigo-400 font-bold uppercase">{getAnalysisScope()}</span>
                                           </div>
                                       </div>
                                   </div>
                               </div>
                           ) : moodboardData?.image_url ? (
                               <img src={moodboardData.image_url} alt="Scene Visual" className="w-full h-full object-cover opacity-80 group-hover:opacity-100 transition-opacity duration-700" />
                           ) : (
                               <div className="w-full h-full bg-gradient-to-br from-emerald-500/10 to-indigo-500/10 flex items-center justify-center text-zinc-500">
                                   No visual generated (Simulation Mode)
                               </div>
                           )}
                           <div className="absolute inset-0 bg-gradient-to-t from-black via-black/20 to-transparent" />
                        </div>
                        <div className="w-full md:w-80 bg-[#0f0f0f] border-l border-[#222] p-8 flex flex-col">
                            <div className="flex justify-between items-center mb-6">
                                <h3 className="text-xl font-black text-white italic tracking-tighter uppercase">Scene Aura</h3>
                                <button onClick={() => setActiveModal(null)} title="Close Moodboard" className="text-zinc-500 hover:text-white"><X className="w-6 h-6" /></button>
                            </div>
                            
                            {isLoading ? (
                                <div className="space-y-4">
                                    <div className="h-4 w-2/3 bg-[#222] rounded animate-pulse" />
                                    <div className="h-20 w-full bg-[#111] rounded animate-pulse" />
                                </div>
                            ) : (
                                <div className="flex-1 overflow-y-auto space-y-8 scrollbar-hide">
                                    <section>
                                        <label className="text-[10px] font-bold text-emerald-400 uppercase tracking-widest mb-3 block">Visual Directive</label>
                                        <p className="text-sm text-zinc-300 leading-relaxed font-serif italic text-justify pr-2">
                                            "{moodboardData?.prompt || 'Deep analysis pending...'}"
                                        </p>
                                    </section>
                                    
                                    <section>
                                        <label className="text-[10px] font-bold text-indigo-400 uppercase tracking-widest mb-3 block">Key Latent Elements</label>
                                        <div className="flex flex-wrap gap-2">
                                            {moodboardData?.elements?.map((el: string) => (
                                                <span key={el} className="px-3 py-1 bg-[#1a1a1a] border border-[#333] rounded-full text-[10px] text-zinc-400">{el}</span>
                                            ))}
                                        </div>
                                    </section>
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            )}

            {/* Continuity Bible Modal */}
            {activeModal === 'bible' && (
                <div className="fixed inset-0 z-[110] flex items-center justify-center p-6">
                    <div className="absolute inset-0 bg-black/80 backdrop-blur-md" onClick={() => setActiveModal(null)} />
                    <div className="relative w-full max-w-5xl bg-[#0a0a0a] border border-[#2a2a2a] rounded-3xl shadow-3xl overflow-hidden flex flex-col h-[85vh] animate-in slide-in-from-bottom-8 duration-500">
                        <header className="p-6 border-b border-[#222] flex items-center justify-between bg-gradient-to-r from-blue-600/10 to-transparent">
                            <div className="flex items-center gap-3">
                                <BookOpen className="w-6 h-6 text-blue-400" />
                                <div>
                                    <h2 className="text-lg font-bold text-white tracking-tight">The Continuity Bible</h2>
                                    <p className="text-[10px] text-zinc-500 uppercase font-black tracking-widest">Extracted World & Lore</p>
                                </div>
                            </div>
                            <button onClick={() => setActiveModal(null)} title="Close Continuity Bible" className="p-2 hover:bg-[#222] rounded-full transition-colors text-zinc-400 hover:text-white"><X className="w-5 h-5" /></button>
                        </header>

                        <div className="flex-1 overflow-y-auto p-8">
                             {isLoading ? (
                                <div className="h-full flex flex-col items-center justify-center p-12 text-center">
                                     <div className="w-full max-w-md space-y-6">
                                        <div className="relative flex justify-center">
                                            <Loader2 className="w-12 h-12 text-blue-500 animate-spin opacity-20" />
                                            <BookOpen className="absolute inset-0 m-auto w-5 h-5 text-blue-400" />
                                        </div>
                                        <div className="space-y-2">
                                            <div className="text-[10px] font-black tracking-[0.3em] text-blue-500/50 uppercase">Continuity Logic Cluster</div>
                                            <div className="text-lg font-medium text-white tracking-tight h-6">
                                                {BIBLE_STATUSES[statusIndex % BIBLE_STATUSES.length]}
                                            </div>
                                            <div className="text-[11px] text-zinc-500">Cross-referencing your narrative characters, traits, and geographical lore.</div>
                                        </div>
                                     </div>
                                </div>
                            ) : (
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-12">
                                    {/* Characters Section */}
                                    <section>
                                        <div className="flex items-center gap-2 mb-6">
                                            <User className="w-4 h-4 text-blue-400" />
                                            <h3 className="text-xs font-black text-zinc-400 uppercase tracking-widest">Dramatis Personae</h3>
                                        </div>
                                        <div className="space-y-4">
                                            {bibleData?.characters?.map((c: any) => (
                                                <div key={c.name} className="group bg-[#111] border border-[#222] p-4 rounded-2xl hover:border-blue-500/40 transition-all hover:shadow-lg hover:shadow-blue-500/5 cursor-default">
                                                    <div className="flex justify-between items-start mb-2 text-justify">
                                                        <span className="text-sm font-bold text-white pr-2">{c.name}</span>
                                                        <span className="text-[9px] font-black px-2 py-0.5 bg-blue-500/10 text-blue-400 border border-blue-500/20 rounded uppercase">{c.role}</span>
                                                    </div>
                                                    <div className="text-[10px] text-zinc-400 italic mb-2">{c.traits}</div>
                                                    <div className="text-[11px] text-zinc-500 leading-normal">{c.details}</div>
                                                </div>
                                            ))}
                                        </div>
                                    </section>

                                    {/* Locations Section */}
                                    <section>
                                        <div className="flex items-center gap-2 mb-6">
                                            <MapPin className="w-4 h-4 text-emerald-400" />
                                            <h3 className="text-xs font-black text-zinc-400 uppercase tracking-widest">Geographical Atlas</h3>
                                        </div>
                                        <div className="space-y-4">
                                            {bibleData?.locations?.map((l: any) => (
                                                <div key={l.name} className="group bg-[#111] border border-[#222] p-4 rounded-2xl hover:border-emerald-500/40 transition-all hover:shadow-lg hover:shadow-emerald-500/5 cursor-default">
                                                    <div className="flex justify-between items-start mb-2">
                                                        <span className="text-sm font-bold text-white">{l.name}</span>
                                                        <span className="text-[9px] font-black px-2 py-0.5 bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 rounded uppercase">{l.type}</span>
                                                    </div>
                                                    <div className="text-[11px] text-zinc-500 leading-normal">{l.description}</div>
                                                </div>
                                            ))}
                                        </div>
                                    </section>
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
