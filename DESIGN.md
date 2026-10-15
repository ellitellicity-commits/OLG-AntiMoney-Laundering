# Design Direction — DRAFT

> **Pre-build draft.** Nothing is built yet. This file sets a starting direction so the dashboard can be built consistently. Once the frontend exists, regenerate this file from the real code with `/impeccable document`, which will replace this draft.
>
> Product context lives in [PRODUCT.md](PRODUCT.md). If the two conflict, PRODUCT.md wins.

## 1. Direction in one line

**A case file, not a casino.** It should feel like a well-kept regulatory ledger: quiet paper-white surfaces, dark ink text, one restrained institutional blue for interaction, and colour reserved for risk. Numbers are set in a monospaced face so investigators can compare them at a glance.

**Avoid:** casino gold, neon, chips or card motifs; purple/blue AI gradients; glassmorphism; glowing cards; big vanity KPI tiles; emoji; sparkle icons for AI features.

## 2. Colour palette (light theme, default)

| Token | Hex | Role |
|---|---|---|
| `--paper` | `#F6F5F1` | Page background (warm off-white, easy on the eyes over long sessions) |
| `--surface` | `#FFFFFF` | Panels, table rows, cards |
| `--surface-sunk` | `#EDECE7` | Table header, selected-row background, input wells |
| `--rule` | `#D5D3CC` | Borders, dividers, table lines |
| `--ink` | `#1A1D21` | Primary text |
| `--ink-muted` | `#545A62` | Secondary text, labels, timestamps (≈7:1 on white) |
| `--accent` | `#1F4E79` | Links, focus ring, primary buttons, selected state. The **only** interaction colour |
| `--accent-ink` | `#FFFFFF` | Text on `--accent` |
| `--focus` | `#1F4E79` | 2px focus outline + 2px offset |
| `--evidence` | `#2F5D50` | Optional marker for "computed evidence" values; never used for risk |

**Risk colours.** Used **only** for risk. Never decorative, never the only signal.

| Band | Score | Badge fill | Badge text | Secondary signal |
|---|---|---|---|---|
| Low | 0–39 | `#E4E6E9` | `#1A1D21` | 1 of 4 meter segments filled |
| Medium | 40–69 | `#E8B84A` | `#1A1D21` | 2 of 4 segments |
| High | 70–89 | `#B4500F` | `#FFFFFF` | 3 of 4 segments |
| Critical | 90–100 | `#8E1B1B` | `#FFFFFF` | 4 of 4 segments + bold label |

Band thresholds are **TBD**: these are a draft and will be tuned in the validation step.

All text/fill pairs above are intended to meet WCAG AA (4.5:1). Re-check them with a contrast tool once implemented.

**Dark theme:** TBD (not needed for the MVP demo).

## 3. Typography

| Use | Font | Size / line-height | Weight |
|---|---|---|---|
| Page title | IBM Plex Sans | 22px / 28px | 600 |
| Section heading | IBM Plex Sans | 16px / 22px | 600 |
| Body, table text | IBM Plex Sans | 14px / 20px | 400 |
| Labels, captions | IBM Plex Sans | 12px / 16px | 500, letter-spacing 0.02em |
| Scores, amounts, IDs, dates | IBM Plex Mono | same size as context | 500, `font-variant-numeric: tabular-nums` |

- Load from Google Fonts (`IBM Plex Sans` 400/500/600, `IBM Plex Mono` 500), with system-ui / ui-monospace as fallbacks.
- Currency is always CAD with explicit format: `$12,450.00`.
- Dates use ISO style in tables (`2026-03-14 21:07`) for unambiguous sorting.

## 4. Spacing scale

4px base. Use only these values:

`--s-1: 4px` · `--s-2: 8px` · `--s-3: 12px` · `--s-4: 16px` · `--s-5: 24px` · `--s-6: 32px` · `--s-7: 48px`

- Table row height: 40px (dense) / 48px (default).
- Panel padding: 16px. Gap between panels: 16px.
- Radius: 4px on controls and badges, 6px on panels. No pill-shaped cards.
- Shadows: none, or a single 1px border. Depth comes from `--rule` lines and `--surface-sunk`.

## 5. Risk badge system

A risk badge **always** contains three things:

```
[ 87  HIGH  ▮▮▮▯ ]
  │    │     └─ 4-segment meter (shape signal, readable without colour)
  │    └─ text label, uppercase, 12px/500
  └─ score 0–100, IBM Plex Mono, tabular
```

- Sizes: **compact** (in the queue table, 24px high) and **large** (player detail header, 40px high).
- Screen-reader text: "Risk score 87 out of 100, High."
- Never show a coloured dot or coloured row on its own without the badge.

## 6. Layout

Single-page desktop dashboard, minimum width 1280px for the demo. Mobile is not a goal.

```
┌───────────────────────────────────────────────────────────────────────┐
│ Header: product name · "SYNTHETIC DATA" tag · filters · search        │
├──────────────────────────┬────────────────────────────────────────────┤
│ ALERT QUEUE (≈40%)       │ PLAYER DETAIL PANEL (≈60%)                 │
│ ranked table             │ header: player ID, peer group, risk badge  │
│                          │ Why flagged (reason list)                  │
│                          │ Peer comparison chart                      │
│                          │ Activity timeline / transactions           │
│                          │ Linked players (stretch)                   │
│                          │ Recommended action + decision buttons      │
└──────────────────────────┴────────────────────────────────────────────┘
```

## 7. Components

### 7.1 Alert queue
- Table columns: **Risk badge** · **Player ID** · **Top reason** (one line) · **Team** (AML / Fraud / Safer Gambling) · **Anomaly types** (text tags) · **Last activity** · **Status** (New / In review / Escalated / Closed).
- Default sort: risk score, descending. Sortable by every column.
- Filters: band, team, anomaly type, status.
- Keyboard: ↑/↓ moves the selection, Enter opens the alert, `/` focuses search.
- Selected row: `--surface-sunk` background + 3px `--accent` left border.

### 7.2 Player detail panel
- Header: player ID, age band, occupation, income band, home region, peer group name, account age, large risk badge.
- All profile values come from synthetic data. Show the "SYNTHETIC" tag.

### 7.3 "Why flagged" list
- Ordered by contribution to the score.
- Each item has: **reason title** (plain English), **evidence line** (the actual numbers), **comparison** (vs own baseline and/or vs peer median), **contribution** (points added to the score), **anomaly type tag**.
- Example:
  > **Deposits far above declared income** — $18,400 deposited in 30 days; declared income band $40–60k/yr. Peer median: $620. **+28 pts** · Income mismatch
- If SHAP is used, its top features map onto these same reason items. Raw SHAP plots are not shown to investigators.
- Optional LLM summary sits **above** the list, labelled "Summary generated from the evidence below", and is never shown without the list.

### 7.4 Peer comparison chart
- Horizontal dot/strip plot per metric (e.g., 30-day deposits, average stake, bets per day, distinct locations).
- Show the peer-group distribution (median + interquartile band in grey), the player's own 90-day baseline (hollow marker) and the player's current value (solid marker in `--ink`).
- Value labels printed next to markers. No reliance on colour.
- Library: hand-built SVG or Chart.js (**TBD**).

### 7.5 Recommended action
- One primary recommendation with its rationale, e.g. "Request source of funds: deposits exceed income band by 30×."
- Buttons: **Accept recommendation** (primary, `--accent`), **Escalate**, **Close as explained** (requires a short reason), **Assign to team**.
- Decisions are written back to the API / Jube case.

### 7.6 Supporting components (MVP)
Filter bar, status tag, anomaly-type tag (text, neutral outline), "SYNTHETIC DATA" tag, empty state ("No alerts match these filters"), loading state (skeleton rows), and error state (plain message + retry).

### 7.7 Stretch components
Linked-players network view (node-link graph of shared devices/payment methods/addresses), activity timeline, case notes.

## 8. Motion

Minimal. 120–160ms ease-out for panel content changes and row selection. No decorative animation. Respect `prefers-reduced-motion`.
