/**
 * 🛡️ FILES-ONLY PURGE
 * This is a standalone desktop app — NOTHING is stored in the browser. Keys, the
 * old "vault", and the shadow-save caches all moved to the encrypted backend vault
 * / local project files. This sweep removes any legacy browser-stored remnants on
 * load so a stale value (e.g. an old key cached in localStorage) can never resurface.
 */
export function purgeLegacyBrowserStorage() {
    if (typeof window === 'undefined') return;
    try {
        const legacy = [
            // legacy API key material (must never live in the browser)
            'tome_master_keys',
            'tome_master_key_gemini', 'tome_master_key_openai', 'tome_master_key_anthropic',
            'tome_master_vault', 'tome_master_vault_v2',
            'shadow_vault_entry', 'shadow_vault_entry_ts',
            // legacy prefs now in the encrypted vault preferences
            'tome-master-theme', 'tome_master_onboarded', 'tome_master_force_primary',
            'tome_master_local_mode', 'tome_master_guide_voice',
            'tome_master_provider', 'tome_master_active_slot',
            'tome_master_boardroom_provider', 'tome_master_boardroom_model',
            'tome_master_custom_words', 'tome_master_ignored_words', 'tome_master_language',
            'tome_master_nerve_pos', 'tome_master_nerve_locked', 'tome_master_shadow_path',
            'tm_boardroom_state',
        ];
        legacy.forEach(k => localStorage.removeItem(k));
        // any leftover shadow_* / dialog position keys from earlier builds
        for (let i = localStorage.length - 1; i >= 0; i--) {
            const key = localStorage.key(i);
            if (key && (key.startsWith('shadow_') || key.startsWith('tome_master_dialog_'))) {
                localStorage.removeItem(key);
            }
        }
        sessionStorage.removeItem('tome_master_greeted_logic');
    } catch (e) {
        // best-effort cleanup; never block app load
    }
}
