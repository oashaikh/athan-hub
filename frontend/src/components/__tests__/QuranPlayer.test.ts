import { flushPromises, mount } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'
import api from '../../api'
import QuranPlayer from '../QuranPlayer.vue'

vi.mock('../../api', () => ({ default: { get: vi.fn() } }))

const verses = [
  { verse_key: '1:1', surah_id: 1, ayah_number: 1 },
  { verse_key: '1:2', surah_id: 1, ayah_number: 2 }
]

describe('QuranPlayer', () => {
  it('repeats a verse before advancing', async () => {
    const wrapper = mount(QuranPlayer, {
      props: { profileId: 1, recitation: { id: 100005, capability: 'ayah' }, verses, repetitions: 3, playbackSpeed: 1 }
    })
    await wrapper.get('audio').trigger('ended')
    await wrapper.get('audio').trigger('ended')
    expect(wrapper.emitted('repetition-complete')).toHaveLength(2)
    expect(wrapper.text()).toContain('Repeat 3 of 3')
  })

  it('does not pretend whole-surah audio can repeat individual verses', async () => {
    const wrapper = mount(QuranPlayer, {
      props: { profileId: 1, recitation: { id: 200046, capability: 'surah' }, verses, repetitions: 3, playbackSpeed: 1 }
    })
    await wrapper.get('audio').trigger('ended')
    expect(wrapper.emitted('repetition-complete')).toBeUndefined()
    expect(wrapper.emitted('range-complete')).toHaveLength(1)
  })

  it('emits the playing verse key while audio plays, and clears it on pause', async () => {
    const wrapper = mount(QuranPlayer, {
      props: { profileId: 1, recitation: { id: 100005, capability: 'ayah' }, verses, repetitions: 1, playbackSpeed: 1 }
    })
    await wrapper.get('audio').trigger('play')
    expect(wrapper.emitted('verse-highlight')?.at(-1)).toEqual(['1:1'])
    await wrapper.get('audio').trigger('pause')
    expect(wrapper.emitted('verse-highlight')?.at(-1)).toEqual([null])
  })

  it('emits the current ayah word-progress fraction on timeupdate', async () => {
    const wrapper = mount(QuranPlayer, {
      props: { profileId: 1, recitation: { id: 100005, capability: 'ayah' }, verses, repetitions: 1, playbackSpeed: 1 }
    })
    const audio = wrapper.get('audio').element as HTMLAudioElement
    Object.defineProperty(audio, 'currentTime', { configurable: true, value: 15 })
    Object.defineProperty(audio, 'duration', { configurable: true, value: 60 })

    await wrapper.get('audio').trigger('play')
    await wrapper.get('audio').trigger('timeupdate')

    expect(wrapper.emitted('word-progress')).toEqual([[{ verseKey: '1:1', fraction: 0.25 }]])
  })

  it('emits segmented-surah word-progress from the current verse segment', async () => {
    vi.mocked(api.get).mockResolvedValueOnce({ data: { segments: { '1:1': { time_from: 1000, time_to: 5000 } } } } as never)
    const wrapper = mount(QuranPlayer, {
      props: { profileId: 1, recitation: { id: 7, capability: 'segmented_surah' }, verses, repetitions: 1, playbackSpeed: 1 }
    })
    await flushPromises()
    const audio = wrapper.get('audio').element as HTMLAudioElement
    Object.defineProperty(audio, 'currentTime', { configurable: true, value: 2 })

    await wrapper.get('audio').trigger('play')
    await wrapper.get('audio').trigger('timeupdate')

    expect(wrapper.emitted('word-progress')).toEqual([[{ verseKey: '1:1', fraction: 0.25 }]])
  })

  it('emits null word-progress for whole-surah recordings', async () => {
    const wrapper = mount(QuranPlayer, {
      props: { profileId: 1, recitation: { id: 200046, capability: 'surah' }, verses, repetitions: 1, playbackSpeed: 1 }
    })

    await wrapper.get('audio').trigger('play')
    await wrapper.get('audio').trigger('timeupdate')

    expect(wrapper.emitted('word-progress')).toEqual([[null]])
  })

  it('clears word-progress on pause', async () => {
    const wrapper = mount(QuranPlayer, {
      props: { profileId: 1, recitation: { id: 100005, capability: 'ayah' }, verses, repetitions: 1, playbackSpeed: 1 }
    })
    const audio = wrapper.get('audio').element as HTMLAudioElement
    Object.defineProperty(audio, 'currentTime', { configurable: true, value: 15 })
    Object.defineProperty(audio, 'duration', { configurable: true, value: 60 })

    await wrapper.get('audio').trigger('play')
    await wrapper.get('audio').trigger('timeupdate')
    await wrapper.get('audio').trigger('pause')

    expect(wrapper.emitted('word-progress')?.at(-1)).toEqual([null])
  })

  it('clears word-progress when audio ends', async () => {
    const wrapper = mount(QuranPlayer, {
      props: { profileId: 1, recitation: { id: 100005, capability: 'ayah' }, verses, repetitions: 1, playbackSpeed: 1 }
    })
    const audio = wrapper.get('audio').element as HTMLAudioElement
    Object.defineProperty(audio, 'currentTime', { configurable: true, value: 15 })
    Object.defineProperty(audio, 'duration', { configurable: true, value: 60 })

    await wrapper.get('audio').trigger('play')
    await wrapper.get('audio').trigger('timeupdate')
    await wrapper.get('audio').trigger('ended')

    expect(wrapper.emitted('word-progress')?.at(-1)).toEqual([null])
  })

  it('does not highlight a verse for whole-surah recordings', async () => {
    const wrapper = mount(QuranPlayer, {
      props: { profileId: 1, recitation: { id: 200046, capability: 'surah' }, verses, repetitions: 1, playbackSpeed: 1 }
    })
    await wrapper.get('audio').trigger('play')
    expect(wrapper.emitted('verse-highlight')?.at(-1) ?? [null]).toEqual([null])
  })
})
