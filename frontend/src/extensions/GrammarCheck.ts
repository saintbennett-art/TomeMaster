import { Extension } from '@tiptap/core';
import { Plugin, PluginKey } from 'prosemirror-state';
import { Decoration, DecorationSet } from 'prosemirror-view';

declare module '@tiptap/core' {
  interface Commands<ReturnType> {
    grammarCheck: {
      setGrammarEdits: (edits: {original: string, suggestion: string, reason: string}[]) => ReturnType;
      removeGrammarEdit: (id: string) => ReturnType;
    }
  }
}

export interface GrammarEdit {
  id: string;
  original: string;
  suggestion: string;
  reason: string;
}

interface GrammarStorage {
  edits: GrammarEdit[];
}

export const GrammarCheck = Extension.create({
  name: 'grammarCheck',

  addStorage() {
    return {
      edits: [] as GrammarEdit[],
    };
  },

  addCommands() {
    return {
      setGrammarEdits: (edits: {original: string, suggestion: string, reason: string}[]) => ({ editor }) => {
        const storage = (editor.storage as unknown as Record<string, GrammarStorage>).grammarCheck;
        storage.edits = edits.map(e => ({ ...e, id: Math.random().toString(36).substring(7) }));
        editor.view.dispatch(editor.state.tr.setMeta('grammar_refresh', true));
        return true;
      },
      removeGrammarEdit: (id: string) => ({ editor }) => {
        const storage = (editor.storage as unknown as Record<string, GrammarStorage>).grammarCheck;
        storage.edits = storage.edits.filter((e: GrammarEdit) => e.id !== id);
        editor.view.dispatch(editor.state.tr.setMeta('grammar_refresh', true));
        return true;
      }
    };
  },

  addProseMirrorPlugins() {
    return [
      new Plugin({
        key: new PluginKey('grammarCheck'),
        state: {
          init() { return DecorationSet.empty; },
          apply: (tr, set) => {
            // Optimization: Skip all calculations if the document is stagnant
            if (!tr.docChanged && !tr.getMeta('grammar_refresh')) {
              return set.map(tr.mapping, tr.doc);
            }

            const storage = (this.editor.storage as unknown as Record<string, GrammarStorage>).grammarCheck;
            const edits = storage.edits;
            
            const decorations: Decoration[] = [];
            const iterateRange = (from: number, to: number, decoList: Decoration[]) => {
                if (!edits || edits.length === 0) return;
                this.editor.state.doc.nodesBetween(from, to, (node, pos) => {
                    if (node.isBlock && node.textContent.length > 0) {
                        const blockText = node.textContent;
                        edits.forEach(edit => {
                            if (!edit.original) return;
                            let idx = blockText.indexOf(edit.original);
                            while (idx !== -1) {
                                const decoFrom = pos + 1 + idx;
                                const decoTo = decoFrom + edit.original.length;
                                decoList.push(Decoration.inline(decoFrom, decoTo, {
                                    class: 'grammar-squiggle',
                                    'nodeName': 'span',
                                    'data-id': edit.id,
                                    'data-suggestion': edit.suggestion,
                                    'data-reason': edit.reason
                                }));
                                idx = blockText.indexOf(edit.original, idx + edit.original.length);
                            }
                        });
                    }
                });
            };

            // CASE 1: Full Refresh (Chunked for Absolute Performance)
            const fullSize = tr.doc.content.size;
            if (tr.getMeta('grammar_refresh')) {
                if (fullSize > 50000) {
                    // Sovereign Gate: Scan only initial 25k for immediate response
                    iterateRange(0, 25000, decorations);
                } else {
                    iterateRange(0, fullSize, decorations);
                }
                return DecorationSet.create(tr.doc, decorations);
            }

            // CASE 2: Differential Optimization
            let newSet = set.map(tr.mapping, tr.doc);
            tr.steps.forEach((step, index) => {
                const map = tr.mapping.maps[index];
                map.forEach((_oldStart, _oldEnd, newStart, newEnd) => {
                    const scanFrom = Math.max(0, newStart - 100);
                    const scanTo = Math.min(tr.doc.content.size, newEnd + 100);
                    newSet = newSet.remove(newSet.find(scanFrom, scanTo));
                    const localDecorations: Decoration[] = [];
                    iterateRange(scanFrom, scanTo, localDecorations);
                    newSet = newSet.add(tr.doc, localDecorations);
                });
            });

            return newSet;
          }
        },
        props: {
          decorations(state) {
            return this.getState(state);
          }
        }
      })
    ];
  }
});
