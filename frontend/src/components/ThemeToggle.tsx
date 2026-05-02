"use client";
import { useState, useEffect } from 'react';
import { Sun, Moon } from 'lucide-react';

export default function ThemeToggle() {
    const [theme, setTheme] = useState<'light' | 'dark'>('dark');

    useEffect(() => {
        const savedTheme = localStorage.getItem('tome-master-theme') as 'light' | 'dark' | null;
        if (savedTheme) {
            setTheme(savedTheme);
            document.documentElement.setAttribute('data-theme', savedTheme);
        } else {
            // Default to Night (No attribute needed as :root is dark, but for consistency we attribute it)
            document.documentElement.setAttribute('data-theme', 'dark');
        }
    }, []);

    const toggleTheme = () => {
        const newTheme = theme === 'light' ? 'dark' : 'light';
        setTheme(newTheme);
        document.documentElement.setAttribute('data-theme', newTheme);
        localStorage.setItem('tome-master-theme', newTheme);
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
