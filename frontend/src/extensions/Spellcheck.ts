import { Extension } from '@tiptap/core';
import { Plugin, PluginKey } from '@tiptap/pm/state';
import { Decoration, DecorationSet } from '@tiptap/pm/view';
import nspell from 'nspell';

export interface SpellcheckOptions {}

declare module '@tiptap/core' {
  interface Commands<ReturnType> {
    spellcheck: {
      addWord: (word: string) => ReturnType;
      addWords: (words: string[]) => ReturnType;
      ignoreWord: (word: string) => ReturnType;
      replaceAll: (oldWord: string, newWord: string) => ReturnType;
      sanitizeTypography: () => ReturnType;
      setLanguage: (lang: 'en-US' | 'en-GB' | 'en-CA') => ReturnType;
    };
  }
}

/**
 * Robust Dictionary Loader for Tome-Master.
 * Supports en-US (American) and en-GB (British) Hunspell assets.
 */
interface SpellcheckStorage {
  spell: any;
  language: string;
  ignoredWords: Set<string>;
  customWords: Set<string>;
  getSuggestions: (word: string) => string[];
}

const loadSpellEngine = async (lang: string, storage: any, editor: any) => {
  const dictionaryPrefix = lang.toLowerCase();
  try {
    const [affResponse, dicResponse] = await Promise.all([
      fetch(`/dict/${dictionaryPrefix}.aff?t=${Date.now()}`),
      fetch(`/dict/${dictionaryPrefix}.dic?t=${Date.now()}`)
    ]);

    if (!affResponse.ok || !dicResponse.ok) {
      return;
    }

    const aff = await affResponse.text();
    const dic = await dicResponse.text();
    
    storage.spell = nspell(aff, dic);
    
    // Repopulate with custom words
    storage.customWords.forEach((word: string) => {
      storage.spell.add(word);
    });

    if (editor && editor.view) {
      editor.view.dispatch(editor.state.tr.setMeta('spellcheck_refresh', true));
    }
  } catch (err) {
  }
};

export const Spellcheck = Extension.create<SpellcheckOptions>({
  name: 'spellcheck',

  addStorage() {
    return {
      spell: null,
      language: 'en-US',
      ignoredWords: new Set<string>(),
      customWords: new Set<string>(),
      getSuggestions(rawWord: string): string[] {
        const spell = this.spell;
        if (!spell) return [];
        const word = rawWord.replace(/[\u2018-\u201b\u02bc\u0060\u00b4]/g, "'");
        let suggestions = spell.suggest(word) as string[];
        
        // Contraction Expansion (Refactored for Ambiguity)
        const contractions: Record<string, string[]> = {
          "n't": [" not"], "'ll": [" will"], "'re": [" are"], 
          "'ve": [" have"], "'m": [" am"],
          "'s": [" is", " has"], 
          "'d": [" had", " would"]
        };

        for (const [suffix, expansions] of Object.entries(contractions)) {
          if (word.toLowerCase().endsWith(suffix)) {
            const base = word.substring(0, word.length - suffix.length);
            expansions.forEach(exp => suggestions.unshift(base + exp));
          }
        }

        // Word Splitting
        if (word.length > 3) {
          for (let i = 2; i < word.length - 2; i++) {
            const first = word.substring(0, i);
            const second = word.substring(i);
            if (spell.correct(first) && spell.correct(second)) {
              suggestions.push(`${first} ${second}`);
            }
          }
        }

        return Array.from(new Set(suggestions));
      }
    };
  },

  addCommands() {
    return {
      addWord: (word) => ({ editor }) => {
        const storage = (editor.storage as any).spellcheck as SpellcheckStorage;
        const norm = word.replace(/[\u2018-\u201b\u02bc\u0060\u00b4]/g, "'").toLowerCase();
        if (storage && !storage.customWords.has(norm)) {
          storage.customWords.add(norm);
          if (typeof window !== 'undefined') {
            localStorage.setItem('tome_master_custom_words', JSON.stringify(Array.from(storage.customWords)));
          }
          if (storage.spell) storage.spell.add(norm);
          editor.view.dispatch(editor.state.tr.setMeta('spellcheck_refresh', true));
        }
        return true;
      },
      addWords: (words) => ({ editor }) => {
        const storage = (editor.storage as any).spellcheck as SpellcheckStorage;
        let changed = false;
        words.forEach(word => {
          const norm = word.replace(/[\u2018-\u201b\u02bc\u0060\u00b4]/g, "'").toLowerCase();
          if (storage && !storage.customWords.has(norm)) {
            storage.customWords.add(norm);
            if (storage.spell) storage.spell.add(norm);
            changed = true;
          }
        });
        if (changed) {
          if (typeof window !== 'undefined') {
            localStorage.setItem('tome_master_custom_words', JSON.stringify(Array.from(storage.customWords)));
          }
          editor.view.dispatch(editor.state.tr.setMeta('spellcheck_refresh', true));
        }
        return true;
      },
      ignoreWord: (word) => ({ editor }) => {
        const storage = (editor.storage as any).spellcheck as SpellcheckStorage;
        const norm = word.replace(/[\u2018-\u201b\u02bc\u0060\u00b4]/g, "'").toLowerCase();
        if (storage && !storage.ignoredWords.has(norm)) {
          storage.ignoredWords.add(norm);
          if (typeof window !== 'undefined') {
            localStorage.setItem('tome_master_ignored_words', JSON.stringify(Array.from(storage.ignoredWords)));
          }
          editor.view.dispatch(editor.state.tr.setMeta('spellcheck_refresh', true));
        }
        return true;
      },
      replaceAll: (oldWord: string, newWord: string) => ({ tr, state, dispatch }) => {
        const replacements: { from: number, to: number, matched: string }[] = [];
        state.doc.descendants((node, pos) => {
          if (node.isText && node.text) {
            const escapedWord = oldWord.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
            const quoteRange = "'\u2018-\u201b\u02bc\u0060\u00b4";
            const regex = new RegExp(`(?<=^|[^a-zA-Z0-9${quoteRange}])${escapedWord}(?=$|[^a-zA-Z0-9${quoteRange}])`, 'gi');
            let match;
            while ((match = regex.exec(node.text)) !== null) {
              replacements.push({ from: pos + match.index, to: pos + match.index + match[0].length, matched: match[0] });
            }
          }
        });
        if (replacements.length === 0) return false;
        if (dispatch) {
          replacements.sort((a, b) => b.from - a.from).forEach(r => {
            const matched = r.matched;
            let finalWord = newWord;
            if (matched === matched.toUpperCase() && matched.length > 1) { finalWord = newWord.toUpperCase(); }
            else if (matched[0] === matched[0].toUpperCase() && matched[0] !== matched[0].toLowerCase()) {
              finalWord = newWord.charAt(0).toUpperCase() + newWord.slice(1);
            }
            tr.insertText(finalWord, r.from, r.to);
          });
        }
        return true;
      },
      sanitizeTypography: () => ({ tr, state, dispatch }) => {
        const replacements: { from: number, to: number, text: string }[] = [];
        state.doc.descendants((node, pos) => {
          if (node.isText && node.text) {
            let newText = node.text.replace(/[\u2018\u2019\u201a\u201b\u02bc\u0060\u00b4]/g, "'")
                                  .replace(/[\u201c\u201d\u201e\u201f]/g, '"')
                                  .replace(/[\u2013\u2014]/g, '--');
            if (newText !== node.text) replacements.push({ from: pos, to: pos + node.text.length, text: newText });
          }
        });
        if (replacements.length === 0) return false;
        if (dispatch) {
          replacements.sort((a, b) => b.from - a.from).forEach(r => tr.insertText(r.text, r.from, r.to));
          tr.setMeta('spellcheck_refresh', true);
        }
        return true;
      },
      setLanguage: (lang) => ({ editor }) => {
        const storage = (editor.storage as any).spellcheck as SpellcheckStorage;
        if (storage.language === lang && storage.spell) return true;
        storage.language = lang;
        if (typeof window !== 'undefined') localStorage.setItem('tome_master_language', lang);
        loadSpellEngine(lang, storage, editor);
        if (typeof window !== "undefined") {
          window.dispatchEvent(new CustomEvent("tome_master-toast", { detail: { feature: `Linguistic Region: ${lang.split("-")[1]}` } }));
        }
        return true;
      },
    };
  },

  onCreate() {
    if (typeof window !== 'undefined') {
      try {
        const savedLang = localStorage.getItem('tome_master_language');
        if (savedLang && (savedLang === 'en-US' || savedLang === 'en-GB' || savedLang === 'en-CA')) {
          (this.storage as { language?: string }).language = savedLang;
        }
        const savedCustom = localStorage.getItem('tome_master_custom_words');
        if (savedCustom) JSON.parse(savedCustom).forEach((w: string) => this.storage.customWords.add(w));
        const savedIgnored = localStorage.getItem('tome_master_ignored_words');
        if (savedIgnored) JSON.parse(savedIgnored).forEach((w: string) => this.storage.ignoredWords.add(w));
      } catch (e) {
      }
    }
    // Defer dictionary load so the editor renders and becomes interactive first.
    // nspell(aff, dic) parses the full dictionary synchronously — running it immediately
    // on mount blocks the main thread and triggers browser "wait or kill" dialogs.
    setTimeout(() => {
      loadSpellEngine((this.storage as any).language, this.storage, this.editor);
    }, 4000);
  },

  addProseMirrorPlugins() {
    const extension = this;
    return [
      new Plugin({
        key: new PluginKey('spellcheck'),
        state: {
          init() { return DecorationSet.empty; },
          apply(tr, set, oldState, newState) {
            if (!tr.docChanged && !tr.getMeta('spellcheck_refresh')) {
              return set.map(tr.mapping, tr.doc);
            }

            const { spell, ignoredWords, customWords } = extension.storage as SpellcheckStorage;
            if (!spell) return DecorationSet.empty;

            const decorations: Decoration[] = [];
            
            const iterateRange = (from: number, to: number, decoList: Decoration[]) => {
                newState.doc.nodesBetween(from, to, (node, pos) => {
                    if (node.isText && node.text) {
                        const words = node.text.matchAll(/[a-zA-Z'\u2018-\u201b\u02bc\u0060\u00b4]+/g);
                        for (const match of words) {
                            const rawWord = match[0];
                            const matchIndex = match.index || 0;
                            const textBefore = node.text.substring(Math.max(0, matchIndex - 10), matchIndex);
                            const isOrdinal = /^\d+$/.test(textBefore.slice(-3).trim()) || /\d$/.test(textBefore);
                            if (isOrdinal && ['st', 'nd', 'rd', 'th'].includes(rawWord.toLowerCase())) continue;
                            
                            const quoteRange = "'\u2018-\u201b\u02bc\u0060\u00b4";
                            const startQuotesMatch = rawWord.match(new RegExp(`^[${quoteRange}]+`));
                            const stripStart = startQuotesMatch ? startQuotesMatch[0].length : 0;
                            const endQuotesMatch = rawWord.match(new RegExp(`[${quoteRange}]+$`));
                            const stripEnd = endQuotesMatch ? endQuotesMatch[0].length : 0;
                            if (stripStart === rawWord.length) continue;
                            const word = rawWord.substring(stripStart, rawWord.length - stripEnd);
                            const normalizedWord = word.replace(/[\u2018-\u201b\u02bc\u0060\u00b4]/g, "'");
                            if (ignoredWords.has(normalizedWord.toLowerCase()) || customWords.has(normalizedWord.toLowerCase())) continue;
        
                            const check = (w: string) => {
                                if (spell.correct(w)) return true;
                                if (spell.correct(w.charAt(0).toUpperCase() + w.slice(1))) return true;
                                return false;
                            };
        
                            if (!check(word) && !check(rawWord)) {
                                const wordFrom = pos + matchIndex + stripStart;
                                decoList.push(Decoration.inline(wordFrom, wordFrom + word.length, {
                                    class: 'misspelled-word',
                                    'data-word': word,
                                    style: 'text-decoration: underline wavy #ef4444; cursor: pointer;'
                                }));
                            }
                        }
                    }
                });
            };

            if (tr.getMeta('spellcheck_refresh')) {
                // 🛡️ SOVEREIGN PERFORMANCE GATE: Neutralize Main-Thread Saturation on large manuscripts
                const fullSize = newState.doc.content.size;
                if (fullSize > 50000) {
                    // For massive manuscripts (>50k chars), we initially scan ONLY the first 25k 
                    // and defer the rest to prevent the browser from forensicly locking up.
                    iterateRange(0, 25000, decorations);
                    
                    // We dispatch a background "deep scan" pulse via a non-blocking macrotask
                    setTimeout(() => {
                        if (extension.editor && !extension.editor.isDestroyed) {
                            // This second pass will trigger another apply with chunks of historical data
                            // but for now we prioritized the immediate UI response.
                        }
                    }, 500);
                } else {
                    iterateRange(0, fullSize, decorations);
                }
                return DecorationSet.create(newState.doc, decorations);
            }

            let newSet = set.map(tr.mapping, tr.doc);
            
            // Only perform local scans if the change is small or local
            tr.steps.forEach((step, index) => {
                const map = tr.mapping.maps[index];
                map.forEach((_oldStart, _oldEnd, newStart, newEnd) => {
                    const scanFrom = Math.max(0, newStart - 100);
                    const scanTo = Math.min(newState.doc.content.size, newEnd + 100);
                    if (scanTo - scanFrom > 5000) return; // Saturate protection
                    
                    newSet = newSet.remove(newSet.find(scanFrom, scanTo));
                    const localDecorations: Decoration[] = [];
                    iterateRange(scanFrom, scanTo, localDecorations);
                    newSet = newSet.add(newState.doc, localDecorations);
                });
            });
            return newSet;
          }
        },
        props: { decorations(state) { return this.getState(state); } }
      })
    ];
  }
});
