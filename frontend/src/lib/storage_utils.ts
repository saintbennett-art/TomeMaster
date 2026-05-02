import LZString from 'lz-string';
import { get, set, del, keys } from 'idb-keyval';

/**
 * Saves a value to IndexedDB with LZString compression if it's a string.
 * This resolves QuotaExceededError by shrinking the storage footprint by ~80%.
 */
export async function saveCompressed(key: string, value: any): Promise<void> {
    try {
        let finalValue = value;
        if (typeof value === 'string') {
            finalValue = LZString.compressToUTF16(value);
        }
        await set(key, finalValue);
    } catch (err: any) {
        if (err.name === 'QuotaExceededError') {
            console.error('Critical: IndexedDB Quota Exceeded even with compression.');
            // Fallback: Clear old non-essential data if needed, or re-throw
            throw err;
        }
        throw err;
    }
}

/**
 * Loads a value from IndexedDB and decompresses it if it's a compressed string.
 */
export async function loadCompressed<T>(key: string): Promise<T | undefined> {
    try {
        const value = await get(key);
        if (typeof value === 'string' && value.length > 0) {
            // Check if it's compressed (compressedToUTF16 starts with specific patterns, but decompress is safe to call)
            const decompressed = LZString.decompressFromUTF16(value);
            if (decompressed !== null) {
                return decompressed as unknown as T;
            }
        }
        return value as T;
    } catch (err) {
        console.error('Failed to load/decompress from IndexedDB:', err);
        return undefined;
    }
}

/**
 * Gathers all 'tome_master_draft_*' keys from IndexedDB into a single JSON object.
 */
export async function exportFullProject(): Promise<string> {
    const allKeys = await keys();
    const projectKeys = (allKeys as string[]).filter(k => k.startsWith('tome_master_draft_') || k.startsWith('tome_master_pacing_'));
    
    const backup: Record<string, any> = {
        version: '2.5.0',
        timestamp: Date.now(),
        data: {}
    };

    for (const key of projectKeys) {
        backup.data[key] = await get(key);
    }
    
    // Also include some critical settings
    backup.settings = {
        model: localStorage.getItem('tome_master_model'),
        provider: localStorage.getItem('tome_master_provider')
    };

    return JSON.stringify(backup);
}

/**
 * Validates and restores a project backup JSON into IndexedDB.
 */
export async function importFullProject(jsonStr: string): Promise<boolean> {
    try {
        const backup = JSON.parse(jsonStr);
        if (!backup.data || typeof backup.data !== 'object') {
            throw new Error('Invalid backup format: Missing data payload.');
        }

        // 1. Clear current project data to prevent merge conflicts
        const allKeys = await keys();
        const projectKeys = (allKeys as string[]).filter(k => k.startsWith('tome_master_draft_') || k.startsWith('tome_master_pacing_'));
        for (const key of projectKeys) {
            await del(key);
        }

        // 2. Restore from backup
        for (const [key, value] of Object.entries(backup.data)) {
            await set(key, value);
        }

        // 3. Restore settings
        if (backup.settings) {
            if (backup.settings.model) localStorage.setItem('tome_master_model', backup.settings.model);
            if (backup.settings.provider) localStorage.setItem('tome_master_provider', backup.settings.provider);
        }

        return true;
    } catch (err) {
        console.error('Migration failed during import:', err);
        return false;
    }
}

