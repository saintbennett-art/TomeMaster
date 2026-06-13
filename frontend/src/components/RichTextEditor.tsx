"use client";
import { useEditor, EditorContent } from '@tiptap/react';
import StarterKit from '@tiptap/starter-kit';
import Placeholder from '@tiptap/extension-placeholder';
import { TextAlign } from '@tiptap/extension-text-align';
import { Bold, Italic, Strikethrough as StrikeIcon, Heading1, Heading2, Pilcrow, List, ListOrdered, Undo, Redo, Quote, AlignLeft, AlignCenter, AlignRight, ReplaceAll, Wand2, Plus, FastForward, EyeOff, Check, BookCheck, Lock, Pen, Type, Globe, Pin, PinOff, Eraser, Search, ArrowUp, ArrowDown, X } from 'lucide-react';
import React, { useEffect, useRef, forwardRef, useImperativeHandle, useState } from 'react';
import DOMPurify from 'dompurify';
import { createPortal } from 'react-dom';
import { Spellcheck } from '../extensions/Spellcheck';
import { GrammarCheck } from '../extensions/GrammarCheck';
import BulkDictionaryModal from './BulkDictionaryModal';
import { useWorkstationState, useWorkstationActions } from "@/context/WorkstationContext";
import { Chapter } from "@/types/industrial";

const SELECTION_NOTIF_DEBOUNCE = 10000; // 10 seconds
let lastSelectionNotif = 0;

export interface RichTextEditorRef {
  insertDictation: (text: string) => void;
  getDecoratedHTML: () => string;
  insertChunk: (html: string) => void;
  setContent: (html: string) => void;
  insertContent: (html: string) => void;
  replaceText: (search: string, replacement: string) => void;
  clearContent: () => void;
  purgePdfMarkers: () => void;
  generateTOC: () => any[];
  sanitizeTypography: () => void;
  setLanguage: (lang: 'en-US' | 'en-GB' | 'en-CA') => void;
  undo: () => void;
  redo: () => void;
}

interface RichTextEditorProps {
  content: string;
  onChange: (text: string, html: string, isEmpty: boolean) => void;
  placeholder?: string;
  isFocusMode?: boolean;
  scrollToText?: string | null;
  onScrollComplete?: () => void;
  acceptedChapter?: { title: string, startingWords: string, timestamp: number } | null;
  acceptedWarning?: { warning: string, startingWords: string, timestamp: number } | null;
  chapters?: Chapter[];
  onCursorPageChange?: (page: number) => void;
  onGrammarCheck?: () => void;
  onSelectionChange?: (text: string) => void;
  onCurrentChapterChange?: (chapterId: string | null) => void;
  onCurrentParagraphChange?: (text: string) => void;
  onWarningPlaced?: (id: string) => void;
  isActivated: boolean;
  onMisspelledCountChange?: (count: number) => void;
}

import { Node, mergeAttributes } from '@tiptap/core';

const PdfPageMarker = Node.create({
  name: 'pdfPageMarker',
  group: 'block',
  addAttributes() {
    return {
      'data-page': { default: null },
      class: { default: 'pdf-page-marker' },
      style: { default: 'display: none;' }
    }
  },
  parseHTML() {
    return [{ tag: 'hr.pdf-page-marker' }]
  },
  renderHTML({ HTMLAttributes }) {
    return ['hr', mergeAttributes(HTMLAttributes)]
  }
});

export const RichTextEditor = forwardRef<RichTextEditorRef, RichTextEditorProps>(({ content, onChange, placeholder, isFocusMode, scrollToText, onScrollComplete, acceptedChapter, acceptedWarning, chapters, onCursorPageChange, onGrammarCheck, onSelectionChange, onCurrentChapterChange, onCurrentParagraphChange, onWarningPlaced, isActivated, onMisspelledCountChange }, ref) => {
  const [spellBubble, setSpellBubble] = useState<{ word: string, pos: number, suggestions: string[], visible: boolean, x: number, y: number, el: HTMLElement } | null>(null);
  const [grammarBubble, setGrammarBubble] = useState<{ id: string, original: string, suggestion: string, reason: string, pos: number, visible: boolean, x: number, y: number, flip: boolean } | null>(null);
  const [isBulkDictOpen, setIsBulkDictOpen] = useState(false);
  const [isLangMenuOpen, setIsLangMenuOpen] = useState(false);
  const [isToolbarPinned, setIsToolbarPinned] = useState(false);
  const [isFindReplaceOpen, setIsFindReplaceOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [replaceQuery, setReplaceQuery] = useState('');
  const [searchOccurrences, setSearchOccurrences] = useState<{node: HTMLElement, pos: number}[]>([]);
  const [currentSearchIndex, setCurrentSearchIndex] = useState(-1);
  const { language } = useWorkstationState();
  const { setLanguage } = useWorkstationActions();
  const [bulkMisspellings, setBulkMisspellings] = useState<string[]>([]);
  const editorContainerRef = useRef<HTMLDivElement>(null);
  const hoverTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const debounceSyncRef = useRef<NodeJS.Timeout | null>(null);
  

  const editor = useEditor({
    extensions: [
      StarterKit,
      Placeholder.configure({
        placeholder: placeholder || 'Write your manuscript here...',
        emptyEditorClass: 'is-editor-empty',
      }),
      PdfPageMarker,
      Spellcheck,
      GrammarCheck,
    ],
    content: content,
    immediatelyRender: false,
    onUpdate: ({ editor }) => {
      // 500ms Debounce to prevent "clunky and slow" app-wide re-renders on every keystroke
      if (debounceSyncRef.current) clearTimeout(debounceSyncRef.current);
      debounceSyncRef.current = setTimeout(() => {
          const text = editor.getText({ blockSeparator: '\n\n' });
          const html = editor.getHTML();
          
          // [PERFORMANCE CACHE]: Establish the serialization result so the sync hook can bypass verification
          lastSyncedContentRef.current = html;
          lastSyncedSizeRef.current = editor.state.doc.content.size;
          
          onChange(text, html, editor.isEmpty);
      }, 500);
    },
    onSelectionUpdate: ({ editor }) => {
      // [PERFORMANCE GATE]: Debounce selection metadata to prevent "Not Responding" hangs on large manuscripts
      if (hoverTimeoutRef.current) clearTimeout(hoverTimeoutRef.current);
      hoverTimeoutRef.current = setTimeout(() => {
        if (!editor || editor.isDestroyed) return;
        const { from, to } = editor.state.selection;
        
        // 1. Capture Selected Text (Local only)
        if (onSelectionChange) {
            const selectedText = (to > from) ? editor.state.doc.textBetween(from, to, ' ') : "";
            onSelectionChange(selectedText);
        }

        // 2. Track Cursor Page & Chapter (Calibrated Discovery)
        const docSize = editor.state.doc.content.size;
        
        // [PERFORMANCE ROOT]: Avoid massive string allocations on large manuscripts
        // We estimate page count based on character density (~6 chars per word, 250 words per page)
        // This is O(1) instead of O(N) serialization.
        const pageNum = Math.floor(from / (6 * 250)) + 1;
        if (onCursorPageChange) onCursorPageChange(pageNum);

        // 3. Track Current Chapter (Scope Root)
        if (onCurrentChapterChange && chapters && chapters.length > 0) {
            let currentChapId = null;
            
            // Forensic Search: Walk the doc to find the nearest heading BEFORE the cursor
            // We use the last 500 characters to find the boundary, preventing full doc traversal
            const searchLimit = Math.max(0, from - 2000); 
            editor.state.doc.nodesBetween(searchLimit, from, (node, pos) => {
                if (node.type.name === 'heading') {
                    const title = node.textContent;
                    const match = chapters.find(c => c.original_heading === title || c.suggested_title === title);
                    if (match) currentChapId = match.starting_words;
                }
                return true; 
            });
            onCurrentChapterChange(currentChapId);
        }

        // 4. Track Current Paragraph for local context
        if (onCurrentParagraphChange) {
            const $pos = editor.state.doc.resolve(from);
            const paraNode = $pos.parent;
            if (paraNode && paraNode.type.name === 'paragraph') {
                onCurrentParagraphChange(paraNode.textContent);
            } else {
                onCurrentParagraphChange("");
            }
        }
      }, 200);
    },
    editorProps: {
      handleDOMEvents: {
        copy: (view, event) => {
            return false;
        },
        cut: (view, event) => {
            return false;
        },
        contextmenu: (view, event) => {
            return false;
        },
        mousedown: (view, event) => {
            return false;
        },
        keydown: (view, event) => {
            const isMod = event.ctrlKey || event.metaKey;
            return false;
        },
      },
      attributes: {
        class: `flex-1 w-full min-w-0 bg-transparent resize-none outline-none p-10 lg:p-16 text-foreground font-serif leading-relaxed text-lg prose prose-p:my-2 prose-p:text-justify prose-headings:font-sans prose-headings:font-bold prose-h1:text-3xl prose-h2:text-2xl min-h-full max-w-none break-words whitespace-pre-wrap`,
        spellcheck: 'false',
      },
    },
  });

  const handleJumpToNextError = () => {
    if (!editorContainerRef.current || !editor) return;
    
    // Small delay to allow ProseMirror to finish decorations update
    setTimeout(() => {
        if (!editorContainerRef.current) return;
        const errorNodes = Array.from(editorContainerRef.current.querySelectorAll('.misspelled-word')) as HTMLElement[];
        if (errorNodes.length === 0) return;

        const containerRect = editorContainerRef.current.getBoundingClientRect();
        let targetNode: HTMLElement | null = null;
        const scrollThreshold = containerRect.top + 80; 
        
        for (let i = 0; i < errorNodes.length; i++) {
            const rect = errorNodes[i].getBoundingClientRect();
            if (rect.height > 0 && rect.top > scrollThreshold) {
                targetNode = errorNodes[i];
                break;
            }
        }
        
        if (!targetNode) targetNode = errorNodes[0];
        
        if (targetNode) {
            targetNode.scrollIntoView({ behavior: 'smooth', block: 'center' });
            targetNode.style.transition = 'background-color 0.4s ease-out';
            targetNode.style.backgroundColor = 'rgba(239, 68, 68, 0.4)';
            setTimeout(() => { if (targetNode) targetNode.style.backgroundColor = '' }, 400);

            // RE-PROBE: Use live posAtDOM to ensure the cursor lands exactly on the current word position
            try {
                const pos = editor.view.posAtDOM(targetNode, 0);
                if (!isNaN(pos) && pos >= 0) {
                    editor.chain().focus().setTextSelection(pos).run();
                }
            } catch (err) {
                // Silent Navigation Probe Failure
            }
        }
    }, 40);
  };

  useImperativeHandle(ref, () => ({
    insertDictation: (text: string) => {
      if (editor) {
        // We append a trailing space so continuous talking chains fluidly
        editor.chain().focus().insertContent(text + " ").run();
      }
    },
    getDecoratedHTML: () => {
      if (editorContainerRef.current) {
         const pmNode = editorContainerRef.current.querySelector('.ProseMirror');
         return pmNode ? pmNode.innerHTML : (editor?.getHTML() || "");
      }
      return editor?.getHTML() || "";
    },
    insertChunk: (html: string) => {
      if (editor) {
        editor.commands.insertContentAt(editor.state.doc.content.size, DOMPurify.sanitize(html));
      }
    },
    setContent: (html: string) => {
      if (editor) {
        editor.commands.setContent(DOMPurify.sanitize(html));
      }
    },
    insertContent: (html: string) => {
      if (editor) {
        editor.chain().focus().insertContent(DOMPurify.sanitize(html)).run();
      }
    },
    replaceText: (search: string, replacement: string) => {
      if (!editor) return;
      const { state } = editor;
      let found = false;
      
      state.doc.descendants((node, pos) => {
        if (found) return false;
        if (node.isText && node.text?.includes(search)) {
          const index = node.text.indexOf(search);
          editor.chain()
            .focus()
            .deleteRange({ from: pos + index, to: pos + index + search.length })
            .insertContentAt(pos + index, replacement)
            .run();
          found = true;
          return false;
        }
      });
    },
    clearContent: () => {
      if (editor) {
        editor.commands.setContent("");
      }
    },
    generateTOC: () => {
      if (!editor) return [];
      const { state } = editor;
      const doc = state.doc;
      const toc: Chapter[] = [];
      
      let currentChapter: Chapter | null = null;
      let chapterText: string[] = [];

      doc.descendants((node, pos) => {
        if (node.type.name === 'heading') {
          // If we were already tracking a chapter, finalize it
          if (currentChapter) {
            currentChapter.content = chapterText.join('\n\n');
            currentChapter.chapter_word_count = chapterText.join(' ').split(/\s+/).filter(w => w.length > 0).length;
            toc.push(currentChapter);
          }

          // Start a new chapter
          const title = node.textContent;
          currentChapter = {
            id: `toc-${toc.length + 1}`,
            chapter_number: toc.length + 1,
            suggested_title: title.replace(/^Chapter\s*\d+\s*[:\-]?\s*/i, '').trim() || `Chapter ${toc.length + 1}`,
            starting_words: "", // Will be populated by the next node
            page_number: Math.floor(pos / 1500) + 1,
            content: "" // Finalized at the next heading or end of doc
          };
          chapterText = [];
        } else if (currentChapter) {
          // Accumulate narrative text for the current chapter
          const text = node.textContent.trim();
          if (text) {
            if (!currentChapter.starting_words) {
              currentChapter.starting_words = text.substring(0, 100);
            }
            chapterText.push(text);
          }
        }
        return true;
      });

      // Finalize the last chapter in the book.
      // (Cast needed: TS doesn't track assignments made inside doc.descendants.)
      const lastChapter = currentChapter as Chapter | null;
      if (lastChapter) {
        lastChapter.content = chapterText.join('\n\n');
        lastChapter.chapter_word_count = chapterText.join(' ').split(/\s+/).filter(w => w.length > 0).length;
        toc.push(lastChapter);
      }
      
      return toc;
    },
    purgePdfMarkers: () => {
      if (!editor) return;
      const { state } = editor;
      let tr = state.tr;
      
      const markers: { from: number, to: number }[] = [];
      state.doc.descendants((node, pos) => {
        if (node.type.name === 'pdfPageMarker' || node.type.name === 'horizontalRule') {
          markers.push({ from: pos, to: pos + node.nodeSize });
        } else if (node.type.name === 'paragraph' && node.textContent.trim().length === 0 && node.attrs.class === 'ignored-page-break') {
          markers.push({ from: pos, to: pos + node.nodeSize });
        }
      });
      
      if (markers.length > 0) {
        markers.sort((a, b) => b.from - a.from).forEach(p => tr.delete(p.from, p.to));
      }
      
      let docAfterMarkers = tr.doc;
      let mergePositions: number[] = [];
      docAfterMarkers.descendants((node, pos) => {
        if (node.type.name === 'paragraph') {
           const nextPos = pos + node.nodeSize;
           const nextNode = docAfterMarkers.nodeAt(nextPos);
           
           if (nextNode && nextNode.type.name === 'paragraph') {
               const textA = node.textContent.trim();
               const textB = nextNode.textContent.trim();
               
               if (textA.length > 0 && textB.length > 0) {
                   const endsWithPunct = /[.?!:"\)]$|[-]$/.test(textA);
                   const startsWithLower = /^[a-z]/.test(textB);
                   if (!endsWithPunct || startsWithLower) {
                       mergePositions.push(nextPos);
                   }
               }
           }
        }
      });
      
      mergePositions.sort((a, b) => b - a).forEach(pos => {
         try {
           tr.join(pos);
           const $pos = tr.doc.resolve(pos - 1);
           const textBefore = $pos.nodeBefore?.textContent || "";
           const textAfter = $pos.nodeAfter?.textContent || "";
           if (textBefore.length > 0 && textAfter.length > 0) {
               if (textBefore.endsWith('-')) {
                   tr.delete(pos - 2, pos - 1);
               } else if (!textBefore.endsWith(' ') && !textAfter.startsWith(' ')) {
                   tr.insertText(' ', pos - 1);
               }
           }
         } catch (e) {
             // Silent Merge Bypass
         }
      });

      editor.view.dispatch(tr);
    },
    sanitizeTypography: () => {
       editor?.commands.sanitizeTypography();
    },
    setLanguage: (lang: 'en-US' | 'en-GB' | 'en-CA') => {
       editor?.commands.setLanguage(lang);
    },
    undo: () => {
       editor?.chain().focus().undo().run();
    },
    redo: () => {
       editor?.chain().focus().redo().run();
    }
  }));

  const lastSyncedContentRef = useRef<string>("");
  const lastSyncedSizeRef = useRef<number>(0);
  const isSettingContentRef = useRef<boolean>(false);

  // Sync external content changes into the editor (REFINED: Prevent "Spinning" Loop)
  useEffect(() => {
    if (!editor || content === undefined || isSettingContentRef.current) return;
    
    // [SOVEREIGN PERFORMANCE GATE]: Instant-bypass for matched string references
    if (content === lastSyncedContentRef.current) return;
    
    const docSize = editor.state.doc.content.size;
    
    // Performance Optimization: 
    // If the string length matches the previous content AND the document size, 
    // we bypass the expensive string comparison.
    if (lastSyncedContentRef.current && content.length === lastSyncedContentRef.current.length && docSize === lastSyncedSizeRef.current) {
        return;
    }

    // Deep check only if metrics differ
    const currentHTML = editor.getHTML();
    if (content !== currentHTML) {
      isSettingContentRef.current = true;
      try {
        editor.commands.setContent(content, { emitUpdate: false });
        lastSyncedContentRef.current = content;
        lastSyncedSizeRef.current = editor.state.doc.content.size;
      } finally {
        isSettingContentRef.current = false;
      }
    }
  }, [content, editor]);

  // [SOVEREIGN SENTINEL]: Synchronize local state with Tiptap storage
  useEffect(() => {
    const editorStorage = editor ? (editor.storage as unknown as Record<string, unknown>) : null;
    if (editorStorage?.spellcheck) {
        (editorStorage.spellcheck as { language: string }).language = language;
    }
  }, [language, editor]);

  useEffect(() => {
    if (editor) {
        editor.view.dispatch(editor.state.tr.setMeta('spellcheck_refresh', true));
        const currentLang = ((editor.storage as unknown as Record<string, unknown>).spellcheck as { language?: string })?.language;
        if (currentLang) setLanguage(currentLang as 'en-US' | 'en-GB' | 'en-CA');
    }
  }, [editor]);

  // Subscribe to GrammarCheck suggestions dispatched from the AI Boardroom globally
  useEffect(() => {
    const handler = (e: Event) => {
        const customEvent = e as CustomEvent;
        if (editor && customEvent.detail && Array.isArray(customEvent.detail.edits)) {
            editor.commands.setGrammarEdits(customEvent.detail.edits);
        }
    };
    window.addEventListener('copy_editor_edits', handler);
    return () => window.removeEventListener('copy_editor_edits', handler);
  }, [editor]);

  // Handle external scroll requests (e.g., from the TOC sidebar)
  useEffect(() => {
    if (editor && scrollToText && onScrollComplete) {
      setTimeout(() => {
        const view = editor.view;
        const domNodes = view.dom.querySelectorAll('p, h1, h2, h3, h4, div');
        
        const matches: HTMLElement[] = [];
        const searchStr = scrollToText.length > 20 ? scrollToText.substring(0, 20) : scrollToText;

        for (let i = 0; i < domNodes.length; i++) {
          if (domNodes[i].textContent && domNodes[i].textContent?.includes(searchStr)) {
            const el = domNodes[i] as HTMLElement;
            // Prevent nested matching (e.g. tracking both a DIV and its child P as separate hits)
            if (matches.length > 0 && matches[matches.length - 1].contains(el)) {
                continue;
            }
            matches.push(el);
          }
        }
        
        if (matches.length > 0) {
            let targetEl = matches[0];
            
            // If there are multiple unique physical matches, skip the internal TOC matches at the top.
            if (matches.length > 1) {
                const headingMatch = matches.find(el => el.tagName.match(/^H[1-6]$/i));
                if (headingMatch) {
                    targetEl = headingMatch;
                } else {
                    targetEl = matches[1];
                }
            }

            targetEl.scrollIntoView({ behavior: 'smooth', block: 'center' });

            targetEl.style.transition = 'background-color 0.5s ease';
            targetEl.style.backgroundColor = 'rgba(99, 102, 241, 0.2)'; 
            setTimeout(() => { targetEl.style.backgroundColor = 'transparent'; }, 2000);
        }
        
        onScrollComplete();
      }, 50);
    }
  }, [scrollToText, editor, onScrollComplete]);

  // Handle interacting with the AI's chapter suggestions to rewrite the DOM
  useEffect(() => {
    if (editor && acceptedChapter) {
      setTimeout(() => {
        const view = editor.view;
        const domNodes = view.dom.querySelectorAll('p, h1, h2, h3, h4, div');
        
        const normalizeForMatch = (s: string) => (s || "").toLowerCase().replace(/[^a-z0-9]/g, "").replace(/\s+/g, "");
        const targetNormalized = normalizeForMatch(acceptedChapter.startingWords);
        
        // If string is long, strip to first 30 chars for high-perf prefix matching
        let searchTarget = acceptedChapter.startingWords || "";
        if (searchTarget.length > 30) searchTarget = searchTarget.substring(0, 30);
        const searchTargetNormalized = normalizeForMatch(searchTarget);
        
        let found = false;
        for (let i = 0; i < domNodes.length; i++) {
          const textContent = domNodes[i].textContent || "";
          const contentNormalized = normalizeForMatch(textContent);
          
          const isExactMatch = textContent.includes(acceptedChapter.startingWords);
          const isNormalizedMatch = targetNormalized.length > 0 && contentNormalized.includes(targetNormalized);
          const isPrefixMatch = searchTargetNormalized.length > 10 && contentNormalized.includes(searchTargetNormalized);

          if (isExactMatch || isNormalizedMatch || isPrefixMatch) {
              // Identify the specific Tiptap Prosemirror position of the DOM node
              const pos = view.posAtDOM(domNodes[i], 0);
              const $targetPos = view.state.doc.resolve(pos);
              const targetNode = $targetPos.nodeAfter;

              let currentPos = pos;
              let startDeletePos = pos;
              
              // If the target node itself is already a heading, we should replace it!
              if (targetNode && targetNode.type.name === 'heading') {
                  // Pre-mark it for replacement; if we find more subtitles above, we'll extend the range
              }

              // Walk backwards up to 5 nodes to hunt for the Author's original Chapter Heading 
              // that this AI heading is replacing, so we can delete it and prevent duplicate titles!
              for (let steps = 0; steps < 5; steps++) {
                  const $pos = view.state.doc.resolve(currentPos);
                  const nodeBefore = $pos.nodeBefore;
                  if (!nodeBefore) break;
                  
                  if (nodeBefore.type.name === 'heading') {
                      startDeletePos = currentPos - nodeBefore.nodeSize;
                      currentPos = startDeletePos; 
                  } else if (nodeBefore.type.name === 'paragraph') {
                      const txt = nodeBefore.textContent.trim().toLowerCase();
                      if (txt.length === 0) {
                          currentPos = currentPos - nodeBefore.nodeSize;
                      } else if (txt.length < 60 && (
                          txt.startsWith('chapter') || 
                          txt.startsWith('prelude') || 
                          txt.startsWith('prologue') ||
                          txt.startsWith('part ') ||
                          txt.startsWith('section ') ||
                          txt.startsWith('episode ') ||
                          txt.startsWith('book ')
                      )) {
                          startDeletePos = currentPos - nodeBefore.nodeSize;
                          currentPos = startDeletePos; 
                      } else {
                          // Hitting actual narrative text wall means we over-walked; stop here.
                          break;
                      }
                  } else {
                      break;
                  }
              }

              // Determine if we should also delete the target node itself if it was a heading
              let endDeletePos = pos;
              if (targetNode && targetNode.type.name === 'heading') {
                  endDeletePos = pos + targetNode.nodeSize;
              }

              // Run the editor chain to precisely mutate the document state
              editor.chain()
                .deleteRange({ from: startDeletePos, to: endDeletePos })
                .insertContentAt(startDeletePos, `<h1 style="page-break-before: always;">${acceptedChapter.title}</h1>`)
                .run();
                
              found = true;
              
              // Scroll the user to the newly created chapter heading
              const el = domNodes[i] as HTMLElement;
              el.scrollIntoView({ behavior: 'smooth', block: 'center' });
              
              // Briefly highlight the line for UX indicating it was modified
              el.style.transition = 'background-color 0.5s ease';
              el.style.backgroundColor = 'rgba(16, 185, 129, 0.2)'; // Emerald green flash for "accepted"
              setTimeout(() => { el.style.backgroundColor = 'transparent'; }, 2000);
              break;
          }
        }
        
        if (!found) {
          // Silent Injection Bypass
          alert("Couldn't automatically place the chapter break because the text has been heavily edited or the AI truncated it. You can place it manually.");
        }
      }, 50);
    }
  }, [acceptedChapter, editor]);

// Handle interacting with Content Advisories to permanently burn them into the manuscript
  useEffect(() => {
    if (editor && acceptedWarning) {
      setTimeout(() => {
        const view = editor.view;
        const tokenize = (s: string) => (s || "").toLowerCase().replace(/[^a-z0-9 ]/g, "").split(/\s+/).filter(w => w.length > 2);
        const normalizeForMatch = (s: string) => (s || "").toLowerCase().replace(/[^a-z0-9]/g, "");
        const targetTokens = tokenize(acceptedWarning.startingWords);
        
        let bestMatchPos = -1;
        let highestScore = 0;
        let found = false;

        // --- NEW: Iron-Lock Chapter Boundary Identification ---
        // Removed inaccurate chapter-boundary logic that was causing regressions
        let searchRangeStart = 0;
        let searchRangeEnd = editor.state.doc.content.size;
        
        if (targetTokens.length > 0) {
          // Phase 3: Iron-Lock Scoring within Forward-Only boundaries
          let bestMatchContent = "";
          editor.state.doc.descendants((node, pos) => {
            if (node.isText) return false;
            
            // Strictly enforce the chapter range (Starting AFTER the header)
            if (pos < searchRangeStart || pos >= searchRangeEnd) return true;
            
            const nodeTokens = tokenize(node.textContent || "");
            // Requirement: Ignore short fragments/headings less than 15 words
            if (nodeTokens.length < 15) return true;
            
            let matchCount = 0;
            const nodeTokenSet = new Set(nodeTokens);
            targetTokens.forEach(t => { if (nodeTokenSet.has(t)) matchCount++; });
            
            const score = matchCount / targetTokens.length;
            
            // 0.0001 floor ensures 0% matches are never picked as 'bestMatchPos'
            if (score > highestScore && score > 0.0001) {
              highestScore = score;
              bestMatchPos = pos;
              bestMatchContent = node.textContent || "";
            }
            return true;
          });
        }
        
        // Threshold check: 30% word-match is safe IF we have already Iron-Locked the chapter
        if (highestScore >= 0.3 && bestMatchPos !== -1) {
              const advisoryHTML = `<p class="content-advisory" style="color: #ef4444; font-weight: bold; padding: 4px 0; border-top: 1px solid rgba(239, 68, 68, 0.1); border-bottom: 1px solid rgba(239, 68, 68, 0.1); margin-bottom: 0.5em; page-break-after: avoid;">[CONTENT ADVISORY: ${acceptedWarning.warning}]</p>`;
              
              editor.chain()
                .focus()
                .insertContentAt(bestMatchPos, advisoryHTML)
                .run();
              
              const coord = view.coordsAtPos(bestMatchPos);
              if (coord) {
                 window.scrollTo({ top: coord.top + window.pageYOffset - (window.innerHeight / 2), behavior: 'smooth' });
              }

              onWarningPlaced?.(acceptedWarning.warning);
              found = true;
        }
        
        if (!found) {
            alert(`Couldn't automatically place [${acceptedWarning.warning}].\n\nSimilarity Score: ${Math.round(highestScore * 100)}% (30% Required).`);
        }
      }, 50);
    }
  }, [acceptedWarning, editor]);

  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  const handleSearch = () => {
      if (!editorContainerRef.current || !editor || !searchQuery) return;
      
      const searchStr = searchQuery.toLowerCase();
      const nodes = Array.from(editorContainerRef.current.querySelectorAll('p, h1, h2, h3, h4, blockquote, li'));
      
      const occurrences: {node: HTMLElement, pos: number}[] = [];
      nodes.forEach(node => {
          const text = (node.textContent || "").toLowerCase();
          if (text.includes(searchStr)) {
              try {
                  const pos = editor.view.posAtDOM(node, 0);
                  if (!isNaN(pos)) {
                      occurrences.push({ node: node as HTMLElement, pos });
                  }
              } catch (e) {}
          }
      });
      
      setSearchOccurrences(occurrences);
      
      if (occurrences.length > 0) {
          setCurrentSearchIndex(0);
          scrollToSearchOccurrence(occurrences[0], true, true); // skipFocus = true
      } else {
          setCurrentSearchIndex(-1);
      }
  };

  useEffect(() => {
      if (isFindReplaceOpen && searchQuery.length > 1) {
          const timer = setTimeout(() => {
              handleSearch();
          }, 400); // 400ms debounce
          return () => clearTimeout(timer);
      } else if (searchQuery.length <= 1) {
          setSearchOccurrences([]);
          setCurrentSearchIndex(-1);
      }
  }, [searchQuery, isFindReplaceOpen]);

  const scrollToSearchOccurrence = (occurrence: {node: HTMLElement, pos: number}, smooth: boolean = false, skipFocus: boolean = false) => {
      if (!occurrence || !occurrence.node) return;
      
      if (smooth) {
          occurrence.node.scrollIntoView({ behavior: 'smooth', block: 'center' });
      } else {
          occurrence.node.scrollIntoView({ block: 'center' });
      }
      
      // Flash highlight
      occurrence.node.style.transition = 'background-color 0.3s ease';
      occurrence.node.style.backgroundColor = 'rgba(99, 102, 241, 0.3)';
      setTimeout(() => {
          if (occurrence.node) occurrence.node.style.backgroundColor = 'transparent';
      }, 1500);
      
      // Move cursor only if not skipped (prevents focus stealing while typing)
      if (!skipFocus) {
          try {
              editor?.chain().focus().setTextSelection(occurrence.pos).run();
          } catch (e) {}
      }
  };

  const nextSearch = () => {
      if (searchOccurrences.length === 0) return;
      const nextIdx = (currentSearchIndex + 1) % searchOccurrences.length;
      setCurrentSearchIndex(nextIdx);
      scrollToSearchOccurrence(searchOccurrences[nextIdx]);
  };

  const prevSearch = () => {
      if (searchOccurrences.length === 0) return;
      const prevIdx = currentSearchIndex - 1 < 0 ? searchOccurrences.length - 1 : currentSearchIndex - 1;
      setCurrentSearchIndex(prevIdx);
      scrollToSearchOccurrence(searchOccurrences[prevIdx]);
  };

  const executeReplace = () => {
      if (!editor || !searchQuery || currentSearchIndex < 0 || currentSearchIndex >= searchOccurrences.length) return;
      
      const occurrence = searchOccurrences[currentSearchIndex];
      const { state } = editor;
      let found = false;
      
      // Only search within the specific node we are focused on to prevent replacing wrong instance
      state.doc.nodesBetween(occurrence.pos, occurrence.pos + occurrence.node.innerText.length + 100, (node, pos) => {
          if (found) return false;
          if (node.isText && node.text?.toLowerCase().includes(searchQuery.toLowerCase())) {
              // Find case-insensitive match
              const textLower = node.text.toLowerCase();
              const searchLower = searchQuery.toLowerCase();
              const index = textLower.indexOf(searchLower);
              
              editor.chain()
                .focus()
                .deleteRange({ from: pos + index, to: pos + index + searchQuery.length })
                .insertContentAt(pos + index, replaceQuery)
                .run();
              found = true;
              return false;
          }
      });
      
      if (found) {
          // Re-run search to update bounds
          setTimeout(handleSearch, 100);
      }
  };

  const executeReplaceAll = () => {
      if (!editor || !searchQuery) return;
      const { state } = editor;
      
      let positionsToReplace: {from: number, to: number}[] = [];
      const searchLower = searchQuery.toLowerCase();
      
      state.doc.descendants((node, pos) => {
          if (node.isText && node.text) {
              let textLower = node.text.toLowerCase();
              let startIndex = 0;
              let index;
              
              while ((index = textLower.indexOf(searchLower, startIndex)) > -1) {
                  positionsToReplace.push({
                      from: pos + index,
                      to: pos + index + searchQuery.length
                  });
                  startIndex = index + searchLower.length;
              }
          }
      });
      
      if (positionsToReplace.length === 0) return;
      
      // Execute in reverse to preserve positions
      const chain = editor.chain().focus();
      positionsToReplace.reverse().forEach(pos => {
          chain.deleteRange({ from: pos.from, to: pos.to }).insertContentAt(pos.from, replaceQuery);
      });
      chain.run();
      
      setTimeout(handleSearch, 100);
  };

  if (!editor || !mounted) {
    return (
      <div className="flex-1 w-full bg-surface-hover/50 animate-pulse rounded-lg border border-border m-4" />
    );
  }

  const handleOpenBulkDict = () => {
    // Quickly snapshot all currently flagged elements in the DOM
    const errorNodes = document.querySelectorAll('.misspelled-word');
    const wordsRaw = Array.from(errorNodes).map(node => 
      node.getAttribute('data-word') || (node as HTMLElement).innerText || ''
    );
    
    // Clean punctuation
    const cleaned = wordsRaw
      .map(w => w.trim().replace(/^[.,!?;:'"“”‘’]+|[.,!?;:'"“”‘’]+$/g, ''))
      .filter(w => w.length > 0);
      
    // Deduplicate case-insensitively, but fiercely preserve Title Case if encountered
    const uniqueMap = new Map<string, string>();
    cleaned.forEach(word => {
      const lower = word.toLowerCase();
      // If we haven't seen it, or if it has capital letters while the stored one doesn't
      if (!uniqueMap.has(lower) || (word !== lower && uniqueMap.get(lower) === lower)) {
        uniqueMap.set(lower, word);
      }
    });

    const uniqueWords = Array.from(uniqueMap.values()).sort((a, b) => a.toLowerCase().localeCompare(b.toLowerCase()));
    
    setBulkMisspellings(uniqueWords);
    setIsBulkDictOpen(true);
  };



  return (
    <div className="flex flex-col flex-1 min-h-0 w-full relative min-w-0">
      <div className={`sticky top-0 z-10 flex gap-2 p-2 bg-background/90 backdrop-blur-sm border-b border-border transition-opacity duration-300 ${(isFocusMode && !isToolbarPinned) ? 'opacity-0 hover:opacity-100' : 'opacity-100'}`}>
        <button
          onClick={() => editor.chain().focus().undo().run()}
          disabled={!editor.can().undo()}
          className={`p-1.5 rounded-md transition-colors text-muted hover:text-foreground hover:bg-surface-hover disabled:opacity-30`}
          title="Undo"
        >
          <Undo className="w-4 h-4" />
        </button>
        <button
          onClick={() => editor.chain().focus().redo().run()}
          disabled={!editor.can().redo()}
          className={`p-1.5 rounded-md transition-colors text-muted hover:text-foreground hover:bg-surface-hover disabled:opacity-30`}
          title="Redo"
        >
          <Redo className="w-4 h-4" />
        </button>
        
                <div className="w-px h-5 bg-border self-center mx-1"></div>
        
        <div className="relative">
          <button
            onClick={() => setIsLangMenuOpen(!isLangMenuOpen)}
            className={`p-1.5 rounded-md transition-colors flex items-center gap-1 ${isLangMenuOpen ? 'bg-accent/20 text-accent' : 'text-muted hover:text-foreground hover:bg-surface-hover'}`}
            title="Linguistic Regional Switch"
          >
            <Globe className="w-4 h-4" />
            <span className="text-[9px] font-black uppercase tracking-tighter">
              {language.split('-')[1]}
            </span>
          </button>
          
          {isLangMenuOpen && (
            <div className="absolute top-full left-0 mt-1 bg-background border border-border rounded-lg shadow-xl py-1 min-w-[120px] z-50 animate-in fade-in zoom-in-95 duration-200">
              {[
                { id: 'en-US', label: 'American' },
                { id: 'en-GB', label: 'British' },
                { id: 'en-CA', label: 'Canada' }
              ].map(lang => (
                <button
                  key={lang.id}
                  onClick={() => {
                    (editor.commands as Record<string, Function>).setLanguage(lang.id);
                    setLanguage(lang.id as 'en-US' | 'en-GB' | 'en-CA');
                    setIsLangMenuOpen(false);
                  }}
                  className={`w-full flex items-center justify-between px-3 py-1.5 text-[10px] font-black uppercase tracking-widest hover:bg-surface-hover transition-colors ${language === lang.id ? 'text-accent' : 'text-muted'}`}
                >
                  {lang.label}
                  {language === lang.id && <Check className="w-3 h-3" />}
                </button>
              ))}
            </div>
          )}
        </div>

        <button
          onClick={() => editor.chain().focus().toggleBold().run()}
          className={`p-1.5 rounded-md transition-colors ${editor.isActive('bold') ? 'bg-accent/20 text-accent' : 'text-muted hover:text-foreground hover:bg-surface-hover'}`}
          title="Bold"
        >
          <Bold className="w-4 h-4" />
        </button>
        <button
          onClick={() => editor.chain().focus().toggleItalic().run()}
          className={`p-1.5 rounded-md transition-colors ${editor.isActive('italic') ? 'bg-accent/20 text-accent' : 'text-muted hover:text-foreground hover:bg-surface-hover'}`}
          title="Italic"
        >
          <Italic className="w-4 h-4" />
        </button>
        <button
          onClick={() => editor.chain().focus().toggleStrike().run()}
          className={`p-1.5 rounded-md transition-colors ${editor.isActive('strike') ? 'bg-accent/20 text-accent' : 'text-muted hover:text-foreground hover:bg-surface-hover'}`}
          title="Strikethrough"
        >
          <StrikeIcon className="w-4 h-4" />
        </button>
        
        <div className="w-px h-5 bg-border self-center mx-1"></div>
        
        <button
          onClick={() => editor.chain().focus().setNode('heading', { level: 1 }).run()}
          className={`p-1.5 rounded-md transition-colors ${editor.isActive('heading', { level: 1 }) ? 'bg-accent/20 text-accent' : 'text-muted hover:text-foreground hover:bg-surface-hover'}`}
          title="Heading 1"
        >
          <Heading1 className="w-4 h-4" />
        </button>
        <button
          onClick={() => editor.chain().focus().setNode('heading', { level: 2 }).run()}
          className={`p-1.5 rounded-md transition-colors ${editor.isActive('heading', { level: 2 }) ? 'bg-accent/20 text-accent' : 'text-muted hover:text-foreground hover:bg-surface-hover'}`}
          title="Heading 2"
        >
          <Heading2 className="w-4 h-4" />
        </button>
        <button
          onClick={() => editor.chain().focus().setParagraph().run()}
          className={`p-1.5 rounded-md transition-colors ${editor.isActive('paragraph') ? 'bg-accent/20 text-accent' : 'text-muted hover:text-foreground hover:bg-surface-hover'}`}
          title="Body Text"
        >
          <Pilcrow className="w-4 h-4" />
        </button>
        
        <div className="w-px h-5 bg-border self-center mx-1"></div>
        
        <button
          onClick={() => editor.chain().focus().toggleBulletList().run()}
          className={`p-1.5 rounded-md transition-colors ${editor.isActive('bulletList') ? 'bg-accent/20 text-accent' : 'text-muted hover:text-foreground hover:bg-surface-hover'}`}
          title="Bullet List"
        >
          <List className="w-4 h-4" />
        </button>
        <button
          onClick={() => editor.chain().focus().toggleOrderedList().run()}
          className={`p-1.5 rounded-md transition-colors ${editor.isActive('orderedList') ? 'bg-accent/20 text-accent' : 'text-muted hover:text-foreground hover:bg-surface-hover'}`}
          title="Numbered List"
        >
          <ListOrdered className="w-4 h-4" />
        </button>
        <button
          onClick={() => editor.chain().focus().toggleBlockquote().run()}
          className={`p-1.5 rounded-md transition-colors ${editor.isActive('blockquote') ? 'bg-indigo-500/20 text-indigo-400' : 'text-zinc-500 hover:text-zinc-300 hover:bg-[#222]'}`}
          title="Quote Block"
        >
          <Quote className="w-4 h-4" />
        </button>
        
        <div className="w-px h-5 bg-border self-center mx-1"></div>
        
        <button
          onClick={() => {
              if (!chapters || chapters.length === 0) {
                  alert("No chapters found. Please run an analysis or sync your headings first!");
                  return;
              }
              const tocHTML = `<div class="editor-toc" style="padding-bottom: 20px;"><h1>Table of Contents</h1>` + chapters.map(c => {
                  const cleanTitle = (c.suggested_title || "").replace(/^Chapter\s*\d+\s*[:\-]?\s*/i, '').trim();
                  return `<p><strong>${cleanTitle}</strong> <span style="float: right">${c.display_page || c.page_number}</span></p>`;
              }).join('') + `<p style="page-break-before: always;"></p></div>`;
              
              const view = editor.view;
              let injectionPos = -1;
              const headings = view.dom.querySelectorAll('h1, h2, h3');
              for (let i = 0; i < headings.length; i++) {
                  const text = (headings[i].textContent || "").toLowerCase();
                  if (text.includes('table of contents') || text.includes('title page') || text.includes('forward') || text.includes('foreword') || text.includes('prologue') || text.includes('prelude')) {
                      continue;
                  }
                  
                  if (i <= 1 && !text.includes('chapter') && !text.includes('part 1') && !text.includes('1')) {
                      continue; // Implicit Book Title Catch
                  }
                  
                  injectionPos = view.posAtDOM(headings[i], 0);
                  break;
              }
              
              if (injectionPos !== -1) {
                  editor.chain().focus().insertContentAt(injectionPos, tocHTML).run();
              } else {
                  editor.chain().focus().insertContent(tocHTML).run();
              }
          }}
          className={`p-1.5 rounded-md transition-colors text-emerald-500 hover:text-emerald-400 hover:bg-[#222]`}
          title="Inject Table of Contents via AI State"
        >
          <ReplaceAll className="w-4 h-4" />
        </button>

        <div className="w-px h-5 bg-[#333] self-center mx-1"></div>
        
        <button
            onClick={() => {
              const { view, state } = editor;
              const { tr } = state;
              const positionsToChange: number[] = [];
              
              state.doc.descendants((node, pos) => {
                 if (node.isBlock && (node.type.name === 'paragraph' || node.type.name === 'heading')) {
                     const text = node.textContent.trim();
                     
                     // Skip if empty or already H1
                     if (!text || (node.type.name === 'heading' && node.attrs.level === 1)) {
                         return false; // skip children
                     }
                     
                     // Convert ANY line under 60 characters to a heading.
                     if (text.length < 60) {
                         positionsToChange.push(pos);
                     }
                     return false; // skip children
                 }
              });
              
              if (positionsToChange.length > 0) {
                  // Applying backwards guarantees positions won't shift during changes
                  for (let i = positionsToChange.length - 1; i >= 0; i--) {
                      tr.setNodeMarkup(positionsToChange[i], state.schema.nodes.heading, { level: 1 });
                  }
                  view.dispatch(tr);
                  setTimeout(() => alert(`Successfully converted ${positionsToChange.length} short lines to Heading 1.`), 50);
              } else {
                  alert("No short lines found to convert.");
              }
            }}
            className="p-1.5 rounded-md transition-colors text-fuchsia-500 hover:text-fuchsia-400 hover:bg-[#222]"
            title="Auto-Format Chapter Headings (Magic Wand)"
        >
            <Wand2 className="w-4 h-4" />
        </button>

        <button
          onClick={() => (editor.commands as Record<string, Function>).sanitizeTypography()}
          className="p-1.5 rounded-md transition-colors text-sky-400 hover:text-sky-300 hover:bg-[#222]"
          title="Sanitize Typography (Straight Quotes)"
        >
          <Type className="w-4 h-4" />
        </button>

        <button
          onClick={() => {
            const { state, view } = editor;
            const tr = state.tr;
            let positionsToRemove: { from: number; to: number }[] = [];
            
            state.doc.descendants((node, pos) => {
                if (node.isBlock && node.textContent.trim().match(/^\d+$/)) {
                    positionsToRemove.push({ from: pos, to: pos + node.nodeSize });
                }
            });
            
            if (positionsToRemove.length > 0) {
                for (let i = positionsToRemove.length - 1; i >= 0; i--) {
                    tr.delete(positionsToRemove[i].from, positionsToRemove[i].to);
                }
                view.dispatch(tr);
                alert(`Purged ${positionsToRemove.length} orphaned page numbers from the manuscript.`);
            } else {
                alert("No orphaned page numbers found.");
            }
          }}
          className="p-1.5 rounded-md transition-colors text-rose-500 hover:text-rose-400 hover:bg-[#222]"
          title="Purge Orphaned Page Numbers (De-Paginate)"
        >
          <Eraser className="w-4 h-4" />
        </button>

        <div className="flex items-center bg-[#222] rounded-md px-1 ml-1 border border-[#333]">
          <button
            onClick={() => {
              (editor.commands as Record<string, Function>).setLanguage('en-US');
              setLanguage('en-US');
            }}
            className={`px-2 py-1 text-[9px] font-bold rounded transition-all ${language === 'en-US' ? 'bg-indigo-600 text-white shadow-lg' : 'text-zinc-500 hover:text-zinc-300'}`}
            title="Switch to American English Spellcheck"
          >
            🇺🇸 US
          </button>
          <button
            onClick={() => {
              (editor.commands as Record<string, Function>).setLanguage('en-GB');
              setLanguage('en-GB');
            }}
            className={`px-2 py-1 text-[9px] font-bold rounded transition-all ${language === 'en-GB' ? 'bg-indigo-600 text-white shadow-lg' : 'text-zinc-500 hover:text-zinc-300'}`}
            title="Switch to British English Spellcheck"
          >
            🇬🇧 UK
          </button>
          <button
            onClick={() => {
              (editor.commands as Record<string, Function>).setLanguage('en-CA');
              setLanguage('en-CA');
            }}
            className={`px-2 py-1 text-[9px] font-bold rounded transition-all ${language === 'en-CA' ? 'bg-indigo-600 text-white shadow-lg' : 'text-zinc-500 hover:text-zinc-300'}`}
            title="Switch to Canadian English Spellcheck"
          >
            🇨🇦 CAN
          </button>
        </div>

        <div className="w-px h-5 bg-[#333] self-center mx-1"></div>

        <button
            onClick={onGrammarCheck}
            className="p-1.5 rounded-md transition-colors text-indigo-400 hover:text-indigo-300 hover:bg-[#222]"
            title="Run AI Grammar Check (Cloud)"
        >
            <Pen className="w-4 h-4" />
        </button>
        <button
            onClick={handleOpenBulkDict}
            className="p-1.5 rounded-md transition-colors text-indigo-400 hover:text-indigo-300 hover:bg-[#222]"
            title="Bulk Add to Dictionary"
        >
            <BookCheck className="w-4 h-4" />
        </button>
        <button
            onClick={handleJumpToNextError}
            className="p-1.5 rounded-md transition-colors text-rose-500 hover:text-rose-400 hover:bg-[#222]"
            title="Jump to Next Misspelled Word"
        >
            <FastForward className="w-4 h-4" />
        </button>

        <div className="w-px h-5 bg-[#333] self-center mx-1"></div>

        <button
            onClick={() => setIsFindReplaceOpen(!isFindReplaceOpen)}
            className={`p-1.5 rounded-md transition-colors ${isFindReplaceOpen ? 'bg-indigo-500/20 text-indigo-400 border border-indigo-500/30' : 'text-zinc-400 hover:text-zinc-200 hover:bg-[#222]'}`}
            title="Find and Replace"
        >
            <Search className="w-4 h-4" />
        </button>

        <div className="ml-auto flex items-center pl-4 pr-1 gap-2">
            <button
               onClick={() => setIsToolbarPinned(!isToolbarPinned)}
               className={`p-1.5 rounded-md transition-all ${isToolbarPinned ? 'bg-indigo-500/20 text-indigo-400 border border-indigo-500/30' : 'text-zinc-600 hover:text-zinc-400 hover:bg-[#222]'}`}
               title={isToolbarPinned ? "Unpin Ribbon (Enable Autohide)" : "Pin Ribbon (Disable Autohide)"}
            >
               {isToolbarPinned ? <Pin className="w-3.5 h-3.5 rotate-45" /> : <PinOff className="w-3.5 h-3.5" />}
            </button>
            <div className="text-[11px] text-zinc-500 bg-[#18181b] flex items-center gap-1.5 px-2.5 py-1.5 rounded-md cursor-help border border-[#2a2a2a] hover:bg-[#222] transition-colors" title="tome_master structures text dynamically. The final standard export will render strictly at 12pt Times New Roman per Publishing House guidelines.">
               <Lock className="w-3 h-3 text-emerald-600/70" />
               <span className="hidden sm:inline font-medium uppercase tracking-wider text-[9px] text-zinc-600 mr-1">Export</span> <span className="text-zinc-400">Times New Roman, 12pt</span>
            </div>
        </div>
      </div>
      
      {isFindReplaceOpen && (
        <div className="flex flex-col gap-2 p-3 bg-surface border-b border-border shadow-md z-10 animate-in fade-in slide-in-from-top-2 duration-200">
            <div className="flex items-center gap-2">
                <Search className="w-4 h-4 text-muted" />
                <input 
                    type="text" 
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder="Find in document..."
                    className="flex-1 bg-background border border-border rounded px-3 py-1.5 text-xs text-foreground focus:outline-none focus:border-accent"
                />
                <span className="text-[10px] text-muted font-mono w-16 text-center">
                    {searchOccurrences.length > 0 ? `${currentSearchIndex + 1} / ${searchOccurrences.length}` : '0 / 0'}
                </span>
                <button onClick={prevSearch} disabled={searchOccurrences.length === 0} className="p-1.5 rounded bg-surface-hover text-muted hover:text-foreground disabled:opacity-30"><ArrowUp className="w-3.5 h-3.5" /></button>
                <button onClick={nextSearch} disabled={searchOccurrences.length === 0} className="p-1.5 rounded bg-surface-hover text-muted hover:text-foreground disabled:opacity-30"><ArrowDown className="w-3.5 h-3.5" /></button>
                <button onClick={() => setIsFindReplaceOpen(false)} className="p-1.5 rounded hover:bg-rose-500/10 text-muted hover:text-rose-400 ml-2"><X className="w-4 h-4" /></button>
            </div>
            <div className="flex items-center gap-2">
                <ReplaceAll className="w-4 h-4 text-muted" />
                <input 
                    type="text" 
                    value={replaceQuery}
                    onChange={(e) => setReplaceQuery(e.target.value)}
                    placeholder="Replace with..."
                    className="flex-1 bg-background border border-border rounded px-3 py-1.5 text-xs text-foreground focus:outline-none focus:border-accent"
                />
                <button 
                    onClick={executeReplace} 
                    disabled={searchOccurrences.length === 0}
                    className="px-3 py-1.5 rounded bg-surface-hover border border-border text-[10px] font-bold uppercase tracking-wider text-muted hover:text-foreground disabled:opacity-30"
                >
                    Replace
                </button>
                <button 
                    onClick={executeReplaceAll}
                    disabled={searchOccurrences.length === 0}
                    className="px-3 py-1.5 rounded bg-indigo-500/10 border border-indigo-500/20 text-[10px] font-bold uppercase tracking-wider text-indigo-400 hover:text-indigo-300 hover:bg-indigo-500/20 disabled:opacity-30"
                >
                    Replace All
                </button>
            </div>
        </div>
      )}

      <div 
        className="flex-1 overflow-y-auto overflow-x-hidden relative bright-scrollbar editor-scroll-container min-w-0 w-full"
        ref={editorContainerRef}
        onScroll={() => { setSpellBubble(null); setGrammarBubble(null); }}
        onMouseMove={(e) => {
          if (!editor) return;
          
          const target = e.target as HTMLElement;
          const misspelledSpan = target.closest('.misspelled-word') as HTMLElement;
          const grammarSpan = target.closest('.grammar-squiggle') as HTMLElement;

          if (misspelledSpan) {
            // [SOVEREIGN PERFORMANCE]: Neutralize "MouseMove Jitter" re-renders
            if (hoverTimeoutRef.current) clearTimeout(hoverTimeoutRef.current);
            
            const word = misspelledSpan.getAttribute('data-word') || misspelledSpan.innerText;
            
            // Re-probe on move ensures coordinate fidelity if scrolling
            const updateBubble = () => {
                if (!editor || editor.isDestroyed) return;
                let pos: number;
                try {
                  pos = editor.view.posAtDOM(misspelledSpan, 0);
                  if (isNaN(pos) || pos < 0) throw new Error('Invalid position');
                } catch (err) { return; }

                if (!spellBubble || spellBubble.word !== word) {
                  const storage = (editor.storage as unknown as Record<string, unknown>).spellcheck as { customWords: Set<string>, ignoredWords: Set<string>, getSuggestions?: (word: string) => string[] };
                  const suggestions = storage?.getSuggestions ? storage.getSuggestions(word) : [];
                  
                  const rect = misspelledSpan.getBoundingClientRect();
                  const centerX = rect.left + rect.width / 2;
                  const centerY = rect.top;
                  const bottomY = rect.bottom;

                  const bubbleWidth = 192;
                  const screenWidth = window.innerWidth;
                  let x = Math.max(bubbleWidth / 2 + 10, Math.min(screenWidth - (bubbleWidth / 2 - 10), centerX));
                  let y = centerY - 5;
                  let flip = false;
                  if (y < 150) { 
                    y = bottomY + 5;
                    flip = true;
                  }

                  setSpellBubble({ word, pos, suggestions, visible: true, x, y, flip, el: misspelledSpan } as unknown as typeof spellBubble);
                }
            };

            // Use a small 40ms pulse to ensure the UI feels responsive but not "clunky"
            hoverTimeoutRef.current = setTimeout(updateBubble, 40);
          } else if (grammarSpan) {
            if (hoverTimeoutRef.current) clearTimeout(hoverTimeoutRef.current);
            const id = grammarSpan.getAttribute('data-id') || '';
            const original = grammarSpan.getAttribute('data-original') || '';
            const suggestion = grammarSpan.getAttribute('data-suggestion') || '';
            const reason = grammarSpan.getAttribute('data-reason') || '';
            
            const updateGrammar = () => {
                if (!editor || editor.isDestroyed) return;
                let pos: number;
                try {
                  pos = editor.view.posAtDOM(grammarSpan, 0);
                  if (isNaN(pos)) throw new Error('Invalid position');
                } catch (err) { return; }

                if (!grammarBubble || grammarBubble.id !== id) {
                  const rect = grammarSpan.getBoundingClientRect();
                  const centerX = rect.left + rect.width / 2;
                  const centerY = rect.top;
                  const bottomY = rect.bottom;

                  const bubbleWidth = 256;
                  const screenWidth = window.innerWidth;
                  let x = Math.max(bubbleWidth / 2 + 10, Math.min(screenWidth - (bubbleWidth / 2 - 10), centerX));
                  let y = centerY - 5;
                  let flip = false;
                  if (y < 200) { 
                    y = bottomY + 5;
                    flip = true;
                  }
                  setGrammarBubble({ id, original, suggestion, reason, pos, visible: true, x, y, flip });
                }
            };
            hoverTimeoutRef.current = setTimeout(updateGrammar, 40);
          } else {
            // Hide bubble with a small delay to allow moving onto it
            if (spellBubble && !target.closest('.spell-bubble')) {
              if (document.activeElement?.id === 'spell-custom-input') return;
              if (hoverTimeoutRef.current) clearTimeout(hoverTimeoutRef.current);
              hoverTimeoutRef.current = setTimeout(() => {
                if (document.activeElement?.id === 'spell-custom-input') return;
                setSpellBubble(null);
              }, 300);
            }
            if (grammarBubble && !target.closest('.grammar-bubble')) {
              if (hoverTimeoutRef.current) clearTimeout(hoverTimeoutRef.current);
              hoverTimeoutRef.current = setTimeout(() => {
                setGrammarBubble(null);
              }, 300);
            }
          }
        }}
        onMouseDown={(e) => {
          // [SOVEREIGN SELECTION RESTORATION]: 
          // If the user clicks a misspelling, we FORCE the selection to land there instantly.
          // This overrides the "2-click" browser lag caused by decorations.
          const target = e.target as HTMLElement;
          const misspelledSpan = target.closest('.misspelled-word') as HTMLElement;
          if (misspelledSpan && editor) {
             try {
                const pos = editor.view.posAtDOM(misspelledSpan, 0);
                if (!isNaN(pos) && pos >= 0) {
                    // We run the command via a microtask to ensure it happens AFTER the current event cycle
                    // but BEFORE the browser decides where to put the cursor on its own.
                    setTimeout(() => {
                        editor.chain().focus().setTextSelection(pos).run();
                    }, 0);
                }
             } catch (err) {}
          }
        }}
      >
        <EditorContent editor={editor} className="h-full w-full min-w-0" />
        
        {/* Spell Check Hover Bubble (Sovereign Portal) */}
        {spellBubble && spellBubble.visible && typeof document !== 'undefined' && createPortal(
          <div 
            className="fixed z-[9999] spell-bubble bg-[#1a1a1a] border border-[#333] rounded-xl shadow-2xl p-2 flex flex-col gap-1 w-48 transition-all animate-in fade-in zoom-in duration-150"
            style={{ 
              left: `${spellBubble.x}px`, 
              top: `${spellBubble.y}px`,
              transform: (spellBubble as { flip?: boolean }).flip ? 'translate(-50%, 0)' : 'translate(-50%, -100%)'
            }}
            onMouseDown={(e) => {
              // Vital prevention: do not let the editor lose focus or it will fire a stale transaction
              if ((e.target as HTMLElement).tagName !== 'INPUT') {
                 e.preventDefault();
              }
            }}
            onMouseEnter={() => {
              if (hoverTimeoutRef.current) clearTimeout(hoverTimeoutRef.current);
            }}
            onMouseLeave={() => {
              if (document.activeElement?.id === 'spell-custom-input') return;
              setSpellBubble(null);
            }}
          >
            <div className="px-2 py-1 border-b border-border mb-1">
              <span className="text-[10px] font-bold text-muted uppercase tracking-widest">Suggestions</span>
            </div>
            
            <div className="max-h-32 overflow-y-auto pr-1 custom-scrollbar">
              {spellBubble.suggestions.length > 0 ? (
                spellBubble.suggestions.slice(0, 5).map((s, i) => (
                  <div key={i} className="group/item flex items-center justify-between rounded-md hover:bg-indigo-500/20 transition-colors">
                    <button
                      onClick={() => {
                        // RE-PROBE: Ensure we use the latest coordinate if the document shifted
                        const livePos = editor?.view.posAtDOM(spellBubble.el, 0) ?? spellBubble.pos;
                        editor?.chain()
                          .insertContentAt({ from: livePos, to: livePos + spellBubble.word.length }, s)
                          .focus()
                          .run();
                        setSpellBubble(null);
                        handleJumpToNextError();
                      }}
                      className="flex-1 text-left px-2 py-1.5 text-sm text-foreground group-hover/item:text-accent font-medium transition-colors"
                      title={`Replace with ${s}`}
                    >
                      {s}
                    </button>
                    <button
                      onClick={(e) => {
                        e.preventDefault(); e.stopPropagation();
                        editor?.chain().replaceAll(spellBubble.word, s).focus().run();
                        setSpellBubble(null);
                        handleJumpToNextError();
                      }}
                      className="px-2 py-1.5 text-[10px] text-zinc-500 hover:text-indigo-300 hover:bg-indigo-500/30 font-bold uppercase tracking-wider rounded-r-md opacity-0 group-hover/item:opacity-100 transition-all"
                      title={`Replace ALL instances with ${s}`}
                    >
                      ALL
                    </button>
                  </div>
                ))
              ) : (
                <div className="px-2 py-2 text-xs text-muted italic">No suggestions</div>
              )}
            </div>

            <div className="px-2 py-1.5 border-t border-border">
              <input 
                id="spell-custom-input"
                type="text" 
                placeholder="Type custom word (Enter to Replace)"
                autoComplete="off"
                className="w-full bg-background border border-border rounded px-2 py-1 text-[11px] text-foreground outline-none focus:border-accent transition-colors"
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    e.preventDefault();
                    const customWord = e.currentTarget.value.trim();
                    if (customWord) {
                      const livePos = editor?.view.posAtDOM(spellBubble.el, 0) ?? spellBubble.pos;
                      editor?.chain()
                        .insertContentAt({ from: livePos, to: livePos + spellBubble.word.length }, customWord)
                        .focus()
                        .run();
                      setSpellBubble(null);
                      handleJumpToNextError();
                    }
                  }
                }}
              />
            </div>

            <div className="border-t border-border mt-1 pt-1 flex flex-col gap-0.5">
              <div className="flex gap-1 w-full pb-0.5">
                <button 
                  onClick={(e) => {
                    e.preventDefault(); e.stopPropagation();
                    const inputEl = document.getElementById('spell-custom-input') as HTMLInputElement;
                    const customWord = inputEl?.value.trim() || spellBubble.suggestions[0];
                    if (customWord) {
                      const livePos = editor?.view.posAtDOM(spellBubble.el, 0) ?? spellBubble.pos;
                      editor?.chain()
                        .insertContentAt({ from: livePos, to: livePos + spellBubble.word.length }, customWord)
                        .focus()
                        .run();
                      setSpellBubble(null);
                      handleJumpToNextError();
                    }
                  }}
                  className="flex-1 text-center justify-center px-1 py-1.5 rounded-md text-[11px] text-zinc-400 hover:bg-indigo-500/10 hover:text-indigo-400 transition-colors flex items-center gap-1.5 font-medium"
                >
                  <Check className="w-3.5 h-3.5" /> Replace
                </button>
                <button 
                  onClick={(e) => {
                    e.preventDefault(); e.stopPropagation();
                    const inputEl = document.getElementById('spell-custom-input') as HTMLInputElement;
                    const customWord = inputEl?.value.trim() || spellBubble.suggestions[0];
                    if (customWord) {
                      editor?.chain().replaceAll(spellBubble.word, customWord).focus().run();
                      setSpellBubble(null);
                      handleJumpToNextError();
                    }
                  }}
                  className="flex-1 text-center justify-center px-1 py-1.5 rounded-md text-[11px] text-zinc-400 hover:bg-indigo-500/10 hover:text-indigo-400 transition-colors flex items-center gap-1.5 font-bold title-replace-all"
                >
                  <ReplaceAll className="w-3.5 h-3.5" /> ALL
                </button>
              </div>

              <button 
                onClick={(e) => {
                  e.preventDefault(); e.stopPropagation();
                  editor?.commands.addWord(spellBubble.word);
                  setSpellBubble(null);
                  handleJumpToNextError();
                }}
                className="w-full text-left px-2 py-1.5 rounded-md text-[11px] text-zinc-400 hover:bg-emerald-500/10 hover:text-emerald-400 transition-colors flex items-center gap-2"
              >
                <Plus className="w-3 h-3" /> Add to Dictionary
              </button>
              <button 
                onClick={(e) => {
                  e.preventDefault(); e.stopPropagation();
                  editor?.commands.ignoreWord(spellBubble.word);
                  setSpellBubble(null);
                  handleJumpToNextError();
                }}
                className="w-full text-left px-2 py-1.5 rounded-md text-[11px] text-zinc-400 hover:bg-zinc-800 hover:text-zinc-200 transition-colors flex items-center gap-2"
              >
                <EyeOff className="w-3 h-3" /> Ignore
              </button>
            </div>
          </div>,
          document.body
        )}

        {/* AI Copy Editor Grammar Bubble (Blue) (Sovereign Portal) */}
        {grammarBubble && grammarBubble.visible && typeof document !== 'undefined' && createPortal(
          <div 
            className="fixed z-[9999] grammar-bubble bg-surface border border-blue-500/30 rounded-xl shadow-2xl p-3 flex flex-col gap-2 w-64 transition-all animate-in fade-in zoom-in duration-150"
            style={{ 
              left: `${grammarBubble.x}px`, 
              top: `${grammarBubble.y}px`,
              transform: grammarBubble.flip ? 'translate(-50%, 0)' : 'translate(-50%, -100%)'
            }}
            onMouseEnter={() => {
              if (hoverTimeoutRef.current) clearTimeout(hoverTimeoutRef.current);
            }}
            onMouseLeave={() => setGrammarBubble(null)}
          >
            <div className="flex items-center gap-2 border-b border-border pb-2">
               <Wand2 className="w-3 h-3 text-blue-400" />
               <span className="text-[10px] font-bold text-blue-400 uppercase tracking-widest leading-none">AI Suggestion</span>
            </div>
            
            <div className="text-zinc-300 text-sm font-medium">
               "{grammarBubble.suggestion}"
            </div>
            
            <div className="text-muted-foreground text-[11px] italic bg-background p-2 rounded border border-border">
               {grammarBubble.reason}
            </div>

            <div className="flex gap-2 mt-1">
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  editor?.chain()
                    .deleteRange({ from: grammarBubble.pos + 1, to: grammarBubble.pos + 1 + grammarBubble.original.length })
                    .insertContentAt(grammarBubble.pos + 1, grammarBubble.suggestion)
                    .removeGrammarEdit(grammarBubble.id)
                    .run();
                  setGrammarBubble(null);
                }}
                className="flex-1 py-1.5 bg-blue-500/20 hover:bg-blue-500/40 text-blue-300 text-xs font-bold rounded transition-colors"
              >
                Accept
              </button>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  editor?.commands.removeGrammarEdit(grammarBubble.id);
                  setGrammarBubble(null);
                }}
                className="flex-1 py-1.5 bg-[#222] hover:bg-rose-500/20 text-zinc-400 hover:text-rose-400 text-xs font-bold rounded transition-colors"
              >
                Ignore
              </button>
            </div>
          </div>,
          document.body
        )}
      </div>

      <style jsx global>{`
        .beta-locked-selection ::selection {
           background: rgba(99, 102, 241, 0.25) !important;
           color: inherit !important;
        }
        .beta-locked-selection {
           -webkit-user-select: text !important;
           user-select: text !important;
        }
      `}</style>
      <BulkDictionaryModal 
        isOpen={isBulkDictOpen} 
        onClose={() => setIsBulkDictOpen(false)} 
        misspelledWords={bulkMisspellings}
        onAddBulk={(words) => {
          if (editor) {
            // 1. Rapidly scan & auto-capitalize any lowercase stragglers that match the user's checked proper nouns
            words.forEach(word => {
              if (word !== word.toLowerCase()) {
                editor.commands.replaceAll(word, word);
              }
            });
            // 2. Add the final array of words to the user's persistent dictionary
            editor.commands.addWords(words);
          }
          setIsBulkDictOpen(false);
        }}
      />
    </div>
  );
});

export default React.memo(RichTextEditor);

