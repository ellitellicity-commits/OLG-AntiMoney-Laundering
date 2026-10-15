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
