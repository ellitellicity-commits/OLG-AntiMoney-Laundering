<!-- Static pipeline diagram (no animation, so it survives PPTX / Google Slides export). -->
<script setup lang="ts">
const steps = [
  { n: '1', title: 'Activity', sub: 'Bets, deposits, devices, locations' },
  { n: '2', title: 'Context', sub: 'Own 90-day history and peer groups' },
  { n: '3', title: 'Detect', sub: 'Rules, Isolation Forest, AI model + SHAP' },
  { n: '4', title: 'Score', sub: 'Out of 100, every point a reason' },
  { n: '5', title: 'Ranked queue', sub: 'Investigator reviews and decides' },
]
</script>

<template>
  <div class="pipeline" role="img"
       aria-label="Pipeline: activity, context, detect, score, ranked queue where the investigator decides.">
    <template v-for="(s, i) in steps" :key="s.n">
      <div class="step" :class="{ last: i === steps.length - 1 }">
        <div class="n num">{{ s.n }}</div>
        <div class="title">{{ s.title }}</div>
        <div class="sub">{{ s.sub }}</div>
      </div>
      <svg v-if="i < steps.length - 1" class="arrow" viewBox="0 0 24 24" aria-hidden="true">
        <path d="M2 12h17M13 5l7 7-7 7" fill="none" stroke="currentColor" stroke-width="2.5"
              stroke-linecap="round" stroke-linejoin="round" />
      </svg>
    </template>
  </div>
</template>

<style scoped>
.pipeline {
  display: flex;
  align-items: stretch;
  gap: 6px;
}
.step {
  flex: 1 1 0;
  min-width: 0;
  background: var(--surface);
  border: 1px solid var(--rule);
  border-top: 4px solid var(--accent);
  border-radius: 6px;
  padding: 14px 12px 16px;
}
.step.last {
  background: var(--accent);
  border-color: var(--accent);
  color: #fff;
}
.n {
  font-size: 14px;
  color: var(--ink-muted);
  margin-bottom: 6px;
}
.step.last .n { color: #fff; }
.title {
  font-size: 21px;
  font-weight: 600;
  line-height: 1.2;
  margin-bottom: 8px;
}
.sub {
  font-size: 16px;
  line-height: 1.35;
  color: var(--ink-muted);
}
.step.last .sub { color: #fff; }
.arrow {
  flex: 0 0 22px;
  width: 22px;
  align-self: center;
  color: var(--ink-muted);
}
</style>
