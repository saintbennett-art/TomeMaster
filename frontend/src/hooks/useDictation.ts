import { useState, useEffect, useRef, useCallback } from 'react';
import { refineProse } from '@/lib/apiClient';

interface SpeechRecognitionEvent extends Event {
  results: SpeechRecognitionResultList;
  resultIndex: number;
}

interface SpeechRecognitionErrorEvent extends Event {
  error: string;
}

interface SpeechRecognition extends EventTarget {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  onresult: (event: SpeechRecognitionEvent) => void;
  onerror: (event: SpeechRecognitionErrorEvent) => void;
  onend: () => void;
  start: () => void;
  abort: () => void;
}

declare global {
  interface Window {
    SpeechRecognition: new () => SpeechRecognition;
    webkitSpeechRecognition: new () => SpeechRecognition;
  }
}

interface UseDictationProps {
  onCommand?: (command: string) => void;
  onDictation?: (text: string) => void;
  isSuperMuseMode?: boolean;
  provider?: string;
  apiKey?: string;
}

export function useDictation({ onCommand, onDictation, isSuperMuseMode, provider, apiKey }: UseDictationProps) {
  const [isListening, setIsListening] = useState(false);
  const [isRefining, setIsRefining] = useState(false);
  const recognitionRef = useRef<SpeechRecognition | null>(null);
  const isListeningRef = useRef(false);
  const isSuperMuseRef = useRef(isSuperMuseMode);
  
  // Use refs for callbacks so we don't recreate the SpeechRecognition object on every render
  const onCommandRef = useRef(onCommand);
  const onDictationRef = useRef(onDictation);
  
  useEffect(() => {
     onCommandRef.current = onCommand;
     onDictationRef.current = onDictation;
     isSuperMuseRef.current = isSuperMuseMode;
  }, [onCommand, onDictation, isSuperMuseMode]);

  useEffect(() => {
    if (typeof window === 'undefined') return;
    
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      return;
    }

    const recognition = new SpeechRecognition();
    recognition.continuous = true;
    recognition.interimResults = false; 
    recognition.lang = 'en-US';

    recognition.onresult = async (e: SpeechRecognitionEvent) => {
      if (!isListeningRef.current) return; 
      
      for (let i = e.resultIndex; i < e.results.length; i++) {
          if (e.results[i].isFinal) {
              const transcript = e.results[i][0].transcript.trim();
              if (!transcript) continue;
              
              const lowMsg = transcript.toLowerCase();
              
              // Wake Word Interceptor Pattern
              if (lowMsg.startsWith("computer") || lowMsg.startsWith("system")) {
                  if (onCommandRef.current) onCommandRef.current(lowMsg);
              } else {
                  // [SUPER MUSE]: Real-time Authorial Smoothing
                  if (isSuperMuseRef.current) {
                      setIsRefining(true);
                      try {
                          // [SOVEREIGN HANDSHAKE]: Sending to Style Mirror for refinement
                          const refinedText = await refineProse(transcript, provider, apiKey);
                          if (onDictationRef.current) onDictationRef.current(refinedText);
                      } finally {
                          setIsRefining(false);
                      }
                  } else {
                      if (onDictationRef.current) onDictationRef.current(transcript);
                  }
              }
          }
      }
    };

    recognition.onerror = (e: SpeechRecognitionErrorEvent) => {
    };

    recognition.onend = () => {
      if (isListeningRef.current) {
        try {
          recognitionRef.current?.start();
        } catch (err) {}
      }
    };

    recognitionRef.current = recognition;

    return () => {
      // We don't change isListeningRef.current here so the mic state survives re-renders
      if (recognitionRef.current) {
         try { recognitionRef.current.abort(); } catch(e) {}
      }
    };
  }, []); // Run ONCE on mount!

  const toggleListening = useCallback(() => {
    if (!recognitionRef.current) {
        alert("Your browser does not support Web Speech API natively. Please use Chrome or Edge.");
        return;
    }
    
    if (isListening) {
      isListeningRef.current = false;
      try { recognitionRef.current.abort(); } catch(e) {}
      setIsListening(false);
    } else {
      if (!window.confirm("Activate Voice Assist microphone? It will listen continuously and dictate prose directly into your document until you click it off.")) {
         return;
      }
      isListeningRef.current = true;
      try {
        recognitionRef.current.start();
      } catch (err) {}
      setIsListening(true);
    }
  }, [isListening]);

  return { isListening, toggleListening, isRefining };
}
