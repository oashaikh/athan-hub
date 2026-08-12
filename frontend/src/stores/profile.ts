import { computed, ref } from 'vue'
import api from '../api'

export interface ChildProfile {
  id: number
  name: string
  theme: 'night_explorer' | 'garden_light' | 'classic_mushaf'
  preferred_recitation_id: number | null
  last_surah_id: number
  start_ayah: number
  end_ayah: number
  repetitions: 1 | 3 | 5 | 10
  playback_speed: number
  show_arabic: boolean
  show_translation: boolean
  show_transliteration: boolean
  recall_mode: boolean
}

const profiles = ref<ChildProfile[]>([])
const selectedId = ref<number | null>(Number(localStorage.getItem('athan-profile-id')) || null)
const selected = computed(() => profiles.value.find(profile => profile.id === selectedId.value) || profiles.value[0] || null)

export const profileState = { profiles, selectedId, selected }

export function useProfileStore() {
  const load = async () => {
    profiles.value = (await api.get('/quran/profiles')).data
    if (!profiles.value.some(profile => profile.id === selectedId.value)) selectedId.value = profiles.value[0]?.id || null
  }
  const select = (id: number) => {
    if (!profiles.value.some(profile => profile.id === id)) return
    selectedId.value = id
    localStorage.setItem('athan-profile-id', String(id))
  }
  return { profiles, selectedId, selected, load, select }
}
