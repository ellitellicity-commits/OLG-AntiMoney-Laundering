# Frontend Outline: audit and proposed restyle

> **Status:** proposal only (2026-10-15, branch `frontend-polish`). No frontend, backend or data file was changed to produce it.
>
> **Sources:**
> - The working frontend: `frontend/index.html`, `frontend/styles.css`, `frontend/app.js`, with `frontend/mock/alerts.json` as the fallback.
> - The root `PRODUCT.md` and `DESIGN.md`. They are the source of truth for behaviour, data, features and the **four risk bands**.
> - `design-reference/`: the "Case File" visual proposal (`DESIGN.md`, `PRODUCT.md`, `mock_frontend.html`, `API_MATCH.md`).
>
> **Precedence:** on facts (bands, detection methods, features), the root files win. On visual style, the design-reference is the proposal adapted here.
>
> **Note on file location:** the brief asked for design notes in `docs/DESIGN_RESTYLE.md`, but this task allowed only one new file. The visual direction (section 4) is therefore in this document. It can be split out into `DESIGN_RESTYLE.md` later.

**Change labels used throughout**

| Label | Meaning |
|---|---|
| **[CSS]** | Style only. `styles.css` changes; no markup or JS changes. |
| **[HTML]** | Markup change in `index.html` that keeps every id, class the JS uses, `data-*` and ARIA hook. |
| **[JS]** | Needs a JS change. **Listed for the team to decide, not done.** "JS (template only)" means editing the HTML template strings in `app.js` without changing logic, fetches or handlers. That is lower risk, but it still touches `app.js`. |

---

## 1. Inventory

### 1.1 Files

| File | Role |
|---|---|
| `frontend/index.html` (107 lines) | Static shell: top bar, banner, queue panel (filters, AI search, table), empty detail panel, empty Overview screen. |
| `frontend/styles.css` (427 lines) | All styling. Light theme only. Tokens on `:root`. Minimum width 1280px. |
| `frontend/app.js` (1183 lines) | Builds everything else as template strings: queue rows, detail header, 5 tabs, action bar, Overview screen. No framework. |
| `frontend/mock/alerts.json` | Hand-written fallback data, used when the API is unreachable. |

**API base:** `?api=` query parameter. Otherwise the same origin when served at `/app/`, else `http://127.0.0.1:8000` (`app.js:16-17`).

### 1.2 Screens and components

| # | Screen / component | What it shows | API calls | Where |
|---|---|---|---|---|
| S0 | **Top bar** | Title "Player Risk Review"; SYNTHETIC DATA tag; activity window and player count; AI status tag (on/offline, model); view switch (Alert queue / Overview); investigator name input (saved in localStorage) | `GET /meta` (once); `GET /ai/status` (every 30 s) | `index.html:16-30`, `app.js:133-193` |
| S0b | **Banner** | Mock-mode notice: API unreachable, showing mock data, decisions not saved | none | `index.html:32`, `app.js:154` |
| S1 | **Alert queue panel** | Count "N of M alerts (+ watchlist)" and min-score filter; filters (Band, Team, Anomaly type, Status, Confidence, Sort by, ID search); keyboard help line | `GET /alerts?limit=5000&include_watchlist=true` | `index.html:35-93`, `app.js:208-312` |
| S1a | **AI queue search** ("Ask the queue") | Plain-English query sets the filters and sort; the explanation and the source (LLM or keyword) appear with Clear. Hidden in mock mode | `POST /ai/search` | `index.html:70-77`, `app.js:1071-1117` |
| S1b | **Watchlist toggle** | "Include watchlist (N below the alert line)". Watchlist rows show a Watchlist tag | (included in `/alerts`) | `index.html:75`, `app.js:165, 1122` |
| S1c | **Queue table** | Per row: risk badge (score, band label, 4-segment meter) and confidence or Watchlist tag · player ID and last activity · top reason and up to 2 anomaly-type tags (+N more) · team · status tag. Sortable headers | none | `app.js:251-280` |
| S1d | **Queue states** | 8 skeleton rows while loading; "No alerts match these filters" when empty; error with Retry | none | `app.js:256-294` |
| S2 | **Detail panel (case file)** | Empty state "No alert open"; "Loading P…"; error with Retry | `GET /alerts/{id}`, `GET /players/{pid}/peers`, `GET /players/{pid}?limit=25&flagged_only=…`, `GET /players/{pid}/network`, `GET /players/{pid}/timeline` (all in parallel) | `app.js:316-355` |
| S2a | **Case header** | Player ID, SYNTHETIC tag, alert/watchlist ID, team, status; profile (age band, occupation, income band, home region, account age, peer group and size, behaviour group); compliance flags (identity not verified, PEP, sanctions, watchlist); large badge; confidence; **Case report** link | link to `GET /alerts/{id}/report` (opens in a new tab) | `app.js:376-399` |
| S2b | **Tab: Overview** | **AI case summary** (text, source line "AI provider/model · numbers checked" or "built-in template", Regenerate, note); key facts (8: 30-day deposits, baseline, deposits vs income, withdrawn, amount bet, net loss, distinct locations, linked accounts); "Does this truly warrant investigation?" (confidence basis, mitigating factors); 3 strongest reasons with points → score; "See all N reasons" link | `GET /alerts/{id}/summary[?refresh=true]` | `app.js:459-501, 609-643` |
| S2c | **Tab: Evidence** | Why flagged: all reasons (title, +points, half-points note, detail, anomaly-type tag, "compared with" own baseline / peer median); points rule note; **peer comparison** SVG strip plot (median, IQR, p5–p95, baseline hollow dot, now solid dot, log scale) and legend; **behaviour group** table (k-means: metric, last 30 days, group median, z) | (from detail load) | `app.js:505-604` |
| S2d | **Tab: Activity** | Weekly timeline SVG (deposits, amount bet, net loss; current / baseline / earlier shading; "Last 30 days →" marker); recent transactions table (time, type, amount, bet, channel, location with "outside Ontario", flag tags, device, payment method) with a **Show flagged only** toggle. Hidden in mock mode | re-calls `GET /players/{pid}?…flagged_only=` on toggle | `app.js:699-783` |
| S2e | **Tab: Network** | Node-link SVG (up to 12 linked accounts; circle fill by band, score inside; shared identifier labels; click to open) and linked list (badge, ID, shared identifiers, Open). Hidden in mock mode | (from detail load) | `app.js:785-859` |
| S2f | **Tab: Ask AI** | AI status line; 3 suggestion chips; question form; Q&A log with an "unverified numbers" warning. Hidden in mock mode | `POST /alerts/{id}/ask` (question and history) | `app.js:645-697` |
| S2g | **Action bar** (pinned) | Recommended action, team and rationale; **Accept recommendation** (primary) / **Escalate** / **Close as explained…** (opens form with a required reason) / **Assign to team…** (opens form with team and optional note); status message; decision history (`<details>`) | `POST /alerts/{id}/decision` | `app.js:863-966` |
| S3 | **Overview screen** (top-bar switch, hidden in mock mode) | Queue at a glance (bars by band, team, confidence, status); regulatory compliance indicators; emerging-risk flag trends (sparkline, recent vs before, "Rising ×N" / "New this month"); watchlist table (badge, ID, reason, AI %, Open); AI model card (ROC-AUC, AP, recall, FPR, top features, cross-seed table); audit trail (last 12) and **Download CSV** | `GET /stats`, `GET /watchlist`, `GET /audit`; link to `GET /audit.csv` | `app.js:968-1069` |

**Endpoint cross-check:** every path above exists in `backend/app/main.py`. The frontend does not call `GET /health` or `GET /model`.

### 1.3 LLM features (all must keep working)

| Feature | Endpoint | Hooks it needs |
|---|---|---|
| AI status tag and Ask-tab status | `GET /meta` → `ai`, `GET /ai/status` | `#ai-status` (`data-on`), `#ask-status` |
| Case summary (+ Regenerate) | `GET /alerts/{id}/summary` | `#ai-summary` (`aria-busy`), `#sum-text`, `#sum-meta`, `#sum-actions`, `#sum-refresh`, `#sum-note` |
| Case Q&A | `POST /alerts/{id}/ask` | `#ask-form`, `#ask-q`, `#ask-log`, `.ask-chip[data-q]`, `.ask-a`, `.ask-warn` |
| Plain-English queue search | `POST /ai/search` | `#ai-search`, `#ai-q`, `#ai-search-result`, `#ai-clear`, and the filter ids it writes into |

### 1.4 Protected hooks (do not rename, remove or re-nest)

**Static ids (`index.html`):**
- Top bar and banner: `window-label`, `ai-status`, `nav-queue`, `nav-overview`, `investigator`, `banner`.
- Queue view: `view-queue`, `queue-title`, `queue-count`.
- Filters: `filters`, `f-band`, `f-team`, `f-type`, `f-status`, `f-confidence`, `f-sort`, `f-search`.
- AI search: `ai-search`, `ai-q`, `f-watchlist`, `watchlist-label`, `ai-search-result`.
- Table and panels: `queue-wrap`, `queue-table`, `queue-help`, `queue-body`, `detail`, `view-overview`.

**Ids generated by `app.js`:**
- Queue: `row-{alert_id}`, `retry`, `retry-detail`.
- Detail header and tabs: `detail-title`, `tab-{overview|evidence|activity|network|ask}`, `panel-{…}`.
- Summary: `ai-summary`, `sum-h`, `sum-text`, `sum-meta`, `sum-actions`, `sum-refresh`, `sum-note`.
- Ask AI: `ask-status`, `ask-form`, `ask-q`, `ask-log`.
- Activity: `activity`, `flagged-toggle`.
- Action bar: `decision-buttons`, `decision-msg`, `close-form`, `close-note`, `assign-form`, `assign-team`, `assign-note`.
- AI search: `ai-clear`.
- Section heading ids: `top-h`, `why-h`, `peer-h`, `bg-h`, `facts-h`, `conf-h`, `tl-h`, `act-h`, `net-h`, `ask-h`, `rec-h`.

**`data-*` attributes:**
- Set by JS and used for behaviour: `data-index` (rows), `data-sort` (headers), `data-tab`, `data-wired`, `data-open-alert`, `data-goto-tab`, `data-act` (accept, escalate, close, assign), `data-cancel`, `data-q`.
- Available for styling: `data-band`, `data-status`, `data-level`, `data-on`.

**Class and structure selectors the JS queries** (keep the class and its nesting):
- Queue: `.queue-table thead`, `.queue-table th[data-sort]`, `#queue-body` rows, `tr[data-index]`, `tr.is-open`.
- Detail: `.detail-tabs [role=tab]`, `.ask-chip`, `.ask-a`, `.form-error`.
- Action bar: `.action-bar button` (all disabled while saving).
- Activity: `#activity .section-head .muted`, used for the reload error text.
- Also `.skeleton`.

**ARIA states the JS sets, and which CSS may style:** `aria-selected` (rows, tabs), `aria-pressed` (view tabs, flagged toggle), `aria-expanded` (close/assign), `aria-sort`, `aria-busy`, `hidden`.

**Fixed text the JS writes:** queue count, banner, AI status, button labels in templates. Changing any of this wording is a **[JS]** change.

---

## 2. Critique and audit summary

> **How it was run:** `/impeccable critique` used two independent assessments, a source-level design review and the bundled detector (`impeccable detect --json frontend/`, exit 2, 3 findings). `/impeccable audit` was scored from the same evidence. **No browser was available**, so nothing was screenshotted and no overlay was injected; rendering was judged from source. The critique snapshot was **not persisted**, because this task allows creating only this file.

### 2.1 Scores

**Critique (Nielsen): 26/40, Acceptable (top of band)**

| # | Heuristic | Score | Key issue |
|---|---|---|---|
| 1 | Visibility of status | 3 | The detail panel blanks to "Loading…" on every open, including the action bar. The "selected" and "open" rows are hard to tell apart. |
| 2 | Match to real world | 3 | Domain copy is strong. Jargon leaks in: z, k-means, ROC-AUC, "Seed 42", FINTRAC-style. |
| 3 | User control | 2 | Accept and Escalate save in one click with no undo. There is no "Clear filters" except after an AI search. |
| 4 | Consistency | 2 | "Overview" is both the top-level screen and a detail tab. High/Critical risk colours are reused for PEP, errors, "Rising" and warnings. |
| 5 | Error prevention | 2 | The investigator name is only checked when a decision is submitted. Focus returns to Accept after saving, so Enter records twice. |
| 6 | Recognition vs recall | 3 | The top reasons (Overview tab) and the peer chart (Evidence tab) are split across tabs. |
| 7 | Flexibility | 3 | Good keyboard model. Missing: auto-advance to the next alert, keys for Escalate/Close/tabs. |
| 8 | Minimalist design | 3 | Calm palette. The queue controls and case header are dense: 7-8 profile fields plus 8 key facts. |
| 9 | Error recovery | 2 | The Overview screen error has no Retry. Raw `err.message` is shown ("Failed to fetch"). |
| 10 | Help | 3 | Good inline notes. "Confidence" is undefined in the queue. Ask AI has no help. |

**Audit (technical): 10/20, Acceptable**

| # | Dimension | Score | Key finding |
|---|---|---|---|
| 1 | Accessibility | 2 | All text passes AA, but there are several AA gaps (below). |
| 2 | Performance | 3 | Lean: no framework, no images. The whole detail panel re-renders with `innerHTML` on every open and decision, and the AI-status poll runs every 30 s. Fine at this scale. |
| 3 | Theming | 2 | Tokens exist on `:root`, but about 30 hex values are hard-coded in `app.js` SVG and badge code (`app.js:21, 586-601, 726, 740, 750, 753-755, 802, 810-813, 991`) and 3 in CSS (`styles.css:173, 293, 321`). No dark theme. |
| 4 | Responsive | 1 | `body { min-width: 1280px }` (`styles.css:36`). Below 1280px the page scrolls sideways, and at 200% zoom it fails WCAG 1.4.10 Reflow. The SVG viewBox scaling makes chart text 12px→≈17px on wide screens. |
| 5 | Implementation integrity | 2 | Specific to the product overall. Detector: 3 "side-tab" warnings (`styles.css:132` banner, `:321` AI summary are true positives; `:390` confidence is a false positive, a deliberate solid-vs-dashed code). Risk colours drift into non-risk roles. |

**AA gaps:**
- Queue rows use `aria-selected` with no grid or listbox role.
- Network nodes with `role="button"` sit inside `<svg role="img">`, so screen readers cannot reach them. The list below them is the fallback.
- Network nodes set `.node:focus { outline: none }`.
- `#queue-count` is `aria-live` and re-announces on every search keystroke.
- Control borders are 1.5:1 (1.4.11 needs 3:1).
- Esc does not close the Close and Assign forms.

### 2.2 Top issues by theme

**Hierarchy**
- The Overview tab leads with AI prose, then 8 key facts, then confidence, then reasons. The evidence ("Strongest reasons") lands last and often below the fold, yet the product principle is *"Evidence, not narrative"*.
- The large badge sits inside the scrolling area, so on Evidence or Activity the score scrolls away. Root DESIGN 7.5 promises "score, reasons and action always on screen together".
- Status ("Escalated", "Closed") is a small outlined tag with almost no visual weight. A decided case looks like an undecided one.

**Clarity**
- "Overview" means two things.
- In mock mode, Overview, Activity, Network and Ask AI disappear without explanation.
- The banner shows a `uvicorn` command, which is aimed at developers.
- The recommendation's team can differ from the alert's team without explanation.

**Scan speed**
- At 1280px the queue panel is about 490px wide.
- The filter bar wraps to about 3 rows, and with the AI row, watchlist row, panel head and help line, about 330px of controls sit above the table. Only 5-6 alerts are visible on a laptop.
- Selection does not open the case (Enter is needed), and the first alert never auto-opens.

**Contrast**
- Text is fine: the lowest is 5.13:1 (white on High `#B4500F`).
- Non-text fails:
  - input borders 1.50:1 and input wells 1.18:1;
  - peer whisker and "earlier" timeline bars 2.43:1;
  - the timeline "current" vs "baseline" bars differ from each other by only 2.43:1;
  - High vs Critical network fills differ by 1.76:1 (the printed score inside saves it).

**Accessibility:** see the AA gaps under 2.1. Small text also falls below DESIGN's 12px floor: `.tag-flag`, `.points-note` and `.edge-label` are 11px.

**Responsiveness:**
- Desktop-only by design, which is acceptable for the demo.
- Reflow at 200% zoom is the real failure.
- The 9-column activity table always scrolls sideways.

**States**

| Area | Loading | Empty | Error |
|---|---|---|---|
| Queue | Skeleton rows (good) | "No alerts match" with no Clear action | Retry available |
| Detail | Replaces the whole panel, action bar included | n/a | Retry available |
| AI summary | Skeleton line (good) | n/a | Raw message |
| Overview screen | Plain text | n/a | **No Retry** |

### 2.3 What already works (keep it)

1. **The risk badge** always shows number, label and 4-segment meter. It has `role="img"` and an aria-label, and the same badge is used in the queue, header, network list and watchlist.
2. **Explainability is concrete:**
   - The points → score line and the overlap "half of N" note.
   - "Compared with" own baseline and peer median.
   - The "Reasons it may be innocent" section.
   - A peer chart that prints every value and reads them out in its aria-label.
3. **Keyboard model:** roving tabindex, ↑↓/PgUp/PgDn/Home/End, `/`, `D`, `Esc`, arrow-key tabs, skip link, sticky sortable headers with `aria-sort`, and the pinned action bar.

---

## 3. Proposed outline

Every element below uses only data the frontend already receives.

### 3.1 Screen: Alert queue + case file (main screen)

```
┌──────────────────────────────────────────────────────────────────────────────────────┐
│ MASTHEAD (ink-navy)  Player Risk Review  [SYNTHETIC DATA]  Activity … · N players     │
│                      [● AI on · model]          [Alert queue] [Team overview]  Deciding│
│                                                                     as: [ name_____ ] │
├──────────────────────────────────────────────────────────────────────────────────────┤
│ banner (mock / API notice, only when shown)                                           │
├────────────────────────────┬─────────────────────────────────────────────────────────┤
│ DOCKET (≈38%, own scroll)  │ CASE FILE (≈62%, own scroll)                            │
│ Alert queue      142 of 160│ ┌ sticky case header ────────────────────────────────┐ │
│ ▁▁▁▂▂▃▅█ band ribbon [JS]  │ │ P-10482 [SYNTHETIC]   ╔ESCALATED╗ stamp            │ │
│ [Search ID  / ][Band▾]     │ │ Alert A-… · AML                 ┌──────────────┐   │ │
│ [Team▾][Type▾][Status▾]    │ │ profile line (wraps, quieter)   │ 94 CRITICAL ▮▮▮▮│ │ │
│ [Conf▾][Sort▾]             │ │ [Identity unverified][PEP]      └──────────────┘   │ │
│ Ask the queue: [_____][Find]│ │                        ● High confidence  Report↗ │ │
│ ☐ Include watchlist (N)    │ └────────────────────────────────────────────────────┘ │
│ ─────────────────────────  │  Overview │ Evidence 6 │ Activity │ Network │ Ask AI   │
│ ▌94 CRIT ▮▮▮▮  P-10482     │ ─────────────────────────────────────────────────────  │
│ ▌● High   2026-10-14 21:07 │  Case summary (AI · numbers checked)   Regenerate       │
│   Deposits far above inco… │  ── evidence thread ─────────────────────────────────  │
│   [Income mismatch] +1     │  ○ +28  Deposits far above declared income              │
│   AML        New           │  │      $18,400 / 30d · own baseline $1,200 · peers $620│
│  87 HIGH ▮▮▮▯  P-…         │  ○ +22  …                                               │
│  …                         │  Points 112 → score 94      See all 6 reasons →         │
│                            │  key facts (4 × 2 ledger)                               │
│                            │  Does this warrant investigation? · innocent reasons    │
│ ↑↓ move · Enter open · D … │ ┌ ACTION BAR (pinned) ───────────────────────────────┐ │
│                            │ │ RECOMMENDED · AML  Request source of funds          │ │
│                            │ │ rationale…                                          │ │
│                            │ │ [Accept recommendation] [Escalate] [Close…] [Assign…]│ │
│                            │ │ Decision history (2) ▸                              │ │
│                            │ └─────────────────────────────────────────────────────┘ │
└────────────────────────────┴─────────────────────────────────────────────────────────┘
```

**What leads, what collapses:**
- **The docket leads with risk.** The band badge is the left anchor of each row, and Critical rows get an extra rule (see 5.3). The controls are compressed so that **10 or more rows** are visible at 1280×800.
- **The case file leads with identity, verdict and score.** The header is sticky, so the score never scrolls away.
- **Overview tab order:** summary (kept above the evidence, per root DESIGN 7.3) → **strongest reasons as the evidence thread** → key facts → confidence. The evidence rises from last to second.
- **The action bar stays pinned.** A decided case shows its status stamp in the header, so the investigator can see it was already handled.
- **Collapses:**
  - the profile list becomes one quieter wrapped line;
  - the decision history stays in `<details>`;
  - the k-means and points-rule notes become small print;
  - less-used filters can collapse behind a "More filters" disclosure (option Q3b).

| # | Change | Type | Notes |
|---|---|---|---|
| Q1 | Masthead in ink-navy; title in serif; SYNTHETIC tag outlined light-on-navy; view switch as underlined tabs | **[CSS]** | `.topbar`, `.brand h1`, `.tag-synthetic`, `.view-tab[aria-pressed]` |
| Q2 | Rename the top-level "Overview" button to **"Team overview"** | **[HTML]** | Text only; `#nav-overview` and `aria-pressed` are unchanged |
| Q3a | Tighten the filter bar so it wraps to 2 rows, not 3: shorter labels via smaller label type, 28px controls, `#f-type` narrower; search first | **[CSS]** for sizes. Moving search first is **[HTML]** (reorder `<label>` elements inside `#filters`; ids unchanged) | The selects stay in `#filters`, so `applyView` and `openLinked` still find them |
| Q3b | *(Option)* Move Type, Status, Confidence and Sort into a `<details class="more-filters">` inside `#filters` | **[HTML]** | Risk: an AI search or `openLinked` can set a filter that is now hidden. Showing an "(n active)" count needs **[JS]**. Recommend Q3a first. |
| Q4 | Queue rows to 52px: badge column fixed width; reason clamped to 1 line with the tags under it; team in small caps; `tr:hover` visible (`--paper-2`) | **[CSS]** | `.queue-table td`, `.reason-cell` |
| Q5 | Make "open" distinct from "selected": `tr.is-open` gets a full-height ink left rule, and selected keeps the accent inset plus background | **[CSS]** | Currently only the ID is underlined (`styles.css:177`) |
| Q6 | **Sticky case header:** `.player-head { position: sticky; top: 0 }`, compact profile row, badge larger. The tabs are then either non-sticky or sticky at a fixed offset | **[CSS]** | `.player-head` is already the first child of `.detail-scroll`. A fixed-offset sticky tabstrip needs a known header height; if that proves fragile, repeat the badge in the action bar instead (**[JS] template**) |
| Q7 | Visually reorder the Overview tab (strongest reasons before key facts and confidence) with `#panel-overview { display: flex; flex-direction: column }` and `order` on `section[aria-labelledby="top-h"]` | **[CSS]** | DOM order is unchanged, so screen-reader and Tab order still reach the summary, facts and confidence first. The only focusables are Regenerate and "See all", so the impact is low. The true reorder is **[JS] template** |
| Q8 | Evidence thread styling for `ol.reasons` (see 5.2) | **[CSS]** | |
| Q9 | Status as stamp (see 5.1) | **[CSS]** | |
| Q10 | Band ribbon above the queue (see 5.3) | **[JS]** | Counts come from `state.alerts`; no API change |
| Q11 | Auto-open row 0 on load; after a decision, advance to the next undecided row and open it; Undo link in `#decision-msg` | **[JS]** | Biggest throughput win. Undo needs a backend decision-revert, or recording a counter-decision |
| Q12 | After saving, do not focus Accept. On decided alerts show "Already Escalated by X on date" and demote the buttons | **[JS]** | Prevents double-recording |
| Q13 | Ask for the investigator name before the first decision ("Deciding as" in the action bar) | **[JS]** | The current check happens only on submit |
| Q14 | Queue a11y: `role="grid"` (or listbox semantics) so selection is announced; debounce or stop `aria-live` on `#queue-count` while typing; Esc closes the Close/Assign forms; network nodes reachable (move `role="img"` to a wrapper `<g>`, keep the list) | **[JS]** (+ **[HTML]** for `#queue-count` `aria-live`) | |
| Q15 | Network node focus ring: remove `outline: none`, use a 2px accent ring | **[CSS]** | `styles.css:405` |
| Q16 | Overview screen error: add Retry; friendly copy instead of raw `err.message` | **[JS]** | |
| Q17 | Empty-filter state: add a "Clear filters" button (can call the existing `clearAiFilter`) | **[JS] template** | |
| Q18 | Loading a case: keep the previous case dimmed (`aria-busy`) instead of blanking the panel and action bar | **[JS]** | CSS can style `[aria-busy]`, but the JS currently replaces the content |

### 3.2 Screen: Case file tabs

```
EVIDENCE                                ACTIVITY                            NETWORK
Why flagged      Points 112 → score 94  Activity over time (weekly)         Linked players · cluster C-… · 4
small print: points rule                ┌ deposits ▁▂▂▃▂▃▅▇ │█▇ ┐           ┌ graph (score in circle, band ring) ┐
○ +28 Deposits far above income         │ amount   ▁▁▂▂▂▃▃▄ │▇█ │           └────────────────────────────────────┘
│  detail · compared with …             │ net loss ▁▂▁▂▂▂▃▃ │█▇ ┘           ▸ 87 HIGH ▮▮▮▯ P-… shares device …  Open
○ +22 …                                 legend: last 30d / baseline / earlier
Compared with peers                     Recent activity  Latest 25 of 1,204  [Show flagged only]
 ┌ strip plot per metric ┐              table: Time · Type · Amount · Bet · Channel · Location · Flags · Device · Payment
 legend                                 (flagged rows: ink left rule + flag tags)
Players who bet like them (k-means)
 metric table                                                                 ASK AI
                                                                              status line
                                                                              [chip] [chip] [chip]
                                                                              [question____________][Ask]
                                                                              Q / A log (unverified-number warning)
```

| # | Change | Type | Notes |
|---|---|---|---|
| T1 | Section headings (`.section h3`) in serif 17px; the tab strip gets a quieter rule and an accent underline on the selected tab | **[CSS]** | |
| T2 | Peer chart and timeline: recolour via CSS on SVG elements (CSS overrides SVG presentation attributes). Whisker and "earlier" bars to a ≥3:1 grey; IQR band to `--paper-2` with a `--rule-strong` outline; current bars ink, baseline bars mid-grey with a hatch | **[CSS]** for the colour changes, using selectors such as `.timeline rect[fill="#A9A69D"]`. That works but is brittle. The clean fix is replacing the hex values with `var(--…)` in `app.js` (**[JS] template**), which Night shift needs anyway | |
| T3 | Fix chart text scale: cap `.peer-chart > svg, .timeline > svg { max-width: 760px }` so 12px labels stay about 12px | **[CSS]** | |
| T4 | Activity table: tighter cells; Device and Payment method columns in muted mono; flagged rows keep the left rule in ink (not the High colour) | **[CSS]** | |
| T5 | Ask AI chips: restyle `.ask-chip` as quiet buttons (border, hover, focus) so they no longer look like tags; Q in serif, A in body; `.ask-warn` uses the new `--warn` token (not High) | **[CSS]** | |
| T6 | Network: band ring and fill via CSS attribute selectors on `circle[fill=…]`. Critical gets a double ring | **[CSS]** (brittle; see T2) | |
| T7 | Close-reason textarea at 3 rows minimum (`#close-note { min-height: 64px }`) | **[CSS]** | `rows="1"` is in the template; CSS min-height overrides it |

### 3.3 Screen: Team overview

```
Queue at a glance  160 alerts · 40 watchlist · 12,000 players
 By risk band (Critical/High/Medium bars, each with badge-style label) │ By team │ By confidence │ By status
Regulatory compliance indicators (bars)       │ Emerging risk (sparkline table, "Rising ×N" stamp-style tag)
Watchlist (badge · ID · reason · AI % · Open) │ Audit trail (last 12) [Download CSV]
▸ About the AI risk model (ROC-AUC, cross-seed)  ← collapsed by default [JS template]
```

| # | Change | Type |
|---|---|---|
| O1 | Panels as paper sheets; headings serif; `.bars .bar` in ink, and in the band colour only inside "By risk band". That needs a per-row hook, so it is **[JS] template**; CSS alone keeps the bars ink | **[CSS]** |
| O2 | Band rows in "By risk band" show band label + meter shape, not just text | **[JS] template** |
| O3 | Model card collapsed behind `<details>` (it is for judges, not investigators) | **[JS] template** |
| O4 | Retry on error | **[JS]** |

### 3.4 States

| State | Today | Proposal | Type |
|---|---|---|---|
| Queue loading | 8 skeleton rows | Keep; skeleton tint `--paper-2`, no shimmer | [CSS] |
| No alert open | Centred text | Paper sheet with a faint "case file" rule pattern and the keyboard hint | [CSS] |
| Case loading | Panel replaced with text | Dim the previous case | [JS] (Q18) |
| Mock mode | Banner with dev command; tabs vanish | Banner styled as a typed notice (no side-tab stripe); copy for investigators, dev hint in small print | [CSS] for the style; [JS] for the copy |
| AI offline | Dashed muted tag | Keep; add "offline" text in the masthead (it already says "AI assistant offline") | [CSS] |
| Errors | Raw message | Friendly line + technical detail in small print | [JS] |

---

## 4. Visual direction: "Case File", adapted to the working frontend

**Personality:**
- A well-kept regulatory dossier: warm paper sheets, ink-navy masthead, serif for the human-readable verdicts (titles, score numeral, reason headlines), IBM Plex Sans for UI, and Plex Mono for every number and ID.
- Colour is reserved for risk; one slate-blue accent marks interaction.

**Adopted from design-reference:**
- paper and card tokens, the ink-navy masthead, serif titles and numerals, the evidence thread, the status stamp, Night shift.

**Not adopted, because the root files win:**
- the 3-band scale;
- "4 bars = High ≥ 90";
- the static "Monitoring" pulse (there is no such data);
- the avatar initials (no data value);
- the daily heat strip in queue rows (the queue summary has no daily series; see 5.3 for the replacement).

### 4.1 Tokens

All tokens are on `:root`. Night shift overrides them under `:root[data-theme="night"]` (needs a toggle, **[JS]**) and/or `@media (prefers-color-scheme: dark)` (**[CSS]**, automatic).

| Token | Day | Night | Role |
|---|---|---|---|
| `--paper` | `#F4F0E6` | `#10151F` | Page ground |
| `--paper-2` | `#EAE4D5` | `#0C1018` | Docket column, table heads, hover |
| `--card` | `#FBF8F1` | `#18202E` | Sheets (replaces `--surface`) |
| `--rule` | `#D6CDB9` | `#2A3446` | Dividers |
| `--rule-strong` | `#857A66` | `#6B7890` | **Control borders and chart outlines (≥3:1, fixes 1.4.11)** |
| `--ink` | `#1B2333` | `#ECE6D8` | Text |
| `--ink-2` | `#4A5265` | `#A9B1C0` | Secondary text (replaces `--ink-muted`) |
| `--navy` / `--navy-ink` | `#16213A` / `#F4F0E6` | `#0A0E16` / `#ECE6D8` | Masthead |
| `--accent` | `#2F55A4` | `#8EB0F2` | The only interaction colour |
| `--accent-ink` | `#FFFFFF` | `#10151F` | Text on accent |
| `--warn` | `#4A5265` + bold + ⚠ glyph | `#ECE6D8` + bold + ⚠ glyph | **New:** non-risk attention (PEP, sanctions, form errors, unverified numbers, "Rising"). Neutral ink, so risk colours stay for risk only |

Keep the old names as aliases (`--surface: var(--card)`, `--ink-muted: var(--ink-2)`) so existing CSS keeps working during the migration.

### 4.2 Risk bands: four bands, number + label + shape + treatment

The badge markup is unchanged (`.risk[data-band]` with `.risk-score`, `.risk-label`, `.risk-meter i.on`), so all of this is **[CSS]**.

| Band | Score | Meter | Day treatment | Night treatment | Extra shape cue |
|---|---|---|---|---|---|
| **Low** | 0–39 | ▮▯▯▯ | soft `#DCEBE7`, text `#155E57` (6.16:1) | soft `#143A36`, text `#5CC3B5` (5.88:1) | none |
| **Medium** | 40–69 | ▮▮▯▯ | soft `#F3E3BF`, text `#7A4F00` (5.62:1) | soft `#3A2F14`, text `#E4B04F` (6.65:1) | none |
| **High** | 70–89 | ▮▮▮▯ | soft `#F5DAD2`, text `#9A2E1E` (5.69:1) | soft `#40241F`, text `#F08A74` (5.77:1) | 1px solid border in the text colour |
| **Critical** | 90–100 | ▮▮▮▮ | **solid `#6E1423` (oxblood), text `#FFFFFF` (11.75:1)** | **solid `#F4A3B0`, text `#10151F` (9.32:1)** | **inverted fill**, 3px double border, bold label |

Notes:
- **Why Critical is not just a "darker High":**
  - High and Critical solids are only 1.56:1 apart in Day and 1.25:1 in Night, too close to rely on.
  - So Critical changes **treatment**: it is the only band with a *solid, inverted* fill and a *double* border, on top of the 4th meter bar and the bold label. That separates it from High in greyscale and for colour-blind users.
- **Meter shape:** make the bars rise (5/7/9/12px) so the meter is a shape as well as a count (`.risk-meter i:nth-child(n) { height: … }`).
- **On card**, every band's text colour passes as plain text: Low `#155E57` 7.15, Medium `#7A4F00` 6.72, High `#9A2E1E` 7.11, Critical `#6E1423` 11.08 (Day). The Night solids on `#18202E` are 7.73 / 8.27 / 6.69 / 8.34.
- **Network circles** (`app.js:21` `BAND_FILL`) and Team overview bars need the same values. Until `BAND_FILL` reads CSS variables (**[JS]**), override them with CSS attribute selectors (T6).
- **Queue sort and screen reader:** unchanged ("Risk score 94 out of 100, Critical").

### 4.3 Typography

| Role | Face | Size | Applies to (existing selector) |
|---|---|---|---|
| Brand | Source Serif 4 600 | 20px | `.brand h1` |
| Case title (player ID) | Source Serif 4 600 + Plex Mono for the ID | 26px | `#detail-title` (the ID keeps `.mono`) |
| Large score numeral | Source Serif 4 600, tabular | 32px | `.risk.large .risk-score` |
| Section heading | Source Serif 4 600 | 17px | `.section h3`, `.panel-head h2` |
| Reason headline | Source Serif 4 600 | 15px | `.reason-title` |
| Body / UI | IBM Plex Sans 400–500 | 14px | body |
| Labels | Plex Sans 600 uppercase +0.04em | 12px (raise all 11px to 12px) | `.label`, `.tag-flag`, `.points-note`, `.edge-label` |
| Numbers, IDs | Plex Mono 500 tabular | context size | `.mono`, `.num` |

Adding Source Serif 4 to the Google Fonts `<link>` is an **[HTML]** change (`index.html:10`); everything else here is **[CSS]**.

### 4.4 Surfaces, shape, motion

- **Surfaces:**
  - Sheets are `--card` with a 1px `--rule` border and an optional faint paper grain (an SVG data-URI background, quieter in Night).
  - No shadows except the selected queue row.
  - Remove the two side-tab stripes the detector flagged:
    - the banner becomes a top-ruled notice;
    - the AI summary becomes a sheet with an "AI · numbers checked" label in the header instead of a coloured left edge.
- **Radius:** 4px on controls and sheets, 2px on tags. No pills.
- **Motion:**
  - 140–200ms ease-out.
  - The case "re-inks" on open (`.detail-body` fade plus score fade-up, **[CSS]**). A count-up would need **[JS]**.
  - Everything is off under `prefers-reduced-motion`, which the existing rule already covers.

### 4.5 Night shift

| | |
|---|---|
| Style-only path | `@media (prefers-color-scheme: dark)` swaps the tokens. **[CSS]** |
| Manual toggle in the masthead | Sets `data-theme` on `<html>` and stores it. **[JS]** + **[HTML]** |
| SVG colours | The hex values in `app.js` charts would stay light-theme in Night until replaced with `var(--…)` (**[JS] template**) or overridden by attribute selectors (brittle **[CSS]**). |

**Recommendation:** do not ship Night until the SVG hex values are tokenised.

---

## 5. Signature moments

### 5.1 The escalation stamp (style only, **[CSS]**)

Where it appears:
- `.tag-status[data-status]` already appears in every queue row and in the case header.
- In the **header**, `.player-head .tag-status` becomes a rubber stamp: mono uppercase, 3px double border, rotated −3°, inked with a short 160ms "press" (scale 1.06→1, opacity 0→1).

Treatment by status:

| Status | Stamp style |
|---|---|
| Escalated | Ink-navy double border, bold |
| In review | Accent single border |
| Closed | Muted, dashed, struck-through baseline |
| New | Plain outline |

Status is never shown by colour alone: the text is always present and the border style differs.

**Why it helps:** a decided case is recognisable at a glance, which supports Q12 (do not decide twice). In queue rows the tag stays small but gains the double border for Escalated.

### 5.2 The evidence thread (style only, **[CSS]**)

- `ol.reasons` gets a 1px vertical rule on the left. Each `li.reason` becomes an **unboxed** row with a ring node on the thread. This also removes the "card inside sheet" nesting the design-reference critique flagged.
- `.reason-points .num` is set large in mono on the left of the headline ("+28").
- The existing "Points 112 → score 94" line closes the thread like a ledger total, with a double rule above it.
- The overlap note ("half of N") is shown as a hollow node.
- **Why it helps:** the investigator reads top to bottom and sees exactly how the score was built, so the evidence reads as a single chain. A bar for each reason relative to the strongest would need **[JS]**; it is optional.

### 5.3 The risk ribbon (needs **[JS]**, no API change)

- A one-line ribbon above the queue table: one segment per band (Critical, High, Medium, Low), each with a count, a band label and a meter glyph. Below it, an 8px proportion bar split by band.
- Clicking a segment sets `#f-band`, the same as using the select.
- Counts come from `state.alerts`, which the queue already has.
- **Why it helps:** shows the shape of the day's workload ("4 Critical, 31 High") without vanity KPI tiles. This replaces the design-reference's per-row daily heat strip, which needs a daily series the queue summary does not have.

**Style-only bonus:** `tr:has(.risk[data-band="Critical"])` gets a hairline oxblood rule above and below. **[CSS]**, and modern browsers support `:has`.

---

## 6. Ranking: impact vs effort vs breakage risk

Scale: H/M/L. **Breakage risk** means the risk of breaking existing behaviour or hooks.

| Rank | Change | Type | Impact | Effort | Breakage risk |
|---|---|---|---|---|---|
| 1 | Token swap to the Case File palette, with old names aliased; `--rule-strong` control borders (fixes 1.4.11); `--warn` for non-risk attention | [CSS] | H | L | L |
| 2 | Four-band badge restyle with a distinct Critical (inverted solid, double border, rising meter) | [CSS] | H | L | L |
| 3 | Evidence thread (5.2) + serif headings and reason headlines + Source Serif link | [CSS] + [HTML] (font link) | H | L | L |
| 4 | Escalation stamp (5.1) + open vs selected row distinction (Q5) | [CSS] | H | L | L |
| 5 | Sticky case header (Q6) | [CSS] | H | M | M (tab offset tuning) |
| 6 | Visual reorder of the Overview tab so the strongest reasons come second (Q7) | [CSS] | M-H | L | L (DOM order unchanged) |
| 7 | Tighter queue controls and rows (Q3a, Q4) | [CSS] / [HTML] | H | M | L |
| 8 | Masthead + "Team overview" rename (Q1, Q2) | [CSS] / [HTML] | M | L | L |
| 9 | Remove side-tab stripes (banner, AI summary); 12px floor; chart max-width; focus ring on network nodes (Q15, T3) | [CSS] | M | L | L |
| 10 | Critical row rule via `:has` | [CSS] | M | L | L |
| 11 | Auto-open first alert + advance after decision + Undo (Q11) | [JS] | **H** | M | M (needs undo semantics) |
| 12 | Decided-case guard, no refocus on Accept, name before first decision (Q12, Q13) | [JS] | H | M | M |
| 13 | Tokenise SVG hex values and `BAND_FILL` in `app.js` | [JS] template | M | M | L |
| 14 | Night shift: `prefers-color-scheme` first, then a toggle | [CSS], then [JS] | M | M | M (blocked by #13) |
| 15 | Risk ribbon (5.3) | [JS] | M | M | L |
| 16 | Queue a11y: grid role, live-region debounce, Esc closes forms, reachable network nodes (Q14) | [JS] | M | M | M |
| 17 | Overview Retry, friendly errors, clear-filters button, dim-on-load (Q16-Q18) | [JS] | M | L-M | L |
| 18 | "More filters" disclosure (Q3b) | [HTML] (+[JS] for the count) | M | L | M (hidden active filters) |
| 19 | Model card collapsed, band rows with meter on Team overview (O2, O3) | [JS] template | L-M | L | L |
| 20 | SVG recolouring via attribute selectors (T2, T6) as a stop-gap | [CSS] | L-M | L | M (brittle) |
| 21 | Reflow below 1280px / 200% zoom (drop `min-width`, stack panels ≤1100px) | [CSS] | M | M | M (layout regressions) |

**Suggested first pass** (all **[CSS]**, plus the one-line font link in **[HTML]**): ranks 1–10. No JS changes, no hook changes, and the four bands are kept. Ranks 11–19 are for the team to decide.

---

## Run notes

- **Critique:** dual assessment (design review and detector, run independently). Detector `impeccable detect --json frontend/` → exit 2, 3 `side-tab` findings (1 false positive). The detector does not scan the markup that `app.js` builds, so about 30 hard-coded hex values there were found by hand.
- **Browser:** none available, so there were no screenshots and no overlay. Contrast ratios were computed from the hex tokens (WCAG relative luminance).
- **Not done (task constraints):** no critique snapshot was persisted (no `.impeccable/` writes) and no files were edited. Questions skipped: the brief says to stop and wait for review.
