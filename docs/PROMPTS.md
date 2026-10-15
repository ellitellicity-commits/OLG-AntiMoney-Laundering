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

### 1.1 — Build the whole MVP from the repo docs   (date: 2026-10-15 · author: TBD (the teammate who ran the session) · tool/model: Claude Code, claude-opus-5-5)

**Context to paste:**
Nothing pasted. The agent cloned the repo and read README.md, PRODUCT.md, DESIGN.md and everything in docs/ itself.

**Exact prompt:**
```
https://github.com/ellitellicity-commits/OLG-AntiMoney-Laundering

import the main branch locally and do whats said in the files there.
```

**Expected output:**
Build steps 1–8 from WORKFLOW.md: `backend/pipeline/{common,generate_data,build_features,detect,validate}.py`,
`backend/app/{main,schemas}.py`, `frontend/{index.html,styles.css,app.js,mock/alerts.json}`, `docs/VALIDATION.md`
(generated), `docs/DEMO.md`, `run_demo.ps1`, `run_demo.sh`, and status updates in README, HANDOFF, WORKFLOW, DESIGN.

**How we test it:**
- Generator run twice with seed 42 → identical SHA-256 for every output file.
- `validate.py` → both "done when" checks pass (see `docs/VALIDATION.md`).
- Every API endpoint called with `curl`, including the error cases (unknown sort → 400, unknown alert → 404,
  close without a reason → 422).
- Headless Chrome (Playwright, outside the repo): keyboard-only open of the top alert → reasons, peer chart and
  action visible → close with a reason → status updates in the queue; no console errors.
- Clean copy of the repo (only files git would commit) → `run_demo.ps1` → fresh venv, full pipeline, API and
  dashboard work; scores identical to the working copy.

**What went wrong / how we fixed it:**
- Generator took 80 s → replaced `rng.choice(p=...)` / `np.select` with cumulative-probability lookups → 29 s.
- Normal players deposited so rarely that a third had $0 in 30 days, so any deposit gave a deposit z-score of
  about 30 → more frequent deposits in the generator, a 0.5 floor on the z scale, and peer stats for deposits /
  stake / bet frequency computed over peers active in the window.
- Peer-deviation players were injected at 8–15× *their own* stake, which could still be close to peers → now
  8–15× the typical stake for the income band, matching the scenario definition.
- Combined score and legacy rules tied at 100% precision@50, so the "beats rules-only" check failed → added
  `steady_high_value` benign players (README's own example of a high earner with steady large deposits), which
  fixed-threshold rules mis-rank. The check now passes (100% vs 98%); VALIDATION.md states this dependency.
- Isolation Forest explanation used a row-wise pandas `apply` (110 s) → vectorised with NumPy (5 s total).
- First false-positive explanations claimed things the data contradicted ("nothing changed against own
  history") → explanations now describe only what was planted.
- UI: close/assign forms ignored `hidden` because of `display: flex`; legend icons inherited the chart's
  `width: 100%`; queue overflowed → `[hidden]` rule, scoped selector, anomaly tags merged into the reason cell.

---

## Step 2 — Features

*Built in the single session logged in 1.1; no separate prompt.*

### 2.1 —

**Context to paste:**

**Exact prompt:**

**Expected output:**

**How we test it:**

**What went wrong / how we fixed it:**

---

## Step 3 — Detection and scoring

*Built in the single session logged in 1.1; no separate prompt.*

### 3.1 —

**Context to paste:**

**Exact prompt:**

**Expected output:**

**How we test it:**

**What went wrong / how we fixed it:**

---

## Step 4 — Validation

*Built in the single session logged in 1.1; no separate prompt.*

### 4.1 —

**Context to paste:**

**Exact prompt:**

**Expected output:**

**How we test it:**

**What went wrong / how we fixed it:**

---

## Step 5 — API

*Built in the single session logged in 1.1; no separate prompt.*

### 5.1 —

**Context to paste:**

**Exact prompt:**

**Expected output:**

**How we test it:**

**What went wrong / how we fixed it:**

---

## Step 6 — Dashboard

*Built in the single session logged in 1.1; no separate prompt.*

### 6.1 —

**Context to paste:**

**Exact prompt:**

**Expected output:**

**How we test it:**

**What went wrong / how we fixed it:**

---

## Step 7 — Bonus features

*Network analysis and recommendations were built in the session logged in 1.1.*

### 7.1 — AI layer, compliance indicators and investigation upgrades   (date: 2026-10-15 · author: Sidneneyyy · tool/model: Claude Code, claude-opus-5-5)

**Context to paste:**
The challenge brief PDF was attached in the chat session (not committed to the repo). The agent read the repo
itself. Earlier in the same session it assessed the `finomaly` library and advised against it: its PyPI release
is broken, it reads and writes Excel files, and it offers only simpler versions of what the pipeline already does.

**Exact prompt:**
```
we dont plan to go small we plan to go big, my task is only to get the bare bones of this project going while
two other teammembers of mine will be polishong the baclend and the frontend of my work. read this pdf and see
what u can upgrade of my project so far, lets plan ahead and do it all in one go. also keep in mind these
hackathon judges love AI so using AI in this system would be massive, but free versions only please
```

**Expected output:**
- `backend/pipeline/train_model.py` (new step 2b): gradient boosting + SHAP, scored out-of-fold, plus a model card.
- `backend/pipeline/generate_data.py`: new `structuring` scenario (30 players).
- `backend/pipeline/build_features.py`: 24-hour deposit windows, structuring features, `transaction_flags.parquet`.
- `backend/pipeline/detect.py`: `STRUCTURING`, `LARGE_TRANSACTION_24H` and `ML_MODEL` reasons; occupation in the
  income-mismatch text; structuring recommendations.
- `backend/pipeline/validate.py`: structuring recall, AI-model orderings, with/without-AI effect table.
- `backend/app/ai.py`: free LLM client (Ollama / Groq / Gemini), number-checked summaries, Q&A, queue search.
- `backend/app/report.py` and new endpoints in `main.py` / `schemas.py`.
- `frontend/`: bare-bones panels for all of the above. Docs and run scripts updated.

**How we test it:**
- Full pipeline run twice from scratch → identical SHA-256 for every output; about 60 s end to end.
- `validate.py` → all three checks pass; the AI model raises recall from 89% to 95% with no extra false positives.
- Every endpoint called with `curl`, including errors (unknown alert → 404, empty question → 422).
- LLM path tested against a fake OpenAI-compatible server: an invented "$77,777" in a summary was caught,
  retried and replaced; a made-up number in a Q&A answer was flagged; an invalid search filter was dropped;
  `<think>` tags were stripped. No-LLM path tested: template summary, keyword search, offline message.
- Headless Chrome (playwright-core, outside the repo) against both modes: queue search, summary, Ask, timeline,
  flagged-only toggle, decision and case report; no console errors.
- Not tested: a real Ollama, Groq or Gemini model (none was installed or keyed on the build machine).

**What went wrong / how we fixed it:**
- `DataFrame.flags` is a built-in pandas attribute → use `flags["flags"]` for the column.
- SHAP listed ordinary values as risk drivers ("deposits vs income 0.2x") because tree models can push risk up
  through interactions → only drivers above the 75th percentile are listed (they still count in the probability).
- 0.9997 rendered as "100% likely" → probabilities above 0.99 are shown as "over 99%".
- The long provenance line squeezed the "Case summary" heading → moved under the summary text.
- The UI test wrote `data/decisions.json` and cached a fake-model summary in `data/ai_cache.json` → both deleted.

### 7.2 — Close every gap against the challenge brief   (date: 2026-10-15 · author: Sidneneyyy · tool/model: Claude Code, claude-opus-5-5)

**Context to paste:**
The challenge brief PDF (attached in the chat, not committed). Earlier in the session the agent had reviewed the
project against every point of the brief and listed partial items and AML gaps; it also noticed that 165 of 241
alerts scored exactly 100, so the queue could not tell them apart.

**Exact prompt:**
```
"I also found a real weakness while checking: 165 of the 241 alerts score exactly 100. The score is capped, so
it can't tell the top two-thirds of the queue apart. Right now they're ordered by recency, not risk. That
directly weakens requirement 03, prioritization." i want you to do something about that.

"Gaps a sharp AML judge could spot:" do we cover all that?

work on every ⚠️ so that all of them can become a ✅, use what they like, remove or dont use what they dont
want, and add your fixes too.
```

**Expected output:**
- Scoring: same-type overlap at half weight, soft cap above 70, ties broken by points then AI probability;
  confidence (High / Medium / Low) with mitigating factors; a watchlist for unusual players below the alert line.
- AML: occupation-vs-income check, low-odds betting, third-party funding, U-turn withdrawals, rapid cash-outs,
  dormant reactivation, KYC / sanctions / PEP; new scenarios and benign look-alikes in the generator.
- AI: behaviour groups (k-means), the supervised model in ranking and confidence, `cross_seed.py`.
- `check_data.py` + `docs/DATA_INTEGRATION.md`; API: watchlist, audit trail (names required), trends, behaviour
  peers; dashboard: tabbed detail, overview screen, network graph, investigator name.

**How we test it:**
- Full pipeline twice from scratch → identical hashes; all validation checks pass (see `docs/VALIDATION.md`).
- Cross-seed: two never-seen populations scored by the seed-42 model, with recall and false positives close to
  seed 42's.
- Every new endpoint called, including a decision without a name (→ 422).
- Headless Chrome: queue filters and sorts, every detail tab, network-node click, watchlist from the overview,
  decision refused without a name then recorded with one; no console errors. Test decisions removed afterwards.

**What went wrong / how we fixed it:**
- U-turn detection first found nothing ("method never used to deposit" misses mules who used their own card
  before) → compare with the method of the deposit the withdrawal followed.
- Quick cash-outs flagged 127 normal players → minimum $300 and require little betting.
- The first soft cap (scale 45) still put 76 alerts at 99 → scale 90: no 99s, largest tie 30, broken by points.
- A structuring reason quoted a single $15,200 deposit as its example → only quote split-deposit episodes.
- Network graph labels overlapped and trend changes read "+6050%" → one shared label, and "×N" / "New this month".

---

## Step 8 — Demo

*Built in the single session logged in 1.1; no separate prompt.*

### 8.1 —

**Context to paste:**

**Exact prompt:**

**Expected output:**

**How we test it:**

**What went wrong / how we fixed it:**

---

## Frontend restyle

### R.1 — Audit the working frontend and propose an outline   (date: 2026-10-15 · author: ellitellicity-commits · tool/model: Claude Code, claude-opus-5-5)

**Context to paste:** root `PRODUCT.md` and `DESIGN.md`, `frontend/` (index.html, styles.css, app.js), `design-reference/` (Case File proposal: DESIGN.md, PRODUCT.md, mock_frontend.html, API_MATCH.md).

**Exact prompt:** the "Audit the existing working frontend and propose a better outline" prompt (analysis only; inventory, `/impeccable critique` + `/impeccable audit`, text wireframes, visual direction, 3 signature moments, impact/effort ranking).

**Expected output:** `docs/FRONTEND_OUTLINE.md` only.

**How we test it:** no code changed; `git status` showed only the new doc.

**What went wrong / how we fixed it:** the brief asked for design notes in `docs/DESIGN_RESTYLE.md` but allowed only one new file, so the visual direction went into section 4 of the outline (extracted to `DESIGN_RESTYLE.md` in R.2).

### R.2 — Apply the CSS-only first pass of the Case File restyle   (date: 2026-10-15 · author: ellitellicity-commits · tool/model: Claude Code, claude-opus-5-5, `/impeccable craft`)

**Context to paste:** as R.1, plus `docs/FRONTEND_OUTLINE.md`.

**Exact prompt:**

```text
BRANCH CHECK (first):
Run `git branch --show-current`. It must be `frontend-polish`. If not, stop and tell me. Never work on `wireframe`, `main` or `backend`. Run no git commands that change anything (no add, commit, push, merge).

/impeccable craft the restyle

CONTEXT RULES:
- The root PRODUCT.md and DESIGN.md belong to my friend and are the source of truth for behaviour, data, features and the 4 risk bands (Low, Medium, High 70-89, Critical 90-100). Do not edit them.
- design-reference/ holds our proposed visual direction. On facts the root files win; on visual style adapt the design-reference.
- Keep every feature working, including the LLM summary, Q&A and search.
- Never stage or commit .claude/.

Read docs/FRONTEND_OUTLINE.md, the root PRODUCT.md and DESIGN.md, and everything in design-reference/.

DECISIONS (from me, they take priority over the outline):
- Apply ranks 1-10 from section 6 of docs/FRONTEND_OUTLINE.md (the CSS-only first pass), including the one font link in index.html for the serif.
- Skip every item marked "needs JS change". List them at the end for my friend (for example: the guard against deciding twice, hard-coded colours in app.js, the risk ribbon, screen-reader fixes for queue rows and the network graph buttons, and Night shift once the chart colours use shared variables).
- For change 5, keep the sticky case header but do NOT reorder content with CSS `order` unless keyboard and screen-reader order stay identical. If unsure, skip the reorder.
- Do not build Night shift yet.
- The outline put the visual direction in its section 4, so also create docs/DESIGN_RESTYLE.md by extracting that section and keeping it updated as you build. That is the one new doc allowed besides docs/PROMPTS.md.

HARD RULES:
- Do not touch anything under backend/, data/, run_demo.ps1 or requirements files.
- Do not change behaviour: keep the JS logic, fetch URLs, API calls, event handlers, element ids and data-* attributes unchanged. If a markup change needs a new class, add it; never rename or remove an existing hook.
- Do not invent data. Never show a field the frontend does not already receive.
- Do not make "needs JS change" items.
- Do not copy any real OLG, Ontario or Canada branding or logos. Keep the neutral name "Sentinel".

DESIGN: follow Impeccable's design guidance and the adapted "Case File" direction. Strong hierarchy, restrained colour with one accent, a real type scale, no generic AI-dashboard patterns (no cards inside cards, gradient text, glassmorphism, identical icon tiles). Keep the old colour variable names as aliases so nothing breaks. Give PEP, sanctions, form-error, "Rising" and AI-warning tags a neutral warning style so they no longer share the High and Critical risk colours. Motion under 300ms and disabled under prefers-reduced-motion. Risk shown by number, label and shape, never colour alone, including a distinct dark-red Critical look. WCAG AA in Day shift. Responsive down to tablet and usable on a phone.

SAFETY CHECKS BEFORE FINISHING:
1. Run `git diff --stat` and `git status`. Every changed file must be inside the frontend folder or docs/. The root PRODUCT.md and DESIGN.md must be unchanged, and no JS file should have logic changes. If anything else changed, revert it and tell me.
2. Compare the JS before and after: list every id, data-* attribute and fetch URL in the original, and confirm each still exists unchanged.
3. If the backend is reachable at the frontend's configured URL, or the frontend's mock fallback can run without it, load the page and test the main flow (queue, dossier tabs, filters, summary, search, AI features). If neither works, say so and mark behaviour as unverified; do a visual review from a static render where possible.

WHEN DONE: run /impeccable critique, apply the top 3 fixes (CSS-only), update docs/DESIGN_RESTYLE.md to match what was built, log this prompt and its result in docs/PROMPTS.md under "Frontend restyle", and print: the branch, the files changed, the safety-check results, the "needs JS change" list, and what I should check in a browser. Do not commit or push anything.
```

Answers given when asked: the brand shows as "Sentinel" with a "Player risk review" subtitle; the local API may be started for testing; tool working files go to a temp folder, not the repo.

**Expected output:** `frontend/styles.css` (rewritten), `frontend/index.html` (title, font link, "Sentinel" h1 with subtitle class, "Team overview" label, search moved first in the filter form; all ids kept), `docs/DESIGN_RESTYLE.md` (new), this entry. `frontend/app.js` unchanged.

**How we test it:**
- `git diff --stat`: only `frontend/index.html` and `frontend/styles.css` changed, plus the new or updated docs. Root `PRODUCT.md` and `DESIGN.md` are unchanged. `app.js` is byte-identical to the original.
- Hook check (script comparing original vs new `index.html` + `app.js`): all 66 ids, 18 `data-*`/dataset hooks, 19 fetch URLs and 61 JS selectors are still present.
- **Live test.** The API ran locally against a throwaway copy of the data in a temp folder (`OLG_DATA_DIR`, bytecode writing off), so nothing under `data/` or `backend/` changed. Headless Edge then drove the page through 32 checks, all PASS, with no console errors:
  - queue, band filter, column sort, ID search, arrow keys and Enter;
  - the case summary;
  - all 5 tabs, the peer chart and the flagged-only toggle;
  - Ask AI (chip and form);
  - Close and Assign forms opening and cancelling;
  - plain-English queue search and clear, and the watchlist toggle;
  - Team overview;
  - a decision refused without a name.

  No decision was saved.
- **Not covered by the live test:**
  - The LLM itself was offline, so the summary, Ask AI and search ran through their built-in fallbacks (template, offline notice, keyword match). The LLM path itself is unverified.
  - `train_model.py` could not run because Windows Application Control blocks a `shap` DLL, so the test data had no AI model probabilities, model card or watchlist.
- **Mock fallback** (`?api=` pointed at a dead port): the banner shows and 5 mock alerts render.
- **Screenshots** at 1440×900, 1280×800, 820 (tablet) and 390 (phone).
- **`/impeccable critique`:** design review 28/40 (up from 26/40 before the restyle). Detector: 10 findings, 8 of them false positives (keycap bevels, a CSS triangle, a table-head band, a spacing sample) plus the intentional paper palette. The triangle was redrawn with `clip-path` anyway.

**What went wrong / how we fixed it:**
- At 1440 the masthead wrapped and the queue table clipped its Status column → tighter masthead, wider docket column (`minmax(500px, 4fr) / 5fr`), filters on one row, anomaly tags allowed to wrap.
- At 1280 the investigator field wrapped → the label text is drawn at zero size below 1400px (still read by screen readers).
- Critique fix "keep tags on one line" made tags unreadable at 1280 ("S…", "Inc…") → reverted; only the tighter cell padding kept.
- Critique fix "unstick the case header on screens under 980px tall" conflicts with the decision to keep it sticky → not applied; logged as a team decision in `DESIGN_RESTYLE.md` §7.
- Applied from the critique:
  - the evidence-thread grid gap (the comparison now sits under the evidence);
  - scroll padding so focus never hides under the sticky header;
  - leaner header and action-bar padding;
  - the "Recommended action" label turned from an accent kicker into ink-2 metadata;
  - the flagged-row side stripe removed;
  - the Sort select minimum width.

**Needs a JS change (not done; for the team):**
1. Guard against deciding twice: no refocus on Accept after saving; decided cases show "Already Escalated by X on date" and demote the buttons.
2. Auto-open the first alert; after a decision, advance to the next undecided alert, with Undo.
3. Ask for the investigator name before the first decision ("Deciding as …" in the action bar).
4. Hard-coded colours in `app.js` (`BAND_FILL`, peer chart, timeline, network, sparkline SVG hex values) → CSS variables. Until then the network circles and Team-overview bars use the old palette.
5. Night shift, once #4 is done.
6. Risk ribbon above the queue (band counts from `state.alerts`, click to filter).
7. Screen-reader fixes:
   - queue rows need grid or listbox semantics so selection is announced;
   - network graph buttons sit inside `role="img"`, so screen readers cannot reach them;
   - `#queue-count` re-announces on every keystroke;
   - Esc should close the Close and Assign forms.
8. Team overview: Retry on error, friendly error messages, the model card collapsed, band rows with a meter.
9. Clear-filters button in the empty queue state; dim the previous case while a new one loads instead of blanking the panel.
10. Overview tab true reorder (strongest reasons before key facts) in the template, not via CSS `order`.
11. Phone master/detail: scroll to the case when a row opens, plus a back-to-queue link.

### R.3 — CSS-only follow-up: quieter Critical in the queue, pinning only on tall screens, polish, critique   (date: 2026-10-15 · author: ellitellicity-commits · tool/model: Claude Code, claude-opus-5-5, `/impeccable quieter`, `/impeccable polish`, `/impeccable critique`)

**Context to paste:** as R.2, plus `docs/DESIGN_RESTYLE.md`.

**Exact prompt (Part A; Part B commits and pushes after the user replies "go"):**

```text
BRANCH CHECK (first):
Run `git branch --show-current`. It must be `frontend-polish`. If not, stop and tell me. Never work on `wireframe`, `main`, `backend` or `integration`.

PART A: CSS-ONLY FOLLOW-UP, USING IMPECCABLE (no git commands that change anything in this part)

Do not touch backend/, data/, run_demo.ps1, requirements files, the root PRODUCT.md or DESIGN.md, or frontend/app.js. Do not rename or remove any id, data-* attribute or class that the JS uses. Never stage or commit .claude/. Read docs/DESIGN_RESTYLE.md and design-reference/ for the visual direction, and follow Impeccable's design guidance throughout. If an Impeccable command named below is not recognized, tell me and use the closest available one.

1. Run /impeccable quieter on the alert queue's Critical badge only. Give it a softer style than the solid dark-red one: keep the number, the label, the double border and the 4th meter bar so it is still clearly the top band, but use a lighter fill so a queue where 45% of alerts are Critical does not read as a solid wall. Keep the solid dark-red Critical badge in the case header.
2. Make the case header and action bar stop being sticky on screens shorter than 900px (use a max-height media query), and keep the sticky behaviour on taller screens.
3. Run /impeccable polish on the files you changed for a final pass: spacing rhythm, alignment, focus states and consistency with the design tokens. Keep every change CSS-only and keep the old variable names as aliases.
4. Run /impeccable critique on the result and apply only fixes that are CSS-only and low risk. List any others for my friend instead of applying them.
5. Re-run the safety checks: `git diff --stat` and `git status` (changes only in frontend/ and docs/; the root PRODUCT.md and DESIGN.md unchanged; nothing under backend/ or data/), confirm frontend/app.js is still byte-identical to the commit this branch started from (`git diff 8d685bd -- frontend/app.js` must be empty), and confirm every id, data-* hook and fetch URL from the original is still present. Check that Critical, High, Medium and Low stay distinct by number, label and shape (not colour alone), and that text contrast still meets WCAG AA.
6. Update docs/DESIGN_RESTYLE.md and the "Frontend restyle" entry in docs/PROMPTS.md with what changed, including which Impeccable commands were used and their results.
```

**Expected output:** `frontend/styles.css` only (plus `docs/DESIGN_RESTYLE.md` and this entry). `index.html` and `app.js` unchanged in this pass.

**What changed:**
- **`/impeccable quieter`:** in the alert queue only, Critical takes the soft fill `#F2D4D8` with oxblood text (8.50:1), keeps the 3px double frame, the bold label and the 4th meter bar, and gains a small solid oxblood plate under the score (white on `#6E1423`, 11.75:1). The case header keeps the solid inverted badge.
- **Pinning:** `@media (max-height: 899px)` makes the case header and action bar static. On desktop, `#detail` becomes the scroller, so the action bar sits at the foot of the case. On screens 900px tall or more, both stay pinned, and the action sentence is set at 15/20.
- **`/impeccable polish`:**
  - Sort select width;
  - the masthead divider tokenised (`color-mix` of `--navy-ink`, no raw rgba);
  - a misplaced media-query comment fixed;
  - duplicate and dead rules removed (`.reason-compare` merged, redundant `.tag-synthetic` sizes, dead `top`/`flex-basis` overrides, `td.date`).
- **`/impeccable critique`:** design review **30/40** (was 28/40). Detector: 9 findings, all known false positives (`<kbd>` keycap bevel ×6, table-head band, intentional paper palette, spacing sample). Applied (CSS-only, low risk):
  - filters in two rows on desktop;
  - `:where()` so the `:has(#f-sort)` and `:has(#f-type)` rules no longer outrank the responsive filter rules;
  - the queue Critical score plate;
  - status stamps from a 3px double frame to a 2px solid frame, so the double frame means only Critical;
  - a smaller action sentence on tall screens.

**How we test it:**
- `git diff --stat` / `git status`: only `frontend/index.html`, `frontend/styles.css` and `docs/` changed. `git diff 8d685bd -- frontend/app.js` is empty. Root `PRODUCT.md` and `DESIGN.md` are unchanged against `8d685bd`. Nothing under `backend/` or `data/`, and no `__pycache__`.
- Hook check against `8d685bd`: all 66 ids, 18 `data-*`/dataset hooks, 19 fetch URLs and 61 JS selectors are present.
- Same live test as R.2 (local API on throwaway data in a temp folder): 32/32 checks PASS, no console errors.
  - At 1280×800 the header is `position: static` and `#detail` scrolls.
  - At 1440×900 both stay pinned.
  - Mock mode shows Critical 95 next to High 87/80/70 and Medium 43.
- **Band distinctness without colour:**

  | Band | Label | Meter | Frame / fill |
  |---|---|---|---|
  | Low | LOW | ▮▯▯▯ | faint frame |
  | Medium | MEDIUM | ▮▮▯▯ | faint frame |
  | High | HIGH | ▮▮▮▯ | 1px solid frame |
  | Critical | CRITICAL (bold) | ▮▮▮▮ | 3px double frame; solid score plate in the queue, solid inverted badge in the header |

- **Text contrast (AA, Day):**

  | Band | Ratio |
  |---|---|
  | Low | 6.16 |
  | Medium | 5.62 |
  | High | 5.69 |
  | Critical, queue | 8.50 (plate 11.75) |
  | Critical, header | 11.75 |

**What went wrong / how we fixed it:**
- The first API restart was blocked by a transient tool-permission error; it was retried after the CSS edits.
- The earlier way of stopping the test API matched processes by command line. This time only the process listening on port 8000 was stopped, and it was confirmed to be the test API.
- Not applied (listed for the team in `DESIGN_RESTYLE.md` §7):
  - the tablet sticky action bar appearing before its case header;
  - pinning a compact action bar on short screens;
  - removing the oxblood Critical row hairlines;
  - custom select chevrons;
  - the "Recommended action" label sitting like a kicker (needs markup);
  - one tag plus "+N more" in the queue (needs JS).
- The "Needs a JS change" list in R.2 is unchanged.

## Chat panel frontend

### C.1 — Persistent AI chat panel: plan, build and check (frontend only)   (date: 2026-10-15 · author: ellitellicity-commits · tool/model: Claude Code, claude-opus-5-5, `/impeccable shape`, `/impeccable craft`, `/impeccable critique`, `/impeccable polish`)

**Context to paste:** `docs/CHAT_PANEL_PLAN.md`, the `frontend/` folder, `docs/DESIGN_RESTYLE.md`, `design-reference/`.

**Exact prompt (Parts A and B; Part C commits and pushes the branch after the user replies "go"):**

```text
BRANCH CHECK (first):
Run `git branch --show-current` and `git status`. If the branch is `frontend-polish` and there are no uncommitted changes to tracked files, run `git checkout -b frontend-chat`. If it is already `frontend-chat`, stay on it. Otherwise stop and tell me. Never work on `frontend-polish`, `wireframe`, `integration`, `main` or `backend`. Run no other git command that changes anything until PART C.

GOAL: Build the frontend half of the AI chat panel described in docs/CHAT_PANEL_PLAN.md, in three parts: A) plan, B) build and check, C) commit and push the branch after I reply "go". If an Impeccable command named below is not recognized, tell me and use the closest available one.

SCOPE: the frontend parts of the plan only: section 3 (layout), section 4 (behaviour), the Pin to case button and display from section 10, and section 12. Out of scope, because they belong to the backend teammate: the /chat implementation, retrieval, lookup tools, Groq and Ollama, the server-side safety checks, and note storage.

HARD RULES (for the whole task):
- Frontend only. Do not touch backend/, data/, run_demo.ps1, requirements files, or the root PRODUCT.md and DESIGN.md. Never stage or commit .claude/.
- Never write an API key or secret anywhere (code, docs, commits).
- Never render model text with innerHTML; build DOM nodes or use textContent. Make player and alert IDs clickable only if they match the known patterns (P00000, ALR-00000, WL-00000) and are not listed in unknown_ids. Render action buttons only from the whitelist (open alert, apply filter, sort, show watchlist) with validated values, and do nothing until the investigator clicks.
- The chat can never record, draft-and-submit, or trigger a decision (Accept, Escalate, Close, Assign). Do not wire any decision endpoint to the chat.
- Keep every existing feature working (queue, filters, sort, search, existing keyboard shortcuts, tabs, decision forms, watchlist, Team overview, mock mode). Remove only the "Ask AI" tab, as the plan says.
- Do not invent data. Do not add features outside the plan.

PART A: PLAN (create only docs/CHAT_FRONTEND_OUTLINE.md and docs/CHAT_CONTRACT.md; edit nothing else)
Read first: docs/CHAT_PANEL_PLAN.md, the frontend folder (index.html, styles.css, app.js, mock/), docs/DESIGN_RESTYLE.md and design-reference/.
1. Inventory the current frontend (views, state, routing, fetch layer, the Ask AI tab, decision forms, filters, keyboard shortcuts, mock mode) and write a regression list of every existing feature that must keep working.
2. Run /impeccable shape on the new layout. Write text wireframes for Mode 1 (queue) and Mode 2 (alert with Back to queue, previous and next) and for laptop, tablet and phone widths (propose how the chat collapses to a thin bar or overlay below about 1100px). Cover the context chip, "Now viewing" dividers, per-answer footer, clickable IDs, action buttons, Pin to case and New chat. Follow the Case File direction: calm and regulatory, no AI-sparkle gradients, risk never by colour alone.
3. Write the technical design: state shape; a view router (queue, overview, alert) where previous and next follow the current filter and sort order; the context object builder (view, alert_id, filters, sort, visible_count); the message store with sessionStorage wrapped in try/catch; a chat transport that posts to the API's /chat in live mode plus a built-in stub, enabled with the URL parameter ?chat=stub, that returns responses in the contract's shape; the mock-mode message "AI unavailable in offline demo data"; safe rendering; the ID and action rules above; keyboard plan (keep existing shortcuts, add Ctrl+K for the chat input, make Esc in Mode 2 go back to the queue); aria-live announcements; focus management.
4. Create docs/CHAT_CONTRACT.md: copy the /chat request and response shapes and the notes endpoints from section 11 of the plan verbatim as the agreed contract with the backend teammate, then add example stub responses for: a normal answer; an answer with clickable IDs and actions; an assumption line; unverified numbers; unknown IDs; fallback_used true; an offline or error response; and the notes responses. State that neither side changes the shape without telling the other.
5. Open decisions: do not wait for me. For each open decision, choose the proposed default, record it under "Decisions taken" in the outline, and continue.
6. Mark every piece of work as "UI only", "JS state" or "needs backend", with a build order and the regression risks.

PART B: BUILD AND CHECK
/impeccable craft the chat panel, following the outline and docs/CHAT_CONTRACT.md. Live mode posts to the API's /chat; if /chat does not exist, show a calm "AI is unavailable" message and keep the rest of the dashboard working. Build: the two-column shell and the queue, overview and alert views with Back to queue, previous and next; the persistent chat with the context chip, "Now viewing" dividers, "Thinking...", the per-answer footer, clickable IDs, action buttons, Pin to case and New chat; the conversation kept in state and sessionStorage (try/catch, works without it); Ctrl+K to the chat input; Esc in Mode 2 back to the queue.
DESIGN: follow Impeccable's design guidance and the Case File direction. The chat panel is about 35% wide (minimum 360px) and collapsible to a thin bar. Motion under 300ms and disabled under prefers-reduced-motion. WCAG AA contrast. New answers are announced through an aria-live region, the input has a label, and the whole chat works by keyboard alone.
CHECKS before finishing:
1. `git diff --stat` and `git status`: changes only in frontend/ and docs/; nothing under backend/ or data/; the root PRODUCT.md and DESIGN.md unchanged. Search the diff for anything that looks like an API key or secret and report the result.
2. Regression: run the same automated browser checks as in the earlier restyle (queue, filters, sort, ID search, keyboard, case summary, all tabs, plain-English search, watchlist, Team overview, decision forms open and close, a decision refused without a name), using a throwaway copy of the data so nothing is saved. Confirm mock mode renders.
3. Chat, in stub mode: the conversation survives opening rows, Back, next and previous, filter changes, the Overview tab and a browser refresh; New chat is the only thing that clears it; the context chip is always correct; a divider appears when a different row opens; IDs, unknown IDs and action buttons behave as specified; the chat cannot trigger a decision; a stub answer containing <img onerror> and <script> text renders as plain text; keyboard-only use works.
4. Screenshots at 1440x900, 1280x800, 1100, 820 and 390 wide, collapsed and expanded, if a browser is available. If not, say so.
5. Run /impeccable critique, apply the low-risk fixes, run /impeccable polish, and list the rest.
6. Add a "Chat panel" section to docs/DESIGN_RESTYLE.md, and log this prompt and its result in docs/PROMPTS.md under "Chat panel frontend".
7. Create docs/CHAT_HANDOFF.md, a one-page start-here guide for teammates and their AI assistants, with: what the chat panel is and which branch it lives on (frontend-chat, stacked on frontend-polish, not merged anywhere); how to get it (`git fetch origin`, then `git checkout frontend-chat`); how to run it (open the dashboard with ?chat=stub for the built-in stub, and without it for live mode once the backend has /chat); what is built, what is stubbed, and what the backend teammate must provide (point to docs/CHAT_CONTRACT.md); the files changed; known gaps; and rules for any AI assistant working on this branch: read docs/CHAT_PANEL_PLAN.md, docs/CHAT_CONTRACT.md and docs/CHAT_FRONTEND_OUTLINE.md first; never push to or merge into integration, main, wireframe or frontend-polish; never change the /chat contract without the team agreeing; the chat must never record or trigger decisions; never write secrets.
Then STOP. Print the check results, the critique score, the "Decisions taken" list from the outline, what was not verified, and a short "backend teammate must provide" list. Wait for me to reply "go". Do not run any git command that changes anything until I do. If a check fails, fix or revert it, tell me, and wait.

PART C: COMMIT AND PUSH THE BRANCH ONLY (only after I reply "go"; no pull request, no merge)
1. Run `git branch --show-current` (must be frontend-chat), then `git status` and `git diff --stat`. Only these paths are allowed: the frontend folder, docs/CHAT_PANEL_PLAN.md, docs/CHAT_FRONTEND_OUTLINE.md, docs/CHAT_CONTRACT.md, docs/CHAT_HANDOFF.md, docs/DESIGN_RESTYLE.md and docs/PROMPTS.md. If anything under backend/ or data/, a .env file, a secret, or .claude/ appears, stop and tell me.
2. Stage only the allowed paths by name (never `git add .` or `git add -A`). Commit with the message: "Add persistent AI chat panel (frontend, stub until /chat exists)".
3. Run `git fetch origin`. Without merging, run `git merge-tree --write-tree HEAD origin/frontend-polish` and `git merge-tree --write-tree HEAD origin/integration` and report any conflicted files for each (skip if the git version does not support it).
4. Push only this branch: `git push -u origin frontend-chat`. Never use --force. Never push to, merge into, or open a pull request against frontend-polish, wireframe, integration, main or backend. If it fails, report the exact error and the likely fix.
5. Print the branch, commit hash, files committed and the remote URL.
6. Print the exact commands a teammate runs to see the branch (`git fetch origin`, then `git checkout frontend-chat`, or `git worktree add ..\AML-chat frontend-chat` to keep their own folder untouched), and a one-line instruction a teammate can give their Claude: "Open this repo on the frontend-chat branch and read docs/CHAT_HANDOFF.md first."
7. Do not open a pull request. Write the draft PR description into your reply only, ready for later, saying the base would be `frontend-polish` while the restyle PR is open and `integration` after it merges.
```

**Expected output:** `frontend/index.html`, `frontend/styles.css`, `frontend/app.js`; new `docs/CHAT_FRONTEND_OUTLINE.md`, `docs/CHAT_CONTRACT.md`, `docs/CHAT_HANDOFF.md`; a "Chat panel" section in `docs/DESIGN_RESTYLE.md`; this entry. `docs/CHAT_PANEL_PLAN.md` (the plan, previously untracked) is committed with them.

**What changed:**
- Two-column shell; the work area shows the queue, the Team overview or one alert (Back to queue, Previous / Next in the current filter and sort order, position "n of N"). The view switch moved from the masthead into the work area. The Ask AI tab is removed.
- The persistent assistant: context chip, "Now viewing" dividers, Thinking… with queued questions, per-answer footer (provider, numbers check, unknown IDs, cases used), clickable known IDs, whitelisted action buttons (labels written by the frontend), Pin to case (name required; Mode 1 asks which named alert), New chat, sessionStorage (try/catch), Ctrl+K, Esc back to the queue, aria-live announcements, collapsible rail on desktop, bottom bar and overlay below 1100px.
- Live mode posts to `/chat`; a missing endpoint shows "AI is unavailable: this API does not have the /chat endpoint yet". `?chat=stub` answers in the contract's shape from the rows on screen and stubs the notes endpoints. Mock mode shows "AI unavailable in offline demo data".
- The decision history is built as DOM nodes and lists pinned AI notes with Remove.

**How we test it:**
- `git status` / `git diff --stat`: only `frontend/` and `docs/` changed; nothing under `backend/` or `data/`; root `PRODUCT.md` and `DESIGN.md` unchanged. Secret scan of the diff and new docs: no keys or secrets (the only "token" hits are the existing `state.token` stale-response guard).
- The API ran on a throwaway copy of the data in a temp folder (`OLG_DATA_DIR`, bytecode writing off). Headless Edge over CDP, no console errors:
  - **Regression, 47/47 PASS:** queue, five filters, column sort and Sort by, `/` and ID search, Esc in search, ↑↓ and Enter, Mode 2 strip and position, case summary, Ask AI tab gone, 4 tabs, peer chart, flagged-only toggle, Close form (reason required, Cancel), Assign form, decision refused without a name, `D` in Mode 2 only, Next / Previous, Esc back to the queue with the row focused, plain-English search and Clear, watchlist toggle, Team overview and audit CSV link, no POST to `/decision`.
  - **Chat in stub mode, 49/49 PASS:** context chip in every view; queued second question; answers in order; aria-live; links and 4 actions; filter change, rows, Back, Next / Previous, Overview and a refresh all keep the conversation; dividers (none duplicated on Next then Previous); Pin needs a name, pins, shows "AI note" in the history, can be removed; Mode 1 pin picker; each action type; assumption; unverified numbers; unknown ID plain and flagged; invalid actions dropped; fallback footer; offline; error notice; `<img onerror>` / `<script>` rendered as text with the title unchanged; hostile `accept` action dropped; no decision request; keyboard-only (Ctrl+K, Enter, Enter on an ID, collapse and expand); New chat clears and stays cleared after refresh; the input has a label.
  - **Live mode, 3/3 PASS:** POST `/chat` → 404 → calm notice; the dashboard keeps working.
  - **Mock mode, 6/6 PASS:** banner, 5 mock alerts, "AI unavailable in offline demo data" with the input disabled, Mode 2, an in-memory decision, and the stub working with `?chat=stub`.
- Screenshots at 1440×900, 1280×800, 1100×900, 820×1180 and 390×844, Mode 1 and Mode 2, collapsed and expanded.
- `/impeccable critique` (dual-agent): **26/40**. The detector findings were false positives or the intended palette. Low-risk fixes and `/impeccable polish` are listed in `DESIGN_RESTYLE.md` §9.

**What went wrong / how we fixed it:**
- Moving the view switch off the navy masthead left it with masthead text colours on paper (the design hook flagged low contrast). It was restyled as ink on paper with an accent underline.
- Next then Previous with no question in between stacked two "Now viewing" dividers. Fixed: the replaced divider re-checks the one before it.
- The warning list rendered "48,000 , 6" because flex gaps split the text nodes. Fixed by wrapping the text in one span.
- Driver bugs, not app bugs: synthetic Enter needed its `\r` text to activate buttons; a refused decision correctly left focus in the name field, so the `D` test now blurs first; there is no "last activity" column header, so the sort check reads the Sort by menu.

**Not verified:** a real `/chat` and the notes endpoints (they do not exist yet); a real LLM (the throwaway data has no provider configured, so the summary used the built-in template); screen readers (only DOM semantics and the aria-live text were checked); touch devices (only mobile emulation).

**Follow-up in the same session (additions requested before Part C, then a resume after a network disconnect):**

```text
go, but first do the additions below, then re-check, then continue to PART C only if every re-check passes.
1. Fix the §9 items where low risk: (a) per-answer metadata into a collapsed, keyboard-accessible "Details" disclosure, warnings always visible; (b) a "new answer" count badge on the collapsed rail and the mobile bottom bar, announced via aria-live, cleared on open; (c) the missing desktop keyboard shortcut, shown in the hints, no clash with arrows, Enter, /, D, Esc, Ctrl+K; (d) New chat: NO confirmation and NO undo, recorded as a deliberate decision.
2. CHAT_CONTRACT.md §3: mark proposed items "PROPOSED, needs backend confirmation"; CORS must allow DELETE; notes in GET /audit, /audit.csv and the case report.
3. CHAT_HANDOFF.md: Decisions taken, Not verified, Backend teammate must provide, Test it.
4. Leave .impeccable/ untracked and note its ignores are local only.
5. Report whether a test API from this session is still running.
RE-CHECKS, then /impeccable critique and polish (low-risk fixes only), update DESIGN_RESTYLE.md §9 and this entry, then PART C.
```

(The resume prompt after the disconnect repeated these steps, asked to verify edits for damage, to stop only processes this session started, and to use port 8002 for any new test server.)

**What changed in the follow-up:**
- Details disclosure, new-answer badge, Esc-to-collapse (decisions 22–25 in CHAT_FRONTEND_OUTLINE.md §7; New chat without undo is deliberate).
- CHAT_CONTRACT.md §3 rewritten as a PROPOSED table plus the required CORS and audit items; CHAT_HANDOFF.md gained Test it, Backend teammate must provide, Decisions taken, Not verified and the `.impeccable/` note.
- Round-2 critique **29/40**; low-risk fixes (24px targets, Pin stays put, log scroll padding, IME-safe Esc).
- **Page-height bug** found by a new check: screen-reader-only spans inside unpositioned scroll boxes stretched the desktop document (13,645px on the queue view, an existing issue from the "+N more" text, and the same pattern in the new chat log). Fixed with `position: relative` on the four scroll boxes.

**How we test it (follow-up):** fresh throwaway data copy, API on port 8002 (port 8000 was in use by an unrelated app; the earlier 8011 test API from this session was stopped). Regression **48/48** (47 + page height), chat **66/66** (49 + Details ×6, Esc collapse ×2, badge ×7, page height), live **3/3**, mock **6/6**, no console errors. Screenshots at the five widths plus badge and Details states.

**What went wrong / how we fixed it:**
- A wrapped keyboard hint and, more importantly, the escaping hidden spans made the desktop page taller than the viewport; diagnosed with a CDP probe after the screenshot run showed a 37px page shift.
- A network disconnect interrupted the run; on resume, all edits were re-read (none half-applied or duplicated) and the suites re-run from scratch.
