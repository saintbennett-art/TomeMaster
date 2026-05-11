// [CERTIFICATION GRADE]: Secure Vault Proxy
// Browser-based storage (localStorage) of API keys is DEPRECATED and REMOVED.
// All keys are now managed via the backend's OS-level environment/vault.

export const secureVault = {
    /**
     * @deprecated Use backend API to save keys.
     */
    save: (keys: Record<string, string>) => {
        console.warn("secureVault.save is deprecated. Use apiClient.saveVaultToEnv instead.");
    },
    
    /**
     * @deprecated Use apiClient.fetchVaultSync to check key presence.
     */
    load: (): Record<string, string> => {
        return {}; // Returns empty to force backend usage
    },
    
    clear: () => {
        if (typeof window === "undefined") return;
        localStorage.removeItem("tome_master_vault_v2");
        localStorage.removeItem("tome_master_vault");
    }
};
