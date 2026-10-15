# Chat Panel: Start Here

> One page for teammates and their AI assistants. Last updated 2026-10-15.

## What it is

A persistent AI chat panel on the right of the dashboard (about 35% wide, collapsible to a thin rail; a bottom bar and overlay below 1100px). The left side switches between the **alert queue**, the **Team overview** and **one alert** (Back to queue, Previous, Next). The conversation survives every navigation and a browser refresh; only **New chat** clears it. The chat always shows what it is looking at (context chip, "Now viewing" dividers), makes known player and alert IDs clickable, offers whitelisted action buttons (open alert, apply filter, sort, show watchlist) that run only when clicked, and can **Pin to case** an answer as an AI note. It **cannot record or trigger a decision**. The old "Ask AI" tab is gone.

Design and rules: [CHAT_PANEL_PLAN.md](CHAT_PANEL_PLAN.md) (the plan) · [CHAT_FRONTEND_OUTLINE.md](CHAT_FRONTEND_OUTLINE.md) (frontend design and decisions) · [CHAT_CONTRACT.md](CHAT_CONTRACT.md) (the agreed `/chat` and notes shapes).

## Where it lives

Branch **`frontend-chat`**, stacked on `frontend-polish` (the Case File restyle). It is **not merged anywhere**.

```
git fetch origin
git checkout frontend-chat
```

Or keep your own folder untouched: `git worktree add ..\AML-chat frontend-chat`.

## Test it

Start the API as usual (`.\run_demo.ps1 -SkipPipeline`, or `uvicorn backend.app.main:app`), then open:

| URL | What you get |
|---|---|
| `http://127.0.0.1:8000/app/?chat=stub` | The built-in **stub**: answers in the contract's shape from the rows on screen, no network, no AI model. Notes are stubbed too (kept in that browser tab). |
| `http://127.0.0.1:8000/app/` | **Live mode**: posts to `/chat`. Until the backend has it, the chat shows "AI is unavailable: this API does not have the /chat endpoint yet" and the rest of the dashboard works. |
| API not running (mock data) | The chat shows "AI unavailable in offline demo data". Add `?chat=stub` to test the chat anyway. |

Stub trigger words (in the question): `top` / `summarise` (IDs + actions), `recent` / `big` (assumption), `numbers` (unverified numbers), `unknown` (unknown IDs), `fallback`, `offline`, `error`, `xss` (hostile text, must render as plain text). Anything else gets a plain answer about the queue or the open alert.

Keyboard: **Ctrl+K** opens the assistant and focuses its input · **Enter** sends, **Shift+Enter** new line · **Esc** inside the assistant collapses it · **Esc** in an open alert (outside the assistant) goes back to the queue · existing ↑ ↓ Enter / D shortcuts unchanged.

## What is built and what is stubbed

| Built (frontend) | Stubbed with `?chat=stub` |
|---|---|
| Two-column shell; queue / overview / alert views; Back, Previous, Next (follow filter + sort); Esc back to the queue; `D` only in the alert view | `/chat` answers |
| Chat panel: context chip, dividers, Thinking… and queued questions, warnings always visible, a collapsed **Details** disclosure (provider, number check, cases used), clickable IDs, action buttons, Pin to case, New chat | Notes endpoints |
| Conversation in sessionStorage (try/catch; works without it); new-answer badge while collapsed | |
| Ctrl+K, Esc to collapse, aria-live announcements, keyboard-only use, overlay on narrow screens | |
| Safe rendering (text nodes only), ID and action validation | |

## Backend teammate must provide

1. `POST /chat`, exactly as in [CHAT_CONTRACT.md](CHAT_CONTRACT.md) §1.
2. `POST /alerts/{id}/notes` and `DELETE /alerts/{id}/notes/{note_id}?investigator=…` (plan §10, §11).
3. **CORS allowing `DELETE`** (today `allow_methods` is only `GET` and `POST`), so a pinned note can be removed from the browser.
4. Notes in `GET /alerts/{id}` (`notes: [...]`), in `GET /audit`, in `/audit.csv` and in the printable case report.
5. Confirmation (or a counter-proposal) of every item marked **PROPOSED, needs backend confirmation** in [CHAT_CONTRACT.md](CHAT_CONTRACT.md) §3: the sort and filters shape, the `sort` / `show_watchlist` action type names, the offline answer shape and the notes response shapes.

## Decisions taken

From [CHAT_FRONTEND_OUTLINE.md](CHAT_FRONTEND_OUTLINE.md) §7; all defaults were taken without waiting, as instructed.

1. **No question round for `/impeccable shape`:** defaults taken from the plan.
2. **Narrow screens (≤ 1100px):** the chat is an overlay from the right (full screen ≤ 560px), collapsed by default to a fixed bottom bar that shows the context.
3. **Desktop width:** `max(360px, 35%)`, collapsible to a 44px rail; the collapsed state is a per-viewer convenience in localStorage.
4. **View switch** (`#nav-queue` / `#nav-overview`) moved from the masthead into the work area, ids unchanged.
5. **Refresh restores the conversation, not the view** (opens on the queue).
6. **Dividers** only once the conversation has started; a divider with no messages after it is replaced, not stacked.
7. **Context sort format:** `"-key"` descending, `"key"` ascending.
8. **Filters object** always has all eight keys, `null` when unset.
9. **Action type names:** `open_alert`, `apply_filter` (plan) plus `sort`, `show_watchlist` (proposed).
10. **Offline response:** same shape with `provider: null`; HTTP errors and a missing `/chat` become calm notices.
11. **Notes response shapes** are frontend proposals; the request shapes are the plan's.
12. **Clickable IDs** must also resolve to a loaded row.
13. **Questions asked while one is in flight** wait in a queue; context is captured when sent.
14. **Mock mode:** "AI unavailable in offline demo data", input disabled, unless `?chat=stub`.
15. **Pin in the queue view with no alert named:** says so and pins nothing.
16. **`D`** only acts in the alert view.
17. **Skip links:** main content and AI assistant.
18. **Action labels** are always written by the frontend; the model's `label` is ignored.
19. **`apply_filter` replaces** the current filters.
20. **Pinning needs the investigator name**, even in mock mode.
21. **Error notices are never sent back** to the backend as history.
22. **Answer metadata:** warnings always visible; provider and model, "Numbers checked" and "Cases used" in a collapsed, keyboard-accessible **Details** disclosure.
23. **New-answer badge** on the rail and the bottom bar while collapsed, announced through aria-live, cleared on open.
24. **Esc inside the assistant collapses it** at every width; Ctrl+K reopens it. No clash with the other shortcuts.
25. **New chat has no confirmation and no undo — deliberate**, as plan §4 says (Pin to case already saves what matters).

## Not verified

- A real `/chat` and the notes endpoints (they do not exist yet; only the missing-`/chat` path was tested live).
- A real AI model (the test data had no provider configured).
- Real screen readers (only DOM semantics, accessible names and the aria-live text were checked).
- Real touch devices (only mobile emulation in headless Edge).

## Files changed on this branch

- `frontend/index.html`: two-column shell, view switch moved into the work area, alert navigation strip, chat panel markup, badge, skip links.
- `frontend/app.js`: router (`showScreen`, `backToQueue`, `stepAlert`), the chat module (context, store, transport, stub, renderer, whitelist, dividers, pin, badge), decision history built as DOM with AI notes, Ask AI tab removed, `api()` errors carry `status`.
- `frontend/styles.css`: shell layout, view switch, alert strip, chat panel, rail, bottom bar and overlay, Details disclosure, badge, AI-note history.
- `docs/`: `CHAT_PANEL_PLAN.md`, `CHAT_FRONTEND_OUTLINE.md`, `CHAT_CONTRACT.md`, `CHAT_HANDOFF.md`, `DESIGN_RESTYLE.md` (§9 Chat panel), `PROMPTS.md` (Chat panel frontend).

## Known gaps

- The view is not restored after a refresh (the conversation is).
- Stub notes live only in that browser tab's sessionStorage.
- More in [DESIGN_RESTYLE.md](DESIGN_RESTYLE.md) §9.

## Local tool state (do not commit)

The untracked **`.impeccable/`** folder holds Impeccable's local settings, including the narrow detector ignores recorded during the critique (cream palette, `<kbd>` bevel, a `color-mix` contrast misread, a table hairline). They are **local only**: the folder is not part of this branch and must not be committed, so a teammate's detector will report those false positives again.

## Rules for any AI assistant working on this branch

1. Read `docs/CHAT_PANEL_PLAN.md`, `docs/CHAT_CONTRACT.md` and `docs/CHAT_FRONTEND_OUTLINE.md` first.
2. Never push to or merge into `integration`, `main`, `wireframe` or `frontend-polish`. Work on `frontend-chat` (or a branch from it).
3. Never change the `/chat` or notes request/response shapes without the team agreeing; update CHAT_CONTRACT.md in the same change.
4. The chat must never record, draft-and-submit or trigger a decision (Accept, Escalate, Close, Assign). No decision endpoint may be reachable from chat code.
5. Never render model text with `innerHTML`; keep the ID patterns and the action whitelist.
6. Never write an API key or secret anywhere (code, docs, commits). Keys live only in `.env`, which is git-ignored.
7. Do not touch `backend/`, `data/`, `run_demo.ps1`, requirements files or the root `PRODUCT.md` / `DESIGN.md` from this branch. Never commit `.claude/` or `.impeccable/`.
