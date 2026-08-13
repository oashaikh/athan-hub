import { mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'
import FullscreenButton from '../FullscreenButton.vue'

describe('FullscreenButton', () => {
  afterEach(() => {
    vi.restoreAllMocks()
    Object.defineProperty(document, 'fullscreenElement', { configurable: true, value: null })
  })

  it('enters full screen and updates its accessible label', async () => {
    let fullscreenElement: Element | null = null
    Object.defineProperty(document, 'fullscreenEnabled', { configurable: true, value: true })
    Object.defineProperty(document, 'fullscreenElement', { configurable: true, get: () => fullscreenElement })
    const requestFullscreen = vi.fn(async () => {
      fullscreenElement = document.documentElement
      document.dispatchEvent(new Event('fullscreenchange'))
    })
    const exitFullscreen = vi.fn(async () => {
      fullscreenElement = null
      document.dispatchEvent(new Event('fullscreenchange'))
    })
    Object.defineProperty(document.documentElement, 'requestFullscreen', { configurable: true, value: requestFullscreen })
    Object.defineProperty(document, 'exitFullscreen', { configurable: true, value: exitFullscreen })

    const wrapper = mount(FullscreenButton)
    await wrapper.vm.$nextTick()
    expect(wrapper.get('button').attributes('aria-label')).toBe('Enter full screen')

    await wrapper.get('button').trigger('click')
    expect(requestFullscreen).toHaveBeenCalledOnce()
    expect(wrapper.get('button').attributes('aria-label')).toBe('Exit full screen')
    expect(wrapper.get('.material-icons').text()).toBe('fullscreen_exit')

    await wrapper.get('button').trigger('click')
    expect(exitFullscreen).toHaveBeenCalledOnce()
    expect(wrapper.get('button').attributes('aria-label')).toBe('Enter full screen')
  })

  it('stays hidden when the browser has no fullscreen API', async () => {
    Object.defineProperty(document, 'fullscreenEnabled', { configurable: true, value: false })
    Object.defineProperty(document.documentElement, 'requestFullscreen', { configurable: true, value: undefined })
    const wrapper = mount(FullscreenButton)
    await wrapper.vm.$nextTick()
    expect(wrapper.find('button').exists()).toBe(false)
  })
})
