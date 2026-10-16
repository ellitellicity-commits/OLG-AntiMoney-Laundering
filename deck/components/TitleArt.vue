<!--
  Title illustration: a magnifying glass over a web of player accounts, picking out a linked ring
  moving money between accounts. Static SVG (no animation) so it survives PDF / PPTX export.
  Red is used only for the flagged ring, as DESIGN.md reserves colour for risk.
-->
<script setup lang="ts">
// background accounts and the links between them
const nodes = [
  [30, 60], [95, 30], [150, 85], [60, 150], [20, 250], [100, 220], [165, 175],
  [70, 320], [150, 300], [205, 345], [350, 16], [372, 72], [395, 170], [385, 300], [320, 345],
]
const links = [
  [0, 1], [1, 2], [0, 3], [2, 3], [3, 5], [4, 5], [5, 6], [2, 6], [4, 7], [7, 8], [5, 8],
  [8, 9], [9, 14], [10, 11], [11, 12], [12, 13], [13, 14], [6, 8],
]
// the ring inside the lens
const ring = [[215, 125], [290, 110], [320, 185], [260, 235], [200, 200]]
</script>

<template>
  <svg class="title-art" viewBox="0 0 420 380" role="img"
       aria-label="A magnifying glass over a web of player accounts, highlighting a linked ring moving money.">
    <g class="web">
      <line v-for="([a, b], i) in links" :key="'l' + i"
            :x1="nodes[a][0]" :y1="nodes[a][1]" :x2="nodes[b][0]" :y2="nodes[b][1]" />
      <circle v-for="([x, y], i) in nodes" :key="'n' + i" :cx="x" :cy="y" r="9" />
    </g>

    <!-- lens -->
    <circle cx="258" cy="172" r="112" class="lens-fill" />
    <g class="ring">
      <line v-for="(p, i) in ring" :key="'r' + i"
            :x1="p[0]" :y1="p[1]" :x2="ring[(i + 1) % ring.length][0]" :y2="ring[(i + 1) % ring.length][1]" />
      <line :x1="ring[0][0]" :y1="ring[0][1]" :x2="ring[2][0]" :y2="ring[2][1]" class="thin" />
      <line :x1="ring[1][0]" :y1="ring[1][1]" :x2="ring[4][0]" :y2="ring[4][1]" class="thin" />
      <g v-for="([x, y], i) in ring" :key="'c' + i">
        <circle :cx="x" :cy="y" r="19" />
        <text :x="x" :y="y + 7" text-anchor="middle">$</text>
      </g>
    </g>
    <circle cx="258" cy="172" r="112" class="lens-rim" />
    <circle cx="258" cy="172" r="100" class="lens-glint" />

    <!-- handle -->
    <line x1="338" y1="252" x2="402" y2="316" class="neck" />
    <line x1="356" y1="270" x2="408" y2="322" class="handle" />

    <!-- tag -->
    <g transform="translate(140 20)">
      <rect width="190" height="32" rx="4" class="tag" />
      <text x="95" y="21" text-anchor="middle" class="tag-text">LINKED RING FLAGGED</text>
    </g>
  </svg>
</template>

<style scoped>
.title-art { width: 100%; height: auto; display: block; }
.web line { stroke: var(--rule); stroke-width: 2.5; }
.web circle { fill: var(--surface); stroke: #9EA3AA; stroke-width: 2.5; }
.lens-fill { fill: var(--surface); }
.ring line { stroke: var(--risk-critical); stroke-width: 3.5; }
.ring line.thin { stroke-width: 2; stroke-dasharray: 5 5; }
.ring circle { fill: var(--risk-critical); }
.ring text { fill: #fff; font: 600 20px var(--mono); }
.lens-rim { fill: none; stroke: var(--ink); stroke-width: 13; }
.lens-glint { fill: none; stroke: var(--accent); stroke-width: 2; opacity: 0.35; }
.neck { stroke: var(--ink); stroke-width: 16; stroke-linecap: round; }
.handle { stroke: var(--accent); stroke-width: 26; stroke-linecap: round; }
.tag { fill: var(--ink); }
.tag-text { fill: #fff; font: 600 14px var(--sans); letter-spacing: 0.08em; }
</style>
