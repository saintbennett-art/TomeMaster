import { useState, useCallback, useRef, useEffect } from 'react';

/**
 * useTextToSpeech Hook
 * 
 * Provides a centralized interface for the Web Speech API's speechSynthesis.
 * Automatically cleans text of common Markdown and technical artifacts.
 */
export function useTextToSpeech() {
    const [isPlaying, setIsPlaying] = useState(false);
    const [isPaused, setIsPaused] = useState(false);
    const utteranceRef = useRef<SpeechSynthesisUtterance | null>(null);

    const stop = useCallback(() => {
        if (typeof window !== 'undefined') {
            window.speechSynthesis.cancel();
            setIsPlaying(false);
            setIsPaused(false);
        }
    }, []);

    const pause = useCallback(() => {
        if (typeof window !== 'undefined' && window.speechSynthesis.speaking) {
            window.speechSynthesis.pause();
            setIsPaused(true);
        }
    }, []);

    const resume = useCallback(() => {
        if (typeof window !== 'undefined' && window.speechSynthesis.paused) {
            window.speechSynthesis.resume();
            setIsPaused(false);
        }
    }, []);

    const speak = useCallback((text: string, voiceType: 'male' | 'female' = 'female', style: 'normal' | 'directorial' = 'normal', onEnd?: () => void) => {
        if (typeof window === 'undefined') return;

        window.speechSynthesis.cancel();

        const cleanText = text
            .replace(/[*#>`~]/g, '')
            .replace(/\[\d+\]/g, '')
            .replace(/\bhttps?:\/\/\S+/gi, 'link')
            .replace(/\n\n+/g, '. ');
        
        if (!cleanText.trim()) return;

        const utterance = new SpeechSynthesisUtterance(cleanText);
        
        // [PROSODY CALIBRATION]: Directorial mode uses a slower, more authoritative cadence
        if (style === 'directorial') {
            utterance.rate = 0.85; 
            utterance.pitch = voiceType === 'male' ? 0.85 : 1.0;
        } else {
            utterance.rate = 0.92; 
            utterance.pitch = voiceType === 'male' ? 0.9 : 1.05; 
        }       
        // [VOICE ARCHIVE DISCOVERY]: Prioritizing Neural and Natural engines for a flowing cadence
        const voices = window.speechSynthesis.getVoices();
        if (voices.length > 0) {
            let targetVoice = null;
            
            // Tiered Search: Neural AU -> Natural AU -> Standard AU -> English fallback
            const findBestVoice = (keywords: string[]) => {
                // [NARRATIVE LOCALE]: Strictly prioritize Australian English (en-AU)
                const auVoices = voices.filter(v => v.lang.includes('en-AU'));
                const enVoices = auVoices.length > 0 ? auVoices : voices.filter(v => v.lang.includes('en'));

                for (const kw of keywords) {
                    const found = enVoices.find(v => v.name.includes(kw) && (voiceType === 'female' ? !v.name.includes('Male') : !v.name.includes('Female')));
                    if (found) return found;
                }
                // Final fallback within the selected English group
                return enVoices.find(v => voiceType === 'female' ? !v.name.includes('Male') : !v.name.includes('Female')) || enVoices[0];
            };

            if (voiceType === 'female') {
                targetVoice = findBestVoice(['Neural', 'Natural', 'Google', 'Natasha', 'Catherine', 'Karen']);
            } else {
                targetVoice = findBestVoice(['Neural', 'Natural', 'Google', 'Liam', 'Daniel', 'Alex']);
            }
            
            if (targetVoice) {
                console.log(`VOICE: Calibrated to ${targetVoice.name} (Fluidity Active).`);
                utterance.voice = targetVoice;
            }
        }
        
        utterance.onstart = () => {
            console.log("VOICE: Liaison Speaking...");
            setIsPlaying(true);
            setIsPaused(false);
        };
        utterance.onend = () => {
            setIsPlaying(false);
            setIsPaused(false);
            if (onEnd) onEnd();
        };
        utterance.onerror = (event) => {
            const silentErrors = ['interrupted', 'canceled', 'not-allowed', 'synthesis-failed'];
            if (!silentErrors.includes(event.error)) {
                console.error("SpeechSynthesis Error Type:", event.error);
            }
            setIsPlaying(false);
            setIsPaused(false);
        };

        // [GESTURE GUARD]: Ensure we don't crash if the browser blocks auto-play
        try {
            window.speechSynthesis.cancel();
            window.speechSynthesis.speak(utterance);
        } catch (e) {
            console.warn("VOICE: Systemic vocalization blocked by browser policy.", e);
        }
    }, []);

    // Safety: Cleanup on unmount
    useEffect(() => {
        return () => {
            if (typeof window !== 'undefined') {
                window.speechSynthesis.cancel();
            }
        };
    }, []);

    // [VOICE ARCHIVE REFRESH]: Force a voice refresh if they haven't loaded yet
    useEffect(() => {
        if (typeof window === 'undefined') return;
        const handleVoicesChanged = () => {
            console.log("VOICE: Narrative Archive Refreshed (Voices Loaded).");
        };
        window.speechSynthesis.onvoiceschanged = handleVoicesChanged;
        // Trigger manually for some browsers
        if (window.speechSynthesis.getVoices().length > 0) handleVoicesChanged();
        return () => { window.speechSynthesis.onvoiceschanged = null; };
    }, []);

    return {
        speak,
        stop,
        pause,
        resume,
        isPlaying,
        isPaused
    };
}
