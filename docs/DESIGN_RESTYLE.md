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

- **Night shift:** tokens are planned in FRONTEND_OUTLINE.md §4.1. It is blocked until the chart and network colours in `app.js` use CSS variables.
- **Network graph circles and Team-overview band bars** in the four-band palette (`BAND_FILL` and SVG hex values in `app.js`).
- **Overview tab reorder** (strongest reasons before key facts). This was skipped on purpose because CSS `order` would split visual order from keyboard and screen-reader order.
- **The rest:** see the "needs JS change" list in [PROMPTS.md](PROMPTS.md) under "Frontend restyle", and FRONTEND_OUTLINE.md §6 ranks 11–19.
