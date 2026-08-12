<template>
  <label class="profile-picker">
    <span class="sr-only">Child profile</span>
    <select v-if="profiles.length" :value="selectedId || ''" @change="select(Number(($event.target as HTMLSelectElement).value))">
      <option v-for="profile in profiles" :key="profile.id" :value="profile.id">{{ profile.name }}</option>
    </select>
    <router-link v-else to="/admin/profiles">Create a profile</router-link>
  </label>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useProfileStore } from '../stores/profile'
const { profiles, selectedId, load, select } = useProfileStore()
onMounted(load)
</script>
