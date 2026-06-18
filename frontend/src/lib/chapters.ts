import { Chapter } from "@/types/industrial";

// Front matter (title page, prelude, table of contents, dedication, etc.) is not a
// jump target in the TOC and not analysis material in the boardroom. Prologue/Epilogue
// are narrative content and are intentionally NOT treated as front matter.
const FRONT_MATTER_KEYS = [
    "title page", "half title", "table of contents", "prelude", "preface",
    "foreword", "dedication", "copyright", "epigraph", "acknowledg",
    "frontispiece", "colophon", "about the author",
];

export function isFrontMatter(chapter: Chapter): boolean {
    const t = (chapter.original_heading || chapter.suggested_title || chapter.title || "").toLowerCase();
    if (!t) return false;
    return FRONT_MATTER_KEYS.some((k) => t.includes(k));
}
