// [WORKSTATION WORKER]: Offloads heavy text processing to a background thread
self.onmessage = (e) => {
    const { type, content } = e.data;
    
    if (type === 'PROCESS_TEXT') {
        const htmlContent = content.replace(/\n\n/g, "</p><p>");
        const wordCount = content.trim() ? content.trim().split(/\s+/).length : 0;
        
        self.postMessage({
            type: 'TEXT_PROCESSED',
            htmlContent,
            wordCount
        });
    }
};
