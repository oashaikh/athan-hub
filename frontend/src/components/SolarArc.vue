<template>
  <figure
    class="solar-figure"
    :class="`is-${state.phase}`"
    role="img"
    :aria-label="`Solar position: ${state.label}. ${state.detail}.`"
  >
    <svg class="solar-svg" viewBox="0 0 360 220" aria-hidden="true">
      <defs>
        <radialGradient id="solar-disc" cx="36%" cy="32%" r="70%">
          <stop offset="0" stop-color="#fffce8" />
          <stop offset="0.36" stop-color="#ffe8a3" />
          <stop offset="0.76" stop-color="#efb75f" />
          <stop offset="1" stop-color="#d47a38" />
        </radialGradient>
        <linearGradient id="solar-horizon" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0" stop-color="#d7a95b" stop-opacity="0" />
          <stop offset="0.5" stop-color="#efd28d" stop-opacity="0.62" />
          <stop offset="1" stop-color="#d7a95b" stop-opacity="0" />
        </linearGradient>
        <filter id="solar-glow" x="-150%" y="-150%" width="400%" height="400%">
          <feGaussianBlur stdDeviation="9" />
        </filter>
      </defs>

      <g class="solar-stars">
        <circle cx="72" cy="58" r="1.2" />
        <circle cx="133" cy="31" r="0.8" />
        <circle cx="229" cy="42" r="1" />
        <circle cx="302" cy="73" r="1.3" />
        <circle cx="264" cy="104" r="0.7" />
      </g>

      <path class="solar-arc-track" d="M30 174 C95 58 265 58 330 174" pathLength="1" />
      <path
        class="solar-arc-progress"
        d="M30 174 C95 58 265 58 330 174"
        pathLength="1"
        :style="{ strokeDashoffset: String(1 - state.daylightProgress) }"
      />
      <path class="solar-horizon-glow" d="M12 176 H348" />
      <path class="solar-horizon" d="M22 176 H338" />

      <g
        class="solar-position"
        :style="{
          transform: `translate(${state.x}px, ${state.y}px)`,
          opacity: state.sunOpacity
        }"
      >
        <circle class="solar-bloom" r="27" filter="url(#solar-glow)" />
        <g class="solar-rays">
          <path d="M0 -24 V-31 M17 -17 L22 -22 M24 0 H31 M17 17 L22 22 M0 24 V31 M-17 17 L-22 22 M-24 0 H-31 M-17 -17 L-22 -22" />
        </g>
        <circle class="solar-disc" r="13" />
        <circle class="solar-disc-highlight" cx="-3.5" cy="-4" r="3" />
      </g>

      <g class="solar-ground">
        <path d="M0 191 Q40 173 86 184 T170 183 T258 181 T360 188 V220 H0Z" />
      </g>
    </svg>

    <figcaption class="solar-caption">
      <span>{{ state.label }}</span>
      <small>{{ state.detail }}</small>
    </figcaption>
  </figure>
</template>

<script setup lang="ts">
import type { SolarState } from '../solar'

defineProps<{ state: SolarState }>()
</script>

<style scoped>
.solar-figure { position: relative; width: min(27vw, 360px); margin: 0; justify-self: end; color: var(--period-primary); }
.solar-svg { display: block; width: 100%; height: auto; overflow: visible; }
.solar-stars { fill: rgba(218,231,236,.76); opacity: calc(.82 - var(--daylight-level) * .82); transition: opacity 1.2s ease; }
.solar-arc-track { fill: none; stroke: rgba(220,235,236,.16); stroke-dasharray: 2 5; stroke-linecap: round; stroke-width: 1.2; }
.solar-arc-progress { fill: none; stroke: color-mix(in srgb, var(--period-primary) 68%, white); stroke-dasharray: 1; stroke-linecap: round; stroke-width: 1.5; opacity: .62; transition: stroke-dashoffset 1s linear, stroke 1.2s ease; }
.solar-horizon { fill: none; stroke: rgba(221,235,235,.25); stroke-width: 1; }
.solar-horizon-glow { fill: none; stroke: url(#solar-horizon); stroke-width: 6; opacity: calc(.15 + var(--twilight-level) * .85); transition: opacity 1.2s ease; }
.solar-position { transform-box: view-box; transform-origin: 0 0; transition: transform 1s linear, opacity 1.2s ease; }
.solar-bloom { fill: #f0b761; opacity: calc(.24 + var(--twilight-level) * .35); }
.solar-rays { fill: none; stroke: rgba(255,226,153,.72); stroke-linecap: round; stroke-width: 1.2; }
.solar-disc { fill: url(#solar-disc); stroke: rgba(255,250,220,.7); stroke-width: .75; }
.solar-disc-highlight { fill: rgba(255,255,245,.6); }
.solar-ground { fill: rgba(4,15,21,.72); }
.solar-caption { display: flex; align-items: baseline; justify-content: space-between; gap: 12px; margin: -6px 22px 0; color: var(--color-text-muted); font-size: .65rem; letter-spacing: .06em; text-transform: uppercase; }
.solar-caption span { color: var(--color-text); font-weight: 760; }
.solar-caption small { color: var(--color-text-subtle); font: inherit; }

@media (max-width: 1120px) {
  .solar-figure { position: absolute; z-index: 0; top: 50%; right: -2%; width: min(46vw, 380px); opacity: .44; transform: translateY(-53%); }
  .solar-caption { display: none; }
}

@media (max-width: 760px) {
  .solar-figure { top: 41%; right: 50%; width: min(92vw, 390px); opacity: .3; transform: translate(50%, -50%); }
}

@media (prefers-reduced-motion: reduce) {
  .solar-stars,
  .solar-arc-progress,
  .solar-horizon-glow,
  .solar-position { transition: none; }
}
</style>
