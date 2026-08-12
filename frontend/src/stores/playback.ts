import { computed, ref } from 'vue'
import api from '../api'

export interface ActiveAthan { prayer: string; remaining_seconds: number; expected_finish_at?: string }

const active = ref<ActiveAthan | null>(null)
let timer: ReturnType<typeof setInterval> | null = null

const poll = async () => {
  try {
    const { data } = await api.get('/playback/status')
    active.value = data.active ? data : null
  } catch { /* retain the last safe state during a transient polling failure */ }
}

export const playbackState = { active }

export function usePlaybackStore() {
  const start = () => {
    if (timer) return
    poll()
    timer = setInterval(poll, 1000)
  }
  const stop = () => {
    if (timer) clearInterval(timer)
    timer = null
  }
  return { active, remaining: computed(() => active.value?.remaining_seconds || 0), start, stop }
}
