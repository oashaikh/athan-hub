import { describe, expect, it } from 'vitest'
import { apiErrorMessage, buildSettingsPayload } from './settingsPayload'

describe('buildSettingsPayload', () => {
  it('submits only fields owned by the general and speaker settings endpoint', () => {
    const payload = buildSettingsPayload({
      timezone: 'Europe/London',
      grace_seconds: '120',
      echo_mac: 'AA:BB:CC:DD:EE:FF',
      pre_connect_seconds: '30',
      connect_retry_seconds: '20',
      sink_volume_percent: '140',
      disconnect_after_play: '0',
      dashboard_background: 'bg.png',
      quran_cache_limit_bytes: '5368709120',
      leaderboard_enabled: '0',
      leaderboard_daily_practice: '1',
    })

    expect(payload).toEqual({
      timezone: 'Europe/London',
      grace_seconds: 120,
      echo_mac: 'AA:BB:CC:DD:EE:FF',
      pre_connect_seconds: 30,
      connect_retry_seconds: 20,
      sink_volume_percent: 140,
      disconnect_after_play: false,
      dashboard_background: 'bg.png',
    })
  })
})

describe('apiErrorMessage', () => {
  it('turns FastAPI validation details into a concise field message', () => {
    const error = {
      response: {
        data: {
          detail: [
            {
              type: 'extra_forbidden',
              loc: ['body', 'quran_cache_limit_bytes'],
              msg: 'Extra inputs are not permitted',
            },
          ],
        },
      },
    }

    expect(apiErrorMessage(error, 'Save failed')).toBe(
      'quran cache limit bytes: Extra inputs are not permitted',
    )
  })
})
