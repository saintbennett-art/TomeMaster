/**
 * SOVEREIGN FILESYSTEM ACCESS BRIDGE
 * Transitioning workstation digital commitments from sandboxed downloads 
 * to native OS filesystem agency.
 */

export async function saveBlobWithSovereignty(blob: Blob, suggestedName: string, description: string = "Manuscript"): Promise<boolean> {
    const extension = suggestedName.split('.').pop() || 'txt';
    
    // 1. ATTEMPT NATIVE OS PICKER HANDSHAKE
    if ('showSaveFilePicker' in window) {
        try {
            const handle = await (window as any).showSaveFilePicker({
                suggestedName,
                types: [{
                    description: `${description} (.${extension})`,
                    accept: { [blob.type]: [`.${extension}`] }
                }]
            });
            
            const writable = await handle.createWritable();
            await writable.write(blob);
            await writable.close();
            return true; // Sovereign Transaction Complete
        } catch (e: any) {
            // Check for explicit user abortion
            if (e.name === 'AbortError') return false; 
            console.warn("[Sovereign Bridge] Native picker failed or restricted. Attempting Fallback Handshake...", e);
        }
    }

    // 2. FALLBACK HANDSHAKE (SANDBOXED DOWNLOAD)
    // Invoked if Browser restricts Picker access (e.g. non-Chrome, insecure context)
    const userFilename = window.prompt(`Enter ${description} name:`, suggestedName);
    if (!userFilename) return false; // Handshake Interrupted by User
    
    // Normalize Naming Persistence
    const finalName = userFilename.toLowerCase().endsWith(`.${extension}`) 
                     ? userFilename 
                     : `${userFilename}.${extension}`;

    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = finalName;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    setTimeout(() => URL.revokeObjectURL(url), 1000);
    return true;
}
