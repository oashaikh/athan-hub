<template>
  <section class="quran-player" aria-label="Recitation player">
    <audio ref="audio" :src="source" preload="none" @loadedmetadata="seekToVerse" @timeupdate="onTimeUpdate" @ended="onEnded" @play="playing = true" @pause="onPause" @error="failed"></audio>
    <button class="player-button" type="button" :disabled="!source" @click="toggle">
      <span class="material-icons" aria-hidden="true">{{ playing ? 'pause' : 'play_arrow' }}</span>
      <span>{{ playing ? 'Pause' : 'Listen' }}</span>
    </button>
    <div class="player-progress">
      <strong>{{ recitation?.capability === 'surah' ? 'Whole surah recording' : current?.verse_key || 'Choose a verse' }}</strong>
      <span v-if="recitation?.capability === 'surah'">Verse-level repetition is unavailable</span><span v-else>Repeat {{ repeatIndex }} of {{ repetitions }}</span>
    </div>
    <button v-if="recitation?.capability !== 'surah'" type="button" class="player-skip" :disabled="verseIndex === 0" @click="previous">Previous</button>
    <button v-if="recitation?.capability !== 'surah'" type="button" class="player-skip" :disabled="verseIndex >= verses.length - 1" @click="next">Next</button>
    <p v-if="audioError" class="player-error" role="status">{{ audioError }} <button type="button" @click="retry">Retry</button></p>
  </section>
</template>

<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import api from '../api'

const props = defineProps<{ profileId: number; recitation: any; verses: any[]; repetitions: number; playbackSpeed: number }>()
const emit = defineEmits<{ 'playback-started': []; 'repetition-complete': [verseKey: string]; 'range-complete': []; 'playback-error': [message: string]; 'verse-highlight': [verseKey: string | null]; 'word-progress': [progress: { verseKey: string; fraction: number } | null] }>()
const audio = ref<HTMLAudioElement | null>(null)
const verseIndex = ref(0)
const repeatIndex = ref(1)
const playing = ref(false)
const segmentMap = ref<Record<string, { time_from: number; time_to: number }>>({})
const segmentEnding = ref(false)
const audioError = ref('')
const started = ref(false)
const current = computed(() => props.verses[verseIndex.value])
const highlightedVerse = computed(() => (playing.value && current.value && props.recitation?.capability !== 'surah') ? current.value.verse_key : null)
watch(highlightedVerse, value => emit('verse-highlight', value))
const source = computed(() => {
  if (!current.value || !props.recitation) return ''
  const query = new URLSearchParams({ surah_id: String(current.value.surah_id) })
  if (props.recitation.capability === 'ayah') query.set('verse_key', current.value.verse_key)
  return `/api/quran/audio/${props.recitation.id}?${query}`
})

const prepare = () => { if (audio.value) audio.value.playbackRate = props.playbackSpeed }
const seekToVerse = () => { if (audio.value && props.recitation?.capability === 'segmented_surah' && current.value) audio.value.currentTime = (segmentMap.value[current.value.verse_key]?.time_from || 0) / 1000 }
const failMessage = 'This recording is not available yet. Check the internet connection or cache space, then retry.'
const failed = () => { playing.value = false; audioError.value = failMessage; emit('playback-error', failMessage) }
const onPause = () => { playing.value = false; emit('word-progress', null) }
const play = async () => { if (!audio.value) return; try { audioError.value = ''; prepare(); await audio.value.play(); if (!started.value) { started.value = true; emit('playback-started') } } catch { failed() } }
const toggle = async () => { if (!audio.value) return; audio.value.paused ? await play() : audio.value.pause() }
const loadAndPlay = async () => { await nextTick(); if (!audio.value) return; audio.value.load(); await play() }
const retry = async () => { if (!audio.value) return; audioError.value = ''; audio.value.load(); await play() }
const emitAyahWordProgress = () => {
  if (!playing.value || !audio.value || !current.value || !Number.isFinite(audio.value.duration) || audio.value.duration <= 0) { emit('word-progress', null); return }
  emit('word-progress', { verseKey: current.value.verse_key, fraction: Math.min(1, Math.max(0, audio.value.currentTime / audio.value.duration)) })
}
const emitSegmentedWordProgress = () => {
  if (!playing.value || !audio.value || !current.value) { emit('word-progress', null); return }
  const segment = segmentMap.value[current.value.verse_key]
  const span = segment && segment.time_to - segment.time_from
  const currentTime = audio.value.currentTime * 1000
  if (!segment || !Number.isFinite(span) || span <= 0 || !Number.isFinite(currentTime)) { emit('word-progress', null); return }
  emit('word-progress', { verseKey: current.value.verse_key, fraction: Math.min(1, Math.max(0, (currentTime - segment.time_from) / span)) })
}
const onEnded = async () => {
  emit('word-progress', null)
  if (props.recitation?.capability === 'surah') { playing.value = false; emit('range-complete'); return }
  if (!current.value) return
  emit('repetition-complete', current.value.verse_key)
  if (repeatIndex.value < props.repetitions) { repeatIndex.value++; await loadAndPlay(); return }
  repeatIndex.value = 1
  if (verseIndex.value < props.verses.length - 1) { verseIndex.value++; await loadAndPlay() }
  else { playing.value = false; emit('range-complete') }
}
const onTimeUpdate = async () => {
  if (props.recitation?.capability === 'ayah') emitAyahWordProgress()
  if (props.recitation?.capability === 'segmented_surah') emitSegmentedWordProgress()
  if (props.recitation?.capability === 'surah') emit('word-progress', null)
  if (!audio.value || !current.value || props.recitation?.capability !== 'segmented_surah' || segmentEnding.value) return
  const segment = segmentMap.value[current.value.verse_key]
  if (segment && audio.value.currentTime * 1000 >= segment.time_to) {
    segmentEnding.value = true
    audio.value.pause()
    await onEnded()
    segmentEnding.value = false
  }
}
const loadSegments = async () => {
  if (props.recitation?.capability !== 'segmented_surah' || !props.verses.length) { segmentMap.value = {}; return }
  try { const { data } = await api.get(`/quran/recitations/${props.recitation.id}/segments`, { params: { surah_id: props.verses[0].surah_id, start_ayah: props.verses[0].ayah_number, end_ayah: props.verses.at(-1).ayah_number } }); segmentMap.value = data.segments || {} } catch { segmentMap.value = {}; failed() }
}
const previous = () => { verseIndex.value = Math.max(0, verseIndex.value - 1); repeatIndex.value = 1 }
const next = () => { verseIndex.value = Math.min(props.verses.length - 1, verseIndex.value + 1); repeatIndex.value = 1 }
watch(() => props.verses, () => { verseIndex.value = 0; repeatIndex.value = 1; started.value = false; audioError.value = '' })
watch(() => props.recitation?.id, () => { started.value = false; audioError.value = '' })
watch(() => props.playbackSpeed, prepare)
watch(() => [props.recitation?.id, props.verses], loadSegments, { immediate: true, deep: true })
</script>
