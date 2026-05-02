/**
 * 🛡️ SOVEREIGN MIGRATION GATE
 * Forensicly unifies fragmented storage coordinates into the Absolute Bedrock Vault.
 */
export function performMasterMigration() {
    if (typeof window === 'undefined') return;

    const VAULT_KEY = 'tome_master_vault';
    const LEGACY_KEYS = ['tome_master_keys', 'tome_master_key_gemini', 'tome_master_key_openai', 'tome_master_key_anthropic'];

    try {
        const existingVault = localStorage.getItem(VAULT_KEY);
        
        // If the vault is already anchored, we bypass to preserve current state purity
        if (existingVault) return;

        console.log("BOARDROOM: Initiating structural migration to Sovereign Vault bedrock...");
        
        const newVault: Record<string, string> = {};
        
        // [AUDIT 1]: Legacy Object Migration
        const objKeys = localStorage.getItem('tome_master_keys');
        if (objKeys) {
            try {
                const parsed = JSON.parse(objKeys);
                Object.assign(newVault, parsed);
            } catch (e) {
                console.warn("BOARDROOM: Legacy key object corrupted. Bypassing.");
            }
        }

        // [AUDIT 2]: Individual Anchor Migration
        LEGACY_KEYS.forEach(k => {
            const val = localStorage.getItem(k);
            if (val && !val.startsWith('{')) {
                const provider = k.split('_').pop() || '';
                if (provider && !newVault[provider]) {
                    newVault[provider] = val;
                }
            }
        });

        // [RESOLUTION]: Absolute Bedrock Anchoring
        if (Object.keys(newVault).length > 0) {
            localStorage.setItem(VAULT_KEY, JSON.stringify(newVault));
            console.log("BOARDROOM: Structural migration successful. Vault bedrock poured.");
        }
    } catch (err) {
        console.error("BOARDROOM: Migration Handshake Failure.", err);
    }
}
