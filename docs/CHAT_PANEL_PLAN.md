===================================================================================================
PLAN: Persistent, context-aware AI chat panel for the Player Risk Review dashboard
Status: agreed design, not built yet. Build on a new branch off `wireframe`.
===================================================================================================

CONTENTS
  1.  The idea in one paragraph
  2.  Decisions already made
  3.  Layout
  4.  How the chat behaves
  5.  The "answer only, never ask back" rule
  6.  What the AI can see (context)
  7.  Multi-player questions: retrieval and tools
  8.  Safety checks on every answer
  9.  AI provider: Groq first, automatic fallback
  10. Pin to case
  11. Backend changes (API design)
  12. Frontend changes
  13. Who builds what
  14. How we know it works (acceptance checks)
  15. Demo script changes
  16. Risks and how we handle them
  17. Suggested build order


---------------------------------------------------------------------------------------------------
1. THE IDEA IN ONE PARAGRAPH
---------------------------------------------------------------------------------------------------

Today the AI chat lives inside one alert ("Ask AI" tab), so an investigator has to open a row before
they can ask anything, and the conversation is lost when they open another row. The new design puts
one AI chat panel permanently on the right side of the screen, like the chat panel in VS Code. The
left side changes (the alert queue, then a player's data when a row is clicked), but the chat stays
open and keeps the whole conversation until the investigator clicks "New chat". The chat always
knows what is on screen, so the investigator can ask about the whole queue ("summarise the top 5
structuring alerts"), open a player, and keep the same conversation going ("how does this one
compare with the ones you just summarised?").


---------------------------------------------------------------------------------------------------
2. DECISIONS ALREADY MADE
---------------------------------------------------------------------------------------------------

  Layout in mode 2     The player's data REPLACES the queue on the left, with "Back to queue" and
                       next / previous arrows. (Not a three-column layout.)
  Chat reset           Only the "New chat" button resets it. It survives navigation and an
                       accidental browser refresh (kept for that browser tab).
  Chat powers          Answers, clickable player / alert IDs, and action buttons that drive the view
                       ("Apply filter", "Open ALR-00405"). It can NEVER record decisions
                       (Accept / Escalate / Close / Assign); the investigator always does that.
  Case summary         The AI case summary stays at the top of each alert's data on the left. The
                       chat is for questions on top of it.
  Retrieval            The backend always gathers the relevant cases first; on Groq the AI can also
                       call read-only lookup tools.
  Follow-up questions  The AI only answers what was asked. It never asks the investigator questions,
                       never offers further help, never suggests next questions (section 5).
  Saving answers       "Pin to case" saves an AI answer to that alert's notes, the audit trail and
                       the printable case report, labelled as AI-generated.
  AI provider          Groq first (fast, 20B model); automatic fallback to local Ollama; built-in
                       template / offline message if neither works.
  Demo laptop          The Ryzen AI 7 / 30 GB laptop (Ollama + llama3.2 already installed and
                       measured there: 3-20 s per summary).


---------------------------------------------------------------------------------------------------
3. LAYOUT
---------------------------------------------------------------------------------------------------

Mode 1: on opening the dashboard

  +--------------------------------------------------------------+-----------------------+
  | Top bar: title, SYNTHETIC DATA, AI status, Investigator name  |                       |
  +--------------------------------------------------------------+   AI CHAT PANEL       |
  | [ Queue | Overview ]                                          |                       |
  | Filters, sort, search, include watchlist                      |  Context: Queue ·     |
  |                                                               |  AML · 156 alerts     |
  |  97 CRITICAL  P01444  Deposits far above declared income ...  |                       |
  |  97 CRITICAL  P00405  Deposits kept just under $10,000  ...   |  (conversation)       |
  |  ...                                                          |                       |
  |                                                               |  [ New chat ]         |
  |                                                               |  [ Ask...      ] Send |
  +--------------------------------------------------------------+-----------------------+

Mode 2: after clicking a row

  +--------------------------------------------------------------+-----------------------+
  | <- Back to queue     P00405 · ALR-00405     < prev  next >    |  ...earlier messages  |
  | [ Overview | Evidence | Activity | Network ]                  |  ---- Now viewing     |
  |  AI case summary, key facts, confidence, reasons ...          |       ALR-00405 ----  |
  |  (scrolls)                                                    |  Context: ALR-00405   |
  |                                                               |                       |
  | Recommended action + decision buttons (pinned at the bottom)  |  [ Ask...      ] Send |
  +--------------------------------------------------------------+-----------------------+

Details
  - Width: left about 65%, chat about 35% (min 360 px). The chat can be collapsed to a thin bar.
  - The "Ask AI" tab is removed from the alert view; the chat panel replaces it.
  - The Overview screen becomes a tab on the left in mode 1; the chat can see its statistics.
  - Next / previous arrows move through the queue in its current filter and sort order.
  - Keyboard: keep the existing shortcuts (arrow keys, Enter, /, D, Esc). Add one to jump to the
    chat input (suggestion: Ctrl+K) and make Esc in mode 2 go back to the queue.


---------------------------------------------------------------------------------------------------
4. HOW THE CHAT BEHAVES
---------------------------------------------------------------------------------------------------

  - One continuous conversation. Opening rows, going back, changing filters or switching to the
    Overview tab never clears it.
  - "New chat" clears it straight away. No confirmation is needed: anything worth keeping has
    already been saved, because "Pin to case" saves immediately.
  - Accidental browser refresh: the conversation is restored (stored in sessionStorage, which
    belongs to that browser tab; wrap every read/write in try/catch and work without it).
  - Context chip above the input always says what the AI is looking at:
      "Context: Queue · all alerts"   "Context: Queue · AML · Critical · 29 alerts"
      "Context: ALR-00405 (P00405)"   "Context: Overview"
  - When the investigator opens a different row, a divider is added to the conversation:
      ---- Now viewing ALR-00405 ----
    From then on "this player" / "this case" means the open alert, while earlier players stay in
    the conversation and can still be referred to by ID or as "the ones you summarised".
  - Player and alert IDs in AI answers (P00405, ALR-00405, WL-02014) are clickable and open that row.
  - Action buttons: the AI can attach buttons to its answer, chosen from a fixed list:
      Open <alert>        Apply filter <band/team/type/status/confidence/min score>
      Sort by <key>       Show watchlist
    Clicking one changes the left side. Nothing happens unless the investigator clicks.
  - The AI never records, drafts-and-submits, or suggests submitting decisions.
  - While the AI is working: "Thinking..." with the context chip, and the input stays usable
    (a new question waits for the previous one).
  - Each answer shows a small footer: provider + model ("Groq gpt-oss-20b" / "Ollama llama3.2 ·
    local"), and "numbers checked" or the orange list of numbers not found in the evidence.


---------------------------------------------------------------------------------------------------
5. THE "ANSWER ONLY, NEVER ASK BACK" RULE
---------------------------------------------------------------------------------------------------

This assistant is not a typical copilot. It answers exactly what the investigator asked and stops.

  Never:  ask the investigator a question ("Do you want me to compare them?")
          offer more help ("Let me know if you'd like...", "I can also...")
          suggest next questions or next steps beyond the case's recommended action
          ask for clarification

  Ambiguous questions: the AI states its assumption in ONE short line, then answers.
      Investigator: "show me the recent big depositors"
      AI: "Taking 'recent' as the last 30 days and 'big' as $10,000 or more: ..."
  If the investigator meant something else, they rephrase.

  Enforced in two places:
  1. The system instructions say so explicitly (and the examples in the prompt follow it).
  2. An automatic check after every answer (same idea as the existing number check):
       - remove a final sentence that ends with "?" or starts with an offer pattern
         ("Would you like", "Do you want", "Let me know", "Shall I", "I can also", "Feel free",
          "If you'd like", "Want me to")
       - if a question appears elsewhere in the answer, regenerate once with a reminder; if it
         still happens, strip the offending sentences.
     Unit-test the check with a list of example answers.


---------------------------------------------------------------------------------------------------
6. WHAT THE AI CAN SEE (CONTEXT)
---------------------------------------------------------------------------------------------------

Every chat request sends the conversation plus a "context" object describing the screen:

  view          "queue" | "overview" | "alert"
  alert_id      the open alert (mode 2), e.g. "ALR-00405"
  filters       the queue filters currently applied (band, team, type, status, confidence,
                min_score, search, include_watchlist) and the sort
  visible_count how many alerts the queue is showing

From that, the backend builds what the AI reads (never the raw database):
  Mode 2:   the open alert's full case file (the same compact file the current summary and Q&A
            use: reasons, evidence, peers, behaviour group, linked accounts, flags, decisions).
  Mode 1:   a compact table of the alerts the question is about (section 7), plus queue statistics
            (counts by band, team, confidence, compliance indicators).
  Overview: the statistics and trends shown on the Overview tab.
  Always:   the cases the conversation has already discussed (by ID), kept short, so follow-up
            questions like "compare it with the first one" work.

Size limit: keep what the AI reads under about 6,000 words. Long case lists are cut to the most
relevant (highest score first) and the AI is told how many were left out, so it can say so.


---------------------------------------------------------------------------------------------------
7. MULTI-PLAYER QUESTIONS: RETRIEVAL AND TOOLS
---------------------------------------------------------------------------------------------------

The AI cannot read all ~300 alerts at once. Two layers:

Layer 1: backend retrieval (always on, works with any model including the small local one)
  Before calling the AI, the backend picks the relevant cases:
    a. IDs mentioned in the question or recent conversation (P00405, ALR-00405, "the first one").
    b. Filters found in the question by the existing plain-English parser (ai.parse_search):
       "critical AML alerts with linked players" -> band=Critical, team=AML, type=linked_players.
    c. Otherwise the current queue filters.
    d. Ranking words: "top 5", "highest", "most recent", "lowest confidence".
  It then sends compact rows for up to ~20 cases (ID, score, band, team, confidence, top reasons
  with their numbers, recommended action) and full case files for up to 3 cases when the question
  needs detail ("compare P00405 and P02426").

Layer 2: lookup tools (only when the provider supports tool calling well: Groq gpt-oss-20b)
  The AI may call these READ-ONLY tools for questions Layer 1 didn't cover:
    search_alerts(filters, sort, limit)    -> compact rows
    get_case(alert_id)                     -> one full case file
    get_stats()                            -> the Overview statistics
    get_linked_accounts(player_id)         -> the network cluster
    get_transactions(player_id, flagged_only, limit)
  Rules: at most 4 tool calls per answer; tools can only read; every tool result counts as
  evidence for the number check. On Ollama, tools are switched off and Layer 1 alone is used.

Example questions this must handle (use them as the test list):
  "Summarise the top 5 structuring alerts."
  "Which critical alerts involve linked accounts, and how many accounts are in each ring?"
  "Compare P00405 and P02426."
  (in mode 2) "Why is this player High confidence?"
  (in mode 2, after the summary question) "Is this one worse than the structuring cases you listed?"
  "How many Safer Gambling alerts are still New?"
  "Which alerts have a sanctions screening match?"


---------------------------------------------------------------------------------------------------
8. SAFETY CHECKS ON EVERY ANSWER
---------------------------------------------------------------------------------------------------

  1. Number check (exists today in backend/app/ai.py): every number in the answer must appear in
     the evidence the AI was given (case files, rows, statistics, tool results). Unverified numbers
     are flagged in orange under the answer.
  2. ID check (new): every player / alert ID in the answer must exist; unknown IDs are flagged and
     not made clickable.
  3. No-follow-up check (new, section 5).
  4. Action check (new): action buttons are only rendered if they come from the fixed list and their
     values are valid (same validation as clean_filters in ai.py).
  5. Grounding instructions (exist today): only facts from the evidence; "indicates / is consistent
     with", never accusations; no field names.
  6. The AI never records decisions, and nothing it writes is stored unless the investigator pins it.


---------------------------------------------------------------------------------------------------
9. AI PROVIDER: GROQ FIRST, AUTOMATIC FALLBACK
---------------------------------------------------------------------------------------------------

  Order:  Groq (GROQ_API_KEY in .env) -> Ollama on this laptop -> built-in template / offline note.
  Fallback must be automatic per request: if Groq times out, errors, or hits a rate limit, retry
  the same request on Ollama straight away (today the code falls back only to the template).
  The answer footer says which provider answered; the top-bar AI status shows both
  ("AI: Groq · fallback Ollama ready").
  Ollama model: llama3.2 today; try qwen2.5:7b on this laptop (30 GB RAM) and keep it if answers are
  better and still fast enough (target under 20 s).
  Pitch line: "In production this runs on a locally hosted model so player data never leaves OLG;
  for the demo we use a free hosted model for speed, and the same code runs fully offline."
  Never put the Groq key in chat or in git. It lives only in .env (git-ignored).
  Warm-up: a small script (or API endpoint) that pre-generates and caches the case summaries for
  the showcase alerts before the demo.


---------------------------------------------------------------------------------------------------
10. PIN TO CASE
---------------------------------------------------------------------------------------------------

  - Every AI answer has a "Pin to case" button when an alert is open (mode 2). In mode 1, the
    button asks which of the alerts mentioned in the answer to pin it to.
  - Pinning saves: the question, the answer, provider + model, the number-check result, the
    investigator's name and the time.
  - It appears in the alert's decision history (marked "AI note"), in GET /audit and the CSV, and in
    the printable case report under "AI notes (AI-generated, reviewed by <name>)".
  - Pinning needs the investigator name, like decisions do.
  - A pinned note can be removed by the investigator; the removal is also recorded in the audit
    trail.


---------------------------------------------------------------------------------------------------
11. BACKEND CHANGES (API DESIGN)
---------------------------------------------------------------------------------------------------

New endpoint
  POST /chat
  Request:
    {
      "messages": [ {"role": "user" | "assistant" | "divider", "content": "..."} ],  // last ~12
      "context":  { "view": "queue" | "overview" | "alert", "alert_id": "ALR-00405" | null,
                    "filters": {...}, "sort": "-score", "visible_count": 156 },
      "question": "Summarise the top 5 structuring alerts"
    }
  Response:
    {
      "answer": "...",
      "provider": "groq", "model": "openai/gpt-oss-20b", "fallback_used": false,
      "verified": true, "unverified_numbers": [], "unknown_ids": [],
      "cases_used": ["ALR-00405", "ALR-00850", ...],
      "actions": [ {"type": "open_alert", "alert_id": "ALR-00405", "label": "Open ALR-00405"},
                   {"type": "apply_filter", "filters": {"type": "structuring"},
                    "label": "Show structuring alerts"} ],
      "assumption": "Taking 'recent' as the last 30 days." | null
    }

New endpoints for pinning
  POST   /alerts/{alert_id}/notes      { question, answer, provider, model, verified, investigator }
  DELETE /alerts/{alert_id}/notes/{note_id}?investigator=...
  Notes are stored next to decisions (data/decisions.json now; the database if the backend
  teammate moves to SQLite) and included in /alerts/{id}, /audit, /audit.csv and the case report.

Changes in existing files
  backend/app/ai.py       chat(): retrieval (Layer 1), tool loop (Layer 2), the new checks,
                          per-request provider fallback. Reuse case_file-style compact views,
                          parse_search, clean_filters, unverified_numbers.
  backend/app/main.py     /chat, /alerts/{id}/notes endpoints; tool functions call the existing
                          list_alerts / case_file / stats / player_network / player_detail.
  backend/app/schemas.py  ChatIn, ChatOut, ChatAction, Note.
  backend/app/report.py   "AI notes" section.
  The existing /alerts/{id}/ask endpoint can stay (or be removed once the chat replaces it).


---------------------------------------------------------------------------------------------------
12. FRONTEND CHANGES
---------------------------------------------------------------------------------------------------

  frontend/index.html   Two-column shell: <main> left area + <aside id="chat"> right panel.
  frontend/app.js       - Left area router: queue / overview / alert views (back + prev / next).
                        - Chat panel: message list, input, New chat, context chip, dividers,
                          "Thinking...", footer per answer, clickable IDs, action buttons,
                          Pin to case.
                        - Keep conversation in state + sessionStorage (try/catch).
                        - Send the current context with every question.
                        - Remove the Ask AI tab from the alert view.
  frontend/styles.css   Panel layout, collapsed state, message styles (follow DESIGN.md: calm,
                        regulatory, no AI-sparkle gradients, risk never by colour alone).
  frontend/mock/        Mock mode: the chat shows "AI unavailable in offline demo data".


---------------------------------------------------------------------------------------------------
13. WHO BUILDS WHAT
---------------------------------------------------------------------------------------------------

  Frontend teammate   Sections 3, 4, 10 (button + display), 12. Can start straight away against
                      a stub /chat that echoes the question, so both sides work in parallel.
  Backend teammate    Sections 5, 6, 7, 8, 9, 10 (storage + endpoints), 11. Unit tests for the
                      no-follow-up check, ID check, retrieval of the example questions, fallback.
  Together            Agree the /chat request / response shape first (section 11) and don't
                      change it without telling each other. Then sections 14 and 15.


---------------------------------------------------------------------------------------------------
14. HOW WE KNOW IT WORKS (ACCEPTANCE CHECKS)
---------------------------------------------------------------------------------------------------

  [ ] The chat panel stays open and keeps the conversation through: opening rows, back to queue,
      next / previous, filter changes, Overview tab, and a browser refresh.
  [ ] "New chat" clears it; nothing else does.
  [ ] The context chip is always right; a divider appears when a different row is opened.
  [ ] All 7 example questions in section 7 get correct, grounded answers on Groq, and on Ollama
      with tools off.
  [ ] No answer ever ends with a question or an offer (run the 7 questions plus 10 ambiguous ones).
  [ ] Ambiguous questions get a one-line assumption, then an answer.
  [ ] Clickable IDs open the right row; unknown IDs are flagged, not clickable.
  [ ] Action buttons apply the right filter / open the right alert, and only when clicked.
  [ ] The AI cannot record or submit a decision in any way.
  [ ] Pin to case works, needs a name, and appears in history, audit, CSV and the case report.
  [ ] Pull the network cable (or remove the Groq key): answers keep coming from Ollama, the footer
      says so, and nothing errors on screen.
  [ ] Stop Ollama too: the chat says the AI is offline; the rest of the dashboard still works.
  [ ] The full pipeline still passes every check in docs/VALIDATION.md (the chat must not change
      scoring).
  [ ] No console errors; keyboard-only use still works.


---------------------------------------------------------------------------------------------------
15. DEMO SCRIPT CHANGES (docs/DEMO.md)
---------------------------------------------------------------------------------------------------

Replace the "Ask the AI" step with a continuous chat moment, for example:
  1. Mode 1: "Summarise the top 5 structuring alerts." -> answer with clickable IDs.
  2. Click one ID -> the left side opens it; divider "Now viewing ALR-00405" appears in the chat.
  3. "Is this one worse than the others you listed? Why?" -> it compares within the same chat.
  4. "Pin to case" -> show it in the case report.
  5. Ask something ambiguous ("show the recent big depositors") to show the one-line assumption
     and that it never asks back.
  Keep the Groq key and the Ollama fallback both working on the demo laptop, and run the warm-up
  before presenting.


---------------------------------------------------------------------------------------------------
16. RISKS AND HOW WE HANDLE THEM
---------------------------------------------------------------------------------------------------

  Small local model gets meaning wrong  -> Groq first; numbers and IDs checked; answers labelled
                                           AI-generated; pinning is the investigator's choice.
  Groq rate limits during testing       -> automatic fallback to Ollama; keep test runs small.
  Venue Wi-Fi fails                     -> Ollama fallback on the demo laptop; warm-up cache.
  Answers too long for the side panel   -> instruct "at most 6 sentences or a short list";
                                           render lists and IDs nicely.
  Chat becomes a black box              -> "cases used" shown under each answer (clickable).
  Privacy questions from judges         -> the pitch line in section 9; the data is synthetic.
  Scope creep                           -> the chat never changes detection or scores; it only
                                           reads what the pipeline already computed.


---------------------------------------------------------------------------------------------------
17. SUGGESTED BUILD ORDER
---------------------------------------------------------------------------------------------------

  1. Agree the /chat request / response shape (30 minutes, both teammates).
  2. Frontend: two-column shell + mode 1 / mode 2 navigation + chat panel against a stub.
     Backend: /chat with Layer 1 retrieval + number / ID / no-follow-up checks on Ollama.
  3. Backend: provider fallback (Groq -> Ollama -> template) and Layer 2 tools on Groq.
  4. Both: context chip, dividers, clickable IDs, action buttons wired end to end.
  5. Pin to case (backend storage + frontend button + report + audit).
  6. Acceptance checks (section 14), then the demo script (section 15), then rehearse.

===================================================================================================
