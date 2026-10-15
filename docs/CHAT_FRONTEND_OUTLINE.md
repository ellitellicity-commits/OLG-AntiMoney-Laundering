# Chat Panel: Frontend Outline

> **Branch:** `frontend-chat`, stacked on `frontend-polish` (2026-10-15).
> **Plan:** [CHAT_PANEL_PLAN.md](CHAT_PANEL_PLAN.md). This file covers only the frontend parts: §3 (layout), §4 (behaviour), the Pin to case button and its display (§10) and §12.
> **Contract with the backend:** [CHAT_CONTRACT.md](CHAT_CONTRACT.md).
> **Visual direction:** [DESIGN_RESTYLE.md](DESIGN_RESTYLE.md) ("Case File"). The root `PRODUCT.md` and `DESIGN.md` are the source of truth for behaviour and the four risk bands.
>
> **Out of scope (backend teammate):** the `/chat` implementation, retrieval, lookup tools, Groq and Ollama, the server-side safety checks and note storage.

---

## 1. Inventory of the current frontend (before this branch)

| Area | What exists today (`frontend/`) |
|---|---|
| Files | `index.html` (107 lines), `styles.css` (724), `app.js` (1182, one IIFE, no framework), `mock/alerts.json` (5 hand-written alerts: ALR-90001…90005). |
| Views | Two screens switched by `showScreen("queue" \| "overview")` from the masthead buttons `#nav-queue` / `#nav-overview`. **Queue screen** (`main#view-queue.layout`) = docket (`section.queue`) on the left + case file (`section#detail`) on the right, side by side. **Team overview** (`main#view-overview`) = stats, compliance, trends, watchlist, model card, audit trail. |
| State | One `state` object: `alerts`, `view` (filtered + sorted), `selected`, `openId`, `openAlert`, `detail`, `sort {key, dir}`, `mock`, `mockAlerts`, `mockDecisions`, `meta`, `token` (stale-response guard), `minScore`, `askHistory`, `flaggedOnly`, `tab`, `includeWatchlist`, `screen`. |
| Routing | None beyond `showScreen`. Opening an alert renders into `#detail` next to the queue. `openLinked(id)` switches to the queue screen, clears filters if the row is hidden, then opens it. |
| Fetch layer | `api(path, opts)` → `fetch(API + path)`; throws `Error(detail)` on non-2xx. `API` = `?api=` or same origin under `/app/`, else `http://127.0.0.1:8000`. |
| Ask AI tab | 5th detail tab (`TABS` entry `ask`): suggestion chips, `#ask-form`, `#ask-log`, POST `/alerts/{id}/ask` with `askHistory`; history is cleared whenever another alert is opened. Hidden in mock mode. |
| Case summary | `#ai-summary` at the top of the Overview tab, GET `/alerts/{id}/summary`, Regenerate link. |
| Decision forms | Action bar pinned at the foot of the case: Accept, Escalate, Close… (`#close-form`, reason required), Assign… (`#assign-form`), `#decision-msg`, decision history `<details>`. POST `/alerts/{id}/decision`. Refused without an investigator name (except mock). |
| Filters | Search (ID), Band, Team, Anomaly type, Status, Confidence, Sort by (`#f-sort`), column-header sort (`aria-sort`), plain-English search (`#ai-search` → POST `/ai/search`, Clear), Include watchlist (`#f-watchlist`), `state.minScore` (set by the plain-English search). |
| Keyboard | Queue rows: ↑ ↓ PageUp PageDown Home End, Enter opens. `/` focuses search (queue screen). In search: Esc clears, Enter / ↓ go to the first row. `D` focuses Accept. Esc inside `#detail` returns focus to the queue row. Detail tabs: ← → between tabs. Network nodes: Enter opens. |
| Mock mode | When the API is unreachable: banner, 5 mock alerts, plain-English search and Team overview hidden, Ask/Activity/Network tabs hidden, decisions kept in memory. |
| Other | Investigator name in `localStorage` (`olg.investigator`, try/catch wrapper `store`). AI status tag in the masthead, refreshed every 30 s. Case report link. |

## 2. Regression list (must keep working)

Every item is checked again in Part B (automated browser run, throwaway data).

1. Queue loads from the API; skeleton while loading; error state with Retry if the API and mock both fail.
2. Band, Team, Anomaly type, Status and Confidence filters; empty state "No alerts match these filters".
3. Sort by menu; column-header sort with `aria-sort`; "Custom (column)" shown for column-only sorts.
4. ID search; `/` focuses it; Esc clears; Enter / ↓ jump to the first row.
5. Queue keyboard: ↑ ↓ PageUp PageDown Home End; Enter opens the selected alert; selected vs open row styling.
6. Case file: sticky header, profile, compliance tags, large badge, confidence, Case report link.
7. Case summary loads (and Regenerate) at the top of the Overview tab.
8. Detail tabs Overview, Evidence, Activity, Network with ← →; "See all N reasons" jumps to Evidence; peer chart; behaviour group.
9. Activity: timeline, transactions, Show flagged only toggle.
10. Network: graph nodes and list "Open" buttons open the linked alert (clearing filters when needed; WL- turns the watchlist on).
11. Decision bar: Accept, Escalate, Close form (reason required, Cancel), Assign form (Cancel), message, history; decision refused without a name; `D` jumps to Accept.
12. Investigator name remembered in the browser.
13. AI status tag and its 30 s refresh.
14. Plain-English queue search and Clear.
15. Include watchlist toggle and its label count.
16. Team overview: all panels, watchlist Open, audit CSV link.
17. Mock mode: banner, 5 mock alerts, mock decisions in memory, hidden live-only features.
18. Skip link, focus rings, reduced motion.

Removed on purpose (plan §3): the **Ask AI tab**. The `/alerts/{id}/ask` endpoint is untouched.

## 3. Shape brief (`/impeccable shape`)

> Impeccable's shape step normally runs a question round. The brief told me not to wait, so the defaults below were taken from the plan and recorded under §7 "Decisions taken".

- **Job and audience.** An OLG investigator, mid-shift, working through a ranked queue. Mode: **Operate**. They want to ask about the queue as a whole, open a case, and keep asking in the same thread without losing the earlier answers.
- **Outcome and proof.** One conversation that survives every navigation; each answer says what it looked at (context chip, "Now viewing" dividers), who wrote it (provider + model), and whether its numbers and IDs check out. The investigator acts on it only by clicking: IDs open rows, action buttons drive the view, Pin to case files the answer. The chat never decides.
- **Direction.** Inside the existing Case File world, no new visual language. The chat is a **marginal notebook beside the dossier**: paper ground, ink text, serif questions, mono IDs and footers, ruled entries. No bubbles, no avatars, no gradients, no sparkle; the only "AI" mark is the outlined mono `AI` tag the case summary already uses. The accent stays the single interaction colour; the neutral warning style carries unverified numbers and unknown IDs.
- **Scope.** Two-column shell, view router (queue, overview, alert), chat panel, Pin to case button and note display. Untouched: scoring, data, the case file content, decision logic.
- **States.** Empty, Thinking (queued question waits), answer, answer with assumption / unverified numbers / unknown IDs / fallback, offline, `/chat` missing (calm "AI is unavailable"), mock mode ("AI unavailable in offline demo data"), collapsed, overlay (narrow).
- **Anti-goals.** A chat-app look (bubbles, typing dots, avatars); suggested follow-up questions; anything that can submit a decision; colour as the only signal.

## 4. Wireframes

### 4.1 Laptop and desktop (> 1100px): Mode 1, queue

```
┌ MASTHEAD (navy) Sentinel [SYNTHETIC DATA] window · ○ AI status                 [Investigator name ] ┐
├──────────────────────────────────────────────────────────────┬───────────────────────────────────────┤
│ [ Alert queue | Team overview ]                    (~65%)    │ Assistant [AI]      [New chat] [»]    │
│ Alert queue                               156 of 156 alerts  │───────────────────────────────────────│
│ [Search ID ( / )             ] Band Team                     │  Summarise the top 5 structuring      │  ← question, serif
│ Type Status Confidence Sort by                               │  alerts.                              │
│ [Ask the queue in plain English…] [Find]  ☐ Include watchlist│  Assumption: taking "top" as highest  │  ← assumption line
│ RISK   PLAYER · ACTIVITY   TOP REASON · TYPES   TEAM  STATUS │  score.                               │
│ 97 CRITICAL ▮▮▮▮  P01444 …                                    │  1. ALR-00405 (P00405) deposits kept  │  ← IDs = links
│ 97 CRITICAL ▮▮▮▮  P00405 …                                    │     just under $10,000 …              │
│ …                                                            │  [Open ALR-00405] [Show structuring]  │  ← action buttons
│                                                              │  Groq gpt-oss-20b · Numbers checked   │  ← footer, mono
│                                                              │  Cases used: ALR-00405, ALR-00850     │
│ ↑↓ move · Enter open · D decide · Esc back · / search        │                         Pin to case   │
│                                                              │───────────────────────────────────────│
│                                                              │ CONTEXT  Queue · all 156 alerts       │  ← context chip
│                                                              │ [Ask about the queue or a case…     ] │
│                                                              │ Ctrl+K · Enter sends · Shift+Enter ↵ [Send]
└──────────────────────────────────────────────────────────────┴───────────────────────────────────────┘
```

### 4.2 Laptop and desktop: Mode 2, alert

```
├──────────────────────────────────────────────────────────────┬───────────────────────────────────────┤
│ [← Back to queue]  ALR-00405 · P00405   3 of 156 [‹ Prev][Next ›] │  …earlier answers                 │
│ ┌ sticky case header: P00405 [SYNTHETIC]  ╔NEW╗   97 CRITICAL ┐ │ ─── NOW VIEWING ALR-00405 · P00405 ── │  ← divider
│ └ profile · compliance                                        ┘ │  Is this one worse than the ones you  │
│ Overview │ Evidence 14 │ Activity │ Network          (no Ask AI)│  listed?                              │
│  Case summary [AI] …                                          │  Thinking…                            │
│  key facts · confidence · strongest reasons (scrolls)         │───────────────────────────────────────│
│ ┌ action bar: RECOMMENDED ACTION · AML                        ┐ │ CONTEXT  ALR-00405 (P00405)           │
│ │ [Accept recommendation] [Escalate] [Close…] [Assign…]       │ │ [Ask…                               ] │
│ └ Decision history (2) — includes "AI note" entries          ┘ │                              [Send]   │
```

Prev / Next follow the queue's current filter and sort order. "3 of 156" is the open alert's position in that list. If the open alert is no longer in the filtered list, the position reads "not in the current filter" and Prev / Next start from the selected row.

### 4.3 Collapsed (desktop)

```
│ … left area takes the full width …                                                    │A│
│                                                                                       │s│  ← 44px bar, vertical label
│                                                                                       │s│     "Assistant", expand button [«]
```

### 4.4 Tablet (≤ 1100px, e.g. 820) and phone (≤ 560px, e.g. 390)

Below 1100px there is no room for a 360px column next to the case file, so the chat becomes an **overlay**:

```
Collapsed (default)                              Expanded (overlay from the right; full screen on phones)
┌ masthead ─────────────────────────┐            ┌ masthead ────────────┬ Assistant [AI] [New chat] [×] ┐
│ [Alert queue | Team overview]     │            │ (left side dimmed,   │ conversation …                │
│ queue / case in page flow         │            │  still in place)     │                               │
│ …                                 │            │                      │ CONTEXT  ALR-00405 (P00405)   │
├───────────────────────────────────┤            │                      │ [Ask…                 ] [Send]│
│ Assistant [AI] · ALR-00405  [Open]│ ← fixed bar└──────────────────────┴───────────────────────────────┘
└───────────────────────────────────┘
```

- The thin bar sits at the bottom of the viewport and always shows the context, so the investigator knows what the AI would see.
- Ctrl+K or the bar's Open button expands it and focuses the input. Esc (focus inside the chat) or × collapses it and returns focus to the bar.
- Clicking an ID or an action button in the overlay closes the overlay, so the left side is visible.
- The pinned action bar on tall tablets sits above the chat bar, not under it.

### 4.5 Component notes

| Element | Treatment |
|---|---|
| Panel | `--paper` ground, 1px `--rule-strong` left rule. Header: serif "Assistant" + outlined mono `AI` tag (same as the case summary). |
| Question | Serif 15/22, 600, ink. No bubble. |
| Answer | Plex Sans 14/21, ink, max 62ch. Lines starting `- `, `* ` or `1.` render as real lists. Paragraph breaks kept. Text nodes only. |
| Assumption | One line above the answer: label "ASSUMPTION" (uppercase 11px) + the sentence in ink-2. |
| Footer | *Updated after the first critique:* warnings (unverified numbers, unknown IDs) stay visible under the answer; the provider line, "Numbers checked" and "Cases used" sit in a collapsed **Details** disclosure next to Pin to case. Originally: mono 12/16 ink-2: `Groq gpt-oss-20b` / `Ollama llama3.2 · local`, `· fallback` when `fallback_used`, then "Numbers checked" or the neutral warning line "Not found in the evidence: …". Unknown IDs: warning line "Unknown ID, not in the data: …". "Cases used: …" (clickable). |
| Clickable IDs | Mono `btn-link`, accent, underlined. Unknown or unresolvable IDs stay plain mono text. |
| Action buttons | Small outlined `.btn`. Label written by the frontend from the validated action, never by the model (see §5.7). |
| Pin to case | Small text button at the end of the footer. After pinning: "Pinned to ALR-00405" (ink-2). Mode 1: an inline select of the alerts mentioned + Pin / Cancel. |
| New chat | Outlined small button in the panel header; clears immediately, no confirmation (plan §4). |
| Divider | `role="separator"`, rules either side, mono uppercase 11px "Now viewing ALR-00405 · P00405". |
| Thinking… | ink-2 text under the question; `aria-busy` on the entry. A second question shows "Waiting for the previous answer…". No animated dots. |
| Context chip | Bordered strip above the input: "CONTEXT" label + value. Examples: `Queue · all 156 alerts`, `Queue · AML · Critical · 29 alerts`, `ALR-00405 (P00405)`, `Overview`. |
| Notice | Offline, `/chat` missing, errors: neutral bordered note in ink-2. Never red, never a risk colour. |
| Notes in history | The decision history lists AI notes with the label "AI note", the question, the answer, the provider and "pinned by <name>", plus Remove. |

Motion: overlay slide and collapse ≤ 200ms; none under `prefers-reduced-motion` (the global rule already exists).

## 5. Technical design

### 5.1 State additions

```js
state.screen        // "queue" | "overview" | "alert"   (was "queue" | "overview")
state.chat = {
  messages: [],      // {id, role: "user"|"assistant"|"divider"|"notice", ...}
  queue: [],         // questions waiting for the previous answer
  busy: false,
  collapsed: false,  // per viewer, localStorage (convenience only)
  stubNotes: {},     // ?chat=stub only: alert_id -> [note]
}
```

Message records:
- `user`: `{id, role, content, context}` (context = snapshot at send time).
- `assistant`: `{id, role, question, data}` where `data` is the **sanitised** response (§5.6), plus `pinned: [{alert_id, note_id}]`.
- `divider`: `{id, role, alert_id, player_id}`.
- `notice`: `{id, role, text}`; never sent to the backend.

`state.askHistory` and the Ask tab code are removed.

### 5.2 View router

`showScreen(name)` handles three views; the left area shows exactly one:

| View | Shown | Entered by |
|---|---|---|
| `queue` | `#view-queue` (docket) + mode tabs | `#nav-queue`, Back to queue, Esc in Mode 2 |
| `overview` | `#view-overview` + mode tabs | `#nav-overview` |
| `alert` | `#view-alert` (alert bar + `#detail`) | row click / Enter, network/watchlist Open, chat IDs and actions, Prev / Next |

- `#nav-queue` and `#nav-overview` keep their ids and `aria-pressed`, but move from the masthead to the top of the left area (plan §3, Mode 1 "[ Queue | Overview ]").
- **Prev / Next** use `state.view` (the current filter + sort). Index = position of `state.openId` in `state.view`; if absent, the selected row. Moving also moves `state.selected`, so Back lands on the same row.
- **Back to queue** shows the queue, keeps the selection on the open row and focuses it.
- Filter changes in Mode 1 rebuild `state.view`; the next Prev / Next uses the new order.
- A refresh restores the conversation, not the view: the page reopens in Mode 1 (the plan only asks for the conversation to survive).

### 5.3 Context builder

```js
buildContext() → {
  view: state.screen,                                  // "queue" | "overview" | "alert"
  alert_id: state.screen === "alert" ? state.openId : null,
  filters: { band, team, type, status, confidence, min_score, search, include_watchlist },  // null when unset
  sort: "-score",                                      // "-key" = descending, "key" = ascending
  visible_count: state.view.length,
}
```

The chip text is derived from the same object, so the chip and the request can never disagree.

### 5.4 Message store

- `sessionStorage["olg.chat.v1"]` = `{messages, stubNotes}`; every read and write in try/catch. Without storage the chat still works for the life of the page.
- Saved after every change; capped at the last 200 entries.
- Loaded once at start-up; anything that fails validation on load is dropped.
- Only **New chat** clears it.

### 5.5 Transport

```
sendQuestion(text) → push user message (+ context snapshot) → enqueue
processQueue()     → one at a time: transport(question, context, history) → assistant message or notice
transport = chatStub   when ?chat=stub
          = chatLive   otherwise (POST API + "/chat")
          = unavailable message in mock mode without ?chat=stub ("AI unavailable in offline demo data")
```

- **History sent:** the last 12 entries with role `user`, `assistant` or `divider`, as `{role, content}` (divider content = "Now viewing ALR-00405 (P00405)"). Notices are never sent.
- **Live errors:** 404 / 405 → "AI is unavailable: this API does not have the /chat endpoint yet. The rest of the dashboard works as usual." Network failure → "AI is unavailable: the API could not be reached." Other errors → "AI is unavailable: <status>". All shown as calm notices.
- **Stub** (`?chat=stub`): built in, no network, answers in the contract shape after a short delay, using only data the page already has (the visible queue, the open alert). Trigger words for testing are listed in [CHAT_CONTRACT.md §4](CHAT_CONTRACT.md). It also stubs the notes endpoints (in sessionStorage).

### 5.6 Safe rendering and validation

- **No `innerHTML` for anything from the model or the user.** The whole chat log is built with `document.createElement` + `textContent`.
- The response is sanitised field by field: `answer` string (≤ 8,000 chars), `provider`/`model` string or null, booleans coerced, `unverified_numbers` strings, `unknown_ids` / `cases_used` only strings matching the ID patterns, `assumption` string or null, `actions` validated (§5.7). Unexpected fields are ignored.
- **Clickable IDs:** the answer is split on `/\b(P\d{5}|ALR-\d{5}|WL-\d{5})\b/`. A match is a link only if it is not in `unknown_ids` **and** it resolves to a row the page knows (`P…` → that player's alert). Otherwise it stays plain mono text.

### 5.7 Action whitelist

| `type` | Payload | Valid when | Effect on click |
|---|---|---|---|
| `open_alert` | `alert_id` | matches ALR-/WL- pattern, not in `unknown_ids`, exists in `state.alerts` | `openLinked(id)` |
| `apply_filter` | `filters` with keys `band`, `team`, `type`, `status`, `confidence`, `min_score` only | every key known and every value in `state.meta` / `CONFIDENCE`; `min_score` integer 0–100 | set the filter controls, go to the queue, `applyView()` |
| `sort` | `sort` (`"-score"`, `"last_activity"`…) | key in the frontend's sort keys | `setSort` + `applyView()`, go to the queue |
| `show_watchlist` | none | always (live data only) | tick Include watchlist, go to the queue |

- Any unknown type, extra filter key or invalid value drops **that action**. At most 4 actions per answer.
- The button label is always written by the frontend from the validated values ("Open ALR-00405", "Show Critical · AML", "Sort by last activity"); the model's `label` is ignored, so an answer cannot put a misleading label on a button.
- `apply_filter` **replaces** the queue filters (like the plain-English search does): the named filters are set, the others and the ID search are cleared.
- Nothing runs until the investigator clicks. **There is no decision action type, and no code path from the chat to `decide()` or `/decision`.**

### 5.8 Dividers

On opening an alert: if the conversation has at least one message and the most recent divider is not for this alert (or the investigator asked something from another view since), add `Now viewing ALR-… · P…`. If the last entry is already a divider with no messages after it, it is replaced instead of stacking.

### 5.9 Pin to case

- **Mode 2:** pins to the open alert. **Mode 1:** an inline picker lists the alerts named in the answer (`cases_used` + clickable IDs); if none, it says "This answer names no alert. Open an alert to pin it there."
- Requires the investigator name (same message and focus as decisions).
- POST `/alerts/{id}/notes` `{question, answer, provider, model, verified, investigator}`. 404 / 405 → "Not pinned: this API has no notes endpoint yet." Stub mode stores it in memory + sessionStorage.
- **Display:** the decision history lists `alert.notes` (live) or the stub notes merged into it, labelled "AI note", with "AI-generated, pinned by <name>" and a Remove button (DELETE `/alerts/{id}/notes/{note_id}?investigator=…`, also name-checked).

### 5.10 Keyboard

| Key | Where | Action |
|---|---|---|
| All existing shortcuts | as before | unchanged (§2) |
| **Ctrl+K** (⌘K on Mac) | anywhere | expand the chat if collapsed and focus its input |
| Enter / Shift+Enter | chat input | send / new line |
| **Esc** | Mode 2, focus not in a field and not in the chat | back to the queue, focus the open row (replaces "focus the queue row") |
| Esc | inside the chat, any width (not in the pin picker's select) | collapse the panel to the rail or bar and focus it; Ctrl+K opens it again |
| `D` | Mode 2 only | focus Accept (it no longer fires in Mode 1, where the case is hidden) |
| `/` | queue view | focus search (unchanged) |

### 5.11 Announcements and focus

- One visually hidden `aria-live="polite"` region (`#chat-live`) announces: "Thinking…", "Answer: <first 160 characters>", "AI unavailable…", "New chat started", "Pinned to ALR-…", "Opened ALR-…". The log itself is not live (avoids re-reading the whole log).
- The log is an `<ol>` with `aria-label="Conversation"`; each answer entry has `aria-busy` while thinking.
- After Send, focus stays in the input. New chat → input. Collapse → expand button; expand → input. Back → open row. Clicking an ID on desktop keeps focus in the chat; in the overlay it closes the overlay and focuses `#detail`.

## 6. Work items, labels and build order

| # | Work item | Label | Regression risk |
|---|---|---|---|
| 1 | Two-column shell in `index.html` (`main#work` + `aside#chat`), mode tabs moved into the left area, `#view-alert` wrapper | UI only | Medium: ids must stay; desktop scroll containers change |
| 2 | Router: `showScreen` with `alert`, Back, Prev / Next, Esc → queue, `D` only in Mode 2 | JS state | High: every open path (`openAlert`, `openLinked`, decide re-render) |
| 3 | Remove the Ask AI tab and its code | JS state | Low |
| 4 | Chat panel markup + CSS (panel, collapsed bar, overlay, messages, chip) | UI only | Medium: responsive rules |
| 5 | Context builder + chip | JS state | Low |
| 6 | Message store (sessionStorage, try/catch) + New chat | JS state | Low |
| 7 | Transport: stub + live POST `/chat` + mock-mode message | JS state / **needs backend** for live answers | Low |
| 8 | Safe renderer: text nodes, lists, ID links, footer, actions | JS state | Medium: XSS if done wrong (tested with `<img onerror>` / `<script>` answers) |
| 9 | Dividers | JS state | Low |
| 10 | Pin to case + notes in history | JS state / **needs backend** for live storage | Low |
| 11 | Keyboard (Ctrl+K, Esc) + aria-live + focus | JS state | Medium: must not steal existing keys |
| 12 | Docs, checks, screenshots | — | — |

Build order: 1 → 2 → 3 (router works with no chat) → 4 → 5 → 6 → 7 → 8 → 9 → 10 → 11 → 12.

## 7. Decisions taken

All open decisions were taken with the proposed default, without waiting (as instructed):

1. **No question round for `/impeccable shape`:** defaults taken from the plan; this list records them.
2. **Narrow screens (≤ 1100px):** the chat is an overlay from the right (full screen ≤ 560px), collapsed by default to a fixed bottom bar that shows the context.
3. **Desktop width:** chat = `max(360px, 35%)`, collapsible to a 44px bar; the collapsed state is a per-viewer convenience in localStorage.
4. **Mode tabs:** `#nav-queue` / `#nav-overview` move from the masthead into the left area (plan §3), ids unchanged.
5. **Refresh restores the conversation, not the view** (opens in Mode 1).
6. **Dividers** only when the conversation is non-empty; a divider with no messages after it is replaced, not stacked.
7. **Context sort format:** `"-key"` for descending, `"key"` for ascending, using the frontend's sort keys (`score`, `last_activity`, `ai`, `player_id`, `top_reason`, `team`, `status`).
8. **Filters object** always has all eight keys, `null` when unset.
9. **Action type names:** `open_alert` and `apply_filter` from the plan; `sort` and `show_watchlist` added by the frontend for the other two whitelist entries (the backend must agree; listed in CHAT_CONTRACT.md).
10. **Offline response:** the same shape with `provider: null`, `model: null` and the offline note in `answer`; HTTP errors and a missing `/chat` are handled by the frontend as notices.
11. **Notes response shapes** (POST returns the stored note; `/alerts/{id}` gains `notes`) are frontend proposals in CHAT_CONTRACT.md; the request shapes are the plan's.
12. **Clickable IDs** must also resolve to a row the page knows; otherwise they stay plain text.
13. **Questions asked while one is in flight** wait in a queue; the context is captured when the question is sent, not when it is processed.
14. **Mock mode:** the chat shows "AI unavailable in offline demo data" with the input disabled, unless `?chat=stub` is set (so the stub can be tested without the API).
15. **Pin in Mode 1 with no alert named:** the picker says so and pins nothing.
16. **`D`** only acts in Mode 2 (the decision buttons are hidden in Mode 1).
17. **Skip links:** "Skip to main content" and "Skip to AI assistant".
18. **Action labels** are always generated by the frontend; the model's `label` field is ignored.
19. **`apply_filter` replaces** the current filters instead of adding to them.
20. **Pinning requires the investigator name even in mock mode** (decisions in mock mode do not; the plan says pinning needs the name "like decisions do", and the stricter reading was taken).
21. **Live `/chat` errors are never sent back** to the backend as history; only user, assistant and divider entries are.
22. **Answer metadata:** warnings always visible; provider and model, "Numbers checked" and "Cases used" in a native `<details>` "Details" disclosure, collapsed by default (keyboard: Tab to it, Enter or Space toggles; screen readers hear "Details: source, number check and cases used").
23. **New-answer badge:** while the panel is collapsed, answers and notices that arrive increment a count badge on the rail (desktop) and the bottom bar (narrow); the count is in the bar's accessible name and announced through `#chat-live` (moved outside the collapsible body so it still speaks). Opening the panel clears it. When collapsed, the full answer is not announced, only the count.
24. **Desktop collapse shortcut:** Esc inside the chat collapses it at every width (it already did in the overlay), and Ctrl+K reopens it. It cannot clash with the other shortcuts: arrows, Enter, `/` and `D` do nothing new; Esc in search, in the case file and in Mode 2 outside the chat keep their meaning because this one fires only when focus is inside the chat.
25. **New chat has no confirmation and no undo — deliberate.** Plan §4: "New chat clears it straight away. No confirmation is needed: anything worth keeping has already been saved, because Pin to case saves immediately."
