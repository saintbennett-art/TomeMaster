import LZString from 'lz-string';
import { get, set, del, keys } from 'idb-keyval';

const COMPRESSED_MARKER = '\x00lz\x00';
const SUPPORTED_VERSIONS = new Set(['2.5.0']);
const PERMITTED_BACKUP_KEYS = /^tome_master_(draft|pacing)_/;
const SENSITIVE_KEY_PATTERNS = /key|vault|token|secret/i;

// Strings larger than this are stored plain — LZString compression on large inputs
// blocks the main thread for 10-30s and triggers browser "wait or kill" dialogs.
const COMPRESS_SIZE_LIMIT = 100_000;

export async function saveCompressed(key: string, value: unknown): Promise<void> {
    try {
        let finalValue = value;
        if (typeof value === 'string' && value.length > 0 && value.length <= COMPRESS_SIZE_LIMIT) {
            finalValue = COMPRESSED_MARKER + LZString.compressToUTF16(value);
        }
        await set(key, finalValue);
    } catch (err) {
        throw err;
    }
}

export async function loadCompressed<T>(key: string): Promise<T | undefined> {
    try {
        const value = await get(key);
        if (typeof value === 'string') {
            if (value.startsWith(COMPRESSED_MARKER)) {
                const decompressed = LZString.decompressFromUTF16(value.slice(COMPRESSED_MARKER.length));
                if (decompressed !== null) return decompressed as unknown as T;
                return undefined;
            }
            // Legacy format: only attempt decompression if first char is outside printable ASCII.
            // LZString UTF-16 output starts with chars > U+00FF; plain HTML/text starts with '<' (60).
            if (value.charCodeAt(0) > 255) {
                const legacy = LZString.decompressFromUTF16(value);
                if (legacy !== null && legacy.length > 0) return legacy as unknown as T;
            }
        }
        return value as T;
    } catch (err) {
        return undefined;
    }
}

export async function exportFullProject(): Promise<string> {
    const allKeys = await keys();
    const projectKeys = (allKeys as string[]).filter(
        k => typeof k === 'string' && PERMITTED_BACKUP_KEYS.test(k) && !SENSITIVE_KEY_PATTERNS.test(k)
    );

    const backup: { version: string, timestamp: number, data: Record<string, unknown> } = {
        version: '2.5.0',
        timestamp: Date.now(),
        data: {}
    };

    for (const key of projectKeys) {
        backup.data[key] = await get(key);
    }

    return JSON.stringify(backup);
}

export async function importFullProject(jsonStr: string): Promise<boolean> {
    try {
        const backup = JSON.parse(jsonStr);

        if (!backup.version || !SUPPORTED_VERSIONS.has(backup.version)) {
            throw new Error(`Unsupported backup version: ${backup.version}`);
        }
        if (!backup.data || typeof backup.data !== 'object') {
            throw new Error('Invalid backup format: Missing data payload.');
        }

        const allKeys = await keys();
        const projectKeys = (allKeys as string[]).filter(
            k => typeof k === 'string' && PERMITTED_BACKUP_KEYS.test(k)
        );
        for (const key of projectKeys) await del(key);

        for (const [key, value] of Object.entries(backup.data)) {
            if (!PERMITTED_BACKUP_KEYS.test(key) || SENSITIVE_KEY_PATTERNS.test(key)) continue;
            await set(key, value);
        }

        return true;
    } catch (err) {
        return false;
    }
}
