import { useState, useEffect } from "react";

/**
 * [SHADOW SAVE]: Industrial Recovery Hook
 * Periodically anchors a volatile state to LocalStorage for crash-resilience.
 * @param key The persistent storage key.
 * @param initialValue The starting value.
 * @param debounceMs Frequency of the "Shadow Sink".
 */
export function useShadowSave<T>(key: string, initialValue: T, debounceMs: number = 2000) {
    const [value, setValue] = useState<T>(() => {
        if (typeof window === "undefined") return initialValue;
        const saved = localStorage.getItem(`shadow_${key}`);
        if (saved) {
            try {
                return JSON.parse(saved) as T;
            } catch (e) {
                return (saved as unknown) as T;
            }
        }
        return initialValue;
    });

    useEffect(() => {
        if (typeof window === "undefined") return;
        
        const timer = setTimeout(() => {
            if (value !== undefined && value !== null) {
                const serialized = typeof value === "string" ? value : JSON.stringify(value);
                localStorage.setItem(`shadow_${key}`, serialized);
                localStorage.setItem(`shadow_${key}_ts`, Date.now().toString());
            }
        }, debounceMs);

        return () => clearTimeout(timer);
    }, [value, key, debounceMs]);

    const clearShadow = () => {
        if (typeof window !== "undefined") {
            localStorage.removeItem(`shadow_${key}`);
            localStorage.removeItem(`shadow_${key}_ts`);
        }
    };

    return [value, setValue, clearShadow] as const;
}
