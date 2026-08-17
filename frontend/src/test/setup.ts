import { vi } from 'vitest'

Object.defineProperty(HTMLMediaElement.prototype, 'pause', { configurable: true, value: vi.fn() })
Object.defineProperty(HTMLMediaElement.prototype, 'play', { configurable: true, value: vi.fn().mockResolvedValue(undefined) })
Object.defineProperty(HTMLMediaElement.prototype, 'load', { configurable: true, value: vi.fn() })
Object.defineProperty(Element.prototype, 'scrollIntoView', { configurable: true, value: vi.fn() })
Object.defineProperty(window, 'matchMedia', {
  configurable: true,
  value: vi.fn().mockImplementation(query => ({
    matches: false,
    media: query,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn()
  }))
})
