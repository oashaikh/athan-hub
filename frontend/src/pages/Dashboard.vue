<template>
  <div ref="dashboardRoot" class="dashboard" :class="`period-${ambienceKey}`" :style="backgroundStyle">
    <ChildHeader />
    <div class="dashboard-scrim">
      <div class="daylight-wash" aria-hidden="true"></div>
      <div class="twilight-wash" aria-hidden="true"></div>
      <div class="ambient-orb" aria-hidden="true"></div>
      <div class="architectural-frame" aria-hidden="true"></div>

      <main class="dashboard-content">
        <section v-if="loading" class="dashboard-loading" aria-label="Loading prayer times" aria-live="polite">
          <div class="skeleton skeleton-kicker"></div>
          <div class="skeleton skeleton-title"></div>
          <div class="skeleton skeleton-time"></div>
          <div class="skeleton-grid">
            <div v-for="index in 6" :key="index" class="skeleton skeleton-card"></div>
          </div>
        </section>

        <section v-else-if="loadError || !today?.date" class="dashboard-empty" role="status">
          <span class="material-icons" aria-hidden="true">event_busy</span>
          <p class="section-kicker">Prayer timetable unavailable</p>
          <h1>There are no prayer times to show.</h1>
          <p>Open Timetable settings to import or review the schedule.</p>
          <router-link class="button is-primary" to="/admin/system">Open timetable settings</router-link>
        </section>

        <template v-else>
          <section class="prayer-hero" aria-labelledby="next-prayer-title">
            <div class="hero-context" data-reveal="hero-copy">
              <p class="section-kicker">Current prayer period</p>
              <div class="current-period">
                <span class="period-indicator" aria-hidden="true"></span>
                <span>{{ currentPeriod }}</span>
              </div>
            </div>

            <div class="hero-primary" data-reveal="hero-time">
              <p class="section-kicker">Next prayer</p>
              <h1 id="next-prayer-title">{{ nextPrayerLabel }}</h1>
              <p class="hero-prayer-time">{{ nextPrayerTime }}</p>
              <div class="countdown-lockup" aria-live="polite" aria-atomic="true">
                <span class="countdown-label">Begins in</span>
                <span ref="countdownElement" class="countdown-value">{{ countdownLabel }}</span>
              </div>
            </div>

            <SolarArc :state="solarState" />
          </section>

          <section class="schedule-section" aria-labelledby="schedule-title">
            <div class="schedule-heading">
              <div>
                <p class="section-kicker">Daily rhythm</p>
                <h2 id="schedule-title">Today’s prayer times</h2>
              </div>
              <p class="schedule-date">{{ dayLabel }}, {{ dateLabel }}</p>
            </div>

            <div class="prayer-grid">
              <article
                v-for="card in prayerCards"
                :key="card.key"
                class="prayer-card"
                :class="{ 'is-next': card.isNext, 'is-current': card.isCurrent, 'is-disabled': !card.enabled }"
                :data-prayer="card.key"
              >
                <div class="card-topline">
                  <span class="prayer-icon material-icons" aria-hidden="true">{{ card.icon }}</span>
                  <span v-if="card.isNext" class="card-status"><span class="status-dot"></span>Next</span>
                  <span v-else-if="card.isCurrent" class="card-status is-current-status">Current</span>
                  <span v-else-if="card.source === 'manual' || card.source === 'override'" class="card-status is-muted">Adjusted</span>
                  <span v-else-if="!card.enabled" class="card-status is-muted">Excluded</span>
                </div>
                <div class="card-copy">
                  <div>
                    <h3>{{ card.label }}</h3>
                    <p>{{ card.caption }}</p>
                  </div>
                  <time class="prayer-time" :datetime="card.time || undefined">{{ card.time || '--:--' }}</time>
                </div>
              </article>
            </div>
          </section>
        </template>
      </main>

      <footer class="dashboard-footer" data-reveal="footer">
        <span>{{ today?.date ? 'Timetable synced' : 'No timetable loaded' }}</span>
        <span class="footer-rule" aria-hidden="true"></span>
        <span>{{ timezone }}</span>
      </footer>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, inject, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import api from '../api'
import SolarArc from '../components/SolarArc.vue'
import ChildHeader from '../components/ChildHeader.vue'
import { animateCounter, animateDashboardEntrance, animatePrayerState } from '../motion'
import { computeSolarState, type SolarSchedule } from '../solar'

const toast = inject<(message: string, type?: any) => void>('toast') || (() => {})
const dashboardRoot = ref<HTMLElement | null>(null)
const countdownElement = ref<HTMLElement | null>(null)
const next = ref<any>(null)
const today = ref<any>(null)
const background = ref('')
const timezone = ref('Europe/London')
const now = ref(new Date())
const loading = ref(true)
const loadError = ref(false)
let entranceContext: ReturnType<typeof animateDashboardEntrance> = null
let tick: ReturnType<typeof setInterval>
let refresh: ReturnType<typeof setInterval>

const prayerMeta = [
  { key: 'fajr', label: 'Fajr', icon: 'dark_mode', caption: 'Dawn prayer' },
  { key: 'shurooq', label: 'Shurooq', icon: 'wb_twilight', caption: 'Sunrise' },
  { key: 'dhuhr', label: 'Dhuhr', icon: 'light_mode', caption: 'Midday prayer' },
  { key: 'asr', label: 'Asr', icon: 'sunny', caption: 'Afternoon prayer' },
  { key: 'maghrib', label: 'Maghrib', icon: 'nights_stay', caption: 'Sunset prayer' },
  { key: 'isha', label: 'Isha', icon: 'bedtime', caption: 'Night prayer' }
]

const localDateString = (value: Date) => {
  const year = value.getFullYear()
  const month = String(value.getMonth() + 1).padStart(2, '0')
  const day = String(value.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

const timeToMinutes = (value?: string | null) => {
  if (!value || !/^\d{1,2}:\d{2}$/.test(value)) return null
  const [hours, minutes] = value.split(':').map(Number)
  return hours * 60 + minutes
}

const dayLabel = computed(() => new Intl.DateTimeFormat(undefined, { weekday: 'long' }).format(now.value))
const dateLabel = computed(() => new Intl.DateTimeFormat(undefined, { day: 'numeric', month: 'long', year: 'numeric' }).format(now.value))
const solarSchedule = computed<SolarSchedule>(() => {
  const value = (key: string, fallback: number) => timeToMinutes(today.value?.prayers?.[key]?.effective) ?? fallback
  const label = (key: string, fallback: string) => today.value?.prayers?.[key]?.effective || fallback
  return {
    fajr: value('fajr', 300),
    sunrise: value('shurooq', 360),
    sunset: value('maghrib', 1080),
    isha: value('isha', 1260),
    sunriseLabel: label('shurooq', '06:00'),
    sunsetLabel: label('maghrib', '18:00'),
    ishaLabel: label('isha', '21:00')
  }
})
const solarState = computed(() => computeSolarState(
  now.value.getHours() * 60 + now.value.getMinutes() + now.value.getSeconds() / 60,
  solarSchedule.value
))
const backgroundStyle = computed(() => ({
  ...(background.value ? { backgroundImage: `url(/backgrounds/${encodeURIComponent(background.value)})` } : {}),
  '--daylight-level': solarState.value.brightness.toFixed(3),
  '--twilight-level': solarState.value.twilight.toFixed(3),
  '--sun-x': `${(solarState.value.x / 360 * 100).toFixed(2)}%`,
  '--sun-y': `${(solarState.value.y / 220 * 100).toFixed(2)}%`
}))
const nextPrayer = computed(() => String(next.value?.next?.prayer || '').toLowerCase())
const nextMeta = computed(() => prayerMeta.find(item => item.key === nextPrayer.value))
const nextPrayerLabel = computed(() => nextMeta.value?.label || 'Not scheduled')
const nextPrayerTime = computed(() => next.value?.next?.time || '--:--')
const nextIsToday = computed(() => !next.value?.next?.date || next.value.next.date === localDateString(now.value))

const currentPeriodKey = computed(() => {
  const minutesNow = now.value.getHours() * 60 + now.value.getMinutes()
  const getTime = (key: string) => timeToMinutes(today.value?.prayers?.[key]?.effective)
  const fajr = getTime('fajr')
  const sunrise = getTime('shurooq')
  const dhuhr = getTime('dhuhr')
  const asr = getTime('asr')
  const maghrib = getTime('maghrib')
  const isha = getTime('isha')
  if (fajr !== null && sunrise !== null && minutesNow >= fajr && minutesNow < sunrise) return 'fajr'
  if (sunrise !== null && dhuhr !== null && minutesNow >= sunrise && minutesNow < dhuhr) return 'shurooq'
  if (dhuhr !== null && asr !== null && minutesNow >= dhuhr && minutesNow < asr) return 'dhuhr'
  if (asr !== null && maghrib !== null && minutesNow >= asr && minutesNow < maghrib) return 'asr'
  if (maghrib !== null && isha !== null && minutesNow >= maghrib && minutesNow < isha) return 'maghrib'
  return 'isha'
})

const currentPeriod = computed(() => currentPeriodKey.value === 'shurooq'
  ? 'Between Fajr and Dhuhr'
  : `${prayerMeta.find(item => item.key === currentPeriodKey.value)?.label || 'Isha'} period`)
const ambienceKey = computed(() => nextPrayer.value || currentPeriodKey.value)

const countdownLabel = computed(() => {
  if (!next.value?.next) return 'Not scheduled'
  const total = Math.max(0, Number(next.value.next.countdown || 0))
  const hours = Math.floor(total / 3600)
  const minutes = Math.floor((total % 3600) / 60)
  const seconds = total % 60
  return `${String(hours).padStart(2, '0')} : ${String(minutes).padStart(2, '0')} : ${String(seconds).padStart(2, '0')}`
})

const prayerCards = computed(() => prayerMeta.map(meta => {
  const entry = today.value?.prayers?.[meta.key] || {}
  return {
    ...meta,
    time: entry.effective || entry.override || entry.base || '',
    enabled: entry.enabled !== false && !entry.excluded,
    source: entry.source || (entry.override ? 'override' : 'timetable'),
    isNext: nextIsToday.value && nextPrayer.value === meta.key,
    isCurrent: currentPeriodKey.value === meta.key && !(nextIsToday.value && nextPrayer.value === meta.key)
  }
}))

const load = async () => {
  const results = await Promise.allSettled([
    api.get('/timetable/next'),
    api.get('/timetable/day', { params: { date: localDateString(new Date()) } }),
    api.get('/public/config')
  ])
  const value = (index: number) => results[index].status === 'fulfilled' ? (results[index] as PromiseFulfilledResult<any>).value.data : null
  next.value = value(0)
  today.value = value(1)
  background.value = value(2)?.dashboard_background || ''
  timezone.value = value(2)?.timezone || 'Europe/London'
  loadError.value = !value(0) || !value(1)
  loading.value = false
}

watch(countdownLabel, () => animateCounter(countdownElement.value))
watch(nextPrayer, prayer => {
  if (!prayer || !dashboardRoot.value) return
  nextTick(() => dashboardRoot.value && animatePrayerState(dashboardRoot.value, prayer))
})

onMounted(async () => {
  try {
    await load()
  } catch {
    loading.value = false
    loadError.value = true
    toast('Could not load prayer times', 'danger')
  }
  await nextTick()
  if (dashboardRoot.value) entranceContext = animateDashboardEntrance(dashboardRoot.value)
  tick = setInterval(() => {
    now.value = new Date()
    if (next.value?.next?.countdown > 0) next.value.next.countdown--
  }, 1000)
  refresh = setInterval(() => load(), 30000)
})

onBeforeUnmount(() => {
  clearInterval(tick)
  clearInterval(refresh)
  entranceContext?.revert()
})
</script>

<style scoped>
.dashboard {
  --period-primary: #9bb8b8;
  --period-secondary: #32566a;
  --period-glow: rgba(127, 180, 188, 0.25);
  min-height: 100vh;
  min-height: 100dvh;
  background-color: #07121a;
  background-position: center;
  background-size: cover;
  color: var(--color-text);
}

.period-shurooq { --period-primary: #ebc88a; --period-secondary: #9b6954; --period-glow: rgba(235, 200, 138, 0.28); }
.period-dhuhr { --period-primary: #e8d8a9; --period-secondary: #74959a; --period-glow: rgba(232, 216, 169, 0.22); }
.period-asr { --period-primary: #d9ad70; --period-secondary: #8c6658; --period-glow: rgba(217, 173, 112, 0.26); }
.period-maghrib { --period-primary: #e6a16e; --period-secondary: #7b526e; --period-glow: rgba(230, 161, 110, 0.27); }
.period-isha { --period-primary: #a7b6d9; --period-secondary: #39466d; --period-glow: rgba(132, 151, 204, 0.24); }

.dashboard-scrim {
  position: relative;
  display: flex;
  min-height: 100vh;
  min-height: 100dvh;
  overflow: hidden;
  flex-direction: column;
  padding: clamp(20px, 3vw, 42px) clamp(18px, 4.4vw, 72px) clamp(22px, 3vw, 38px);
  background:
    linear-gradient(125deg, rgba(4, 14, 21, 0.95) 0%, rgba(5, 17, 24, 0.78) 46%, rgba(4, 12, 19, 0.92) 100%),
    linear-gradient(180deg, rgba(3, 12, 18, 0.2), rgba(3, 12, 18, 0.76));
}

.dashboard-scrim::before {
  position: absolute;
  inset: 0;
  background-image: linear-gradient(rgba(255,255,255,0.018) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.018) 1px, transparent 1px);
  background-size: 72px 72px;
  mask-image: linear-gradient(to bottom, black, transparent 74%);
  content: '';
  pointer-events: none;
}

.daylight-wash,
.twilight-wash {
  position: absolute;
  inset: 0;
  pointer-events: none;
  transition: opacity 1.2s ease;
}

.daylight-wash {
  background:
    radial-gradient(circle at var(--sun-x) var(--sun-y), rgba(255,226,158,.34), transparent 22%),
    linear-gradient(180deg, rgba(110,161,178,.48), rgba(53,112,116,.24) 62%, rgba(18,47,51,.08));
  mix-blend-mode: screen;
  opacity: calc(var(--daylight-level) * .78);
}

.twilight-wash {
  background:
    radial-gradient(ellipse at var(--sun-x) 44%, rgba(237,151,87,.38), transparent 32%),
    linear-gradient(180deg, transparent 28%, rgba(159,80,67,.22) 68%, rgba(224,145,79,.12));
  mix-blend-mode: screen;
  opacity: calc(var(--twilight-level) * .72);
}

.ambient-orb {
  position: absolute;
  top: -30%;
  left: 45%;
  width: min(70vw, 980px);
  aspect-ratio: 1;
  border-radius: 50%;
  background: radial-gradient(circle, var(--period-glow), transparent 66%);
  pointer-events: none;
  transition: background 1.2s ease;
}

.architectural-frame {
  position: absolute;
  top: 8%;
  right: 5%;
  width: min(32vw, 420px);
  aspect-ratio: 0.72;
  border: 1px solid rgba(255,255,255,0.055);
  border-bottom: 0;
  border-radius: 48% 48% 0 0 / 22% 22% 0 0;
  opacity: 0.55;
  pointer-events: none;
}

.dashboard-content,
.dashboard-footer {
  position: relative;
  z-index: 1;
  width: min(100%, 1480px);
  margin-inline: auto;
}

.dashboard-content { display: grid; flex: 1; align-content: center; padding-block: clamp(42px, 6vh, 86px) clamp(34px, 5vh, 68px); }

.prayer-hero {
  display: grid;
  grid-template-columns: minmax(180px, .72fr) minmax(360px, 1.25fr) minmax(220px, .75fr);
  align-items: center;
  gap: clamp(28px, 5vw, 84px);
  min-height: clamp(260px, 36vh, 420px);
}

.section-kicker { color: var(--color-accent); font-size: .68rem; font-weight: 800; letter-spacing: .19em; text-transform: uppercase; }
.current-period { display: flex; align-items: center; gap: 10px; margin-top: 13px; color: var(--color-text); font-family: var(--font-display); font-size: clamp(1.15rem, 2vw, 1.55rem); font-weight: 650; }
.period-indicator { width: 8px; height: 8px; border-radius: 50%; background: var(--period-primary); box-shadow: 0 0 0 6px var(--period-glow); }
.hero-primary { text-align: center; }
.hero-primary h1 { margin-top: 8px; color: var(--color-text); font-family: var(--font-display); font-size: clamp(3.4rem, 7.4vw, 7.2rem); font-weight: 650; letter-spacing: -.055em; line-height: .92; text-wrap: balance; }
.hero-prayer-time { margin-top: 15px; color: var(--period-primary); font-family: var(--font-display); font-size: clamp(2rem, 4.2vw, 4.4rem); font-variant-numeric: tabular-nums; font-weight: 560; letter-spacing: -.035em; line-height: 1; text-shadow: 0 8px 34px var(--period-glow); transition: color .8s ease; }
.countdown-lockup { display: inline-flex; min-height: 38px; align-items: center; gap: 12px; margin-top: 22px; padding: 8px 15px; border: 1px solid var(--color-border); border-radius: var(--radius-pill); background: rgba(7,18,24,.58); box-shadow: var(--shadow-sm); }
.countdown-label { color: var(--color-text-subtle); font-size: .66rem; font-weight: 750; letter-spacing: .12em; text-transform: uppercase; }
.countdown-value { color: var(--color-text); font-size: .83rem; font-variant-numeric: tabular-nums; font-weight: 750; letter-spacing: .08em; }

.schedule-section { margin-top: clamp(12px, 2vh, 24px); }
.schedule-heading { display: flex; align-items: flex-end; justify-content: space-between; gap: 18px; margin-bottom: 18px; }
.schedule-heading h2 { margin-top: 4px; color: var(--color-text); font-family: var(--font-display); font-size: clamp(1.35rem, 2.5vw, 2rem); font-weight: 620; letter-spacing: -.025em; }
.schedule-date { color: var(--color-text-muted); font-size: .78rem; font-weight: 700; }
.prayer-grid { display: grid; grid-template-columns: repeat(6, minmax(0, 1fr)); gap: 10px; }
.prayer-card { position: relative; display: grid; min-width: 0; min-height: 132px; align-content: space-between; gap: 24px; overflow: hidden; padding: 17px; border: 1px solid var(--color-border); border-radius: var(--radius-lg); background: linear-gradient(155deg, rgba(17,35,42,.76), rgba(8,20,27,.72)); box-shadow: var(--shadow-card); transition: border-color var(--motion-base) var(--ease-standard), background var(--motion-base) var(--ease-standard), box-shadow var(--motion-base) var(--ease-standard); }
.prayer-card::after { position: absolute; right: -34px; bottom: -52px; width: 110px; height: 110px; border: 1px solid rgba(255,255,255,.045); border-radius: 50%; content: ''; }
.prayer-card:hover { border-color: var(--color-border-strong); background: linear-gradient(155deg, rgba(22,43,50,.88), rgba(9,23,30,.84)); box-shadow: var(--shadow-card-hover); }
.prayer-card.is-next { border-color: color-mix(in srgb, var(--period-primary) 58%, transparent); background: linear-gradient(155deg, color-mix(in srgb, var(--period-secondary) 32%, rgba(14,30,37,.92)), rgba(9,21,28,.9)); box-shadow: 0 16px 42px rgba(0,0,0,.28), inset 0 1px rgba(255,255,255,.055); }
.prayer-card.is-current:not(.is-next) { border-color: rgba(126,167,163,.38); }
.prayer-card.is-disabled { opacity: .55; }
.card-topline { display: flex; min-height: 24px; align-items: center; justify-content: space-between; gap: 8px; }
.prayer-icon { color: var(--period-primary); font-size: var(--icon-md); }
.card-status { display: inline-flex; min-height: 24px; align-items: center; gap: 6px; padding: 0 8px; border: 1px solid color-mix(in srgb, var(--period-primary) 38%, transparent); border-radius: var(--radius-pill); color: var(--color-text); font-size: .58rem; font-weight: 800; letter-spacing: .1em; text-transform: uppercase; }
.card-status .status-dot { width: 5px; height: 5px; border-radius: 50%; background: var(--period-primary); box-shadow: 0 0 0 3px var(--period-glow); }
.card-status.is-current-status { border-color: rgba(126,167,163,.3); color: #bad2ce; }
.card-status.is-muted { border-color: var(--color-border); color: var(--color-text-subtle); }
.card-copy { display: flex; align-items: flex-end; justify-content: space-between; gap: 10px; }
.card-copy h3 { color: var(--color-text); font-family: var(--font-display); font-size: 1.05rem; font-weight: 650; }
.card-copy p { margin-top: 3px; color: var(--color-text-subtle); font-size: .66rem; }
.prayer-time { flex: 0 0 auto; color: var(--color-text); font-family: var(--font-display); font-size: clamp(1.35rem, 2.1vw, 2rem); font-variant-numeric: tabular-nums; font-weight: 600; letter-spacing: -.035em; line-height: 1; }
.is-next .prayer-time { color: var(--period-primary); }

.dashboard-footer { display: flex; align-items: center; gap: 14px; color: var(--color-text-subtle); font-size: .68rem; font-weight: 600; letter-spacing: .04em; }
.footer-rule { width: 32px; height: 1px; background: var(--color-border-strong); }

.dashboard-loading { display: grid; width: min(900px, 100%); justify-self: center; place-items: center; }
.skeleton { overflow: hidden; border-radius: var(--radius-md); background: rgba(255,255,255,.06); }
.skeleton::after { display: block; width: 45%; height: 100%; background: linear-gradient(90deg, transparent, rgba(255,255,255,.08), transparent); content: ''; animation: skeleton-shimmer 1.5s ease-in-out infinite; }
.skeleton-kicker { width: 120px; height: 12px; }
.skeleton-title { width: min(460px, 70vw); height: 78px; margin-top: 20px; }
.skeleton-time { width: 220px; height: 50px; margin-top: 16px; }
.skeleton-grid { display: grid; grid-template-columns: repeat(6, 1fr); gap: 10px; width: 100%; margin-top: 70px; }
.skeleton-card { height: 132px; }
.dashboard-empty { max-width: 620px; justify-self: center; padding: clamp(28px, 5vw, 52px); border: 1px solid var(--color-border); border-radius: var(--radius-xl); background: var(--color-surface); text-align: center; }
.dashboard-empty > .material-icons { margin-bottom: 18px; color: var(--color-accent); font-size: 36px; }
.dashboard-empty h1 { margin: 8px 0 10px; font-family: var(--font-display); font-size: clamp(1.8rem, 4vw, 3rem); }
.dashboard-empty > p:not(.section-kicker) { margin: 0 auto 24px; color: var(--color-text-muted); }

@keyframes skeleton-shimmer { from { transform: translateX(-140%); } to { transform: translateX(260%); } }

@media (max-width: 1120px) {
  .prayer-hero { position: relative; z-index: 0; grid-template-columns: .7fr 1.3fr; }
  .hero-context,
  .hero-primary { position: relative; z-index: 1; }
  .prayer-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); }
}

@media (max-width: 760px) {
  .dashboard-scrim { padding: max(16px, env(safe-area-inset-top)) 14px max(18px, env(safe-area-inset-bottom)); }
  .dashboard-content { align-content: start; padding-block: 48px 32px; }
  .prayer-hero { grid-template-columns: 1fr; gap: 28px; min-height: 0; text-align: center; }
  .hero-context { display: grid; place-items: center; }
  .hero-date { max-width: none; }
  .hero-primary h1 { font-size: clamp(3.7rem, 17vw, 5.7rem); }
  .hero-prayer-time { font-size: clamp(2.25rem, 11vw, 3.5rem); }
  .schedule-section { margin-top: 48px; }
  .prayer-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 9px; }
  .prayer-card { min-height: 128px; padding: 15px; }
  .card-copy { display: block; }
  .prayer-time { display: block; margin-top: 10px; font-size: clamp(1.6rem, 8vw, 2.2rem); }
  .dashboard-footer { justify-content: center; }
  .skeleton-grid { grid-template-columns: repeat(2, 1fr); margin-top: 48px; }
}

@media (max-width: 380px) {
  .dashboard-scrim { padding-inline: 10px; }
  .hero-primary h1 { font-size: 3.45rem; }
  .countdown-lockup { gap: 8px; padding-inline: 12px; }
  .countdown-label { font-size: .58rem; }
  .countdown-value { font-size: .75rem; }
  .schedule-heading { align-items: flex-start; }
  .prayer-card { min-height: 122px; padding: 13px; }
  .card-status { padding-inline: 6px; font-size: .52rem; }
}

@media (prefers-reduced-motion: reduce) {
  .daylight-wash,
  .twilight-wash,
  .ambient-orb,
  .prayer-time { transition: none; }
  .skeleton::after { animation: none; }
}
</style>
