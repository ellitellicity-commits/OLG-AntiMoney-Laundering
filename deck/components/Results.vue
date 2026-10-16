<!--
  Every number here is copied from docs/VALIDATION.md (seed 42). Sources are listed in deck/SOURCES.md.
  Static (no hover or animation) so it exports cleanly to PDF / PPTX.
-->
<script setup lang="ts">
const fp = [
  { who: 'Our score', value: 0.40, text: '0.40%', ours: true },
  { who: 'Fixed rules', value: 2.76, text: '2.76%', ours: false },
]
const max = 2.76
const topK = [
  { k: 'Top 25', ours: '100%', rules: '92%' },
  { k: 'Top 50', ours: '100%', rules: '96%' },
  { k: 'Top 100', ours: '100%', rules: '98%' },
]
</script>

<template>
  <div class="results">
    <div class="panel hero">
      <div class="label">Alerts raised</div>
      <div class="big num">296</div>
      <div class="muted">from 5,000 synthetic players</div>
    </div>

    <div class="panel">
      <div class="label">Normal players wrongly alerted</div>
      <div class="bars" role="img" aria-label="Normal players alerted: our score 0.40%, fixed rules 2.76%.">
        <div v-for="b in fp" :key="b.who" class="bar-row">
          <div class="who">{{ b.who }}</div>
          <div class="track">
            <div class="bar" :class="{ ours: b.ours }" :style="{ width: (b.value / max * 100) + '%' }" />
          </div>
          <div class="val num">{{ b.text }}</div>
        </div>
      </div>
      <div class="muted small">Lower is better</div>
    </div>

    <div class="panel">
      <div class="label">Real cases in top alerts</div>
      <table>
        <thead><tr><th></th><th>Ours</th><th>Rules</th></tr></thead>
        <tbody>
          <tr v-for="r in topK" :key="r.k">
            <td>{{ r.k }}</td>
            <td class="num strong">{{ r.ours }}</td>
            <td class="num muted">{{ r.rules }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<style scoped>
.results {
  display: grid;
  grid-template-columns: 0.8fr 1.25fr 1fr;
  gap: 16px;
  align-items: stretch;
}
.panel { display: flex; flex-direction: column; gap: 12px; padding: 18px 20px; }
.big { font-size: 88px; line-height: 1; color: var(--accent); margin-top: 8px; }
.hero .muted { font-size: 18px; }
.small { font-size: 15px; margin-top: auto; }

.bars { display: flex; flex-direction: column; gap: 14px; margin-top: 6px; }
.bar-row { display: grid; grid-template-columns: 104px 1fr 64px; align-items: center; gap: 10px; }
.who { font-size: 17px; font-weight: 500; }
.track { height: 24px; }
.bar { height: 100%; background: #9EA3AA; border-radius: 0 4px 4px 0; min-width: 4px; }
.bar.ours { background: var(--accent); }
.val { font-size: 20px; text-align: right; }

table { border-collapse: collapse; width: 100%; font-size: 19px; }
th { font-size: 14px; font-weight: 500; letter-spacing: 0.06em; text-transform: uppercase;
     color: var(--ink-muted); text-align: right; padding: 0 0 6px; border-bottom: 1px solid var(--rule); }
td { padding: 8px 0; border-bottom: 1px solid var(--rule); text-align: right; }
td:first-child { text-align: left; }
tr:last-child td { border-bottom: none; }
.strong { color: var(--accent); }
</style>
