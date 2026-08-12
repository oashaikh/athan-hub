<template>
  <div class="admin-page">
    <header class="admin-page-heading"><p class="section-kicker">Household</p><h1>Child profiles</h1><p>Create the profiles children can switch between. Progress stays separate.</p></header>
    <form class="surface-card profile-form" @submit.prevent="create"><label>Name<input v-model="draft.name" required maxlength="80"></label><label>Gender<select v-model="draft.gender"><option :value="null">Not set</option><option value="boy">Boy</option><option value="girl">Girl</option></select></label><label>Theme<select v-model="draft.theme"><option :value="null">Use gender default</option><option v-for="theme in themes" :key="theme.value" :value="theme.value">{{ theme.label }}</option></select></label><button data-test="create-profile" class="button is-primary">Create profile</button></form>
    <div class="profile-admin-grid">
      <article v-for="profile in profiles" :key="profile.id" class="surface-card admin-profile" :class="{ archived: !profile.active }">
        <span class="profile-avatar" :data-theme="profile.theme">{{ profile.name[0] }}</span><div><h2>{{ profile.name }}</h2><p>{{ profile.memorised_count }} memorised · {{ profile.gender || 'gender not set' }}</p></div>
        <div class="profile-theme"><label :for="`theme-${profile.id}`">Theme</label><select :id="`theme-${profile.id}`" :value="profile.theme" @change="setTheme(profile, ($event.target as HTMLSelectElement).value)"><option v-for="theme in themes" :key="theme.value" :value="theme.value">{{ theme.label }}</option></select></div>
        <div class="profile-buttons"><button class="button is-small" @click="correct(profile)">Correct progress</button><button class="button is-small" @click="rename(profile)">Rename</button><button class="button is-small" @click="toggle(profile)">{{ profile.active ? 'Archive' : 'Restore' }}</button><button class="button is-small is-danger" @click="remove(profile)">Delete</button></div>
      </article>
    </div>
  </div>
</template>
<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import api from '../api'
const themes = [{ value: 'night_explorer', label: 'Night explorer' }, { value: 'garden_light', label: 'Garden light' }, { value: 'classic_mushaf', label: 'Classic mushaf' }]
const profiles = ref<any[]>([]), draft = reactive<{name:string;gender:string|null;theme:string|null}>({ name: '', gender: null, theme: null })
const load = async () => profiles.value = (await api.get('/admin/profiles')).data
const create = async () => { const payload = { name: draft.name, gender: draft.gender, theme: draft.theme }; await api.post('/admin/profiles', payload); draft.name=''; draft.gender=null; draft.theme=null; await load() }
const rename = async (profile:any) => { const name=window.prompt('Profile name',profile.name)?.trim(); if(name){ await api.put(`/admin/profiles/${profile.id}`,{name}); await load() } }
const setTheme = async (profile:any, theme:string) => { await api.put(`/admin/profiles/${profile.id}`, { theme }); await load() }
const toggle = async (profile:any) => { await api.post(`/admin/profiles/${profile.id}/${profile.active?'archive':'restore'}`); await load() }
const remove = async (profile:any) => { if(window.confirm(`Permanently delete ${profile.name} and all progress?`)){ await api.delete(`/admin/profiles/${profile.id}`); await load() } }
const correct = async (profile:any) => { const key=window.prompt('Verse to correct (for example 2:255)')?.trim(); if(!key)return; const state=window.prompt('State: learning, needs_practice, or memorised','needs_practice')?.trim(); if(!['learning','needs_practice','memorised'].includes(state||''))return; await api.put(`/admin/profiles/${profile.id}/progress/${key}`,{state,completed_repetitions:0}); await load() }
onMounted(load)
</script>
