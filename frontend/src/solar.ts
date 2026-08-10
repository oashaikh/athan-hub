export type SolarSchedule = {
  fajr: number
  sunrise: number
  sunset: number
  isha: number
  sunriseLabel: string
  sunsetLabel: string
  ishaLabel: string
}

export type SolarState = {
  phase: 'night' | 'dawn' | 'day' | 'dusk'
  label: string
  detail: string
  x: number
  y: number
  daylightProgress: number
  brightness: number
  twilight: number
  sunOpacity: number
}

const clamp = (value: number, min = 0, max = 1) => Math.min(max, Math.max(min, value))
const smoothstep = (value: number) => {
  const amount = clamp(value)
  return amount * amount * (3 - 2 * amount)
}

const cubicPoint = (progress: number) => {
  const t = clamp(progress)
  const inverse = 1 - t
  return {
    x: inverse ** 3 * 30 + 3 * inverse ** 2 * t * 95 + 3 * inverse * t ** 2 * 265 + t ** 3 * 330,
    y: inverse ** 3 * 174 + 3 * inverse ** 2 * t * 58 + 3 * inverse * t ** 2 * 58 + t ** 3 * 174
  }
}

export const computeSolarState = (nowMinutes: number, schedule: SolarSchedule): SolarState => {
  const { fajr, sunrise, sunset, isha, sunriseLabel, sunsetLabel, ishaLabel } = schedule

  if (nowMinutes >= sunrise && nowMinutes < sunset) {
    const progress = clamp((nowMinutes - sunrise) / Math.max(1, sunset - sunrise))
    const altitude = Math.sin(Math.PI * progress)
    const point = cubicPoint(progress)
    const isMorning = progress < 0.24
    const isEvening = progress > 0.76
    return {
      phase: 'day',
      label: isMorning ? 'Morning light' : isEvening ? 'Golden hour' : 'Daylight',
      detail: isEvening ? `Sunset ${sunsetLabel}` : `Sunset at ${sunsetLabel}`,
      ...point,
      daylightProgress: progress,
      brightness: clamp(0.42 + 0.58 * Math.pow(altitude, 0.48)),
      twilight: clamp((1 - altitude) * 0.82),
      sunOpacity: 1
    }
  }

  if (nowMinutes >= fajr && nowMinutes < sunrise) {
    const progress = smoothstep((nowMinutes - fajr) / Math.max(1, sunrise - fajr))
    return {
      phase: 'dawn',
      label: 'Dawn light',
      detail: `Sunrise ${sunriseLabel}`,
      x: 18 + 12 * progress,
      y: 194 - 20 * progress,
      daylightProgress: 0,
      brightness: 0.08 + 0.34 * progress,
      twilight: 0.22 + 0.68 * progress,
      sunOpacity: 0.3 + 0.7 * progress
    }
  }

  if (nowMinutes >= sunset && nowMinutes < isha) {
    const progress = smoothstep((nowMinutes - sunset) / Math.max(1, isha - sunset))
    return {
      phase: 'dusk',
      label: 'Evening twilight',
      detail: `Nightfall ${ishaLabel}`,
      x: 330 + 12 * progress,
      y: 174 + 20 * progress,
      daylightProgress: 1,
      brightness: 0.36 * (1 - progress),
      twilight: 0.92 * (1 - progress) + 0.08,
      sunOpacity: 1 - 0.72 * progress
    }
  }

  const adjustedNow = nowMinutes < fajr ? nowMinutes + 1440 : nowMinutes
  const nightProgress = clamp((adjustedNow - isha) / Math.max(1, fajr + 1440 - isha))
  return {
    phase: 'night',
    label: 'Night passage',
    detail: `Sunrise ${sunriseLabel}`,
    x: 342 - 324 * nightProgress,
    y: 194 + 14 * Math.sin(Math.PI * nightProgress),
    daylightProgress: nightProgress < 0.5 ? 1 : 0,
    brightness: 0,
    twilight: 0,
    sunOpacity: 0.16
  }
}
