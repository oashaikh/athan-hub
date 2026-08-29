export type SettingsSource = Record<string, unknown>

const numberValue = (value: unknown): number => {
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : 0
}

const booleanValue = (value: unknown): boolean =>
  [true, 1, '1', 'true', 'True', 'yes', 'on'].includes(value as never)

export const buildSettingsPayload = (settings: SettingsSource) => ({
  timezone: String(settings.timezone || ''),
  grace_seconds: numberValue(settings.grace_seconds),
  echo_mac: String(settings.echo_mac || ''),
  pre_connect_seconds: numberValue(settings.pre_connect_seconds),
  connect_retry_seconds: numberValue(settings.connect_retry_seconds),
  sink_volume_percent: Math.max(0, Math.min(150, numberValue(settings.sink_volume_percent))),
  disconnect_after_play: booleanValue(settings.disconnect_after_play),
  dashboard_background: String(settings.dashboard_background || ''),
})

export const apiErrorMessage = (error: any, fallback: string): string => {
  const detail = error?.response?.data?.detail
  if (typeof detail === 'string' && detail.trim()) return detail
  if (Array.isArray(detail) && detail.length) {
    const first = detail[0]
    const field = Array.isArray(first?.loc)
      ? first.loc.slice(first.loc[0] === 'body' ? 1 : 0).join(' ').replace(/_/g, ' ')
      : ''
    const message = typeof first?.msg === 'string' ? first.msg : fallback
    return field ? `${field}: ${message}` : message
  }
  return fallback
}
