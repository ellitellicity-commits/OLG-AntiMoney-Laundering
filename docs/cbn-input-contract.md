# CBN Crash Game input contract

**Status: DRAFT for approval.** Nothing is built against it yet. The open questions at the end need an answer first.

This document says exactly what this repo needs from a CBN Crash Game export so that it can build
**Player Profiles** (win/loss ratio and money totals) and **Staff Profiles** (who exported what, and when).

## Where this comes from

This repo already has a data contract: `transactions.csv` in
[DATA_INTEGRATION.md](DATA_INTEGRATION.md), enforced by `backend/pipeline/check_data.py`. **That format
is the source of truth.** The CBN game data file uses those exact column names, value lists and units,
so CBN rows can go into the existing AML pipeline as they are. It adds three things the existing format
doesn't define:

| Addition | Why | Type |
|---|---|---|
| `round_id` column | Ties a bet to its payout so each round counts as a win or a loss, and allows de-duplication | New column (required in CBN exports) |
| UTC timestamps with `Z` | The existing format has no timezone. That's fine for synthetic data, but not for an outside system | Stricter format for the existing `timestamp` column |
| `export_audit.csv` | No audit or staff format exists in the repo | New file (**proposal**) |

Nothing in the repo identifies staff yet. The only staff-like field is the free-text `investigator`
name on decisions in `data/decisions.json`, which is unrelated to exports.

## Delivery

One export = one folder with two files:

```
<any folder name>/
  transactions.csv    game data: one row per money event (bet or payout)
  export_audit.csv    export log: one row per export made, ever (cumulative)
```

| Rule | Value |
|---|---|
| Format | CSV following RFC 4180. A field that contains a comma, quote or line break is wrapped in double quotes; a quote inside it is written twice (`""`) |
| Encoding | UTF-8. A leading byte-order mark (BOM) is tolerated and stripped |
| Delimiter | Comma `,` |
| Line endings | LF or CRLF |
| Header row | Required, first line, exact lower-case column names as below. Columns may be in any order |
| Unknown columns | Ignored, with a warning |
| Empty values | Empty field only. `NULL`, `null`, `NaN`, `N/A`, `-` and whitespace-only fields are errors |
| Whitespace | No leading or trailing spaces in any value |
| Line numbers in error reports | The header is line 1, so the first data row is line 2 |

## File 1: `transactions.csv`

**One row per money event.** A crash round produces:

- one `bet` row when the player places their stake, and
- one `payout` row **only if** they cashed out before the crash. A busted round has no payout row.

`round_id` is the game round. Many players share it, so a row is identified by `txn_id`, and a round
*for one player* is identified by (`player_id`, `round_id`).

| Column | Type | Required | Allowed values / format | Notes |
|---|---|---|---|---|
| `txn_id` | string | **yes** | 1–64 chars from `A–Z a–z 0–9 _ -`. Must be unique across **all** CBN exports, not only within one file | Suggested: prefix `CBN-` |
| `player_id` | string | **yes** | 1–64 chars from `A–Z a–z 0–9 _ -`. Case-sensitive | See [Identifiers](#identifiers) |
| `round_id` | string | **yes** | 1–64 chars from `A–Z a–z 0–9 _ -` | The game round. The same value is used for every player in that round |
| `timestamp` | datetime | **yes** | UTC, ISO 8601, second precision, ending in `Z`: `YYYY-MM-DDTHH:MM:SSZ`, e.g. `2026-10-01T18:00:05Z`. No offsets like `+00:00` and no fractional seconds | When the bet was accepted, or when the cash-out was paid |
| `type` | enum | **yes** | `bet`, `payout`. (`deposit`, `withdrawal` are also allowed if CBN has a wallet; see below) | Lower case |
| `amount_cad` | decimal | **yes** | **Canadian dollars, not cents.** Up to 2 decimal places, `.` as decimal point, no currency symbol, no thousands separator, no sign. Must be > 0. Examples: `20.00`, `20`, `1250.5` | `bet` = the stake. `payout` = the total returned (stake × multiplier), not the profit |
| `odds` | decimal | conditional | The **cash-out multiplier**, ≥ 1.00, up to 2 decimal places, e.g. `1.85`. Required on a `payout` row. On a `bet` row, the same multiplier if that round was cashed out, and **empty if it busted** | Uses the existing `odds` column, so the pipeline's low-odds check (< 1.30) catches very early cash-outs |
| `sport` | string | **yes** | Always `crash` | Optional in the base contract; fixed here so CBN rows are easy to tell apart |
| `market` | string | **yes** | Always `crash` | As above |
| `channel` | enum | **yes** | `app`, `web`, `retail` | Existing value list |
| `device_id` | string | optional | Pseudonymous device ID | Used by the existing new-device and linked-account checks |
| `ip_region` | string | optional | A region name the pipeline knows (`Toronto`, `Ottawa`, `Hamilton-Niagara`, `Southwestern ON`, `Eastern ON`, `Northern ON`, `Quebec`, `Manitoba`, `New York, US`, `Michigan, US`, `Florida, US`, `Malta`, `Cyprus`, `Philippines`) | An unknown region is a warning, not an error (existing behaviour) |
| `payment_method_id` | string | optional | Tokenised ID, never a card number | Only meaningful on `deposit` / `withdrawal` rows |

### Consistency rules (checked per row and across rows)

1. Each (`player_id`, `round_id`) has **exactly one** `bet` row and **at most one** `payout` row.
2. A `payout` row must have a matching `bet` row for the same `player_id` and `round_id`, in the same
   export or an earlier one.
3. `payout.amount_cad` = `bet.amount_cad` × `odds`, to within $0.01.
4. On a cashed-out round, the bet and payout rows have the same `odds`.
5. A payout's `timestamp` is not earlier than its bet's `timestamp`.

### Win, loss and the W/L ratio (derived, not sent)

CBN does **not** send an `outcome` column. It is derived, so it can never disagree with the money:

| Round for one player | Outcome |
|---|---|
| `bet` row, no `payout` row | **loss** |
| `payout.amount_cad` > `bet.amount_cad` | **win** |
| `payout.amount_cad` = `bet.amount_cad` (cash-out at exactly 1.00×) | **push**: counted in rounds and totals, not in wins or losses |

W/L ratio = wins ÷ losses. With zero losses it is reported as "no losses" (no number); with zero wins it is 0.

### De-duplication

Export date ranges may overlap, so the same row can arrive twice.

| Case | Result |
|---|---|
| Same `txn_id`, every field identical | Duplicate: kept once, reported as a warning with both line numbers |
| Same `txn_id`, any field different | **Error** on both lines; neither row is used until CBN corrects it |
| Different `txn_id`, but a second `bet` (or second `payout`) for the same (`player_id`, `round_id`) | **Error** (rule 1) |

### Deposits and withdrawals (optional)

If the CBN game keeps its own wallet, it may also send `deposit` and `withdrawal` rows using the
existing contract: `round_id`, `odds`, `sport` and `market` empty; `payment_method_id` filled in. Player
Profiles don't need them, but the AML detectors (structuring, the $10,000 24-hour rule, quick cash-outs)
do.

## File 2: `export_audit.csv` (PROPOSAL)

**One row per export a staff member made.** The file is cumulative: each delivery contains every export
so far, so Staff Profiles can be rebuilt from any one delivery. Rows are de-duplicated by `export_id`
the same way as `txn_id` above.

| Column | Type | Required | Allowed values / format | Notes |
|---|---|---|---|---|
| `export_id` | string | **yes** | 1–64 chars from `A–Z a–z 0–9 _ -`, unique | *Added to your proposal*: needed to de-duplicate the cumulative log |
| `staff_id` | string | **yes** | 1–64 chars from `A–Z a–z 0–9 _ -`. Case-sensitive. **Pseudonymous: not a name or email** | See [Identifiers](#identifiers) |
| `exported_at` | datetime | **yes** | UTC ISO 8601 with `Z`, as for `timestamp` | When the export ran |
| `date_from` | datetime | **yes** | UTC ISO 8601 with `Z` | *Added*: start of the exported period, **inclusive** |
| `date_to` | datetime | **yes** | UTC ISO 8601 with `Z`, later than `date_from` | *Added*: end of the period, **exclusive**. A full day of 1 October is `2026-10-01T00:00:00Z` to `2026-10-02T00:00:00Z` |
| `filters` | string | optional | `key=value` pairs separated by `;`, e.g. `game=crash;player_id=P00012`. Empty = no filter | Free text from CBN's export screen. Kept and shown as is, not parsed for logic |
| `row_count` | integer | **yes** | Whole number ≥ 0, no separators | Data rows in that export's `transactions.csv`, **not counting the header** |
| `schema_version` | string | **yes** | `cbn-<major>.<minor>`, currently `cbn-1.0` | An unknown major version rejects the whole delivery. A higher minor version is a warning |

`date_from` and `date_to` are separate columns so Staff Profiles can show date ranges without parsing
`filters`.

**Check that ties the two files together:** the audit row with the latest `exported_at` describes
*this* delivery. Its `row_count` must equal the number of data rows in `transactions.csv`, and every
`timestamp` must fall within its `date_from` and `date_to`. A mismatch is an error.

## Identifiers

Profiles are joined on these IDs, so they must be stable and exact.

| ID | Rule |
|---|---|
| `player_id` | **Must be the same ID** this repo uses in `players.csv`, which comes from the player account system (synthetic format `P00001`). Same player = same ID in every export and every file, forever. It is pseudonymous, so no names, emails or usernames. If CBN only has its own internal player IDs, CBN (not this repo) must map them to the account ID before export. Matching is exact and case-sensitive; `p00001` is a different player from `P00001` |
| `staff_id` | A stable, pseudonymous employee ID (e.g. `S0042`), the same for that person across every export. No names or emails. The link to a real person is kept outside this repo |
| `round_id`, `txn_id`, `export_id` | Opaque strings, never reused |

Allowed characters are deliberately narrow (`A–Z a–z 0–9 _ -`) so IDs survive CSV, Excel and URLs
unchanged. Excel turns IDs like `00012` into `12`, so leading zeros must only appear after a letter
prefix.

## Example

Synthetic. One round (`R000000101`): `P00001` stakes $20.00 and cashes out at 1.85× (a **win**, payout
$37.00); `P00002` stakes $50.00 and busts (a **loss**).

[`tests/fixtures/cbn_export_sample.csv`](../tests/fixtures/cbn_export_sample.csv):

```csv
txn_id,player_id,round_id,timestamp,type,amount_cad,odds,sport,market,channel,device_id,ip_region,payment_method_id
CBN-T0000001,P00001,R000000101,2026-10-01T18:00:05Z,bet,20.00,1.85,crash,crash,web,D00001,Toronto,
CBN-T0000002,P00001,R000000101,2026-10-01T18:00:11Z,payout,37.00,1.85,crash,crash,web,D00001,Toronto,
CBN-T0000003,P00002,R000000101,2026-10-01T18:00:06Z,bet,50.00,,crash,crash,app,D00002,Ottawa,
```

[`tests/fixtures/cbn_export_audit_sample.csv`](../tests/fixtures/cbn_export_audit_sample.csv):

```csv
export_id,staff_id,exported_at,date_from,date_to,filters,row_count,schema_version
EXP-000001,S0042,2026-10-02T09:15:00Z,2026-10-01T00:00:00Z,2026-10-02T00:00:00Z,game=crash,3,cbn-1.0
```

## Open questions (answer before Step C)

1. **Timezone.** The repo's current `timestamp` has no timezone, and the night-betting feature reads it
   as Ontario local time (hour < 6). This contract asks CBN for UTC with `Z`, and the ingest would convert
   it to `America/Toronto` before passing rows on. OK?
2. **Rounds are shared.** I assumed a crash `round_id` is one game round that many players join, so
   de-duplication is by `txn_id`, with (`player_id`, `round_id`) as the round key, not `round_id` alone.
   Is that right for CBN?
3. **One bet per round.** Some crash games allow two bets per round. Does CBN? If so, the contract needs a
   `bet_slot` column (or similar) to match each payout to its bet.
4. **Player ID mapping.** Does CBN use the same player IDs as the account system, or its own?
5. **Additions to your proposal:** `export_id`, `date_from` and `date_to` in the audit file; `outcome`
   derived instead of sent; your `bet_amount` / `payout` / `cashout_multiplier` mapped to the existing
   `amount_cad` (with `type`) and `odds`. OK?
