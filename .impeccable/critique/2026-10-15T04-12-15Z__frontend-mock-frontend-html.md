---
target: dashboard mock
total_score: 22
max_score: 36
na_heuristics: 9
p0_count: 0
p1_count: 2
target_identity: "file:C:\\Users\\lynbo\\Documents\\OLG-AntiMoney-Laundering\\frontend\\mock_frontend.html"
target_fingerprint: "sha256:85735c3bd67802338a48e702f8d1a225e083e120034babb2a75e76fc702397d8"
target_path: "C:\\Users\\lynbo\\Documents\\OLG-AntiMoney-Laundering\\frontend\\mock_frontend.html"
timestamp: 2026-10-15T04-12-15Z
slug: frontend-mock-frontend-html
---
Method: dual-agent (A: design review · B: detector + browser evidence)

## Design Health Score (pre-fix): 22/36 (heuristic 9 n/a: static mock has no input/error paths) — Acceptable
| # | Heuristic | Score | Key issue |
|---|---|---|---|
| 1 | Visibility of system status | 3 | Switching rows kept old scroll position; no alert age |
| 2 | Match system / real world | 3 | Escalate primary on already-escalated case |
| 3 | User control and freedom | 2 | "Override with a reason" promised, no surface |
| 4 | Consistency and standards | 2 | Meter filled by score, disagreed with band label |
| 5 | Error prevention | 2 | Enforcement button was default emphasis on SG / no-action cases |
| 6 | Recognition rather than recall | 3 | Heat strip unlabeled |
| 7 | Flexibility and efficiency | 1 | No keyboard queue navigation |
| 8 | Aesthetic and minimalist | 3 | Score stated 4–5 ways; heat-strip noise |
| 9 | Error recovery | n/a | Static mock |
| 10 | Help and documentation | 3 | Charts self-explain; meter/strip don't |

## Design specificity
Authored for the product: docket + case file, inked stamp, evidence thread that sums to the score, log peer strip. Drifts generic below the thread (uniform card grid, half-empty Locations, stock initials avatars). Detector: cream-palette x1 (brief-pinned), nested-cards x4 (reason cards in sheet; valid, low severity). Contrast AA everywhere, lowest 5.6:1; no 390px overflow.

## Priority issues
1. [P1] Row switch kept dossier scroll; new case opened mid-evidence. FIXED (scroll to top, focus title, scroll into view on mobile).
2. [P1] Decision buttons not tied to recommendation; Escalate always primary. FIXED (header buttons equal weight; recommendation sheet owns primary button named after the action + Override with reason).
3. [P2] Meter contradicted band (47 Medium = 2 bars = 32 Low). FIXED (band-driven 1/2/3, 4th bar at 90+).
4. [P2] Queue not built for throughput: no arrow/shortcut nav, no alert age/team, unlabeled heat strip. OPEN (shortcuts out of mock scope).
5. [P3] Score sheet redundant; Why flagged partly below fold; uniform card grid below. OPEN.

## Persona red flags
- AML investigator, 80th alert: landed mid-case on row switch (fixed); can't jump to linked player; no next/prev keys; no alert age.
- Screen-reader/keyboard user: whole dossier was aria-live (fixed: focus moves to case title); row accessible names verbose; queue is a nav landmark.
- Safer Gambling officer: enforcement vocabulary dominates; no prior-intervention / limits history.

## Minor
Peer band drawn from $100 floor not $0; night masthead blends with ribbon; ribbon counts look like buttons; two stacked serif headings in Recommended action; network reason type missing from anomaly tags.
