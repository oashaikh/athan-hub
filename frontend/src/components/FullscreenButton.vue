<template>
  <button
    v-if="supported"
    type="button"
    class="header-icon-button"
    :aria-label="label"
    :aria-pressed="active"
    :title="label"
    @click="toggleFullscreen"
  >
    <span class="material-icons" aria-hidden="true">{{ active ? 'fullscreen_exit' : 'fullscreen' }}</span>
  </button>
  <span v-if="error" class="sr-only" role="status">{{ error }}</span>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'

type FullscreenDocument = Document & {
  webkitExitFullscreen?: () => Promise<void> | void
  webkitFullscreenElement?: Element | null
  webkitFullscreenEnabled?: boolean
}

type FullscreenElement = HTMLElement & {
  webkitRequestFullscreen?: () => Promise<void> | void
}

const supported = ref(false)
const active = ref(false)
const error = ref('')
const label = computed(() => active.value ? 'Exit full screen' : 'Enter full screen')

const syncFullscreenState = () => {
  const fullscreenDocument = document as FullscreenDocument
  active.value = Boolean(document.fullscreenElement || fullscreenDocument.webkitFullscreenElement)
}

const toggleFullscreen = async () => {
  const fullscreenDocument = document as FullscreenDocument
  const root = document.documentElement as FullscreenElement
  error.value = ''
  try {
    if (document.fullscreenElement || fullscreenDocument.webkitFullscreenElement) {
      if (document.exitFullscreen) await document.exitFullscreen()
      else await fullscreenDocument.webkitExitFullscreen?.()
    } else if (root.requestFullscreen) {
      await root.requestFullscreen()
    } else {
      await root.webkitRequestFullscreen?.()
    }
    syncFullscreenState()
  } catch {
    error.value = 'Full screen could not be opened. Try again or use your browser menu.'
  }
}

onMounted(() => {
  const fullscreenDocument = document as FullscreenDocument
  const root = document.documentElement as FullscreenElement
  supported.value = Boolean(
    document.fullscreenEnabled ||
    fullscreenDocument.webkitFullscreenEnabled ||
    root.requestFullscreen ||
    root.webkitRequestFullscreen
  )
  syncFullscreenState()
  document.addEventListener('fullscreenchange', syncFullscreenState)
  document.addEventListener('webkitfullscreenchange', syncFullscreenState)
})

onBeforeUnmount(() => {
  document.removeEventListener('fullscreenchange', syncFullscreenState)
  document.removeEventListener('webkitfullscreenchange', syncFullscreenState)
})
</script>
