---
version: 1
slug: "frontend-mock-frontend-html"
primary_target: "frontend/mock_frontend.html"
related_targets: []
---

# Surface: investigator dashboard — static mock

Mode: Operate. Static mock (single self-contained HTML) to show the final look and the data the backend must supply. Only interactions: Night shift theme toggle, queue-row click swaps dossier. Filters, search, decision buttons are visual placeholders. Data: 8 fictional, synthetic players.

Audience/job: OLG AML, Fraud and Safer Gambling investigators triaging a ranked queue; must answer "worth my time / why flagged / what next" on one screen.

## Direction contract

THESIS: The alert is a case file being read, not a KPI wall. Refuses the card-grid analytics dashboard: one ranked docket on the left, one open dossier on the right, evidence laid out as a thread whose points sum to the score.

OWN-WORLD: Warm paper surfaces with faint grain, ink-navy header, Source Serif 4 for headings and large numerals, Plex Sans UI, Plex Mono for IDs/figures. Teal/amber/coral-red only for risk; one slate-blue UI accent. Status shown as an inked rubber stamp. Risk badge = number + label + 4 rising bars.

STORY: Investigator sees how many cases at each band, picks the top case, reads the score, the evidence thread, the peer and history comparison, linked players, then the recommended action.

FIRST VIEWPORT: Navy header with mark, monitoring pulse, Night shift switch; band-count ribbon. Left 400px docket with 8 rows; right dossier: case header with stamp and three actions, score ring beside recommended action, evidence thread starting above the fold.

FORM: Two-pane docket + dossier (case-file reader), code-led. seed: none (unavailable)

SIGNATURE: selecting a row re-inks the dossier — score counts up and the ring fills in under 300 ms; reduced-motion shows the final state.
