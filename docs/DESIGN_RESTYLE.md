# Design Restyle: "Case File"

> **Status:** built in `frontend/styles.css` and `frontend/index.html` on branch `frontend-polish` (2026-10-15). This is a CSS-only first pass. `frontend/app.js` is unchanged.
>
> **Source:** extracted from section 4 of [FRONTEND_OUTLINE.md](FRONTEND_OUTLINE.md) and updated to match what was built.
>
> **Precedence:** the root [PRODUCT.md](../PRODUCT.md) and [DESIGN.md](../DESIGN.md) remain the source of truth for behaviour, data, features and the **four risk bands**. This file only describes the visual layer.
>
> **Name:** "Sentinel" is a neutral placeholder name. No real OLG, Ontario or Canada branding or logos are used.

## 1. Direction

**A case file, not a casino.** The investigator reads each alert like a well-kept regulatory dossier:
- **Paper and ink:** warm paper surfaces, ink text and an ink-navy masthead.
- **Serif for verdicts:** Source Serif 4 sets the case title, the score numeral, section headings and reason headlines.
- **Plex for work:** IBM Plex Sans for the interface; IBM Plex Mono for every amount, date and code.
- **Colour reserved for risk:** one slate-blue accent marks everything interactive.

Avoided: casino gold, neon, chips; AI-dashboard gradients, glass, glows, KPI tile walls; cards inside cards; coloured side stripes; emoji or glyph icons.

## 2. Colour (Day)

All tokens are CSS custom properties on `:root` in `frontend/styles.css`. The old token names are kept as **aliases**:

| Old name | Now points to |
|---|---|
| `--surface` | `--card` |
| `--surface-sunk` | `--paper-2` |
| `--ink-muted` | `--ink-2` |
| `--risk-*-bg`, `--risk-*-ink` | the matching new band tokens |

### Neutrals and accent
| Token | Hex | Role | Contrast |
|---|---|---|---|
| `--paper` | `#F4F0E6` | Page ground, AI summary, action bar | |
| `--paper-2` | `#EAE4D5` | Docket column, table heads | |
| `--card` | `#FBF8F1` | Case file, panels, controls | |
| `--rule` | `#D6CDB9` | Hairlines | |
| `--rule-strong` | `#857A66` | Control borders, chart rules | 3.98:1 on card, 3.33:1 on paper-2 (≥3:1, WCAG 1.4.11) |
| `--ink` | `#1B2333` | Text | 14.8:1 on card |
| `--ink-2` | `#4A5265` | Secondary text | 7.4:1 on card, 6.2:1 on paper-2 |
| `--navy` / `--navy-ink` / `--navy-ink-2` | `#16213A` / `#F4F0E6` / `#C3C9D6` | Masthead | 14.1:1 and 9.6:1 |
| `--accent` | `#2F55A4` | Primary button, selected row ring, selected tab, links, focus ring. The **only** interaction colour | 6.7:1 on card; white on accent 7.1:1 |
| `--accent-deep` | `#26468A` | Primary button hover | |
| `--evidence` | `#2F5D50` | Computed comparison values in reasons | 7.1:1 |

### Neutral warning
A neutral warning style, never a risk colour, is used for:
- PEP, sanctions and identity flags (`.tag-flag-strong`);
- "Rising ×N" and "New this month" (`.tag-rising`);
- form errors (`.form-error`) and AI "unverified numbers" (`.ask-warn`);
- the mock banner.

The style is ink text (`--warn-ink`) on `--warn-bg #EFE6D2` (12.7:1), with an authored SVG warning triangle drawn through `mask` in `currentColor`. This removes the old reuse of the High and Critical colours for non-risk signals.

### Risk bands: number + label + shape + treatment
Badge markup is unchanged (`.risk[data-band]` > `.risk-score`, `.risk-label`, `.risk-meter i.on`). The meter bars **rise** (5/7/9/12px), so the meter is a shape as well as a count.

| Band | Score | Meter | Fill / text | Contrast | Extra cue |
|---|---|---|---|---|---|
| Low | 0–39 | ▮▯▯▯ | soft `#DCEBE7` / `#155E57` | 6.16:1 | none |
| Medium | 40–69 | ▮▮▯▯ | soft `#F3E3BF` / `#7A4F00` | 5.62:1 | none |
| High | 70–89 | ▮▮▮▯ | soft `#F5DAD2` / `#9A2E1E` | 5.69:1 | 1px solid border in the text colour |
| **Critical** | 90–100 | ▮▮▮▮ | **solid oxblood `#6E1423` / white** | **11.75:1** | **inverted fill, 3px double frame, bold label** |

**Critical stands apart by treatment, not hue alone.** It is the only band with the 3px double frame, the fourth meter bar and a 700-weight label. The treatment depends on where the badge sits:

- **Case header (large badge):** solid oxblood `#6E1423` with white text (11.75:1), inverted against every other band.
- **Alert queue** (`/impeccable quieter`, follow-up pass): about 45% of alerts are Critical, so solid badges read as a wall. In the queue, Critical takes the soft fill `#F2D4D8` with oxblood text (8.50:1). Its **score sits on a small solid oxblood plate** (white on `#6E1423`, 11.75:1), which keeps a light/dark cue that survives greyscale. High has no plate, a single 1px frame and three bars.
- **Elsewhere** (network list, watchlist): the solid badge.

In the queue, Critical rows also get an oxblood hairline above and below (`tr:has(.risk[data-band="Critical"])`).

**One meaning per frame:** the 3px double frame belongs to Critical risk only. Status tags and stamps use a 2px solid frame (Escalated in ink or navy, In review in accent).

**Screen reader:** unchanged ("Risk score 97 out of 100, Critical").

**Not yet restyled:** the network graph circles and the Team-overview bars. Their colours are hard-coded in `app.js` (`BAND_FILL`, SVG attributes), so they still use the previous palette until that JS change is made.

### Confidence
The level is the word plus a shape-coded dot:

| Level | Dot | Text |
|---|---|---|
| High | filled | bold |
| Medium | half-filled | regular |
| Low | hollow | regular |

## 3. Typography

| Role | Face | Size / line | Selector |
|---|---|---|---|
| Brand "Sentinel" | Source Serif 4 700 | 22 / 28 | `.brand h1` |
| Case title (player ID) | Source Serif 4 600 | 26 / 32 (22 on phones) | `.player-head h2` |
| Large score numeral | Source Serif 4 600 | 32 | `.risk.large .risk-score` |
| Panel heading | Source Serif 4 600 | 19 / 24 | `.panel-head h2` |
| Section heading | Source Serif 4 600 | 17 / 22 | `.section h3` |
| Reason headline, Ask question, recommended action | Source Serif 4 600 | 16–17 | `.reason-title`, `.ask-q`, `.action-rec .what` |
| Body / UI | IBM Plex Sans 400–500 | 14 / 20 | `body` |
| Summary prose | IBM Plex Sans 400 | 15 / 23, max 72ch | `.summary-text` |
| Labels | IBM Plex Sans 600, uppercase, +0.04em | 12 / 16 | `.label`, filter labels, table heads |
| IDs, amounts, dates, scores | IBM Plex Mono 500, tabular | context size | `.mono`, `.num` |
| Mono tags (SYNTHETIC, status) | IBM Plex Mono 500, +0.08em | 11 | `.tag-synthetic`, `.tag-status` |

- **Font loading:** one Google Fonts `<link>` in `index.html` loads Plex Sans, Plex Mono and Source Serif 4.
- **Size floor:** nothing runs below 11px. 11px is used only for uppercase mono tags and the 11px profile labels.

## 4. Layout

```
┌───────────────────────────────────────────────────────────────────────────────┐
│ MASTHEAD (navy) Sentinel [SYNTHETIC DATA] window · ○ AI   Alert queue │ Team overview  [name]│
├──────────────────────────────┬────────────────────────────────────────────────┤
│ DOCKET (paper-2, own scroll) │ CASE FILE (card, own scroll)                   │
│ Alert queue        N of M    │ ┌ sticky case header ─────────────────────────┐│
│ [Search ID ( / )          ]  │ │ P01444 [SYNTHETIC]          ┌─────────────┐ ││
│ Band Team Type Status Conf Sort│ │ Alert … · AML · ╔NEW╗ stamp │97 CRITICAL ▮▮▮▮│ ││
│ [Ask the queue…][Find] ☐ WL  │ │ profile (inline label · value)└─────────────┘ ││
│ RISK  PLAYER  REASON TEAM STATUS│ └──────────────────────────────────────────────┘│
│ ▸ rows (selected = accent ring,│ Overview │ Evidence 14 │ Activity │ Network │ Ask AI │
│   open = card + ink marker)  │ … tab content (evidence thread, charts, tables) │
│ ↑↓ move · Enter open · …     │ ┌ action bar (paper, pinned) ──────────────────┐│
│                              │ │ RECOMMENDED ACTION · AML  serif action        ││
│                              │ │ [Accept recommendation] [Escalate] [Close…] […]││
└──────────────────────────────┴────────────────────────────────────────────────┘
```

| Breakpoint | Behaviour |
|---|---|
| > 1100px | The page is fixed to the viewport. Docket and case file scroll on their own. Columns are `minmax(500px, 4fr) / 5fr`. |
| ≤ 1560px | The "Player risk review" subtitle hides; "Sentinel" stays. |
| ≤ 1400px | The "Investigator" label text is drawn at zero size. It still names the input for screen readers, and the placeholder says what the field is for. Filters wrap to two rows of three. |
| Desktop (> 1100px wide) | Search shares the first filter row with Band and Team; the remaining filters form the second row. |
| **≥ 900px tall** | The case header and action bar stay pinned. The recommended-action sentence is set at 15/20 so the evidence keeps more room. |
| **< 900px tall** (`max-height: 899px`) | Nothing is pinned: the case header and action bar scroll with the case. On desktop, `#detail` becomes the scroller (`.detail-scroll` stops scrolling on its own), so the action bar sits at the foot of the case. Opening another alert resets the scroll, because the loading state is short. |
| ≤ 1100px (tablet) | One column. The docket is on top, with the table capped at 60vh. The case follows in page flow. On screens 900px tall or more, the case header sticks to the viewport top and the action bar to the bottom. |
| ≤ 760px | The case header and action bar stop sticking. Key facts drop to 2 columns, and Team overview drops to 1 column. |
| ≤ 560px (phone) | Queue rows become stacked records: badge, ID and status on top, then reason and tags, then team. The column headers are visually hidden; the "Sort by" menu sorts. Filters run two per row. Reasons stack their points under the text. |

**Sticky case header.** It keeps the identity, status stamp and score on screen while the tab content scrolls. `.detail-scroll` has `scroll-padding-top` so a keyboard-focused element never lands under it. Because a CSS-only change cannot pin the header and the tab strip together, the tab strip now scrolls with the content; it used to be sticky. Content order is unchanged (no CSS `order`), so the visual, keyboard and screen-reader order stay identical.

## 5. Components

| Component | Built treatment |
|---|---|
| Masthead | Navy band. Serif "Sentinel"; outlined mono SYNTHETIC tag. The AI status tag has a filled dot when on and a dashed outline with a hollow dot when offline. The view switch is underlined tabs. The investigator field is a light input. |
| Docket rows | No zebra striping. Hover is a translucent card. **Selected** (keyboard cursor) is the card colour plus a 1px accent ring. **Open** (the case on the right) is the card colour, a bold ID and an ink triangle marker drawn with `clip-path`. Top reason is clamped to 2 lines; anomaly tags wrap, so they stay readable rather than being cut. Team is small and secondary. Cell padding is 6px. |
| Status tag | Mono uppercase; the shape varies by status: New is a plain ink-2 outline, In review an accent outline, **Escalated a 2px solid ink frame**, Closed dashed. |
| **Status stamp** (case header) | The same status tag, rotated −3°. It "presses" in over 180ms when a case opens: Escalated has a 2px navy frame, In review a 2px accent frame, New a plain 1px frame, Closed a dashed frame. |
| **Evidence thread** (`ol.reasons`) | Unboxed rows on one vertical ruled thread with ink ring nodes. A *hollow* node marks a reason counted at half points because it overlaps a stronger one (`.reason:has(.points-note)`). Serif headline, mono "+N pts" on the right. The "Compared with" line sits directly under the evidence sentence (grid row 3), with the anomaly-type tag aligned beside it. Comparison values are in `--evidence`. |
| Key facts | A ledger strip: 4 columns, each with a top rule, a small label and a mono value. |
| AI case summary | A plain paper section (no side stripe) with an outlined mono "AI" mark beside the heading. The prose is 15/23 at a 72ch measure. The meta line still says which source wrote it. |
| Action bar | Paper-toned, pinned at the foot of the case, with tight padding. The label "Recommended action · team" is metadata in ink-2 uppercase, not an accent kicker. The action is in serif. Primary button in accent; the others are outlined. An open Close or Assign button shows as pressed. |
| Ask AI | Suggestion chips are real-looking buttons (outlined, accent hover). Q&A entries are separated by rules; the question is in serif. |
| Tables | Uppercase 12px heads on paper-2 with a strong rule. Flagged transactions get a faint warning tint plus their flag tags. There is no side stripe and no risk colour. |
| Team overview | Panels are paper sheets with a single 1px border. Headings are serif. Bars are ink. Trend tags use the neutral warning style. |
| Browser surfaces | Text selection is accent; caret is accent; thin scrollbars use the rule-strong colour; focus rings are a 2px accent ring (navy-ink on the masthead); checkbox `accent-color`. |

## 6. Motion

| Motion | Duration | Easing |
|---|---|---|
| Case "re-ink" on open (`.detail-body`: fade plus 4px rise) | 200ms | `cubic-bezier(.16, 1, .3, 1)` |
| Status stamp press | 180ms | same |
| Hover and colour changes | 140ms | ease-out |

All motion is under 300ms. Everything is switched off under `prefers-reduced-motion: reduce`.

## 7. Impeccable passes and known limits

| Pass | Command | Result |
|---|---|---|
| First build | `/impeccable craft` (alias for new-work; the direction was pinned by the brief) | Case File restyle, CSS-only |
| First closing critique | `/impeccable critique` | 28/40. Applied: evidence-thread grid gap, scroll padding, leaner bars, kicker colour, flagged-row stripe removed |
| Follow-up | `/impeccable quieter` | Critical badge in the queue only: soft fill, solid score plate, double frame and fourth bar kept |
| Follow-up | Pinning change | Case header and action bar pinned only on screens ≥ 900px tall |
| Follow-up | `/impeccable polish` | Sort select width; masthead divider tokenised; misplaced comment and duplicate or dead rules removed (`.reason-compare` merged, redundant `.tag-synthetic` sizes, dead `top`/`flex-basis` overrides) |
| Follow-up | `/impeccable critique` | **30/40.** Detector: 9 findings, all known false positives |

Changes applied from the follow-up critique (all CSS-only and low risk):
- filters in two rows on desktop;
- `:where()` around the `:has(#f-sort)` and `:has(#f-type)` rules, so the responsive filter rules still apply;
- the score plate on queue Critical badges;
- status stamps moved from the double frame to a 2px solid frame;
- a smaller action sentence on tall screens.

Known limits (not fixed; for the team):
- **Queue density.** At 1440×900 about 5–6 alerts are visible, because the reason and its anomaly tags share one narrow column. Cutting the tags to one line was tried and rejected: at 1280 they shrank to "S…" and "Inc…". Showing one tag plus "+N more" needs JS, since CSS hiding would make the JS-generated count wrong.
- **Tablet, ≥ 900px tall.** The sticky action bar appears at the bottom of the screen as soon as the case file scrolls into view, before its header. It was kept because the brief keeps pinning on tall screens. **Team decision:** make it static on tablets too, or keep it.
- **Below 900px tall (unpinned).** The score and decision buttons scroll away while reading evidence; the `D` shortcut still jumps to the decision buttons. Pinning a compact action bar there is possible in CSS but would hide the rationale line. **Team decision.**
- **Oxblood row hairlines** under Critical rows repeat on almost every row of a Critical-heavy queue and add colour without information. They were kept because they were part of the agreed first pass. **Team decision.**
- **Native select chevrons** are still browser-default.
- **Phone:** the queue is a 60vh scroll box inside the page, and the decision buttons sit at the end of a long case. A proper master/detail flow needs JS (scroll to the case on open, plus a back link).
- **"Recommended action · team"** still sits above its heading like a kicker. The real fix is a markup change.

## 8. Not built in this pass (need JS changes; for the team)

- ~~**Night shift**~~: built on `frontend-chat` as a light/dark theme; see §10.
- **Network graph circles and Team-overview band bars** in the four-band palette. *Update:* they are now CSS tokens (`--net-*`, `--chart-*`) with the previous Day values, so this is a token change only.
- **Overview tab reorder** (strongest reasons before key facts). This was skipped on purpose because CSS `order` would split visual order from keyboard and screen-reader order.
- **The rest:** see the "needs JS change" list in [PROMPTS.md](PROMPTS.md) under "Frontend restyle", and FRONTEND_OUTLINE.md §6 ranks 11–19.

## 9. Chat panel (branch `frontend-chat`)

> Built 2026-10-15 on `frontend-chat`, stacked on `frontend-polish`. Plan: [CHAT_PANEL_PLAN.md](CHAT_PANEL_PLAN.md). Frontend design and decisions: [CHAT_FRONTEND_OUTLINE.md](CHAT_FRONTEND_OUTLINE.md). Contract: [CHAT_CONTRACT.md](CHAT_CONTRACT.md). Start here: [CHAT_HANDOFF.md](CHAT_HANDOFF.md). This pass changes `app.js` as well as the markup and CSS.

**Direction.** A marginal notebook beside the dossier, inside the Case File world: paper ground, serif questions, ruled entries, mono provenance lines, a mono "Now viewing" rule, and the same outlined mono `AI` tag as the case summary. No bubbles, avatars, gradients or sparkle. The accent stays the single interaction colour; unverified numbers and unknown IDs use the neutral warning style.

### Layout

| Width | Behaviour |
|---|---|
| > 1100px | Two columns: work area `minmax(0, 1fr)` + assistant `max(360px, 35%)`. Collapsible to a 44px rail with a vertical "Assistant" label (`.shell:has(> .chat[data-collapsed="true"])`). The collapsed state is remembered per viewer (localStorage). |
| ≤ 1100px | The assistant is a fixed navy bar at the foot of the screen showing the context; expanded, an overlay from the right (440px) over a navy scrim, with the work area `inert`. The pinned action bar on tall tablets sits above the bar (`bottom: var(--chat-bar-h)`). |
| ≤ 560px | The overlay is full screen; the keyboard hint is hidden. |

The work area shows one view at a time. **Mode 1:** the view switch "Alert queue | Team overview" (moved from the masthead, now ink on paper with an accent underline) above the docket or the overview. **Mode 2:** a paper-2 strip "Back to queue · ALR · P · n of N · Previous / Next · Esc back · D decide" above the case file. The old queue + case side-by-side layout (`.layout`) is gone, and so is the tablet 60vh queue box.

### Components

| Component | Treatment |
|---|---|
| Panel header | Serif "Assistant" + mono `AI` tag; New chat (small outlined); collapse chevron (authored SVG, no glyph). |
| Question | Serif 15/22 600; a hidden "You asked:" prefix for screen readers. |
| Answer | Plex Sans 14/21, 62ch; real lists with mono markers; IDs as mono accent links, unknown IDs as plain mono. |
| Assumption | "ASSUMPTION" label + ink-2 sentence above the answer. |
| Actions | Small outlined buttons, labels written by the frontend. |
| Warnings | Neutral warning lines (unverified numbers, unknown IDs) always visible under the answer. |
| Footer row | A grid: a native **Details** disclosure on the left (collapsed by default; 24px target; screen readers hear "Details: source, number check and cases used") holding the mono provider line ("Groq gpt-oss-20b", "Ollama llama3.2 · local · fallback", "Built-in stub · not an AI model") + "Numbers checked" and "Cases used" (only when it adds IDs the answer does not already link); **Pin to case** on the right, which stays on the top row when Details opens. |
| New-answer badge | While collapsed: an accent count pill on the desktop rail, a navy-ink pill on the narrow bottom bar (7.10:1 and 14.06:1); the count is in the bar's accessible name and announced through `#chat-live` (outside the collapsible body); cleared on open. |
| Divider | Mono uppercase 11px between two rule-strong hairlines. |
| Notice | Card with a rule-strong border, ink-2 text; never a risk colour. |
| Composer | Paper-2 band: "CONTEXT" label + chip text, labelled textarea, keyboard hint (Enter send · Shift Enter new line · Esc collapse · Ctrl K open; each pair kept on one line), Send as an **outlined** button so the only solid accent button in Mode 2 is Accept recommendation. |
| AI notes in history | "AI note" mono tag, question in 600, answer pre-wrapped, provider line, Remove. |
| Icons | One authored 16px chevron path, 1.7 stroke, `currentColor`. |

**Motion:** answers re-ink (200ms), overlay slides 24px (200ms), both `cubic-bezier(.16, 1, .3, 1)`; off under `prefers-reduced-motion`.

**Contrast (Assessment B):** every chat text pair passes AA: ink 12.4–14.8, ink-2 6.2–7.4, accent links 5.6–6.7, navy-ink-2 on navy 9.63.

### Impeccable passes

| Pass | Result |
|---|---|
| `/impeccable shape` | Brief and wireframes in CHAT_FRONTEND_OUTLINE.md §3–4. The question round was skipped as instructed; defaults recorded under "Decisions taken". |
| `/impeccable craft` (alias for new-work) | Shell, router, chat panel. |
| `/impeccable critique` | Dual-agent (design review + detector). **26/40.** Detector: 16 CLI findings, all false positives or intended (13 `<kbd>` bevels, 1 contrast misread of a `color-mix` ground, 1 table hairline, 1 cream palette); the in-browser detector found only the intended cream palette. Narrow ignores recorded in `.impeccable/config.json` with reasons. |
| Low-risk fixes applied | Masthead status says "chat: built-in stub" in stub mode; Send made secondary; hidden "You asked:" prefix; warnings included in the aria-live announcement; "Cases used" de-duplicated; warning list spacing ("48,000, 6"). |
| `/impeccable polish` | Dead `.ask-warn` rules removed, Send states aligned with `.btn`. |
| Additions (round 2) | Details disclosure; new-answer badge; **Esc inside the assistant collapses it** at every width (Ctrl+K reopens; no clash with arrows, Enter, `/`, `D`, or Esc in search / the case file / Mode 2 outside the chat). |
| `/impeccable critique` round 2 | Dual-agent. **29/40** (from 26). CLI detector clean with the recorded ignores (without them: the same four suppressed rules only, 18 hits, 15 of them `<kbd>` bevels); browser detector: only the accepted cream palette plus two line-length notes on existing case-file text. |
| Round-2 low-risk fixes + `/impeccable polish` | 24px targets for Details and Pin; Pin no longer jumps when Details opens (footer grid); log scroll padding; Esc ignores IME composition. **Page-height bug fixed:** screen-reader-only spans inside scroll boxes (the chat log, and the queue's existing "+N more" text) had no positioned ancestor and stretched the document to 13,645px on the desktop queue (hidden by `overflow: hidden`, but `scrollIntoView` could shift the masthead). `.chat-log`, `.table-wrap`, `.detail-scroll` and `.overview` are now `position: relative`; a page-height check was added to both suites. |

### Not done (for the team)

- **New chat has no confirmation and no undo — deliberate.** Plan §4: New chat clears straight away; Pin to case already saves what matters. Not a gap.
- **"Numbers checked" is behind Details.** Round-2 review suggests a quiet visible "Numbers checked" next to the warnings, so a clean answer differs from an unchecked one. Moving it into Details was an explicit instruction; **team decision**.
- **The badge does not say which alert the unread answer is about** (e.g. "1 new answer, about ALR-00099"). Needs JS.
- **Error notices count as "new answers"** in the badge; "message" would be more exact. Needs a small JS wording change.
- **No keyboard jump** from the input to the latest answer's Details or Pin (Tab order works, but it walks the whole log).
- **Empty state has no example questions** (left out because the plan bars the assistant from suggesting questions; static examples would be a team call).
- **`aria-pressed` vs `aria-current`** on the view switch (kept as before).
- **The view is not restored after a refresh** (the conversation is).
- **Existing case-file text measure** (browser detector): `.reason-detail` runs to about 113 characters at 1440 and the case summary to about 97 (its `72ch` cap counts "0" widths). Outside the chat; left for the restyle owner.

## 10. Light / dark theme (branch `frontend-chat`)

> Built 2026-10-15. Implements the "Night shift" plan in FRONTEND_OUTLINE.md §4.1 and §4.5.

- **How it switches:** with no saved choice the page follows the system setting (`prefers-color-scheme`). The masthead button (sun/moon icon + "Light"/"Dark", `aria-pressed`, screen readers hear "Dark theme: …") saves an explicit choice in localStorage (`olg.theme`), which wins over the system. A tiny inline script in `<head>` applies a saved choice before first paint, so there is no flash. Storage failures are caught; the theme then simply follows the system.
- **Tokens:** dark overrides live in `@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) }` and `:root[data-theme="dark"]`, using the §4.1 Night values (paper `#10151F`, card `#18202E`, ink `#ECE6D8`, ink-2 `#A9B1C0`, accent `#8EB0F2` with dark text on it, rule-strong `#6B7890`) and the §4.2 Night band colours. Critical keeps its distinct treatment (solid inverted pink `#F4A3B0` with dark text, double frame, fourth bar).
- **Charts:** the hard-coded hex values in `app.js` (peer chart, timeline, sparkline, network graph) were replaced by `style="fill:var(--…)"` tokens (`--chart-ink`, `--chart-mid`, `--chart-faint`, `--chart-band`, `--chart-marker`, `--chart-shade`, `--net-<band>` and `--net-<band>-ink`). Day values are the previous hex values; only the white fills (baseline marker, network label plate) now use `--card`. The network focus ring uses `!important` because inline token styles outrank stylesheet rules.
- **Also fixed:** with an empty conversation the composer now stays at the bottom of the assistant panel (`.chat-empty { flex: 1 }`).
- **Checked:** headless Edge, 11 theme checks (system default, toggle, persistence, explicit light over system dark, chart and timeline colours following the theme, network tokens), plus the full suites in light (regression 48/48, chat 66/66, live 3/3, mock 6/6). Screenshots of the queue, alert, evidence, activity, network, overview and phone chat in dark.
- **Not verified:** a full contrast audit of every dark pair (the token values come from the §4.1/§4.2 table, which lists their ratios), real devices, Windows high-contrast mode.
