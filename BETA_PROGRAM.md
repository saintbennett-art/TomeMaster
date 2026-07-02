# Tome-Master Beta Program — 5 Authors

**Objective:** 5 external authors each complete the full pipeline — *manuscript in → edited → boardroom-analyzed → submission-ready export out* — on their own machines, with their own manuscripts, without Bennett Consulting touching their keyboard.

**Why 5:** small enough to support personally, large enough that every hard-coded assumption about "how authors work" gets broken at least once.

**Duration:** 6 weeks (2 recruit/onboard + 4 active use).

---

## 1. Success criteria (defined before we start, so we can't move the goalposts)

The beta **succeeds** if, by end of week 6:

| # | Criterion | Target |
|---|---|---|
| 1 | Authors who complete install without a live support call | ≥ 3 of 5 |
| 2 | Authors who run a full boardroom analysis on their real manuscript | ≥ 4 of 5 |
| 3 | Authors who produce an export they would actually send (query letter + Shunn docx, or EPUB) | ≥ 3 of 5 |
| 4 | Authors who return in week 4 without being prompted | ≥ 3 of 5 |
| 5 | "Would you be upset if this disappeared?" — *very disappointed* | ≥ 2 of 5 |

The beta **fails honestly** if fewer than 3 authors finish the pipeline. A failure tells us exactly which stage bleeds users — that's worth as much as a success.

## 2. Who to recruit (candidate profile)

Recruit for **coverage of the pipeline**, not fandom:

1. **The scanner** — has a drawer/box manuscript (handwritten or typed pages). Exercises OCR ingestion, the hardest path.
2. **The querying author** — finished novel, actively submitting to agents. Exercises boardroom analysis + Shunn export. Most motivated user we can get.
3. **The self-publisher** — has shipped on KDP before. Exercises EPUB/PDF export quality against Vellum/Atticus expectations. Will be the harshest judge.
4. **The privacy-conscious writer** — refuses ChatGPT on principle. Exercises the local/sovereign story; ideal first user for the Sovereign AI Pack when it lands.
5. **The novice** — writes in Word, has never used writing software beyond it. Exercises onboarding, defaults, and every error message. If the novice survives, the product works.

**Where to find them:** local writing groups/associations (personal ask > cold post), r/selfpublish and r/writing (transparent "5-seat beta" post), NaNoWriMo alumni groups, querying communities (QueryTracker forums). Personal referrals first — beta #1 should be someone who will pick up the phone.

## 3. The deal (both directions)

**They get:** free lifetime license of the release version, direct line to the developer, their format requests prioritized, named in acknowledgments (opt-in).

**They commit to:** using their **real manuscript** (the privacy story makes this safe — it never leaves their machine), one 20-minute call at onboarding and one at exit, a weekly 5-minute check-in form, and reporting the first moment they were confused or gave up.

**Privacy commitments we make in writing:** manuscripts never leave their machine; we never ask for manuscript content in bug reports (the `api_usage_log.jsonl` ledger contains token counts and model names, no prose); any screen-share is at their initiation.

## 4. Onboarding (week 1–2)

Per author, a 20-minute guided setup call:

1. **Install** from the packaged exe (`build_exe.bat` output). *Prereq task: verify the exe runs on a clean Windows machine with no dev tools — this is currently untested territory and the #1 beta risk.*
2. **Key setup** — free Gemini tier via the onboarding modal (already built). Author creates their own key; we never see it.
3. **First ingest** — their manuscript via upload (.docx/.pdf/.txt) or OCR path for the scanner.
4. **One boardroom run** together on a single chapter, so they see the value in the first session.
5. Leave them with the **week-1 task list** (below).

## 5. Structured tasks by week (the test script)

- **Week 1 — Ingest & edit:** get the full manuscript in; fix chapterization; use the editor for at least one real revision session.
- **Week 2 — Analysis:** full boardroom run; per-agent re-runs at different intensities; judge one report as "useful / generic / wrong" (their words, captured verbatim).
- **Week 3 — Export:** produce their real target format (Shunn for queriers, EPUB/PDF for self-pubs, FDX/Fountain for the screenplay-curious); open it in the destination tool (Word/Kindle Previewer/Final Draft) and report what looks wrong.
- **Week 4 — Free use:** no tasks. We watch (via check-in, not telemetry) whether they come back unprompted — criterion #4.
- **Weeks 5–6 — Buffer + exit interviews.**

## 6. Feedback capture

- **Weekly form** (5 min, 4 questions): What did you do? Where did you stop and why? What was confusing? What did you expect that didn't exist?
- **Bug channel:** email or a shared doc per author — whatever *they* already use; don't make authors learn GitHub.
- **Exit interview** (20 min): walk their pipeline end to end, the disappearance question (criterion #5), what they'd pay, what's missing before they'd recommend it.
- **Internally:** every report gets triaged into `BETA_FINDINGS.md` as *blocker / friction / polish / request* within 48h. Blockers get fixed during the beta; requests get parked unless they block a success criterion (scope discipline — the beta tests the pipeline that exists).

## 7. Known rough edges to disclose upfront (honesty policy)

- Word shows a field-update prompt on DOCX open — answer **Yes**; it fills the TOC and running headers (by design).
- Free Gemini tier has daily quotas; heavy boardroom use can hit them (quota-aware fallback exists, but analysis may slow).
- The desktop app requires Microsoft Edge WebView (Windows standard, but stated).
- Sovereign/offline AI is not yet packaged for novices — the privacy-conscious author starts on free-tier cloud keys with the local pack promised in-beta if it ships (see SOVEREIGN_PACK plan).

## 8. Pre-flight checklist (must be green before author #1)

- [ ] Packaged exe verified on a clean Windows 11 machine (no Python, no Node)
- [ ] Onboarding modal → free Gemini key → first analysis works on that machine
- [ ] OCR path tested with a real phone-photo of a typed page
- [ ] All 10 export formats produce openable files on that machine
- [ ] Crash behavior verified: app restart recovers the project file (files-only persistence)
- [ ] BETA_FINDINGS.md created; weekly form drafted
- [ ] One-page install/quickstart PDF written (novice-proof, screenshots)

## 9. Exit decision

At week 6, one of three honest calls:

1. **≥ 4/5 criteria met** → move to open beta / early access; convert findings into the release backlog.
2. **2–3 criteria met** → fix the top 3 bleed points, re-run a 2-week mini-beta with the same authors.
3. **< 2 criteria met** → stop building features entirely; the gap is product-market fit or onboarding, not capability. Re-plan from the exit interviews.
