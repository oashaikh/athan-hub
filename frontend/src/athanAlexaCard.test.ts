// The Ask Alexa card ships from deploy/homeassistant/www; jsdom here exercises it.
import { describe, expect, it, vi } from 'vitest'
import '../../deploy/homeassistant/www/athan-alexa-card.js'

function mount() {
  const callService = vi.fn().mockResolvedValue(undefined)
  const card = document.createElement('athan-alexa-card') as HTMLElement & {
    setConfig(c: object): void
    hass: object
  }
  card.setConfig({ entity: 'media_player.echo', phrases: ['Dinner is ready'] })
  card.hass = { states: { 'media_player.echo': { state: 'idle', attributes: { friendly_name: 'Hallway Echo' } } }, callService }
  document.body.append(card)
  const root = card.shadowRoot as ShadowRoot
  const input = root.querySelector('input') as HTMLInputElement
  const type = (text: string) => { input.value = text; input.dispatchEvent(new Event('input')) }
  return { root, input, type, callService }
}

const flush = () => new Promise((r) => setTimeout(r, 0))

describe('athan-alexa-card', () => {
  it('says the typed message and clears the box', async () => {
    const { root, input, type, callService } = mount()
    expect(root.querySelector('.speaker')?.textContent).toContain('Hallway Echo')
    type('  hello there ')
    ;(root.querySelector('.say') as HTMLButtonElement).click()
    await flush()
    expect(callService).toHaveBeenCalledWith('script', 'alexa_say', { message: 'hello there' })
    expect(input.value).toBe('')
  })

  it('asks Alexa through the text box the script reads', async () => {
    const { root, type, callService } = mount()
    type('turn off the lights')
    ;(root.querySelector('.ask') as HTMLButtonElement).click()
    await flush()
    expect(callService.mock.calls).toEqual([
      ['input_text', 'set_value', { value: 'turn off the lights' }, { entity_id: 'input_text.alexa_command' }],
      ['script', 'ask_alexa', {}],
    ])
  })

  it('a phrase chip says itself and leaves typed text alone', async () => {
    const { root, input, type, callService } = mount()
    type('draft')
    ;(root.querySelector('.chip') as HTMLButtonElement).click()
    await flush()
    expect(callService).toHaveBeenCalledWith('script', 'alexa_say', { message: 'Dinner is ready' })
    expect(input.value).toBe('draft')
  })

  it('does nothing with an empty box', () => {
    const { root, callService } = mount()
    ;(root.querySelector('.say') as HTMLButtonElement).click()
    expect(callService).not.toHaveBeenCalled()
  })
})
