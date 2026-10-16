"""Printable case report for one alert (GET /alerts/{id}/report).

A single self-contained HTML page an investigator can print or save as PDF and attach
to a case or a supervisor review. It is a case file, not a regulatory filing.
"""
from __future__ import annotations

from html import escape

from backend.pipeline.common import TXN_FLAGS

CSS = """
:root { --ink:#1A1D21; --muted:#545A62; --rule:#D5D3CC; --sunk:#EDECE7; --accent:#1F4E79; }
* { box-sizing: border-box; }
body { margin: 0; padding: 32px; font: 13px/1.45 "IBM Plex Sans", system-ui, "Segoe UI", sans-serif;
       color: var(--ink); background: #fff; max-width: 1000px; }
h1 { font-size: 22px; margin: 0 0 4px; } h2 { font-size: 15px; margin: 24px 0 8px; padding-bottom: 4px;
     border-bottom: 1px solid var(--rule); }
.muted { color: var(--muted); } .mono, td.num { font-family: "IBM Plex Mono", Consolas, monospace; }
.tag { display: inline-block; border: 1px solid var(--ink); border-radius: 4px; padding: 1px 6px; font-size: 11px;
       font-weight: 600; letter-spacing: .06em; }
.head { display: flex; justify-content: space-between; gap: 24px; align-items: flex-start; }
.score { font: 600 28px "IBM Plex Mono", Consolas, monospace; text-align: right; }
.grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 4px 24px; margin-top: 8px; }
.grid div span { display: block; font-size: 11px; color: var(--muted); text-transform: uppercase; letter-spacing: .03em; }
table { width: 100%; border-collapse: collapse; } th, td { text-align: left; padding: 4px 6px;
        border-bottom: 1px solid var(--rule); vertical-align: top; }
th { background: var(--sunk); font-weight: 500; font-size: 12px; color: var(--muted); }
td.num, th.num { text-align: right; white-space: nowrap; }
.summary { border-left: 3px solid var(--accent); padding: 8px 12px; background: #F6F5F1; }
.rec { border: 1px solid var(--rule); padding: 8px 12px; }
footer { margin-top: 32px; font-size: 11px; color: var(--muted); border-top: 1px solid var(--rule); padding-top: 8px; }
@media print { body { padding: 0; } .noprint { display: none; } h2 { break-after: avoid; } tr { break-inside: avoid; } }
"""


def money(v) -> str:
    return "n/a" if v is None else (f"-${abs(v):,.2f}" if v < 0 else f"${v:,.2f}")


def fmt(v, unit: str) -> str:
    if v is None:
        return "n/a"
    if unit == "money":
        return money(v)
    if unit == "percent":
        return f"{v:.0%}"
    return f"{v:,.2f}"


def table(head: list[str], rows: str, empty: str, num_cols: tuple = ()) -> str:
    if not rows:
        return f'<p class="muted">{empty}</p>'
    ths = "".join(f'<th class="num">{h}</th>' if i in num_cols else f"<th>{h}</th>" for i, h in enumerate(head))
    return f"<table><thead><tr>{ths}</tr></thead><tbody>{rows}</tbody></table>"


def render(alert: dict, player: dict, peers: dict, network: dict, flagged: list[dict], summary: dict,
           generated_at: str) -> str:
    e = escape
    p = alert["profile"]
    rows = "".join(
        f"<tr><td><b>{e(r['title'])}</b><br><span class='muted'>{e(r['detail'])}</span></td>"
        f"<td>{e(r['anomaly_type'].replace('_', ' '))}</td><td class='num'>+{r['points']}</td></tr>"
        for r in alert["reasons"])
    peer_rows = "".join(
        f"<tr><td>{e(m['label'])}</td><td class='num'>{fmt(m['current'], m['unit'])}</td>"
        f"<td class='num'>{fmt(m['baseline'], m['unit'])}</td><td class='num'>{fmt(m['peer']['median'], m['unit'])}</td>"
        f"<td class='num'>{fmt(m['z'], 'number')}</td></tr>"
        for m in peers["metrics"])
    ml = alert.get("ml")
    ml_html = ""
    if ml:
        drv = "".join(f"<li>{e(d['label'])}: <span class='mono'>{d['value']:,}</span> "
                      f"<span class='muted'>(SHAP +{d['impact']:.2f})</span></li>" for d in ml["drivers"])
        prob = "over 99%" if ml["probability"] > 0.99 else f"{ml['probability']:.0%}"
        ml_html = (f"<h2>AI risk model</h2><p>Gradient-boosting model probability "
                   f"<b class='mono'>{prob}</b> (scored out-of-fold, explained with SHAP).</p>"
                   + (f"<ul>{drv}</ul>" if drv else ""))

    def shared(link: dict) -> str:
        return ", ".join(x["identifier_type"].replace("_", " ") + " " + x["identifier_value"] for x in link["shared"])

    link_rows = "".join(
        f"<tr><td class='mono'>{e(l['player_id'])}</td><td class='num'>{l['score']} {e(l['band'])}</td>"
        f"<td>{e(shared(l))}</td></tr>" for l in network["linked_players"][:20])
    flag_rows = "".join(
        f"<tr><td class='mono'>{e(t['timestamp'][:16])}</td><td>{e(t['type'])}</td><td class='num'>{money(t['amount_cad'])}</td>"
        f"<td>{e(t.get('ip_region') or '')}</td><td>{e(', '.join(TXN_FLAGS.get(f, f) for f in t['flags']))}</td></tr>"
        for t in flagged[:40])
    dec_rows = "".join(
        f"<tr><td class='mono'>{e(d['recorded_at'])}</td><td>{e(d.get('investigator') or 'not recorded')}</td>"
        f"<td>{e(d['decision'])}</td><td>{e(d['status'])}</td>"
        f"<td>{e(d.get('team') or '')}</td><td>{e(d.get('note') or '')}</td></tr>" for d in alert.get("decisions", []))
    conf = alert.get("confidence") or {}
    mitig = "".join(f"<li>{e(m)}</li>" for m in alert.get("mitigating", []))
    conf_html = (f"<h2>Assessment confidence</h2><p><b>{e(conf.get('level', 'n/a'))}</b> "
                 f"<span class='muted'>({e(conf.get('basis', ''))})</span></p>"
                 + (f"<p>Mitigating factors (reasons this may be innocent):</p><ul>{mitig}</ul>" if mitig
                    else "<p class='muted'>No mitigating factors found.</p>"))
    bg = alert.get("behaviour_group") or {}
    links_html = table(["Player", "Risk", "Shared identifiers"], link_rows,
                       "No other account shares a device, payment method or address.", (1,))
    flags_html = table(["Time", "Type", "Amount", "Location", "Flags"], flag_rows,
                       "No individual transaction was flagged.", (2,))
    if len(flagged) > 40:
        flags_html += f'<p class="muted">Showing 40 of {len(flagged)} flagged transactions.</p>'
    peer_html = table(["Metric", "Last 30 days", "Own baseline", "Peer median", "Peer z"], peer_rows, "", (1, 2, 3, 4))
    dec_html = table(["Recorded", "Investigator", "Decision", "Status", "Team", "Note"], dec_rows,
                     "No decisions recorded yet.")
    notes = "".join(
        "<div class='summary' style='white-space:pre-line;margin-bottom:8px'>" + (f"<b>{e(n['question'])}</b><br>" if n["question"] else "") + e(n["answer"])
        + f"<div class='muted' style='margin-top:6px;font-size:11px'>AI-generated, reviewed by "
          f"{e(n['investigator'])} · pinned {e(n['recorded_at'])} · {e(n['provider'] or 'no provider')} "
          f"{e(n['model'] or '')}{'' if n['verified'] else ' · numbers not fully checked'}</div></div>"
        for n in alert.get("notes", []))
    s = player["summary"]
    key = [("30-day deposits", money(s["deposits_30d"])), ("Baseline deposits / 30 days", money(s["deposits_base_30d"])),
           ("30-day withdrawals", money(s["withdrawals_30d"])), ("Amount bet (30 days)", money(s["turnover_30d"])),
           ("Net loss (30 days)", money(s["net_loss_30d"])), ("Deposits vs income", f"{s['deposit_income_ratio']:.1f}x"),
           ("Distinct locations", str(s["distinct_ip_regions_30d"])),
           ("Impossible-travel events", str(s["impossible_travel_count_30d"])),
           ("Linked-account cluster", str(s["network_cluster_size"]))]
    src = "Built-in template, generated from the evidence below"
    if summary["source"] == "llm":
        src = (f"AI-generated from the evidence below · {summary['provider']} {summary['model']} · "
               "numbers checked against the case file")
    key_rows = "".join(f'<tr><td>{e(k)}</td><td class="num">{e(v)}</td></tr>' for k, v in key)
    rec = alert["recommended_action"]
    return f"""<!doctype html><html lang="en-CA"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Case report {e(alert['alert_id'])}</title><style>{CSS}</style></head><body>
<div class="head"><div>
  <h1>Case report · <span class="mono">{e(alert['player_id'])}</span></h1>
  <div class="muted">Alert <span class="mono">{e(alert['alert_id'])}</span> · Team {e(alert['team'])} ·
    Status {e(alert['status'])} · <span class="tag">SYNTHETIC DATA</span></div>
</div><div class="score">{alert['score']}<div class="muted" style="font-size:13px">{e(alert['band'])} risk</div></div></div>
<div class="grid">
  <div><span>Age band</span>{e(p['age_band'])}</div><div><span>Occupation</span>{e(p['occupation'])}</div>
  <div><span>Income band</span>${e(p['income_band'])}/yr</div><div><span>Home region</span>{e(p['home_region'])}</div>
  <div><span>Signed up</span>{e(p['signup_date'])}</div>
  <div><span>Peer group</span>{e(alert['peer_group'])} ({alert['peer_group_size']} players)</div>
  <div><span>Identity (KYC)</span>{e(str(p.get('kyc_status', 'n/a')))}</div>
  <div><span>Screening</span>Sanctions: {e(str(p.get('sanctions_screening', 'n/a')))} · PEP: {'yes' if p.get('pep') else 'no'}</div>
  <div><span>Behaviour group</span>{e(str(bg.get('name', 'n/a')))}{f" ({bg['size']} players)" if bg.get('size') else ''}</div>
</div>
<h2>Case summary</h2><div class="summary">{e(summary['text'])}<div class="muted" style="margin-top:6px;font-size:11px">{e(src)}</div></div>
{conf_html}
<h2>Recommended action</h2><div class="rec"><b>{e(rec['action'])}</b> ({e(rec['team'])})<br>
  <span class="muted">{e(rec['rationale'])}</span></div>
<h2>Why flagged</h2><p class="muted">Points total {alert['points_total']} → score {alert['score']}. Points count
one-for-one up to 70, then progressively less; within one anomaly type the strongest flag counts in full and the
rest at half.</p>
<table><thead><tr><th>Reason and evidence</th><th>Type</th><th class="num">Points</th></tr></thead><tbody>{rows}</tbody></table>
{ml_html}
<h2>Key figures</h2><table><tbody>{key_rows}</tbody></table>
<h2>Peer comparison</h2><p class="muted">{e(peers['peer_group'])} · {e(peers['peer_group_level'])} · {peers['peer_group_size']} players</p>
{peer_html}
<h2>Linked accounts</h2>{links_html}
<h2>Flagged transactions</h2>{flags_html}
<h2>Decision history</h2>{dec_html}
{f"<h2>AI notes</h2><p class='muted'>Chat answers pinned to this case. They are AI-generated and are not decisions.</p>{notes}" if notes else ""}
<footer>Generated {e(generated_at)} by the Player Risk Review prototype (ThunderHacks 2026). All players and
transactions are synthetic. This report lists risk indicators for investigator review; it is not a regulatory
filing and does not by itself establish wrongdoing.
<span class="noprint"> · <a href="javascript:window.print()">Print or save as PDF</a></span></footer>
</body></html>"""
