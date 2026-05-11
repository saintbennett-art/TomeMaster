"use client";
import { useState, useEffect, memo, useCallback } from 'react';
import { useTextToSpeech } from '@/hooks/useTextToSpeech';
import { getBriefing } from '@/lib/apiClient';

interface GuideAssistantProps {
    content: string;
    selectedText?: string;
    misspelledCount?: number;
    wordCount?: number;
    hasToc?: boolean;
    hasReports?: boolean;
    folderPath?: string | null;
}

/**
 * AmbientGuide: The Invisible Directorial Engine
 * Returns null (Invisible) but listens for focus/hover events to provide ambient speech.
 */
function AmbientGuide({ content, wordCount = 0, hasToc = false, hasReports = false, folderPath = null }: GuideAssistantProps) {
    const { speak } = useTextToSpeech();
    const [lastSpoken, setLastSpoken] = useState<string>("");
    const [lastSpokenTime, setLastSpokenTime] = useState<number>(0);

    const directorialSpeak = useCallback((text: string) => {
        const voice = (localStorage.getItem('tome_master_guide_voice') || 'female') as 'off' | 'male' | 'female';
        if (voice === 'off') return;

        // Debounce: Don't repeat the same thing within 20 seconds
        const now = Date.now();
        if (text === lastSpoken && (now - lastSpokenTime) < 20000) return;

        // [SYSTEMIC SIGNAL]: Broadcast speaking state
        window.dispatchEvent(new CustomEvent('tome-master-liaison-speaking'));
        
        speak(text, voice === 'male' ? 'male' : 'female');
        setLastSpoken(text);
        setLastSpokenTime(now);

        // [SYSTEMIC RESET]: Estimate speech duration (Simplified)
        setTimeout(() => {
            window.dispatchEvent(new CustomEvent('tome-master-liaison-silent'));
        }, text.length * 80); // Roughly 80ms per character
    }, [speak, lastSpoken, lastSpokenTime]);

    useEffect(() => {
        const handleGuideEvent = (e: Event) => {
            const customEvent = e as CustomEvent<{ text: string }>;
            const detail = customEvent.detail;
            if (!detail || !detail.text) return;
            directorialSpeak(detail.text);
        };

        window.addEventListener('tome-master-guide-speak', handleGuideEvent);
        return () => window.removeEventListener('tome-master-guide-speak', handleGuideEvent);
    }, [directorialSpeak]);

    // [DIRECTORIAL CO-PILOT]: Proactive Phase-Based Guidance
    useEffect(() => {
        if (!directorialSpeak || !content) return;
        
        const timer = setTimeout(async () => {
            const hasGreeted = sessionStorage.getItem('tome_master_greeted_logic');
            if (hasGreeted) return;

            const welcomePrefix = "Welcome to Tome-Master. I am the System Workflow Coordinator. ";

            // [SOVEREIGN BRIEFING]: Attempt to pull high-fidelity session intel
            if (folderPath) {
                const briefing = await getBriefing(folderPath);
                directorialSpeak(welcomePrefix + briefing);
            } else {
                if (content.length < 100) {
                    directorialSpeak(welcomePrefix + "Our first objective is Ingestion. I recommend we begin by Transcribing your physical photos using the high-velocity engine in the top-bar.");
                } else if (!hasToc) {
                    directorialSpeak(welcomePrefix + "Digital prose detected, but the architecture is flat. I recommend we move to the Synthesis phase next. Simply hover over the Table of Contents in the sidebar to begin.");
                } else if (!hasReports) {
                    directorialSpeak(welcomePrefix + "Architecture stabilized. The Boardroom Specialists are now standing by for a full narrative audit. You may convene the specialists via the Analysis button.");
                }
            }

            sessionStorage.setItem('tome_master_greeted_logic', 'true');
        }, 3000); // 3-second delay for systemic settling
        
        return () => clearTimeout(timer);
    }, [content, hasToc, hasReports, directorialSpeak]);

    return null; // The Liaison is now invisible intelligence.
}

export default memo(AmbientGuide);
