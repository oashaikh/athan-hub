import { flushPromises, mount } from '@vue/test-utils'
import { ref } from 'vue'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import QuranPractice from '../QuranPractice.vue'
import api from '../../api'

vi.mock('../../api', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn()
  }
}))

const profile = {
  id: 1,
  theme: 'classic_mushaf',
  preferred_recitation_id: null,
  last_surah_id: 1,
  start_ayah: 1,
  end_ayah: 7,
  repetitions: 3,
  playback_speed: 1,
  show_arabic: true,
  show_translation: true,
  show_transliteration: false,
  recall_mode: false
}

vi.mock('../../stores/profile', () => ({
  useProfileStore: () => ({ load: vi.fn(), selected: ref(profile) })
}))

const surahs = [
  { id: 1, name_simple: 'Al-Fatihah', translated_name: 'The Opener', ayah_count: 7 },
  { id: 78, name_simple: 'An-Naba', translated_name: 'The Announcement', ayah_count: 40 }
]

describe('QuranPractice surah rail', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(api.get).mockImplementation((url: string) => {
      if (url === '/quran/surahs') return Promise.resolve({ data: surahs })
      if (url === '/quran/recitations') return Promise.resolve({ data: [] })
      if (url.includes('/verses')) return Promise.resolve({ data: [] })
      if (url.includes('/rewards')) return Promise.resolve({ data: null })
      if (url === '/quran/leaderboard') return Promise.resolve({ data: null })
      if (/\/quran\/profiles\/\d+$/.test(url)) return Promise.resolve({ data: { progress: [] } })
      return Promise.resolve({ data: null })
    })
  })

  const mountPage = async () => {
    const wrapper = mount(QuranPractice, {
      global: { stubs: { ChildHeader: true, QuranPlayer: true, RewardSummary: true } }
    })
    await flushPromises()
    return wrapper
  }

  it('renders a Juz heading per non-empty group in Juz order', async () => {
    const wrapper = await mountPage()
    const nav = wrapper.get('.surah-rail nav')
    const headings = nav.findAll('.juz-heading').map(node => node.text())
    expect(headings).toEqual(['Juz 1', 'Juz 30'])
  })

  it('renders Juz headings as h3 elements for screen-reader navigation', async () => {
    const wrapper = await mountPage()
    const nav = wrapper.get('.surah-rail nav')
    const headings = nav.findAll('h3.juz-heading').map(node => node.text())
    expect(headings).toEqual(['Juz 1', 'Juz 30'])
  })

  it('hides a Juz group whose surahs are all filtered out by search', async () => {
    const wrapper = await mountPage()
    await wrapper.get('input[type="search"]').setValue('Naba')
    const nav = wrapper.get('.surah-rail nav')
    const headings = nav.findAll('.juz-heading').map(node => node.text())
    expect(headings).toEqual(['Juz 30'])
    expect(nav.findAll('button')).toHaveLength(1)
  })

  it('marks the currently selected surah button active', async () => {
    const wrapper = await mountPage()
    const active = wrapper.get('.surah-rail nav button.active')
    expect(active.text()).toContain('Al-Fatihah')
  })

  it('selects a surah and closes the mobile panel on click', async () => {
    const wrapper = await mountPage()
    await wrapper.get('.mobile-quran-tools button').trigger('click')
    expect(wrapper.find('.surah-rail.mobile-open').exists()).toBe(true)

    const buttons = wrapper.get('.surah-rail nav').findAll('button')
    await buttons[1].trigger('click')
    await flushPromises()

    expect(wrapper.get('.surah-rail nav button.active').text()).toContain('An-Naba')
    expect(wrapper.find('.surah-rail.mobile-open').exists()).toBe(false)
  })
})
