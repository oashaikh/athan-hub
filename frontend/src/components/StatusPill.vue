<template>
  <span class="status-pill" :class="`is-${tone}`">
    <span class="status-pill-dot" aria-hidden="true"></span>
    <slot />
  </span>
</template>

<script setup lang="ts">
withDefaults(defineProps<{ tone?: string }>(), { tone: 'info' })
</script>
