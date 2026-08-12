import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import AdminProfiles from '../../pages/AdminProfiles.vue'
import api from '../../api'

vi.mock('../../api', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn()
  }
}))

describe('AdminProfiles', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(api.get).mockResolvedValue({ data: [] })
    vi.mocked(api.post).mockResolvedValue({ data: {} })
  })

  it('creates a profile with the administrator-selected gender and theme', async () => {
    const wrapper = mount(AdminProfiles)
    await flushPromises()

    await wrapper.get('input').setValue('Maryam')
    const selects = wrapper.findAll('select')
    await selects[0].setValue('girl')
    await selects[1].setValue('garden_light')
    await wrapper.get('form').trigger('submit')
    await flushPromises()

    expect(api.post).toHaveBeenCalledWith('/admin/profiles', {
      name: 'Maryam',
      gender: 'girl',
      theme: 'garden_light'
    })
  })
})
