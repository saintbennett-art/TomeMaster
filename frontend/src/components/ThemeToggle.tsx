"use client";
import { useState, useEffect } from 'react';
import { Sun, Moon } from 'lucide-react';
import { loadPreferences, getPref, setPref } from '@/lib/preferences';

export default function ThemeToggle() {
    const [theme, setTheme] = useState<'light' | 'dark'>('dark');

    useEffect(() => {
        // [FILES-ONLY]: theme comes from the vault preferences, not localStorage.
        (async () => {
            await loadPreferences();
            const savedTheme = getPref<'light' | 'dark'>('theme', 'dark');
            setTheme(savedTheme);
            document.documentElement.setAttribute('data-theme', savedTheme);
        })();
    }, []);

    const toggleTheme = () => {
        const newTheme = theme === 'light' ? 'dark' : 'light';
        setTheme(newTheme);
        document.documentElement.setAttribute('data-theme', newTheme);
        setPref('theme', newTheme);
    };

    return (
        <button 
            onClick={toggleTheme}
            className="p-2 rounded-lg bg-surface border border-border hover:border-accent transition-all duration-300 group"
            aria-label={theme === 'light' ? 'Switch to Night Mode' : 'Switch to Day Mode'}
        >
            {theme === 'light' ? (
                <Moon className="w-4 h-4 text-muted-foreground group-hover:text-accent transition-colors" />
            ) : (
                <Sun className="w-4 h-4 text-muted-foreground group-hover:text-accent transition-colors" />
            )}
        </button>
    );
}
