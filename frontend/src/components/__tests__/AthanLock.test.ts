import { mount } from '@vue/test-utils'
import { nextTick } from 'vue'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import AthanLock from '../AthanLock.vue'
import { playbackState } from '../../stores/playback'

describe('AthanLock', () => {
  beforeEach(() => {
    document.body.innerHTML = '<main id="child-application"><audio src="quran.mp3"></audio></main>'
    playbackState.active.value = null
    vi.mocked(HTMLMediaElement.prototype.pause).mockClear()
  })

  it('pauses every audio element and makes child content inert', async () => {
    mount(AthanLock)
    playbackState.active.value = { prayer: 'fajr', remaining_seconds: 30 }
    await nextTick()

    expect(HTMLMediaElement.prototype.pause).toHaveBeenCalled()
    expect(document.querySelector('#child-application')?.hasAttribute('inert')).toBe(true)
    expect(document.querySelector('audio')?.getAttribute('src')).toBeNull()
    const key = new KeyboardEvent('keydown', { key: 'Tab', bubbles: true, cancelable: true })
    document.dispatchEvent(key)
    expect(key.defaultPrevented).toBe(true)
  })
})
