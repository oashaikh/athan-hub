<template>
  <header class="child-header">
    <router-link class="child-brand" to="/" aria-label="Athan Hub home"><span>A</span>Athan Hub</router-link>
    <nav aria-label="Main navigation">
      <router-link to="/">Prayer times</router-link>
      <router-link to="/quran">Quran practice</router-link>
    </nav>
    <div class="child-actions"><ProfilePicker /><a class="admin-lock" href="https://github.com/oashaikh/athan-hub" target="_blank" rel="noreferrer" aria-label="Athan Hub source code"><span class="material-icons">code</span></a><router-link class="admin-lock" to="/admin" aria-label="Open admin"><span class="material-icons">lock</span></router-link></div>
  </header>
</template>
<script setup lang="ts">
import ProfilePicker from './ProfilePicker.vue'
</script>
