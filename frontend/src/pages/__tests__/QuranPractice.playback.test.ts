import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import QuranPractice from '../QuranPractice.vue'
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
const wordProgressVerses = [
  { verse_key: '1:1', surah_id: 1, ayah_number: 1, arabic: 'بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ', translation: 'In the name of Allah', transliteration: '' },
  { verse_key: '1:2', surah_id: 1, ayah_number: 2, arabic: 'الْحَمْدُ لِلَّهِ رَبِّ الْعَالَمِينَ', translation: 'All praise is due to Allah', transliteration: '' }
]
let verseFixture = verses

describe('QuranPractice', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    verseFixture = verses
    vi.mocked(api.get).mockImplementation((url: string) => {
      if (url === '/quran/profiles') return Promise.resolve({ data: [profile] })
      if (url === '/quran/surahs') return Promise.resolve({ data: surahs })
      if (url === '/quran/recitations') return Promise.resolve({ data: recitations })
      if (url === '/quran/profiles/1') return Promise.resolve({ data: { ...profile, progress: [] } })
      if (url === '/quran/profiles/1/rewards') return Promise.resolve({ data: { stars: 0, streak: 0, badges: [] } })
      if (url === '/quran/leaderboard') return Promise.resolve({ data: { enabled: false, entries: [] } })
      if (url === '/quran/surahs/1/verses') return Promise.resolve({ data: verseFixture })
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

  it('scrolls without a smooth animation when the user prefers reduced motion', async () => {
    vi.spyOn(window, 'matchMedia').mockReturnValue({ matches: true } as MediaQueryList)
    const wrapper = mount(QuranPractice, { global: { stubs: { ChildHeader: true, RewardSummary: true } } })
    await flushPromises()

    await wrapper.get('audio').trigger('play')
    await flushPromises()

    const playingVerse = wrapper.get('.verse.playing').element
    expect(playingVerse.scrollIntoView).toHaveBeenCalledWith({ behavior: 'auto', block: 'center' })
  })

  it('highlights the word corresponding to the playback fraction', async () => {
    verseFixture = wordProgressVerses
    const wrapper = mount(QuranPractice, { global: { stubs: { ChildHeader: true, RewardSummary: true } } })
    await flushPromises()
    const audio = wrapper.get('audio').element as HTMLAudioElement
    Object.defineProperty(audio, 'currentTime', { configurable: true, value: 15 })
    Object.defineProperty(audio, 'duration', { configurable: true, value: 60 })

    await wrapper.get('audio').trigger('play')
    await wrapper.get('audio').trigger('timeupdate')

    expect(wrapper.get('.verse.playing .arabic .arabic-word:nth-child(2)').classes()).toContain('active-word')
    expect(wrapper.get('.verse.playing .arabic .arabic-word:nth-child(3)').classes()).not.toContain('active-word')
    expect(wrapper.findAll('.verse:not(.playing) .active-word')).toHaveLength(0)
  })

  it('removes the active word when playback pauses', async () => {
    verseFixture = wordProgressVerses
    const wrapper = mount(QuranPractice, { global: { stubs: { ChildHeader: true, RewardSummary: true } } })
    await flushPromises()
    const audio = wrapper.get('audio').element as HTMLAudioElement
    Object.defineProperty(audio, 'currentTime', { configurable: true, value: 15 })
    Object.defineProperty(audio, 'duration', { configurable: true, value: 60 })

    await wrapper.get('audio').trigger('play')
    await wrapper.get('audio').trigger('timeupdate')
    expect(wrapper.find('.verse.playing .active-word').exists()).toBe(true)
    await wrapper.get('audio').trigger('pause')

    expect(wrapper.findAll('.active-word')).toHaveLength(0)
  })
})
