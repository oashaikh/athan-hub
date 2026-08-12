import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import QuranPlayer from '../QuranPlayer.vue'

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
})
