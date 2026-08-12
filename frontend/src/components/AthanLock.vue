<template>
  <div v-if="active" class="athan-lock" role="alertdialog" aria-modal="true" aria-live="assertive">
    <div class="athan-lock-mark"><span class="material-icons" aria-hidden="true">volume_up</span></div>
    <p class="section-kicker">The call to prayer is playing</p>
    <h1>{{ prayerName }}</h1>
    <p>Please listen. Practice will be available again in {{ active.remaining_seconds }} seconds.</p>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, watch } from 'vue'
import { usePlaybackStore } from '../stores/playback'
const { active } = usePlaybackStore()
const prayerName = computed(() => active.value?.prayer ? active.value.prayer[0].toUpperCase() + active.value.prayer.slice(1) : 'Athan')
const blockKeyboard = (event: KeyboardEvent) => {
  if (!active.value) return
  event.preventDefault()
  event.stopImmediatePropagation()
}
watch(active, value => {
  const child = document.querySelector<HTMLElement>('#child-application')
  if (value) {
    document.querySelectorAll<HTMLMediaElement>('audio,video').forEach(media => {
      media.pause(); media.removeAttribute('src'); media.load()
    })
    child?.setAttribute('inert', '')
    document.documentElement.classList.add('athan-is-active')
  } else {
    child?.removeAttribute('inert')
    document.documentElement.classList.remove('athan-is-active')
  }
}, { immediate: true })
onMounted(() => document.addEventListener('keydown', blockKeyboard, true))
onBeforeUnmount(() => {
  document.removeEventListener('keydown', blockKeyboard, true)
  document.documentElement.classList.remove('athan-is-active')
})
</script>

<style scoped>
.athan-lock { position: fixed; z-index: 10000; inset: 0; display: grid; place-content: center; gap: 14px; padding: 24px; text-align: center; color: #f8f4e8; background: radial-gradient(circle at 50% 30%, #244d45, #07151a 58%); }
.athan-lock-mark { display: grid; width: 84px; height: 84px; margin: auto; place-items: center; border: 1px solid rgba(224,190,113,.7); border-radius: 50%; color: #e0be71; }
.athan-lock-mark span { font-size: 40px; }
.athan-lock h1 { margin: 0; font: 700 clamp(2.5rem, 7vw, 5rem)/1 Manrope, sans-serif; }
.athan-lock p { max-width: 520px; margin: auto; color: #b9c7c7; }
</style>
<style>
html.athan-is-active { overflow: hidden; }
</style>
