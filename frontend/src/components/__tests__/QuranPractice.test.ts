import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import QuranPractice from '../../pages/QuranPractice.vue'
import api from '../../api'

vi.mock('../../api', () => ({
  default: { get: vi.fn(), post: vi.fn(), put: vi.fn(), delete: vi.fn() }
}))

const profile = { id: 1, name: 'Zayd', theme: 'classic_mushaf', preferred_recitation_id: 100005, last_surah_id: 1, start_ayah: 1, end_ayah: 3, repetitions: 1, playback_speed: 1, show_arabic: true, show_translation: true, show_transliteration: false, recall_mode: false }
const surahs = [{ id: 1, name_simple: 'Al-Fatihah', translated_name: 'The Opening', ayah_count: 7 }]
const recitations = [{ id: 100005, name: 'Test Reciter', capability: 'ayah' }]
const verses = [
  { verse_key: '1:1', surah_id: 1, ayah_number: 1, arabic: 'a', translation: 'one', transliteration: '' },
  { verse_key: '1:2', surah_id: 1, ayah_number: 2, arabic: 'b', translation: 'two', transliteration: '' },
  { verse_key: '1:3', surah_id: 1, ayah_number: 3, arabic: 'c', translation: 'three', transliteration: '' }
]

describe('QuranPractice', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(api.get).mockImplementation((url: string) => {
      if (url === '/quran/profiles') return Promise.resolve({ data: [profile] })
      if (url === '/quran/surahs') return Promise.resolve({ data: surahs })
      if (url === '/quran/recitations') return Promise.resolve({ data: recitations })
      if (url === '/quran/profiles/1') return Promise.resolve({ data: { ...profile, progress: [] } })
      if (url === '/quran/profiles/1/rewards') return Promise.resolve({ data: { stars: 0, streak: 0, badges: [] } })
      if (url === '/quran/leaderboard') return Promise.resolve({ data: { enabled: false, entries: [] } })
      if (url === '/quran/surahs/1/verses') return Promise.resolve({ data: verses })
      return Promise.resolve({ data: {} })
    })
  })

  it('scrolls the ayah being recited to the middle of the page', async () => {
    const wrapper = mount(QuranPractice, { global: { stubs: { ChildHeader: true, RewardSummary: true } } })
    await flushPromises()

    await wrapper.get('audio').trigger('play')
    await flushPromises()

    const playingVerse = wrapper.get('.verse.playing').element
    expect(playingVerse.scrollIntoView).toHaveBeenCalledWith({ behavior: 'smooth', block: 'center' })
  })
})
