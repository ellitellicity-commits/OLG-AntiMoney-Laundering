# Prompt Log

Record every AI prompt that produced code or content in this project so teammates can reproduce, review and fix the results. Add an entry each time you prompt, under the matching build step from [WORKFLOW.md](WORKFLOW.md). Copy the entry template as many times as needed.

**Rules**
- Paste the exact prompt, not a summary.
- Never paste the confidential OLG brief into a public tool or a public repo.
- If you edited the output by hand afterwards, say so under "What went wrong / how we fixed it".

## Entry template

```markdown
### <step>.<n> — <short title>   (date: YYYY-MM-DD · author: <name> · tool/model: <name>)

**Context to paste:**
<files, schemas or earlier outputs given to the model>

**Exact prompt:**
<verbatim>

**Expected output:**
<file names / shape of result>

**How we test it:**
<command or check, and its result>

**What went wrong / how we fixed it:**
<problem → fix, or "nothing">
```

---

## Step 1 — Synthetic data

### 1.1 —

**Context to paste:**

**Exact prompt:**

**Expected output:**

**How we test it:**

**What went wrong / how we fixed it:**

---

## Step 2 — Features

### 2.1 —

**Context to paste:**

**Exact prompt:**

**Expected output:**

**How we test it:**

**What went wrong / how we fixed it:**

---

## Step 3 — Detection and scoring

### 3.1 —

**Context to paste:**

**Exact prompt:**

**Expected output:**

**How we test it:**

**What went wrong / how we fixed it:**

---

## Step 4 — Validation

### 4.1 —

**Context to paste:**

**Exact prompt:**

**Expected output:**

**How we test it:**

**What went wrong / how we fixed it:**

---

## Step 5 — API

### 5.1 —

**Context to paste:**

**Exact prompt:**

**Expected output:**

**How we test it:**

**What went wrong / how we fixed it:**

---

## Step 6 — Dashboard

### 6.1 —

**Context to paste:**

**Exact prompt:**

**Expected output:**

**How we test it:**

**What went wrong / how we fixed it:**

---

## Frontend mock

### F.1 — Static dashboard mock + API contract   (date: 2026-10-15 · author: TBD · tool/model: Claude Code, Opus 5.5, with the `/impeccable shape` and `/impeccable critique` skills)

**Context to paste:**
`PRODUCT.md` and the pre-build `DESIGN.md` draft, plus the existing docs (README, WORKFLOW, HANDOFF) so references could be updated.

**Exact prompt:**
```
/impeccable shape dashboard

Read PRODUCT.md and DESIGN.md first and follow them, with the updates below.

THIS IS A STATIC MOCK ONLY. Its purpose is to show how the final dashboard should look and which data the backend must provide. Do NOT implement real functionality: no fetch calls, no filtering logic, no search logic, no keyboard shortcuts, no working buttons, no state changes. Buttons and filters are visual only. The only interactions allowed are (1) the light/dark toggle and (2) clicking a queue row to show that player's dossier, implemented in a few lines of JS over hardcoded data. Do not touch any backend code.

FILE: Build the mock as a single file, /frontend/mock_frontend.html. Keep it fully self-contained: CSS in a <style> block, JS in a <script> block, data hardcoded inline, inline SVG for charts, and fonts from Google Fonts with sensible fallbacks. It must open correctly by double-clicking the file, with no server needed. Do not copy any real OLG, Ontario or Canada branding or logos; use a neutral product name, "Sentinel", with a simple original mark.

DATA: Hardcode 8 fictional sports betting players inline. Each has: player_id, initials, age, occupation, income_band, province, risk_score (0-100), band (Low 0-39, Medium 40-69, High 70-100), anomaly_types (income_mismatch, peer_deviation, location, behaviour_change), reasons[] (type, headline, evidence, weight), monthly_spend, peer_median, peer_p90, activity_30d (30 numbers), locations[] (region, count), linked_players[], status, recommended_action. Cover all four anomaly types and all three bands, and make two players linked.

SCREEN (single page, two panels):
- Header: product name and mark, "monitoring" indicator, light/dark toggle labelled "Night shift", and a ribbon of alert counts by band.
- Left: alert queue ranked by risk. Row = initials avatar, player ID, one-line top reason, risk badge (number + label + 4-segment meter; never colour alone), status, thin 30-day heat strip. Show filter and search controls as visual placeholders.
- Right: dossier for the selected player: case header with status stamp and three placeholder buttons (Escalate, Dismiss, Request info); large risk score with a ring; "evidence thread" of reason cards; peer strip plot (player marker vs peer median and p90); 30-day activity chart; location breakdown; linked players list.

DESIGN: "Case File" personality with civic discipline. Warm paper surfaces, ink-navy header, Source Serif 4 for headings and big numerals, IBM Plex Sans for UI, IBM Plex Mono for IDs and figures. Palette: ink navy, paper, teal (low), amber (medium), coral-red (high), one UI accent. Add life with a gentle pulse on the monitoring indicator, a short score count-up and ring fill, and subtle paper grain on dossier cards, all under 300ms and disabled under prefers-reduced-motion. Light is default; dark mode fully designed, not just inverted. CSS variables for all colour and spacing tokens. WCAG AA contrast, visible focus states, semantic HTML, no lorem ipsum.

ALSO CREATE docs/API_CONTRACT.md: a plain-English guide for the backend developer listing every field the mock displays, its type, an example value, where it appears on screen, and which detection output must supply it. Then propose 3 endpoints (GET /alerts, GET /players/{id}, GET /summary) with example JSON responses matching the mock. Mark any field that needs the backend to compute something non-trivial.

CONSISTENCY: Update every reference to the frontend entry file in README.md, DESIGN.md, docs/WORKFLOW.md, docs/HANDOFF.md and docs/API_CONTRACT.md to say mock_frontend.html (the real live frontend will be a separate index.html built later).

WHEN DONE: run /impeccable critique on the mock, apply the top 3 fixes, update DESIGN.md to match what was actually built, log this prompt and its outcome in docs/PROMPTS.md under "Frontend mock", and list the files created or changed and anything I should check.
```

**Expected output:**
`frontend/mock_frontend.html` (self-contained static mock), `docs/API_CONTRACT.md`, an updated `DESIGN.md`, updated references in README / WORKFLOW / HANDOFF, and this log entry.

**How we test it:**
- **Screenshots:** headless Edge captured 1440×900 (day and Night shift) and 390px mobile.
- **Detector:** ran `impeccable detect`.
- **Critique:** two independent critique passes (design review, and detector plus browser contrast measurements).
- **Fix checks:**
  - the dossier scrolls back to top on row change (`scrollTop` 0, focus on the case title);
  - the meters read 1/2/3/4 by band;
  - there is no page overflow at 1440px or horizontal scroll at 390px.
- **Result:** every text pair measured WCAG AA in both themes (lowest 5.6:1).

**What went wrong / how we fixed it:**
- **Screenshot setup:** `playwright-cli` couldn't find Chrome, and blocks `file://` URLs. Fixed by using `--browser=msedge` and a throwaway local Node static server, for screenshots only. The mock itself still opens by double-click.
- **Chart labels:** SVG charts scaled with their container, so the labels shrank to about 6px on mobile. The charts are now drawn at their measured pixel width.
- **Page overflow:** the desktop page overflowed by 2px. Fixed with a flex-column page layout.
- **Critique score:** 22/36 before fixes (heuristic 9 was n/a). The top 3 issues fixed:
  1. a new case opened mid-scroll;
  2. Escalate was always the primary button, ignoring the recommendation;
  3. the risk meter disagreed with the band label.
- **Still open:** listed in `DESIGN.md` → "Known gaps".
- **Risk bands:** went from 4 to 3 bands (Low/Medium/High) per this brief. Updated README, PRODUCT.md and HANDOFF to match.

---

## Step 7 — Bonus features

### 7.1 —

**Context to paste:**

**Exact prompt:**

**Expected output:**

**How we test it:**

**What went wrong / how we fixed it:**

---

## Step 8 — Demo

### 8.1 —

**Context to paste:**

**Exact prompt:**

**Expected output:**

**How we test it:**

**What went wrong / how we fixed it:**
