---
theme: default
title: Pitch deck
colorSchema: light
aspectRatio: 16/9
canvasWidth: 980
transition: none
drawings:
  enabled: false
download: false
info: false
exportFilename: pitch-deck
routerMode: hash
favicon: ./favicon.svg
fonts:
  provider: none
  sans: IBM Plex Sans
  mono: IBM Plex Mono
  local: IBM Plex Sans, IBM Plex Mono
layout: default
---

<div class="title-slide">
  <div class="title-text">
    <div class="label">ThunderHacks 2026 · Bytes of the Round Table</div>
    <h1 class="name"><ProjectName /></h1>
    <p class="tagline">Finding laundering patterns in sports betting, and explaining every flag.</p>
    <div class="problem panel">
      <div class="label">The problem</div>
      <p>Fixed rules raise many alerts but never say why, or whether it matters.</p>
    </div>
  </div>
  <div class="title-art-wrap"><TitleArt /></div>
  <div class="footer">
    <span class="tag-synthetic">Synthetic data</span>
    <span class="label">All players and transactions are generated</span>
  </div>
</div>

<style>
.title-slide { display: grid; grid-template-columns: 1.3fr 1fr; grid-template-rows: 1fr auto; column-gap: 28px; height: 100%; }
.title-slide .title-text { display: flex; flex-direction: column; justify-content: center; }
.title-slide .name { font-size: 46px; line-height: 1.08; margin: 14px 0 14px; }
.title-slide .tagline { font-size: 22px; color: var(--ink-muted); }
.title-slide .problem { margin-top: 28px; border-left: 4px solid var(--accent); }
.title-slide .problem p { font-size: 21px; margin-top: 4px; }
.title-slide .title-art-wrap { display: flex; align-items: center; }
.title-slide .footer { grid-column: 1 / -1; }
</style>

<!--
[0:00–0:30] (~30 s)
- We're Bytes of the Round Table.
- Investigators review a huge number of alerts every day. Most come from fixed rules: they fire often, but don't say why, or whether it's unusual for that person.
- Our tool looks for laundering patterns like the linked ring in the lens: accounts sharing a device, card or address and moving money between them.
- Everything you'll see runs on synthetic data we generated. No real player data.
-->

---

<div class="label">How it works · <span class="tag-synthetic">Synthetic data</span></div>

# One score, with the evidence behind every flag

<div class="how">
  <Pipeline vertical />
  <div>
    <figure class="shot">
      <img src="/img/dashboard-alert.png" alt="Top alert opened in the dashboard: risk badge 97 Critical, high confidence, and a case summary built from the evidence." />
      <span class="hl" style="left: 81.5%; top: 6%; width: 14.5%; height: 15%"></span>
      <span class="marker num" style="left: 76%; top: 8%">1</span>
      <span class="hl" style="left: 1%; top: 31%; width: 49%; height: 34%"></span>
      <span class="marker num" style="left: 51%; top: 31%">2</span>
    </figure>
    <div class="legend">
      <div><span class="marker static num">1</span>Score and confidence</div>
      <div><span class="marker static num">2</span>Summary from evidence only</div>
    </div>
  </div>
</div>


<style>
.how { display: grid; grid-template-columns: 290px 1fr; gap: 20px; margin-top: 10px; align-items: start; }
.shot { position: relative; margin: 0; border: 1px solid var(--rule); border-radius: 6px; overflow: hidden; background: var(--surface); }
.shot img { display: block; width: 100%; height: auto; }
.hl { position: absolute; border: 3px solid var(--accent); border-radius: 4px; }
.marker {
  position: absolute;
  width: 28px; height: 28px; border-radius: 50%;
  display: inline-flex; align-items: center; justify-content: center;
  background: var(--accent); color: #fff; font-size: 16px;
  box-shadow: 0 0 0 3px #fff;
}
.marker.static { position: static; margin-right: 10px; flex: none; }
.legend { display: flex; gap: 24px; margin-top: 12px; font-size: 18px; white-space: nowrap; font-weight: 500; }
.legend > div { display: flex; align-items: center; }
.legend .cap { margin-left: auto; font-size: 15px; font-weight: 400; }
</style>

<!--
[0:30–1:20] (~50 s)
- Left, the pipeline: activity in (bets, deposits, devices, locations, all synthetic); context, so every flag compares the player with their own 90-day history and with peers; detection with transparent rules, peer z-scores, Isolation Forest and a gradient-boosting model whose SHAP drivers become one more reason.
- The score is out of 100 and every point comes from a named reason with its numbers. Output: one ranked queue across AML, Fraud and Safer Gambling.
- Right, a real screenshot of our dashboard on synthetic data, top alert opened.
- 1: the score with a number, a label and a meter, never colour alone, plus a confidence rating and reasons it may be innocent.
- 2: a case summary written only from computed evidence; any AI-written number is checked against the case file. It ends with a recommended next step.
- The investigator decides (Accept, Escalate, Close as explained, Assign), recorded with their name. Also built: Evidence, Activity and Network tabs for linked accounts.
Sources: README.md "Our Solution" and "How the score works"; docs/VALIDATION.md "AI model (supervised)".
-->

---

<div class="label">Results · synthetic data, seed 42</div>

# Fewer false alarms, real cases on top

<div class="results-wrap">
  <Results />
</div>

<div class="next">
  <div class="panel">
    <div class="label">Roadmap</div>
    <p><strong>Jube</strong> case management <span class="muted">(mock today)</span> · <strong>CBN Crash Game</strong> feed <span class="muted">(draft contract)</span></p>
  </div>
  <div class="panel">
    <div class="label">Responsible by design</div>
    <p>Synthetic data only · The investigator decides · Every flag explained</p>
  </div>
</div>

<div class="footer">
  <span class="qa">Questions?</span>
  <span class="label">Bytes of the Round Table · Source: docs/VALIDATION.md</span>
</div>

<style>
.results-wrap { margin-top: 6px; }
.next { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-top: 14px; }
.next .panel { padding: 10px 16px; }
.next p { font-size: 17px; margin-top: 4px; }
.qa { font-size: 30px; font-weight: 600; color: var(--accent); line-height: 1; }
</style>

<!--
[1:20–2:00] (~40 s)
- 296 alerts from 5,000 synthetic players.
- Only 0.40% of normal players get alerted; fixed-threshold rules flag 2.76%.
- Ranking: the top 25, 50 and 100 alerts are all real planted cases; rules alone get 92%, 96%, 98%.
- Honest caveat: our team built both the data and the detectors, so this shows the pipeline works, not real-world accuracy.
- Next: real Jube case management (today only a mock of its API) and a CBN Crash Game feed (the data contract is a draft).
- Responsible by design: synthetic data only; the investigator decides and can override with a reason; no score without its reasons.
- Thank you. Questions?
Source for every number: docs/VALIDATION.md ("Dataset", "Prioritisation: precision@k", "False positives"). See deck/SOURCES.md.
-->
