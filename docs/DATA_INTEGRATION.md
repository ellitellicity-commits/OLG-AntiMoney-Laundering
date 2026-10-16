# Data integration: from synthetic data to a real gaming environment

The prototype runs on synthetic data because no real data was available. Every step reads plain
files with a fixed set of columns (the **data contract**), so moving to real data means exporting
those columns from existing systems. Nothing in the detectors depends on the data being synthetic.

Check any export against the contract before running the pipeline on it:

```bash
python backend/pipeline/check_data.py --dir path/to/export
```

It reports missing files, missing or empty columns, unexpected values, unparseable dates, orphaned
transactions, too little history (120+ days needed), and IP regions or occupations that the
configuration doesn't know yet. It exits with code 1 on any failure.

## The data contract

| File | Columns | Typical source | Used for |
|---|---|---|---|
| `players.csv` | `player_id`, `age_band`, `occupation`, `income_band`, `home_region`, `signup_date` | Account registration / player profile | Peer groups, income and occupation checks, account age |
| | `kyc_status`, `pep`, `sanctions_screening` | Identity-verification and screening providers | Identity & screening reasons |
| `transactions.csv` | `txn_id`, `player_id`, `timestamp`, `type` (deposit / withdrawal / bet / payout), `amount_cad` | Wallet and betting ledger | Every money and behaviour measure |
| | `sport`, `market`, `odds` | Bet slips | Low-odds (minimal-risk) betting |
| | `channel`, `device_id`, `ip_region` | Session and device logs, IP geolocation | Location, impossible travel, new devices |
| | `payment_method_id` | Payment processor (tokenised, never raw card numbers) | Third-party funding, U-turn withdrawals |
| `payment_methods.csv` | `payment_method_id`, `player_id`, `method_type`, `holder_matches_player`, `first_used` | Payment processor's name-match result | Third-party funding |
| `linked_identifiers.csv` | `player_id`, `identifier_type` (device / payment_method / address), `identifier_value` | Derived from the above plus addresses | Network analysis of linked accounts |

Privacy by design: the pipeline needs pseudonymous IDs, bands (not exact ages or salaries) and
tokenised payment methods. It never needs names, card numbers or exact addresses; a hashed address
is enough for linking accounts.

## Beyond sports betting

The detectors work on four generic event types (money in, money out, a wager, a win), so other
gaming environments map onto the same contract:

| Environment | Money in | Wager | Win | Money out | Notes |
|---|---|---|---|---|---|
| Online sports betting (built) | Deposit | Bet | Payout | Withdrawal | As in the prototype |
| Online casino | Deposit | Spin / hand | Win | Withdrawal | Low-odds betting becomes low-volatility play (e.g. even-money bets on both sides) |
| Land-based casino (player card) | Cash or card buy-in, chip purchase | Rated play | Jackpot / win | Chip redemption, cheque | `channel = retail`. The $10,000 24-hour rule and structuring checks apply to cash directly |
| Lottery | Ticket purchase | Ticket | Prize claim | Prize payment | Repeated large prize claims and unusual purchase patterns fit the same peer and own-history comparisons |

What would need tuning for each environment: rule thresholds (`THRESHOLDS` in `detect.py`), the
peer-group definition, and the occupation income table (`OCCUPATION_INCOME` in `common.py`). The
validation step (`validate.py`) and the cross-seed test exist to measure the effect of every change.

## Running it for real

- **Schedule:** batch scoring, for example nightly. The full pipeline takes about a minute per 5,000
  players and 650,000 transactions on a laptop, so it scales by days, not seconds. Real-time scoring
  is not needed for investigation queues.
- **Labels for the AI model:** in the prototype, the supervised model learns from planted scenarios.
  In production it would learn from investigator outcomes: alerts closed as explained (negative) and
  escalations confirmed as reportable (positive). Every decision is already recorded with the
  investigator's name in `data/decisions.json` (`GET /audit`, `GET /audit.csv`).
- **Monitoring:** rerun `validate.py` against confirmed outcomes each month, and watch the overview
  screen's flag trends for new patterns the rules don't cover yet. The watchlist exists for exactly
  that.
- **Case management:** decisions already go through `POST /alerts/{id}/decision`, the natural hook for
  a case-management system (Jube was the planned option).
- **What it does not do:** it raises indicators for investigators. It does not decide whether
  something is reportable or file reports. The case report supports that decision; it is not a filing.
