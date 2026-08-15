<template>
  <div class="quran-workspace" :data-profile-theme="profile?.theme || 'classic_mushaf'">
    <ChildHeader />
    <div v-if="!profile" class="quran-empty"><span class="material-icons">person_add</span><h1>An admin needs to create a profile first.</h1><router-link to="/admin/profiles">Open profile settings</router-link></div>
    <main v-else class="quran-layout">
      <div class="mobile-quran-tools"><button type="button" :aria-expanded="surahOpen" @click="surahOpen = true"><span class="material-icons">menu_book</span>Surahs</button><button type="button" :aria-expanded="practiceOpen" @click="practiceOpen = true"><span class="material-icons">tune</span>Practice setup</button></div>
      <button v-if="surahOpen || practiceOpen" type="button" class="panel-backdrop" aria-label="Close panel" @click="closePanels"></button>
      <aside class="surah-rail" :class="{ 'mobile-open': surahOpen }">
        <button type="button" class="mobile-panel-close" aria-label="Close surah picker" @click="surahOpen = false"><span class="material-icons">close</span></button>
        <div class="rail-heading"><p class="section-kicker">The Quran</p><h1>Choose a surah</h1></div>
        <input v-model="search" type="search" placeholder="Search 114 surahs" aria-label="Search surahs">
        <nav aria-label="Surahs">
          <button v-for="surah in filteredSurahs" :key="surah.id" type="button" :class="{ active: surah.id === surahId }" @click="selectSurah(surah.id)">
            <span>{{ surah.id }}</span><strong>{{ surah.name_simple }}</strong><small>{{ surah.translated_name }}</small>
          </button>
        </nav>
      </aside>

      <section class="verse-reader">
        <header><div><p class="section-kicker">Now practising</p><h2>{{ selectedSurah?.name_simple }}</h2></div><RewardSummary :rewards="rewards" :leaderboard="leaderboard" /></header>
        <div v-if="error" class="reader-error" role="status"><span class="material-icons">error_outline</span><span>{{ error }}</span><button type="button" @click="retry">Retry</button></div>
        <div v-if="loading" class="reader-message">Loading verses…</div>
        <div v-else class="verse-list">
          <article v-for="verse in selectedVerses" :key="verse.verse_key" :ref="el => setVerseEl(verse.verse_key, el)" class="verse" :class="[progressState(verse.verse_key), { playing: verse.verse_key === highlightedVerse }]">
            <span class="verse-number">{{ verse.ayah_number }}</span>
            <p v-if="profile.show_arabic && (!profile.recall_mode || (listenCounts[verse.verse_key] || 0) < profile.repetitions || revealed.has(verse.verse_key))" class="arabic" dir="rtl">{{ verse.arabic }}</p>
            <button v-else-if="profile.show_arabic" type="button" class="reveal" @click="revealed.add(verse.verse_key)">Reveal Arabic</button>
            <p v-if="profile.show_translation" class="translation">{{ verse.translation }}</p>
            <p v-if="profile.show_transliteration" class="transliteration">{{ verse.transliteration }}</p>
            <div class="mastery-controls" aria-label="Memorisation state">
              <button type="button" @click="mark(verse, 'learning')">Learning</button>
              <button type="button" @click="mark(verse, 'needs_practice')">Needs practice</button>
              <button type="button" @click="mark(verse, 'memorised')">Memorised</button>
            </div>
          </article>
        </div>
        <QuranPlayer v-if="recitation && selectedVerses.length" :profile-id="profile.id" :recitation="recitation" :verses="selectedVerses" :repetitions="profile.repetitions" :playback-speed="profile.playback_speed" @playback-started="startSession" @repetition-complete="repetition" @range-complete="completeSession" @playback-error="showError" @verse-highlight="key => highlightedVerse = key" />
      </section>

      <aside class="practice-panel" :class="{ 'mobile-open': practiceOpen }">
        <button type="button" class="mobile-panel-close" aria-label="Close practice setup" @click="practiceOpen = false"><span class="material-icons">close</span></button>
        <p class="section-kicker">Practice setup</p><h2>Make this session yours</h2>
        <label>Reciter<select v-model.number="profile.preferred_recitation_id" @change="saveState"><option v-for="row in recitations" :key="row.id" :value="row.id">{{ row.name }} · {{ capabilityLabel(row) }}{{ recommendation(row) }}</option></select></label>
        <div class="range"><label>From<input v-model.number="profile.start_ayah" type="number" min="1" :max="selectedSurah?.ayah_count" @change="saveState"></label><label>To<input v-model.number="profile.end_ayah" type="number" min="1" :max="selectedSurah?.ayah_count" @change="saveState"></label></div>
        <label>Repetitions<select v-model.number="profile.repetitions" @change="saveState"><option v-for="count in [1,3,5,10]" :key="count">{{ count }}</option></select></label>
        <label>Speed<select v-model.number="profile.playback_speed" @change="saveState"><option :value=".75">0.75×</option><option :value="1">Normal</option><option :value="1.25">1.25×</option></select></label>
        <fieldset><legend>Reader</legend><label><input v-model="profile.show_arabic" type="checkbox" @change="saveState"> Arabic</label><label><input v-model="profile.show_translation" type="checkbox" @change="saveState"> English</label><label><input v-model="profile.show_transliteration" type="checkbox" @change="saveState"> Transliteration</label><label><input v-model="profile.recall_mode" type="checkbox" @change="saveState"> Recall mode</label></fieldset>
        <p v-if="recitation" class="capability-note"><strong>{{ capabilityLabel(recitation) }}</strong>{{ capabilityNote(recitation) }}</p>
      </aside>
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, reactive, ref, watch } from 'vue'
import api from '../api'
import ChildHeader from '../components/ChildHeader.vue'
import QuranPlayer from '../components/QuranPlayer.vue'
import RewardSummary from '../components/RewardSummary.vue'
import { useProfileStore } from '../stores/profile'

const store = useProfileStore(), surahs = ref<any[]>([]), recitations = ref<any[]>([]), verses = ref<any[]>([]), rewards = ref<any>(null), leaderboard = ref<any>(null), search = ref(''), loading = ref(true), error = ref(''), revealed = reactive(new Set<string>()), listenCounts = reactive<Record<string,number>>({}), progress = ref<any[]>([]), sessionId = ref<number | null>(null), sessionRepetitions = ref(0), surahOpen = ref(false), practiceOpen = ref(false), highlightedVerse = ref<string | null>(null)
let sessionStartedAt = 0
let repetitionQueue: Promise<void> = Promise.resolve()
let initialising = true
const profile = computed(() => store.selected.value), surahId = ref(1)
const selectedSurah = computed(() => surahs.value.find(row => row.id === surahId.value))
const filteredSurahs = computed(() => surahs.value.filter(row => `${row.name_simple} ${row.translated_name}`.toLowerCase().includes(search.value.toLowerCase())))
const selectedVerses = computed(() => verses.value.filter(row => !profile.value || (row.ayah_number >= profile.value.start_ayah && row.ayah_number <= profile.value.end_ayah)))
const recitation = computed(() => recitations.value.find(row => row.id === profile.value?.preferred_recitation_id) || recitations.value[0])
const capabilityLabel = (row: any) => row.capability === 'ayah' ? 'Verse audio' : row.capability === 'segmented_surah' ? 'Timed surah' : 'Whole surah'
const recommendation = (row:any) => row.recommended === 'muallim' ? ' · recommended for memorisation' : row.recommended === 'kids_repeat' ? ' · recommended for younger children' : ''
const capabilityNote = (row: any) => row.capability === 'surah' ? ' — exact verse looping is unavailable for this recording.' : ' — supports the selected practice range.'
const progressState = (key: string) => progress.value.find(row => row.verse_key === key)?.state || ''
const message = (caught:any, fallback:string) => caught?.response?.status === 507 ? 'The Quran audio cache is full. Ask an admin to free space or raise its limit.' : caught?.response?.data?.detail || fallback
const showError = (value:string) => { error.value = value }
const closePanels = () => { surahOpen.value = false; practiceOpen.value = false }
const selectSurah = (id:number) => { surahId.value = id; surahOpen.value = false }
const loadVerses = async (resetRange = true) => { loading.value = true; error.value = ''; try { verses.value = (await api.get(`/quran/surahs/${surahId.value}/verses`)).data; if (profile.value && resetRange) { profile.value.start_ayah = 1; profile.value.end_ayah = selectedSurah.value?.ayah_count || 1; await saveState() } } catch (caught) { verses.value = []; error.value = message(caught, 'Quran text is unavailable. Ask an admin to run the diagnostic check.') } finally { loading.value = false } }
const saveState = async () => { if (!profile.value) return; if (profile.value.end_ayah < profile.value.start_ayah) profile.value.end_ayah = profile.value.start_ayah; sessionId.value = null; try { await api.put(`/quran/profiles/${profile.value.id}/state`, { recitation_id: recitation.value?.id || null, surah_id: surahId.value, start_ayah: profile.value.start_ayah, end_ayah: profile.value.end_ayah, repetitions: profile.value.repetitions, playback_speed: profile.value.playback_speed, show_arabic: profile.value.show_arabic, show_translation: profile.value.show_translation, show_transliteration: profile.value.show_transliteration, recall_mode: profile.value.recall_mode }) } catch (caught) { error.value = message(caught, 'Practice preferences could not be saved.') } }
const startSession = async () => { if (!profile.value || sessionId.value) return; try { const { data } = await api.post(`/quran/profiles/${profile.value.id}/sessions`, { surah_id: surahId.value, start_ayah: profile.value.start_ayah, end_ayah: profile.value.end_ayah, recitation_id: recitation.value?.id || null }); sessionId.value = data.id; sessionRepetitions.value = 0; sessionStartedAt = Date.now() } catch (caught) { error.value = message(caught, 'This practice session could not be started.') } }
const repetition = (key: string) => { if (!profile.value) return; const profileId = profile.value.id; sessionRepetitions.value += 1; listenCounts[key] = (listenCounts[key] || 0) + 1; let existing = progress.value.find(row => row.verse_key === key); if (!existing) { existing = { verse_key: key, state: 'learning', completed_repetitions: 0 }; progress.value.push(existing) } existing.completed_repetitions += 1; const completed = existing.completed_repetitions, state = existing.state || 'learning'; repetitionQueue = repetitionQueue.then(async () => { await api.put(`/quran/profiles/${profileId}/progress/${key}`, { state, completed_repetitions: completed }); const [rewardResult, leaderboardResult] = await Promise.all([api.get(`/quran/profiles/${profileId}/rewards`), api.get('/quran/leaderboard')]); if (profile.value?.id === profileId) { rewards.value = rewardResult.data; leaderboard.value = leaderboardResult.data } }).catch(caught => { error.value = message(caught, 'Repetition progress could not be saved.') }) }
const mark = async (verse: any, state: string) => { if (!profile.value) return; const existing = progress.value.find(row => row.verse_key === verse.verse_key); try { await api.put(`/quran/profiles/${profile.value.id}/progress/${verse.verse_key}`, { state, completed_repetitions: existing?.completed_repetitions || 0 }); await loadProfile() } catch (caught) { error.value = message(caught, 'Memorisation progress could not be saved.') } }
const loadProfile = async () => { if (!profile.value) return; const [detail, rewardResult, leaderboardResult] = await Promise.all([api.get(`/quran/profiles/${profile.value.id}`), api.get(`/quran/profiles/${profile.value.id}/rewards`), api.get('/quran/leaderboard')]); progress.value = detail.data.progress; rewards.value = rewardResult.data; leaderboard.value = leaderboardResult.data }
const completeSession = async () => { if (!profile.value || !sessionId.value) return; const elapsed = Math.max(1, Math.round((Date.now() - sessionStartedAt) / 1000)); const completedRepetitions = recitation.value?.capability === 'surah' ? 1 : sessionRepetitions.value; try { await repetitionQueue; await api.put(`/quran/profiles/${profile.value.id}/sessions/${sessionId.value}`, { repetitions: completedRepetitions, practice_seconds: elapsed, completed: true }); sessionId.value = null; sessionRepetitions.value = 0; await loadProfile() } catch (caught) { error.value = message(caught, 'Practice completion could not be saved.') } }
const verseEls = reactive<Record<string, Element>>({})
const setVerseEl = (key: string, el: Element | { $el: Element } | null) => { if (el) verseEls[key] = el instanceof Element ? el : el.$el }
const retry = () => loadVerses(false)
watch(highlightedVerse, async key => { if (!key) return; await nextTick(); verseEls[key]?.scrollIntoView({ behavior: 'smooth', block: 'center' }) })
watch(surahId, () => { if (!initialising) loadVerses(true) })
watch(profile, async (value, oldValue) => { if (!initialising && value && value.id !== oldValue?.id) { initialising = true; surahId.value = value.last_surah_id; await loadProfile(); await loadVerses(false); initialising = false } })
onMounted(async () => { try { await Promise.all([store.load(), api.get('/quran/surahs').then(r => surahs.value = r.data), api.get('/quran/recitations').then(r => recitations.value = r.data)]); if (profile.value) { surahId.value = profile.value.last_surah_id; await loadProfile(); await loadVerses(false) } else loading.value = false } catch (caught) { error.value = message(caught, 'Quran practice could not be loaded.'); loading.value = false } finally { initialising = false } })
</script>
