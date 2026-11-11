// The Home Assistant Lists card ships from deploy/homeassistant/www, not this
// app, but jsdom here is the cheapest place to exercise it.
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
// @ts-expect-error plain JS module without types
import { buildDescription, parseDescription } from '../../deploy/homeassistant/www/athan-list-card.js'

type Item = { uid: string; summary: string; status: string; description?: string; due?: string }

function mount(items: Item[], features = 1 | 2 | 4 | 16 | 64) {
  let push: (msg: { items: Item[] }) => void = () => {}
  const callService = vi.fn().mockResolvedValue(undefined)
  const hass = {
    states: {
      'todo.to_do': { entity_id: 'todo.to_do', attributes: { supported_features: features } },
      'person.judy': { entity_id: 'person.judy', attributes: { friendly_name: 'Judy' } },
      'person.osama': { entity_id: 'person.osama', attributes: { friendly_name: 'Osama' } },
    },
    callService,
    connection: {
      subscribeMessage: (cb: typeof push) => { push = cb; return Promise.resolve(() => {}) },
    },
  }
  const card = document.createElement('athan-list-card') as HTMLElement & {
    setConfig(c: object): void; hass: object
  }
  card.setConfig({ entity: 'todo.to_do', title: 'To-do', count: '{n} open', order: 'alpha' })
  document.body.appendChild(card)
  card.hass = hass
  push({ items })
  const root = card.shadowRoot!
  const click = (sel: string) => (root.querySelector(sel) as HTMLElement).click()
  return { card, root, click, callService, push }
}

const items: Item[] = [
  { uid: 'a', summary: 'Bins out', status: 'needs_action', description: '@Judy\nGreen one' },
  { uid: 'b', summary: 'Call the plumber', status: 'needs_action', description: '@Osama' },
  { uid: 'c', summary: 'Buy stamps', status: 'needs_action' },
  { uid: 'd', summary: 'Fix shelf', status: 'completed' },
]

describe('athan-list-card', () => {
  beforeEach(async () => {
    vi.useFakeTimers()
    localStorage.clear()
    // @ts-expect-error plain JS module without types
    await import('../../deploy/homeassistant/www/athan-list-card.js')
  })
  afterEach(() => { document.body.innerHTML = ''; vi.useRealTimers() })

  it('keeps the assignee in the description', () => {
    expect(parseDescription('@Judy\nGreen one')).toEqual({ who: 'Judy', notes: 'Green one' })
    expect(parseDescription('just notes')).toEqual({ who: null, notes: 'just notes' })
    expect(buildDescription('Judy', 'Green one')).toBe('@Judy\nGreen one')
    expect(buildDescription('Osama', '')).toBe('@Osama')
    expect(buildDescription(null, '  ')).toBeNull()
  })

  it('groups open items by person and counts them', () => {
    const { root } = mount(items)
    const heads = [...root.querySelectorAll('.group-head .toggle span:not(.avatar):not(.n)')].map((e) => e.textContent)
    expect(heads).toEqual(['Judy', 'Osama', 'Anyone', 'Done'])
    expect(root.querySelector('.count')!.textContent).toBe('3 open')
  })

  it('collapses a group and remembers it', () => {
    const { root, click } = mount(items)
    click('[data-group="p:Judy"]')
    expect(root.querySelector('.group')!.classList.contains('collapsed')).toBe(true)
    expect(JSON.parse(localStorage.getItem('athan-list:todo.to_do')!).groups['p:Judy']).toBe(true)
  })

  it('collapses the whole list from its header', () => {
    const { root } = mount(items)
    ;(root.querySelector('.head') as HTMLElement).click()
    expect(root.querySelector('ha-card')!.classList.contains('collapsed')).toBe(true)
  })

  it('deletes everything selected after the undo window', () => {
    const { root, click, callService } = mount(items)
    click('.select')
    click('[data-all]')
    expect(root.querySelector('.bar .grow')!.textContent).toBe('4 selected')
    click('[data-delete-selected]')
    expect(root.querySelectorAll('.item')).toHaveLength(0)
    expect(callService).not.toHaveBeenCalled()
    vi.advanceTimersByTime(6000)
    expect(callService).toHaveBeenCalledWith('todo', 'remove_item', { item: ['a', 'b', 'c', 'd'] }, { entity_id: 'todo.to_do' })
  })

  it('undo brings deleted items back without telling Home Assistant', () => {
    const { root, click, callService } = mount(items)
    click('.select')
    click('.item[data-uid="c"] .check')
    click('[data-delete-selected]')
    click('[data-undo]')
    vi.advanceTimersByTime(10000)
    expect(callService).not.toHaveBeenCalled()
    expect(root.querySelector('.item[data-uid="c"]')).not.toBeNull()
  })

  it('swipe left deletes one item', () => {
    const { root, callService } = mount(items)
    const slide = root.querySelector('.item[data-uid="c"] .summary')!
    slide.dispatchEvent(new MouseEvent('pointerdown', { bubbles: true, clientX: 300, clientY: 10 }))
    window.dispatchEvent(new MouseEvent('pointermove', { clientX: 200, clientY: 12 }))
    window.dispatchEvent(new MouseEvent('pointerup', { clientX: 120, clientY: 12 }))
    vi.advanceTimersByTime(200)
    expect(root.querySelector('.item[data-uid="c"]')).toBeNull()
    vi.advanceTimersByTime(6000)
    expect(callService).toHaveBeenCalledWith('todo', 'remove_item', { item: ['c'] }, { entity_id: 'todo.to_do' })
  })

  it('a vertical drag scrolls instead of deleting', () => {
    const { root } = mount(items)
    const slide = root.querySelector('.item[data-uid="c"] .summary')!
    slide.dispatchEvent(new MouseEvent('pointerdown', { bubbles: true, clientX: 300, clientY: 10 }))
    window.dispatchEvent(new MouseEvent('pointermove', { clientX: 290, clientY: 60 }))
    window.dispatchEvent(new MouseEvent('pointerup', { clientX: 100, clientY: 80 }))
    vi.advanceTimersByTime(7000)
    expect(root.querySelector('.item[data-uid="c"]')).not.toBeNull()
  })

  it('reassigns an item from its editor', () => {
    const { root, click, callService } = mount(items)
    click('.item[data-uid="c"] .text')
    click('.editor .chip[data-who="Judy"]')
    ;(root.querySelector('.editor textarea') as HTMLTextAreaElement).value = 'First class'
    click('.editor [type="submit"]')
    expect(callService).toHaveBeenCalledWith('todo', 'update_item',
      { item: 'c', rename: 'Buy stamps', due_date: null, description: '@Judy\nFirst class' },
      { entity_id: 'todo.to_do' })
  })

  it('adds an item for the chosen person', () => {
    const { root, callService } = mount(items)
    ;(root.querySelector('.add .chip[data-who="Osama"]') as HTMLElement).click()
    const input = root.querySelector('.add input') as HTMLInputElement
    input.value = 'Renew passport'
    input.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter' }))
    expect(callService).toHaveBeenCalledWith('todo', 'add_item',
      { item: 'Renew passport', description: '@Osama' }, { entity_id: 'todo.to_do' })
  })

  it('lists without descriptions are not assignable', () => {
    const { root } = mount(items, 1 | 2 | 4 | 8)
    expect(root.querySelector('.who')).toBeNull()
    const heads = [...root.querySelectorAll('.group-head .toggle span:not(.n)')].map((e) => e.textContent)
    expect(heads).toEqual(['Done'])
  })
})
