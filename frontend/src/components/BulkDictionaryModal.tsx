import { useState, useEffect } from "react";
import { X, CheckCheck, Loader2, ListChecks } from "lucide-react";

interface BulkDictionaryModalProps {
  isOpen: boolean;
  onClose: () => void;
  misspelledWords: string[];
  onAddBulk: (words: string[]) => void;
}

export default function BulkDictionaryModal({ isOpen, onClose, misspelledWords, onAddBulk }: BulkDictionaryModalProps) {
  const [selectedWords, setSelectedWords] = useState<Set<string>>(new Set());
  const [isProcessing, setIsProcessing] = useState(false);

  // When modal opens, auto-select all words initially
  useEffect(() => {
    if (isOpen) {
      setSelectedWords(new Set(misspelledWords));
      setIsProcessing(false);
    }
  }, [isOpen, misspelledWords]);

  if (!isOpen) return null;

  const toggleWord = (word: string) => {
    const next = new Set(selectedWords);
    if (next.has(word)) {
      next.delete(word);
    } else {
      next.add(word);
    }
    setSelectedWords(next);
  };

  const selectAll = () => {
    if (selectedWords.size === misspelledWords.length) {
      setSelectedWords(new Set()); // Deselect all if all are selected
    } else {
      setSelectedWords(new Set(misspelledWords)); // Otherwise, select all
    }
  };

  const handleApply = async () => {
    if (selectedWords.size === 0) return;
    setIsProcessing(true);
    
    // Slight timeout allows the UI "Processing..." state to render before heavy Tiptap dispatching
    setTimeout(() => {
      onAddBulk(Array.from(selectedWords));
      setIsProcessing(false);
      onClose();
    }, 50);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 animate-in fade-in duration-200">
      <div className="bg-[#111] border border-zinc-800 rounded-xl shadow-2xl w-full max-w-md overflow-hidden flex flex-col">
        
        {/* Header */}
        <div className="px-5 py-4 border-b border-zinc-800 flex justify-between items-center bg-[#18181b]">
          <div className="flex items-center gap-2">
            <ListChecks className="w-5 h-5 text-indigo-400" />
            <h2 className="text-sm font-semibold text-zinc-100 uppercase tracking-widest">Bulk Dictionary Loader</h2>
          </div>
          <button 
            onClick={onClose}
            className="p-1.5 text-zinc-500 hover:bg-[#222] hover:text-zinc-300 rounded-md transition-colors"
            title="Close Dictionary Loader"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Content */}
        <div className="p-5 flex-1 flex flex-col bg-[#0a0a0a]">
          <p className="text-zinc-400 text-sm mb-4 leading-relaxed">
            Found <strong className="text-indigo-400">{misspelledWords.length}</strong> unique flagged words. Select the ones you want to permanently add to your custom dictionary.
          </p>

          <div className="flex justify-between items-center mb-2 px-1">
            <span className="text-xs font-medium text-zinc-500 uppercase tracking-wide">
              {selectedWords.size} Selected
            </span>
            <button 
              onClick={selectAll}
              className="text-xs text-indigo-400 hover:text-indigo-300 font-medium"
            >
              {selectedWords.size === misspelledWords.length ? "Deselect All" : "Select All"}
            </button>
          </div>

          <div className="flex-1 max-h-64 overflow-y-auto border border-zinc-800 rounded-md bg-[#111] p-2 pr-3 bright-scrollbar relative">
            {misspelledWords.length === 0 ? (
              <div className="text-center p-8 text-zinc-600 text-sm italic">
                No misspelled words found in document.
              </div>
            ) : (
              <div className="grid grid-cols-2 gap-2">
                {misspelledWords.map(word => {
                  const isChecked = selectedWords.has(word);
                  return (
                    <label 
                      key={word}
                      className={`flex items-center gap-2 p-2 rounded-md cursor-pointer transition-colors border ${
                        isChecked ? 'border-indigo-500/30 bg-indigo-500/10' : 'border-zinc-800/50 hover:bg-[#18181b]'
                      }`}
                    >
                      <input 
                        type="checkbox"
                        checked={isChecked}
                        onChange={() => toggleWord(word)}
                        className="accent-indigo-500 cursor-pointer w-4 h-4 rounded-sm border-zinc-700 bg-[#222]"
                      />
                      <span className={`text-sm font-medium ${isChecked ? 'text-indigo-100' : 'text-zinc-400'}`}>
                        {word}
                      </span>
                    </label>
                  );
                })}
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="px-5 py-4 border-t border-zinc-800 bg-[#18181b] flex justify-end gap-3">
          <button 
            onClick={onClose}
            className="px-4 py-2 text-sm font-medium text-zinc-400 hover:text-white hover:bg-[#333] rounded-lg transition-colors"
          >
            Cancel
          </button>
          <button 
            onClick={handleApply}
            disabled={isProcessing || selectedWords.size === 0}
            className={`flex items-center gap-2 px-4 py-2 text-sm font-bold rounded-lg transition-colors shadow-lg shadow-indigo-500/20 ${
              isProcessing || selectedWords.size === 0 
                ? 'bg-indigo-600/50 text-indigo-200/50 cursor-not-allowed' 
                : 'bg-indigo-600 text-white hover:bg-indigo-500 hover:shadow-indigo-500/40'
            }`}
          >
            {isProcessing ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" /> Processing...
              </>
            ) : (
              <>
                <CheckCheck className="w-4 h-4" /> Add Selected to Dictionary
              </>
            )}
          </button>
        </div>

      </div>
    </div>
  );
}
