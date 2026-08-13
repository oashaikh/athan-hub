<template>
  <div class="admin-page">
    <header class="admin-page-heading"><p class="section-kicker">Quran resources</p><h1>Downloads & rewards</h1><p>Keep chosen recitations offline and choose whether siblings see a weekly leaderboard.</p></header>
    <div class="admin-stat-grid"><article class="surface-card"><span class="material-icons">storage</span><strong>{{ format(cache.byte_count) }}</strong><small>of {{ format(cache.limit_bytes) }} cached</small></article><article class="surface-card"><span class="material-icons">audio_file</span><strong>{{ cache.object_count || 0 }}</strong><small>recordings available offline</small></article><article class="surface-card"><span class="material-icons">push_pin</span><strong>{{ cache.pinned_count || 0 }}</strong><small>protected from cleanup</small></article></div>

    <form class="surface-card cache-download-form" @submit.prevent="prefetch">
      <div><h2>Download for offline use</h2><p>The download continues in the background. Pin individual recordings below to protect them from automatic cleanup.</p></div>
      <label>Reciter<select v-model.number="download.recitation_id" required><option disabled value="">Choose a reciter</option><option v-for="reciter in recitations" :key="reciter.id" :value="reciter.id">{{ reciter.name }} · {{ capability(reciter) }}</option></select></label>
      <label>Coverage<select v-model="download.surah_id"><option value="">Entire Quran</option><option v-for="surah in surahs" :key="surah.id" :value="surah.id">{{ surah.id }}. {{ surah.name_simple }}</option></select></label>
      <button class="button is-primary" :disabled="downloading">{{ downloading ? 'Starting…' : 'Start download' }}</button>
      <p v-if="notice" class="form-notice" role="status">{{ notice }}</p>
    </form>

    <form class="surface-card cache-limit-form" @submit.prevent="saveLimit"><div><h2>Storage limit</h2><p>Older unpinned recordings are removed automatically when this limit is reached.</p></div><label>Maximum cache (GB)<input v-model.number="limitGb" type="number" min="0.0625" max="1024" step="0.25" required></label><button class="button is-primary">Save limit</button></form>

    <details v-if="cache.by_reciter?.length" class="surface-card cache-groups"><summary>Usage by reciter</summary><ul><li v-for="row in cache.by_reciter" :key="row.recitation_id"><span>{{ row.name }}</span><strong>{{ format(row.byte_count) }} · {{ row.object_count }} files</strong></li></ul></details>

    <section v-if="cache.items?.length" class="surface-card cache-library">
      <div><h2>Downloaded recordings</h2><p>Recently used recordings appear first.</p></div>
      <div class="cache-list">
        <article v-for="item in cache.items" :key="item.id">
          <span class="material-icons">{{ item.pinned ? 'push_pin' : 'audio_file' }}</span>
          <div><strong>{{ reciterName(item.recitation_id) }}</strong><small>{{ selectionName(item.content_key) }} · {{ format(item.byte_count) }}</small></div>
          <button class="button is-small" @click="pin(item)">{{ item.pinned ? 'Unpin' : 'Pin' }}</button>
          <button class="button is-small is-danger is-light" aria-label="Delete cached recording" @click="remove(item)"><span class="material-icons">delete</span></button>
        </article>
      </div>
    </section>

    <form class="surface-card leaderboard-form" @submit.prevent="save"><div><h2>Sibling leaderboard</h2><p>Off by default. Stars recognise daily practice, completed surahs, and memorisation milestones—not individual ayahs or repetitions.</p></div><label class="toggle-line"><input v-model="reward.enabled" type="checkbox"> Show weekly leaderboard</label><fieldset :disabled="!reward.enabled"><legend>Include points for</legend><label><input v-model="reward.daily_practice" type="checkbox"> Daily practice</label><label><input v-model="reward.memorised" type="checkbox"> Memorisation milestones</label><label><input v-model="reward.surahs" type="checkbox"> Completed surahs</label></fieldset><button class="button is-primary">Save reward settings</button></form>
    <article class="surface-card source-notice"><h2>Verified sources</h2><p>Arabic text, Saheeh International, transliteration and the 139-reciter catalogue are pinned from QUL. Source hashes and notices ship with this installation.</p><router-link to="/admin/quran-sources">Review sources and licences</router-link></article>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import api from '../api'

const cache = reactive<any>({ items: [] })
const reward = reactive<any>({ enabled: false, repetitions: false, daily_practice: true, memorised: true, surahs: true })
const download = reactive<any>({ recitation_id: '', surah_id: '' })
const recitations = ref<any[]>([])
const surahs = ref<any[]>([])
const notice = ref('')
const downloading = ref(false)
const limitGb = ref(5)
const format = (n = 0) => new Intl.NumberFormat(undefined, { style: 'unit', unit: 'megabyte', maximumFractionDigits: 1 }).format(n / 1048576)
const capability = (row: any) => row.source_kind === 'ayah' ? 'ayah audio' : row.capability === 'segmented_surah' ? 'timed surah audio' : 'surah audio'
const reciterName = (id: number) => recitations.value.find(row => row.id === id)?.name || `Recitation ${id}`
const selectionName = (key: string) => key.includes(':') ? `Ayah ${key}` : surahs.value.find(row => row.id === Number(key))?.name_simple || `Surah ${key}`
const loadCache = async () => Object.assign(cache, (await api.get('/admin/quran/cache')).data)
const load = async () => {
  const [cacheResponse, rewardResponse, settingsResponse, recitationResponse, surahResponse] = await Promise.all([api.get('/admin/quran/cache'), api.get('/admin/quran/rewards'), api.get('/admin/quran/settings'), api.get('/quran/recitations'), api.get('/quran/surahs')])
  Object.assign(cache, cacheResponse.data); Object.assign(reward, rewardResponse.data); recitations.value = recitationResponse.data; surahs.value = surahResponse.data
  limitGb.value = settingsResponse.data.quran_cache_limit_bytes / 1073741824
}
const save = async () => Object.assign(reward, (await api.put('/admin/quran/rewards', reward)).data)
const saveLimit = async () => { const { data } = await api.put('/admin/quran/settings', { quran_cache_limit_bytes: Math.round(limitGb.value * 1073741824) }); limitGb.value = data.quran_cache_limit_bytes / 1073741824; await loadCache() }
const pin = async (item: any) => { await api.put(`/admin/quran/cache/${item.id}`, { pinned: !item.pinned }); await loadCache() }
const remove = async (item: any) => { await api.delete(`/admin/quran/cache/${item.id}`); await loadCache() }
const prefetch = async () => {
  downloading.value = true; notice.value = ''
  try {
    await api.post('/admin/quran/cache/prefetch', { recitation_id: download.recitation_id, surah_id: download.surah_id || null })
    notice.value = download.surah_id ? 'Surah download started.' : 'Full-recitation download started. This may take a while.'
  } finally { downloading.value = false }
}
onMounted(load)
</script>
