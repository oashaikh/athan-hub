<template><div class="admin-layout"><aside><router-link class="admin-brand" to="/admin"><span>A</span><strong>Athan Hub</strong><small>Administration</small></router-link><nav><router-link v-for="item in items" :key="item.to" :to="item.to"><span class="material-icons">{{ item.icon }}</span>{{ item.label }}</router-link></nav><router-link class="return-child" to="/"><span class="material-icons">arrow_back</span>Child dashboard</router-link></aside><main><router-view /></main></div></template>
<script setup lang="ts">
const items = [
  { to: '/admin', icon: 'dashboard', label: 'Overview' },
  { to: '/admin/profiles', icon: 'groups', label: 'Child profiles' },
  { to: '/admin/timetable', icon: 'calendar_today', label: 'Timetable' },
  { to: '/admin/bluetooth', icon: 'speaker', label: 'Bluetooth & speaker' },
  { to: '/admin/activity', icon: 'history', label: 'Activity' },
  { to: '/admin/exclusions', icon: 'block', label: 'Exclusions' },
  { to: '/admin/audio', icon: 'graphic_eq', label: 'Athan audio' },
  { to: '/admin/general', icon: 'tune', label: 'General' },
  { to: '/admin/quran-cache', icon: 'download', label: 'Quran downloads' },
  { to: '/admin/quran-sources', icon: 'verified', label: 'Sources & licences' }
]
</script>
