---
name: Sentinel
description: Case-file review dashboard for sports-betting AML, Fraud and Safer Gambling investigators.
colors:
  paper: "#F4F0E6"
  paper-2: "#EAE4D5"
  card: "#FBF8F1"
  rule: "#D6CDB9"
  rule-strong: "#B9AE95"
  ink: "#1B2333"
  ink-2: "#4A5265"
  navy: "#16213A"
  navy-ink: "#F4F0E6"
  accent: "#2F55A4"
  accent-soft: "#E1E7F3"
  low: "#1F7A72"
  low-soft: "#DCEBE7"
  low-ink: "#155E57"
  medium: "#C98D1C"
  medium-soft: "#F3E3BF"
  medium-ink: "#7A4F00"
  high: "#B23A27"
  high-soft: "#F5DAD2"
  high-ink: "#9A2E1E"
  night-paper: "#10151F"
  night-card: "#18202E"
  night-ink: "#ECE6D8"
  night-ink-2: "#A9B1C0"
  night-accent: "#8EB0F2"
  night-low: "#5CC3B5"
  night-medium: "#E4B04F"
  night-high: "#F08A74"
typography:
  display-numeral:
    fontFamily: "Source Serif 4, Georgia, serif"
    fontSize: "48px"
    fontWeight: 600
    lineHeight: 1
    letterSpacing: "-0.03em"
  case-title:
    fontFamily: "Source Serif 4, Georgia, serif"
    fontSize: "30px"
    fontWeight: 600
    lineHeight: "36px"
    letterSpacing: "-0.02em"
  section-heading:
    fontFamily: "Source Serif 4, Georgia, serif"
    fontSize: "19px"
    fontWeight: 600
    lineHeight: "24px"
    letterSpacing: "-0.01em"
  body:
    fontFamily: "IBM Plex Sans, system-ui, sans-serif"
    fontSize: "14px"
    fontWeight: 400
    lineHeight: "20px"
  label:
    fontFamily: "IBM Plex Sans, system-ui, sans-serif"
    fontSize: "11px"
    fontWeight: 600
    letterSpacing: "0.05em"
  figure:
    fontFamily: "IBM Plex Mono, ui-monospace, monospace"
    fontSize: "13px"
    fontWeight: 500
rounded:
  sm: "2px"
  md: "4px"
spacing:
  s-1: "4px"
  s-2: "8px"
  s-3: "12px"
  s-4: "16px"
  s-5: "24px"
  s-6: "32px"
  s-7: "48px"
components:
  button-primary:
    backgroundColor: "{colors.accent}"
    textColor: "#FFFFFF"
    rounded: "{rounded.md}"
    height: "36px"
    padding: "0 16px"
  button-secondary:
    backgroundColor: "{colors.card}"
    textColor: "{colors.ink}"
    rounded: "{rounded.md}"
    height: "36px"
    padding: "0 16px"
  badge-high:
    backgroundColor: "{colors.high-soft}"
    textColor: "{colors.high-ink}"
    rounded: "{rounded.md}"
    height: "24px"
  badge-medium:
    backgroundColor: "{colors.medium-soft}"
    textColor: "{colors.medium-ink}"
    rounded: "{rounded.md}"
    height: "24px"
  badge-low:
    backgroundColor: "{colors.low-soft}"
    textColor: "{colors.low-ink}"
    rounded: "{rounded.md}"
    height: "24px"
  sheet:
    backgroundColor: "{colors.card}"
    rounded: "{rounded.md}"
    padding: "24px"
  masthead:
    backgroundColor: "{colors.navy}"
    textColor: "{colors.navy-ink}"
    height: "60px"
---

# Design System: Sentinel

> **Source of truth:** this file describes what is **actually built** in `frontend/mock_frontend.html`, the static design mock (updated 2026-10-15 after an `/impeccable critique` pass).
> - **Live dashboard:** the real one will be a separate `frontend/index.html` (build step 6). It should reuse these tokens and components.
> - **Regenerate:** once that live frontend exists, regenerate this file from the real code with `/impeccable document`.
> - **Precedence:** product context lives in [PRODUCT.md](PRODUCT.md), and wins on any conflict.
> - **Draft placeholder:** "Sentinel" is a neutral placeholder name. The mock deliberately uses no real OLG, Ontario or Canada branding.

## Overview

**A case file, not a casino.** The investigator reads a dossier the way they would read a paper case file:
- **Docket and case file:** a ranked docket of alerts sits on the left, and one open case file on the right.
- **Score and stamp:** the case file has a big serif score and an inked status stamp.
- **Evidence thread:** the evidence is laid out as a thread whose points add up exactly to the score.

The tone is calm, serious and evidence-first. Warm paper surfaces with a faint grain, ink-navy masthead and ink text. Colour is reserved for risk, and one slate-blue accent marks the interactive things.

**Signature moment:** selecting a case re-inks the dossier. The score counts up and the ring fills in about 260ms.

**Two themes:**
- **Day** (default) is warm paper.
- **Night shift** is a separately designed dark theme, not an inversion: deep blue-black paper, warm off-white ink, and risk colours re-tuned for dark ground.

## Colors

All colours are CSS custom properties on `:root`. Night shift overrides them under `:root[data-theme="night"]`.

### Primary
- **Accent `#2F55A4`** (night `#8EB0F2`): the only UI accent. Use it for the primary button, the selected queue row border, focus rings, the team label and the text-selection highlight. Never use it for risk.

### Neutral
| Token | Day | Night | Role |
|---|---|---|---|
| `--paper` | `#F4F0E6` | `#10151F` | Page ground, reason cards |
| `--paper-2` | `#EAE4D5` | `#0C1018` | Queue column (sunk) |
| `--card` | `#FBF8F1` | `#18202E` | Dossier sheets (with grain) |
| `--rule` / `--rule-strong` | `#D6CDB9` / `#B9AE95` | `#2A3446` / `#3B475C` | Borders, dividers, control outlines |
| `--ink` | `#1B2333` | `#ECE6D8` | Primary text |
| `--ink-2` | `#4A5265` | `#A9B1C0` | Secondary text (≥ 6.1:1 in both themes) |
| `--navy` | `#16213A` | `#0A0E16` | Masthead |

### Risk (only ever used for risk)
| Band | Score | Solid | Soft fill | Ink (text) | Night solid |
|---|---|---|---|---|---|
| Low | 0–39 | `#1F7A72` teal | `#DCEBE7` | `#155E57` | `#5CC3B5` |
| Medium | 40–69 | `#C98D1C` amber | `#F3E3BF` | `#7A4F00` | `#E4B04F` |
| High | 70–100 | `#B23A27` coral-red | `#F5DAD2` | `#9A2E1E` | `#F08A74` |

Three bands, as set by the dashboard brief. Cut-offs are a draft until validation (WORKFLOW step 4).

### Named rules
- **Colour is never alone.** Every risk colour comes with a number, a text label and a bar-count shape.
- **Measured contrast:** every text pair measured AA in both themes, at both 1280px and 390px. The lowest was the badge text at 5.6:1.

## Typography

| Role | Face | Size / line | Weight |
|---|---|---|---|
| Score numeral (ring) | Source Serif 4 | 48px / 1 | 600, −0.03em |
| Case title | Source Serif 4 | 30px / 36px | 600 |
| Brand name | Source Serif 4 | 22px / 28px | 700 |
| Sheet heading | Source Serif 4 | 19px / 24px | 600 |
| Reason headline | Source Serif 4 | 16px / 22px | 600 |
| Body / UI | IBM Plex Sans | 14px / 20px | 400–500 |
| Secondary text | IBM Plex Sans | 13px | 400 |
| Labels (uppercase) | IBM Plex Sans | 11–12px | 600, +0.04–0.05em |
| IDs, scores, points, figures | IBM Plex Mono | 12–18px | 500 |

- Fonts load from Google Fonts. Fallbacks: Georgia, system-ui and ui-monospace.
- All text uses `tabular-nums`.
- Money is formatted `$14,850` (en-CA).
- The smallest text is 11px: uppercase labels and chart axes.

## Layout

```
┌──────────────────────────────────────────────────────────────────────────┐
│ Masthead (navy): mark · Sentinel · SYNTHETIC tag · ● Monitoring · Night   │
├──────────────────────────────────────────────────────────────────────────┤
│ Ribbon: "8 open alerts" · [3 HIGH] [3 MEDIUM] [2 LOW] · proportion bar   │
├──────────────────────┬───────────────────────────────────────────────────┤
│ ALERT QUEUE          │ DOSSIER (max 1040px, scrolls on its own)          │
│ 360–420px, scrolls   │ case header: case no · Player ID · stamp · 3 btns │
│ search + 3 filters   │ [Risk score ring] [Recommended action + buttons]  │
│ ranked rows          │ Why flagged (evidence thread)                     │
│                      │ Compared with peers (log strip plot)              │
│                      │ [30-day activity] [Locations]                     │
│                      │ Linked players                                    │
└──────────────────────┴───────────────────────────────────────────────────┘
```

- **≥ 901px:** the page is fixed to the viewport, and the queue and dossier scroll independently.
- **≤ 1180px:** the dossier's two-column rows stack.
- **≤ 900px:** single column. The queue sits on top (max 420px tall, scrolls), with the dossier below. Tapping a row scrolls the page to the dossier.
- **≤ 560px:** the brand subtitle and scan time hide, and buttons wrap to full width. No horizontal overflow at 390px.
- **Spacing:** a 4px scale (`--s-1` 4px … `--s-7` 48px). Sheet padding is 24px (16px on mobile), and the gap between sheets is 16px.

## Elevation & Depth

Depth comes from tone and hairlines, not shadows.
- **Sheets:** 1px `--rule` border on `--card`, with a faint SVG paper-grain texture (`--grain`). The grain is quieter in night mode.
- **Reason cards:** sit on `--paper` inside the sheet, a darker inset.
- **Shadow:** only the **selected queue row** has one (`0 1px 2px` + `0 4px 14px`, at 6% ink).

## Shapes

- **Radius:** 4px on controls, badges and sheets; 2px on tags; 50% on avatars and the ring. No pills.
- **Rubber stamp:** 3px double border, rotated −3°.
- **Meter:** 4 rising bars of 5/7/9/12px.

## Components

### Masthead
Navy bar containing:
- **Mark:** a framed eye with a teal slit, drawn as original SVG.
- **Name:** "Sentinel" in serif.
- **Subtitle:** "Sports betting · Case review".
- **Tag:** an outlined `SYNTHETIC DATA · STATIC MOCK` tag in mono.
- **Monitoring indicator:** a teal dot whose ring expands in about 290ms every 2.4s, plus the last-scan time.
- **Night shift toggle:** a `role="switch"` button.

### Band ribbon
- **Total:** "N open alerts".
- **Band counts:** one box per band with a serif count and a coloured uppercase label.
- **Proportion bar:** one 8px bar split by band.
- **Placeholder note:** "Filters, search and case buttons are placeholders in this mock."

### Alert queue row
A full-width `<button>`, ranked by score. It contains:
- **Avatar:** initials in a circle.
- **ID and status:** player ID in mono, plus an outlined status tag.
- **Reason:** the top reason headline on one line, cut off with an ellipsis.
- **Risk badge:** at the right.
- **Heat strip:** a 30-day strip with one cell per day; darker means more wagered.

States:
- **Hover:** card background.
- **Selected (`aria-current="true"`):** card background, 1px accent border, soft shadow and an accent-tinted avatar.

### Risk badge
Always three parts: **score (mono) + band label (uppercase) + 4-bar meter**. Screen-reader label: "Risk score 91 out of 100, High".

The meter is driven by the **band, not the raw score**:

| Band | Bars filled |
|---|---|
| Low | 1 |
| Medium | 2 |
| High | 3 |
| High, score 90 or more | 4 |

### Status stamp
Double-bordered, rotated, mono uppercase. Colour by status (text is always present):

| Status | Colour |
|---|---|
| Escalated | high-ink |
| In review | accent |
| Awaiting info | medium-ink |
| New | ink-2 |

### Case header
- **Top line:** case number (`Case SNT-2026-10482`, mono).
- **Title:** "Player P-10482", serif 30px, `tabindex=-1`. Focus moves here when a row is clicked.
- **Stamp:** the status stamp sits beside the title.
- **Meta line:** age, occupation, income band, province.
- **Buttons:** **Escalate**, **Request info** and **Dismiss** at the right, all in secondary weight (Dismiss is quiet and underlined). None of them is the primary action. Placeholders in the mock.

### Risk score sheet
- **Ring:** 132px with a 10px stroke in the band colour. It fills over 280ms while the serif numeral counts up over 260ms.
- **Band text:** "High risk" in serif, in the band's ink colour.
- **Meter:** a large meter and "91 out of 100".
- **Tags:** neutral outlined anomaly-type tags.

### Recommended action sheet
- **Action:** heading "Recommended action", then the action in serif 22px.
- **Team:** "AML TEAM" in uppercase accent.
- **Rationale:** the reason for the recommendation.
- **The page's one primary button:** it is labelled with the recommended action itself (e.g. "Request source of funds", "No action — keep monitoring"). Next to it is a quiet "Override with reason" button.
- **Footnote:** "A recommendation, not a decision…".

### Evidence thread ("Why flagged")
- **Order:** reasons are ordered by points, highest first, on a vertical 1px thread with ring nodes.
- **Each reason card:**
  - an uppercase type label,
  - a serif headline,
  - an evidence sentence with real figures,
  - "+36 points" in mono, with a bar relative to the strongest reason.
- **Sum line:** "4 reasons · points total 91 = risk score 91".

### Peer strip plot ("Compared with peers")
- **Plot:** inline SVG on a log scale from $100 to $30k. A shaded band runs up to the peer 90th percentile, with a solid tick at the peer median, a dashed tick at p90, and the player as a labelled ink diamond.
- **Below the plot:** a legend, plus mono ratios ("47.9× the peer median").
- **Rendering:** charts are drawn at their measured pixel width, so labels stay 11px at every size.

### 30-day activity chart
- **Bars:** 30 daily bars of amount wagered. The last 7 days are solid ink and earlier days 55% ink.
- **Baseline:** a dashed accent line at the first-half daily average.
- **Axes:** gridlines at 0, half and max, and date labels Sep 15 / Sep 30 / Oct 14.

### Locations
- **Each row:** region, mono count and a bar.
- **Flag:** "In province" (ink-2) or "Outside province" (high-ink, with a coral bar).

### Linked players
- **Each row:** avatar, ID, how they are linked (shared device or card) and the linked player's badge.
- **Empty state:** "No linked players found. Shared devices, payment methods and addresses were checked."

### Placeholders (visual only in the mock)
Search field, Band/Type/Status filter chips, and all case and decision buttons.

## Motion

| Motion | Duration | Easing |
|---|---|---|
| Score count-up | 260ms | ease-out cubic |
| Ring fill | 280ms | `cubic-bezier(.16,1,.3,1)` |
| Toggle thumb | 200ms | same curve |
| Row and button hover | 140ms | ease-out |
| Monitoring pulse (expansion phase of a 2.4s loop) | ~290ms | same curve |

Under `prefers-reduced-motion: reduce`, every transition and animation is switched off and the final state is shown immediately.

## Do's and Don'ts

### Do:
- Show risk as number + label + meter, every time.
- Tie every score to reasons whose points add up to it.
- Label every demo screen as synthetic.
- Make the recommended action the primary button. Keep enforcement actions (Escalate, Dismiss) secondary.
- Open each case at its header.

### Don't:
- Use risk colours for decoration, or the accent for risk.
- Use casino motifs (gold, neon, chips), AI-dashboard gradients, glass, glows or KPI tile walls.
- Use real OLG, Ontario or Canada branding or logos.
- Add motion longer than 300ms, or any motion that ignores reduced-motion.

## Known gaps (from the 2026-10-15 critique, not yet fixed)

1. **Queue throughput.**
   - No arrow-key or shortcut navigation, though PRODUCT.md asks for keyboard navigation.
   - Rows show no alert age or assigned team.
   - The heat strip has no label.
2. **Evidence cards are nested.** The cards sit inside the bordered sheet, which the detector flags as "card inside card". Consider unboxed rows separated by rules.
3. **The score sheet repeats itself.** It states the score four ways and pushes "Why flagged" partly below the fold at 1440×900.
4. **Night shift masthead blends in.** It barely separates from the ribbon.
5. **Linked players are plain text.** They are not clickable through to their case.
6. **Safer Gambling context is missing.** Cases have no prior-interventions or limits history, which SG cases need.
