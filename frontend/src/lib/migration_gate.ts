/**
 * 🛡️ SOVEREIGN MIGRATION GATE
 * Forensicly unifies fragmented storage coordinates into the Absolute Bedrock Vault.
 */
export function performMasterMigration() {
    if (typeof window === 'undefined') return;
    const { secureVault } = require('./vault');

    const VAULT_KEY = 'tome_master_vault';
    const LEGACY_KEYS = ['tome_master_keys', 'tome_master_key_gemini', 'tome_master_key_openai', 'tome_master_key_anthropic'];

    try {
        const existingVault = secureVault.load();
        
        // If the vault is already targeted, we bypass to preserve current state purity
        if (Object.keys(existingVault).length > 0) return;

        
        const newVault: Record<string, string> = {};
        
        // [AUDIT 1]: Legacy Object Migration
        const objKeys = localStorage.getItem('tome_master_keys');
        if (objKeys) {
            try {
                const parsed = JSON.parse(objKeys);
                Object.assign(newVault, parsed);
            } catch (e) {
            }
        }

        // [AUDIT 2]: Individual Folder Migration
        LEGACY_KEYS.forEach(k => {
            const val = localStorage.getItem(k);
            if (val && !val.startsWith('{')) {
                const provider = k.split('_').pop() || '';
                if (provider && !newVault[provider]) {
                    newVault[provider] = val;
                }
            }
        });

        // [RESOLUTION]: Absolute Bedrock Rooting & Upgrading
        if (Object.keys(newVault).length > 0) {
            // [UPGRADE]: Map legacy brands to their respective slots if they don't exist yet
            if (newVault.gemini && !newVault.slot_primary) newVault.slot_primary = newVault.gemini;
            if (newVault.openai && !newVault.slot_specialist) newVault.slot_specialist = newVault.openai;
            if (newVault.groq && !newVault.slot_velocity) newVault.slot_velocity = newVault.groq;
            
            secureVault.save(newVault);
        }
    } catch (err) {
    }
}
