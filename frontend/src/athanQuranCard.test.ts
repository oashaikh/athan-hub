// The Quran player card ships from deploy/homeassistant/www; jsdom here exercises it.
import { describe, expect, it, vi } from 'vitest'
// @ts-expect-error plain JS module without types
import { matchSurah, reciterList } from '../../deploy/homeassistant/www/athan-quran-card.js'

const kahf = { id: 18, name_simple: 'Al-Kahf', translated_name: 'The Cave', name_arabic: 'الكهف', ayah_count: 110 }
const surahs = [{ id: 1, name_simple: 'Al-Fatihah', translated_name: 'The Opener', name_arabic: 'الفاتحة', ayah_count: 7 }, kahf]
const reciters = [
  { id: 2, name: 'Mishari Rashid al-`Afasy', capability: 'surah', source_kind: 'surah', style: null },
  { id: 3, name: 'Husary (archived)', capability: 'ayah', source_kind: 'ayah', style: 'Muallim' },
  { id: 1, name: 'Abdul Basit', capability: 'ayah', source_kind: 'ayah', style: 'Murattal' },
]

describe('surah search', () => {
  it('finds by name, meaning, number and Arabic', () => {
    for (const q of ['kahf', 'Al Kahf', 'al-kahf', 'cave', '18', 'الكهف', '']) expect(matchSurah(kahf, q)).toBe(true)
    for (const q of ['1', 'fatiha', '180']) expect(matchSurah(kahf, q)).toBe(false)
  })
})

describe('reciters', () => {
  it('hides archived duplicates and sorts by name', () => {
    expect(reciterList(reciters).map((r: { id: number }) => r.id)).toEqual([1, 2])
  })
})

function mount(player: string | null = 'browser') {
  localStorage.setItem('athan-quran-card', JSON.stringify({ reciter: 1, speaker: player }))
  const callWS = vi.fn(async (msg: { type: string }) => {
    if (msg.type === 'quran_hub/surahs') return surahs
    if (msg.type === 'quran_hub/recitations') return reciters
    if (msg.type === 'quran_hub/players') return [
      { entity_id: 'media_player.echo', name: 'Echo', platform: 'alexa_media', supported: true },
      { entity_id: 'media_player.tv', name: 'TV', platform: 'alexa_media', supported: true },
    ]
    if (msg.type === 'quran_hub/audio_url') return { url: `/audio/${(msg as { verse_key?: string }).verse_key || 'surah'}` }
    if (msg.type === 'quran_hub/remote/play') return { duration_ms: 60000 }
    return {}
  })
  const hass = { states: { 'media_player.echo': { state: 'idle', attributes: { volume_level: 0.4 } }, 'media_player.tv': { state: 'unavailable' } }, callWS, callService: vi.fn().mockResolvedValue(undefined), connection: { subscribeMessage: vi.fn(() => Promise.resolve(() => {})) } }
  const card = document.createElement('athan-quran-card') as HTMLElement & { setConfig(c: object): void; hass: object }
  card.setConfig({})
  document.body.append(card)
  card.hass = hass
  return { card, root: card.shadowRoot as ShadowRoot, callWS }
}

const flush = () => new Promise((r) => setTimeout(r, 0))

describe('athan-quran-card', () => {
  it('lists surahs and filters them as you type', async () => {
    const { root } = mount()
    await flush()
    expect(root.querySelectorAll('.surah').length).toBe(2)
    const input = root.querySelector('.find-surah') as HTMLInputElement
    input.value = 'cave'
    input.dispatchEvent(new Event('input'))
    expect([...root.querySelectorAll('.surah')].map((b) => (b as HTMLElement).dataset.surah)).toEqual(['18'])
  })

  it('plays an ayah reciter on this device ayah by ayah', async () => {
    const { card, root, callWS } = mount()
    await flush()
    const audio = (card as unknown as { _audio: HTMLAudioElement })._audio
    audio.play = vi.fn().mockResolvedValue(undefined)
    ;(root.querySelector('[data-surah="1"]') as HTMLButtonElement).click()
    await flush(); await flush()
    expect(callWS).toHaveBeenCalledWith({ type: 'quran_hub/audio_url', recitation_id: 1, surah_id: 1, verse_key: '1:1' })
    expect(audio.getAttribute('src')).toBe('/audio/1:1')
    audio.dispatchEvent(new Event('ended'))
    await flush(); await flush()
    expect(audio.getAttribute('src')).toBe('/audio/1:2')
    expect(root.querySelector('.player .sub')?.textContent).toContain('ayah 2 of 7')
  })

  it('sends a whole surah to a speaker', async () => {
    const { root, callWS } = mount('media_player.echo')
    await flush()
    ;(root.querySelector('[data-surah="18"]') as HTMLButtonElement).click()
    await flush(); await flush()
    expect(callWS).toHaveBeenCalledWith({
      type: 'quran_hub/remote/play', entity_id: 'media_player.echo', recitation_id: 1, surah_id: 18,
      start_ayah: 1, end_ayah: 110, repetitions: 1, playback_speed: 1,
    })
    expect(root.querySelector('.player .sub')?.textContent).toContain('Echo')
  })

  it('lists every speaker, greys out one that is off, and picks the Echo first', async () => {
    const { root } = mount(null)
    await flush()
    const opts = [...root.querySelectorAll('.devices .opt')] as HTMLButtonElement[]
    expect(opts.map((o) => o.dataset.player)).toEqual(['browser', 'media_player.echo', 'media_player.tv'])
    expect(opts.map((o) => o.disabled)).toEqual([false, false, true])
    expect(root.querySelector('.speaker .big')?.textContent).toBe('Echo')
    opts[0].click()
    expect(root.querySelector('.speaker .big')?.textContent).toBe('This device')
  })

  it('a rebuilt card still pauses what the old one started', async () => {
    const first = mount()
    await flush()
    const audio = (first.card as unknown as { _audio: HTMLAudioElement })._audio
    audio.play = vi.fn().mockResolvedValue(undefined)
    ;(first.root.querySelector('[data-surah="1"]') as HTMLButtonElement).click()
    await flush(); await flush()
    first.card.remove()
    const second = mount()
    await flush()
    expect(second.root.querySelector('.player .title')?.textContent).toBe('1. Al-Fatihah')
    Object.defineProperty(audio, 'paused', { value: false, configurable: true })
    audio.pause = vi.fn()
    ;(second.root.querySelector('.toggle') as HTMLButtonElement).click()
    expect(audio.pause).toHaveBeenCalled()
  })

  it('seeks an ayah reciter to the ayah under the slider', async () => {
    const { card, root, callWS } = mount()
    await flush()
    const audio = (card as unknown as { _audio: HTMLAudioElement })._audio
    audio.play = vi.fn().mockResolvedValue(undefined)
    ;(root.querySelector('[data-surah="1"]') as HTMLButtonElement).click()
    await flush(); await flush()
    const seek = root.querySelector('.seek') as HTMLInputElement
    expect(seek.disabled).toBe(false)
    seek.value = '500'
    seek.dispatchEvent(new Event('input'))
    expect(root.querySelector('.times .at')?.textContent).toBe('Ayah 4')
    seek.dispatchEvent(new Event('change'))
    await flush(); await flush()
    expect(callWS).toHaveBeenCalledWith({ type: 'quran_hub/audio_url', recitation_id: 1, surah_id: 1, verse_key: '1:4' })
    expect(audio.getAttribute('src')).toBe('/audio/1:4')
  })

  it('seeks on an Echo by starting again from that ayah', async () => {
    const { root, callWS } = mount('media_player.echo')
    await flush()
    ;(root.querySelector('[data-surah="18"]') as HTMLButtonElement).click()
    await flush(); await flush()
    const seek = root.querySelector('.seek') as HTMLInputElement
    seek.value = '500'
    seek.dispatchEvent(new Event('change'))
    await flush(); await flush(); await flush()
    expect(callWS).toHaveBeenCalledWith(expect.objectContaining({ type: 'quran_hub/remote/play', surah_id: 18, start_ayah: 56, end_ayah: 110 }))
  })

  it('pauses and resumes a speaker through Quran Hub', async () => {
    const { root, callWS } = mount('media_player.echo')
    await flush()
    ;(root.querySelector('[data-surah="1"]') as HTMLButtonElement).click()
    await flush(); await flush()
    const toggle = root.querySelector('.toggle') as HTMLButtonElement
    toggle.click()
    expect(callWS).toHaveBeenLastCalledWith({ type: 'quran_hub/remote/pause', entity_id: 'media_player.echo' })
    expect(toggle.getAttribute('aria-label')).toBe('Play')
    toggle.click()
    expect(callWS).toHaveBeenLastCalledWith({ type: 'quran_hub/remote/resume', entity_id: 'media_player.echo' })
    expect(toggle.getAttribute('aria-label')).toBe('Pause')
  })

  it('sets the speaker volume and mutes', async () => {
    const { root } = mount('media_player.echo')
    await flush()
    ;(root.querySelector('[data-surah="1"]') as HTMLButtonElement).click()
    await flush(); await flush()
    const card = root.host as unknown as { _hass: { callService: ReturnType<typeof vi.fn> } }
    const volume = root.querySelector('.volume') as HTMLInputElement
    expect(volume.value).toBe('40')
    volume.value = '70'
    volume.dispatchEvent(new Event('input'))
    expect(root.querySelector('.vol .pct')?.textContent).toBe('70%')
    volume.dispatchEvent(new Event('change'))
    expect(card._hass.callService).toHaveBeenLastCalledWith('media_player', 'volume_set', { volume_level: 0.7 }, { entity_id: 'media_player.echo' })
    ;(root.querySelector('.mute') as HTMLButtonElement).click()
    expect(card._hass.callService).toHaveBeenLastCalledWith('media_player', 'volume_set', { volume_level: 0 }, { entity_id: 'media_player.echo' })
    ;(root.querySelector('.mute') as HTMLButtonElement).click()
    expect(card._hass.callService).toHaveBeenLastCalledWith('media_player', 'volume_set', { volume_level: 0.7 }, { entity_id: 'media_player.echo' })
  })

  it('sets this device volume', async () => {
    const { card, root } = mount()
    await flush()
    const audio = (card as unknown as { _audio: HTMLAudioElement })._audio
    audio.play = vi.fn().mockResolvedValue(undefined)
    ;(root.querySelector('[data-surah="1"]') as HTMLButtonElement).click()
    await flush(); await flush()
    const volume = root.querySelector('.volume') as HTMLInputElement
    volume.value = '25'
    volume.dispatchEvent(new Event('change'))
    expect(audio.volume).toBe(0.25)
  })

  it('moves what is playing when another speaker is picked', async () => {
    const { card, root, callWS } = mount('media_player.echo')
    await flush()
    const audio = (card as unknown as { _audio: HTMLAudioElement })._audio
    audio.play = vi.fn().mockResolvedValue(undefined)
    ;(root.querySelector('[data-surah="1"]') as HTMLButtonElement).click()
    await flush(); await flush()
    ;(card as unknown as { _remoteEvent(e: object): void })._remoteEvent({ entity_id: 'media_player.echo', state: 'playing', verse_key: '1:3', position_ms: 1000, duration_ms: 60000 })
    ;(root.querySelector('.devices [data-player="browser"]') as HTMLButtonElement).click()
    await flush(); await flush(); await flush()
    expect(callWS).toHaveBeenCalledWith({ type: 'quran_hub/remote/stop', entity_id: 'media_player.echo' })
    expect(audio.getAttribute('src')).toBe('/audio/1:3')
    expect(root.querySelector('.player .sub')?.textContent).toContain('This device')
  })

  it('shows a speaker that was already reciting when the page opens', async () => {
    const { card, root, callWS } = mount()
    await flush()
    ;(card as unknown as { _now: null })._now = null // nothing left over from earlier tests
    ;(card as unknown as { _remoteEvent(e: object): void })._remoteEvent({
      entity_id: 'media_player.echo', state: 'playing', verse_key: '18:5', position_ms: 4000, duration_ms: 60000,
      recitation_id: 1, surah_id: 18, start_ayah: 1, end_ayah: 110,
    })
    expect(root.querySelector('.player .title')?.textContent).toBe('18. Al-Kahf')
    expect(root.querySelector('.player .sub')?.textContent).toContain('ayah 5 of 110')
    ;(root.querySelector('.toggle') as HTMLButtonElement).click()
    expect(callWS).toHaveBeenLastCalledWith({ type: 'quran_hub/remote/pause', entity_id: 'media_player.echo' })
  })
})
