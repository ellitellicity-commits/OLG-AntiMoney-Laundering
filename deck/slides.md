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
  <div class="label">ThunderHacks 2026 · Team TBD</div>
  <h1 class="name"><ProjectName /></h1>
  <p class="tagline">Sports-betting risk review that explains every flag.</p>
  <div class="problem panel">
    <div class="label">The problem</div>
    <p>Fixed rules raise many alerts but never say why, or whether it matters.</p>
  </div>
  <div class="footer">
    <span class="tag-synthetic">Synthetic data</span>
    <span class="label">All players and transactions are generated</span>
  </div>
</div>

<style>
.title-slide { display: flex; flex-direction: column; height: 100%; }
.title-slide .name { font-size: 64px; margin: 56px 0 12px; }
.title-slide .tagline { font-size: 28px; color: var(--ink-muted); }
.title-slide .problem { margin-top: 48px; max-width: 880px; border-left: 4px solid var(--accent); }
.title-slide .problem p { font-size: 26px; margin-top: 6px; }
</style>

<!--
[0:00–0:20] (~20 s)
- Investigators review a huge number of alerts every day.
- Most come from fixed rules: they fire often, but don't say why, or whether it's unusual for that person.
- We built a tool that ranks players by risk and explains every flag.
- Everything you'll see runs on synthetic data we generated. No real player data.
-->

---

<div class="label">Our solution</div>

# One score, one ranked queue, evidence behind every flag

<div class="pipeline-wrap">
  <Pipeline />
</div>

<p class="lead caption">Each flag compares a player with their own history and with similar players.</p>

<div class="footer">
  <span class="tag-synthetic">Synthetic data</span>
  <span class="label">How it works</span>
</div>

<style>
.pipeline-wrap { margin-top: 36px; }
.caption { margin-top: 32px; }
</style>

<!--
[0:20–0:50] (~30 s)
- Activity in: bets, deposits, devices, locations (all synthetic).
- Context: every flag compares the player with their own 90-day history AND with peers (same age, income, region; and players who bet like them).
- Detect: transparent rules, peer z-scores, Isolation Forest, and a gradient-boosting model whose SHAP drivers become one more reason.
- Score out of 100: every point comes from a named reason with its numbers.
- Output: one ranked queue across AML, Fraud and Safer Gambling. The investigator decides.
Sources: README.md "How the score works"; docs/VALIDATION.md "AI model (supervised)".
-->

---

<div class="label">Live dashboard</div>

# Ranked, scored and explained on one screen

<div class="shots">
  <figure class="shot">
    <img src="/img/dashboard-queue.png" alt="Alert queue ranked by risk score, each with a score, label and confidence." />
    <span class="hl" style="left: 0.3%; top: 32.5%; width: 15.7%; height: 62%"></span>
    <span class="marker num" style="left: 9.8%; top: 30.7%">1</span>
  </figure>
  <figure class="shot">
    <img src="/img/dashboard-alert.png" alt="Top alert opened: risk badge 97 Critical, high confidence, and a case summary built from the evidence." />
    <span class="hl" style="left: 81.5%; top: 6%; width: 14.5%; height: 15%"></span>
    <span class="marker num" style="left: 75%; top: 8%">2</span>
    <span class="hl" style="left: 1%; top: 31%; width: 49%; height: 34%"></span>
    <span class="marker num" style="left: 51%; top: 31%">3</span>
  </figure>
</div>

<div class="legend">
  <div><span class="marker static num">1</span>Ranked by risk</div>
  <div><span class="marker static num">2</span>Score and confidence</div>
  <div><span class="marker static num">3</span>Summary from evidence only</div>
</div>

<div class="footer">
  <span class="tag-synthetic">Synthetic data</span>
  <span class="label">Real screenshots, running locally</span>
</div>

<style>
.shots { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-top: 16px; }
.shot { position: relative; margin: 0; border: 1px solid var(--rule); border-radius: 6px; overflow: hidden; background: var(--surface); }
.shot img { display: block; width: 100%; height: auto; }
.marker {
  position: absolute;
  width: 30px; height: 30px; border-radius: 50%;
  display: inline-flex; align-items: center; justify-content: center;
  background: var(--accent); color: #fff; font-size: 17px;
  box-shadow: 0 0 0 3px #fff;
}
.hl { position: absolute; border: 3px solid var(--accent); border-radius: 4px; }
.marker.static { position: static; margin-right: 10px; flex: none; }
.legend { display: flex; gap: 36px; margin-top: 18px; font-size: 21px; font-weight: 500; }
.legend > div { display: flex; align-items: center; }
</style>

<!--
[0:50–1:20] (~30 s)
- Real screenshots of our dashboard running locally on synthetic data (left: the queue; right: the top alert opened).
- 1: one ranked queue across AML, Fraud and Safer Gambling. Every score shows a number, a label and a meter, never colour alone.
- 2: the score with a confidence rating; the alert also lists reasons it may be innocent.
- 3: a case summary written only from computed evidence; every number is checked against the case file. It ends with a recommended next step.
- The investigator decides: Accept, Escalate, Close as explained or Assign, recorded with their name in an audit trail.
- Also built (not shown): Evidence, Activity and Network tabs (linked accounts sharing a device, card or address).
-->

---

<div class="label">Results · synthetic data, seed 42</div>

# Fewer false alarms, real cases on top

<div class="results-wrap">
  <Results />
</div>

<p class="muted note">We built the data and the detectors, so this shows the pipeline works, not real-world accuracy.</p>

<div class="footer">
  <span class="tag-synthetic">Synthetic data</span>
  <span class="label">Source: docs/VALIDATION.md</span>
</div>

<style>
.results-wrap { margin-top: 24px; }
.note { margin-top: 20px; font-size: 18px; }
</style>

<!--
[1:20–1:45] (~25 s)
- 296 alerts from 5,000 synthetic players.
- Only 0.40% of normal players get alerted; fixed-threshold rules flag 2.76%.
- Ranking: the top 25, 50 and 100 alerts are all real planted cases; rules alone get 92%, 96%, 98%.
- Honest caveat: same team built the data and the detectors.
Source for every number: docs/VALIDATION.md ("Dataset", "Prioritisation: precision@k", "False positives"). See deck/SOURCES.md.
-->

---

<div class="label">Next steps</div>

# Roadmap, responsible by design

<div class="two-col">
  <div class="panel">
    <div class="label">Roadmap</div>
    <ul>
      <li><strong>Jube</strong> case management<div class="muted note-sm">Today: a mock of its API</div></li>
      <li><strong>CBN Crash Game</strong> data feed<div class="muted note-sm">Today: a draft data contract</div></li>
    </ul>
  </div>
  <div class="panel">
    <div class="label">Responsible by design</div>
    <ul>
      <li>Synthetic data only</li>
      <li>The investigator decides</li>
      <li>Every flag explained</li>
    </ul>
  </div>
</div>

<div class="qa">Questions?</div>

<div class="footer">
  <span class="tag-synthetic">Synthetic data</span>
  <span class="label"><ProjectName /> · Team TBD</span>
</div>

<style>
.two-col { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-top: 24px; }
.two-col ul { margin: 10px 0 0; padding-left: 22px; font-size: 24px; }
.two-col li { margin: 8px 0; }
.two-col .note-sm { font-size: 18px; }
.qa { font-size: 44px; font-weight: 600; color: var(--accent); margin: 36px 0 16px; }
</style>

<!--
[1:45–2:00] (~15 s)
- Roadmap: real Jube case management (today we only have a mock of its API), and a CBN Crash Game feed (data contract is a draft).
- Responsible by design: synthetic data only; the tool recommends, the investigator decides and can override with a reason; no score without its reasons.
- Thank you. Questions?
-->
