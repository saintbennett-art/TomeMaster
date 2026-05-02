# PRoeditor: AI Architect Directives & Guardrails

This document establishes the permanent "Source of Truth" mandates for all AI agent development within the PRoeditor ecosystem. These rules are non-negotiable and must be audited before any UI or Data modification.

## 🏛️ The Truth-Source Mandate
- **Manuscript First**: Never fallback to Table of Contents (TOC) or Sidebar metadata for structural auditing. 
- **The Raw Prose Rule**: The "Structural Audit" view must prioritize raw manuscript content (`aiChapters`) over simplified UI TOC entries. If there is a mismatch, the Manuscript is ALWAYS correct.

## 🛡️ Anti-Hallucination Protocol: "Prose-Hunter"
To prevent "Ghost TOC" data leakage and hallucinated chapter headings:
- **Narrative Anchor Extraction**: Always extract anchors directly from the first 15 words of raw story prose.
- **250-Word Filter**: Actively filter out front-matter (e.g., Prelude, Forward, Dedication, Title Page) from structural pacing audits. A chapter must have >250 words or represent actual narrative prose to be considered a structural "beat."
- **Side-by-Side Comparison**: Ensure "Chapter Heading" and "Narrative Anchor" are distinct columns with no recycled data.

## 🛠️ Implementation Guardrails
- **Data-Prop Audit**: Before modifying ANY rendering code in `AnalysisDashboard.tsx` or `BoardroomReport.tsx`, you MUST perform a data-prop audit to confirm exactly where the chapter data is being sourced from.
- **Aesthetic Sovereignty**: UI updates must maintain the established "Dark Schrodinger" aesthetic: high-contrast, premium dark modes (HSL tailored), and smooth transitions. No generic colors.

---
*Last Hardened: 2026-04-02 — PRoeditor Development Team.*
