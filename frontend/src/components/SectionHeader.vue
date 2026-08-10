<template>
  <header class="section-header">
    <div class="section-icon" aria-hidden="true">
      <span class="material-icons">{{ icon }}</span>
    </div>
    <div class="section-heading-copy">
      <p class="section-kicker">Athan Hub settings</p>
      <h1>{{ title }}</h1>
      <p>{{ subtitle }}</p>
    </div>
  </header>
</template>

<script setup lang="ts">
defineProps<{ icon: string; title: string; subtitle: string }>()
</script>
