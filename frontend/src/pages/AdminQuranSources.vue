<template>
  <div class="admin-page">
    <header class="admin-page-heading"><p class="section-kicker">Provenance</p><h1>Sources & licences</h1><p>Every packaged Quran resource is pinned to a reviewed upstream revision and checksum.</p></header>
    <div v-if="sources" class="source-grid">
      <article class="surface-card source-summary"><span class="material-icons">verified</span><div><h2>Verified QUL snapshot</h2><p><strong>{{ shortCommit }}</strong> · imported {{ formatDate(sources.snapshot_at) }}</p><p>{{ sources.database.surahs }} surahs · {{ sources.database.ayahs.toLocaleString() }} ayahs · {{ sources.database.recitations }} recitations</p><a :href="sources.repository" target="_blank" rel="noreferrer">Open upstream repository</a><span v-if="sources.mirror"> · </span><a v-if="sources.mirror" :href="sources.mirror" target="_blank" rel="noreferrer">Open maintained mirror</a></div></article>
      <article v-for="dataset in sources.datasets" :key="dataset.name" class="surface-card dataset-card"><h2>{{ dataset.name }}</h2><p>{{ dataset.notice }}</p><details><summary>Source URLs and checksums</summary><ul><li v-for="url in dataset.urls" :key="url"><a :href="sourceUrl(url)" target="_blank" rel="noreferrer">{{ url }}</a><code v-if="dataset.sha256_by_url[url]">{{ dataset.sha256_by_url[url] }}</code></li></ul></details></article>
      <article class="surface-card notice-card"><h2>Required notice</h2><pre>{{ sources.notice }}</pre></article>
    </div>
    <p v-else class="reader-message">Loading source records…</p>
  </div>
</template>
<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import api from '../api'
const sources = ref<any>(null)
const shortCommit = computed(() => sources.value?.commit?.slice(0, 12))
const formatDate = (value:string) => new Intl.DateTimeFormat(undefined,{dateStyle:'medium',timeStyle:'short'}).format(new Date(value))
const sourceUrl = (url:string) => url.replace('{surah_id}','1')
onMounted(async()=>sources.value=(await api.get('/admin/quran/sources')).data)
</script>
