<template>
  <div class="settings-shell">
    <aside class="settings-sidebar">
      <router-link class="settings-brand" to="/">
        <span class="settings-brand-mark" aria-hidden="true">A</span>
        <span><strong>Athan Hub</strong><small>Settings</small></span>
      </router-link>

      <nav class="sidebar-nav" aria-label="Settings sections">
        <button
          v-for="section in sections"
          :key="section.id"
          type="button"
          class="nav-item"
          :class="{ active: activeSection === section.id }"
          :aria-current="activeSection === section.id ? 'page' : undefined"
          @click="selectSection(section.id)"
        >
          <span class="material-icons" aria-hidden="true">{{ section.icon }}</span>
          <span>{{ section.label }}</span>
          <span class="nav-chevron material-icons" aria-hidden="true">chevron_right</span>
        </button>
      </nav>

      <div class="sidebar-status">
        <span class="sidebar-status-icon material-icons" aria-hidden="true">dns</span>
        <div><strong>Local service</strong><small>athan.local</small></div>
        <span class="online-dot" aria-label="Online"></span>
      </div>
    </aside>

    <section class="settings-content" aria-label="Settings content">
      <div class="settings-mobile-bar">
        <div>
          <p class="section-kicker">Settings</p>
          <p>{{ activeSectionMeta.label }}</p>
        </div>
        <StatusPill :tone="bt.connected ? 'success' : 'info'">{{ bt.connected ? 'Speaker connected' : 'Local' }}</StatusPill>
      </div>

      <nav class="settings-mobile-nav" aria-label="Settings sections">
        <button
          v-for="section in sections"
          :key="section.id"
          type="button"
          class="nav-item"
          :class="{ active: activeSection === section.id }"
          :aria-current="activeSection === section.id ? 'page' : undefined"
          @click="selectSection(section.id)"
        >
          <span class="material-icons" aria-hidden="true">{{ section.icon }}</span>
          <span>{{ section.label }}</span>
        </button>
      </nav>

      <div v-if="pageLoading" class="settings-skeleton" aria-label="Loading settings" aria-live="polite">
        <div class="skeleton skeleton-heading"></div>
        <div class="skeleton-card-grid">
          <div class="skeleton skeleton-panel"></div>
          <div class="skeleton skeleton-panel"></div>
          <div class="skeleton skeleton-panel is-wide"></div>
        </div>
      </div>

      <Transition v-else mode="out-in" :css="false" @enter="enterPane" @leave="leavePane">
        <div :key="activeSection" class="settings-pane">
          <template v-if="activeSection === 'general'">
            <SectionHeader icon="tune" title="General" subtitle="Set the dashboard’s local context and visual atmosphere." />
            <div class="card-grid two-col">
              <section class="surface-card">
                <div class="surface-heading"><span class="surface-heading-icon material-icons" aria-hidden="true">public</span><div><h2>Local time</h2><p>The scheduler and dashboard use this timezone.</p></div></div>
                <div class="field"><label class="label" for="timezone">Timezone</label><input id="timezone" class="input" v-model="settings.timezone" placeholder="Europe/London" /><p class="field-help">Use an IANA timezone such as Europe/London.</p></div>
                <div class="field"><label class="label" for="grace-seconds">Playback grace window</label><input id="grace-seconds" class="input" type="number" min="0" v-model.number="settings.grace_seconds" /><p class="field-help">Seconds the scheduler may still play after a prayer begins.</p></div>
              </section>

              <section class="surface-card">
                <div class="surface-heading"><span class="surface-heading-icon material-icons" aria-hidden="true">landscape</span><div><h2>Dashboard atmosphere</h2><p>Choose the background beneath the prayer interface.</p></div></div>
                <div class="field"><label class="label" for="dashboard-background">Background image</label><div class="select is-fullwidth"><select id="dashboard-background" v-model="settings.dashboard_background"><option v-for="name in backgrounds" :key="name" :value="name">{{ name }}</option></select></div><p class="field-help">Choose a bundled image or upload your own PNG, JPEG or WebP.</p></div>
                <UploadBox label="Upload a new background" accept="image/png,image/jpeg,image/webp" @file="uploadBackground" />
              </section>
            </div>
            <div class="pane-actions"><button type="button" class="button is-primary" @click="saveSettings"><span class="material-icons" aria-hidden="true">check</span>Save general settings</button></div>
          </template>

          <template v-else-if="activeSection === 'bluetooth'">
            <SectionHeader icon="speaker" title="Bluetooth & speaker" subtitle="Manage the Echo connection, playback timing and output level." />
            <section class="speaker-overview surface-card">
              <div class="speaker-identity">
                <span class="speaker-icon material-icons" aria-hidden="true">speaker</span>
                <div><p class="section-kicker">Audio output</p><h2>{{ bt.sink_label || 'Echo speaker' }}</h2><p>{{ bt.sink || 'No active audio sink' }}</p></div>
              </div>
              <StatusPill :tone="bt.connected ? 'success' : 'danger'">{{ bt.connected ? 'Connected' : 'Disconnected' }}</StatusPill>
            </section>

            <div class="card-grid two-col speaker-settings-grid">
              <section class="surface-card">
                <div class="surface-heading"><span class="surface-heading-icon material-icons" aria-hidden="true">bluetooth</span><div><h2>Connection</h2><p>Identity and connection retry behaviour.</p></div></div>
                <div class="field"><label class="label" for="echo-mac">Echo MAC address</label><input id="echo-mac" class="input" v-model="settings.echo_mac" placeholder="AA:BB:CC:DD:EE:FF" autocomplete="off" /></div>
                <div class="discovery-tools">
                  <button type="button" class="button" :class="{ 'is-loading': scanning }" :disabled="scanning || Boolean(pairingMac)" @click="scanDevices"><span class="material-icons" aria-hidden="true">radar</span>Scan nearby devices</button>
                  <p class="field-help">Put the speaker into pairing mode before scanning.</p>
                </div>
                <div v-if="devices.length" class="device-list" aria-live="polite">
                  <div v-for="device in devices" :key="device.mac" class="device-row">
                    <span class="material-icons" aria-hidden="true">speaker</span>
                    <span><strong>{{ device.name }}</strong><small>{{ device.mac }}</small></span>
                    <button type="button" class="button is-small is-accent" :class="{ 'is-loading': pairingMac === device.mac }" :disabled="Boolean(pairingMac)" @click="pairDevice(device)">Pair</button>
                  </div>
                </div>
                <div class="form-grid">
                  <div class="field"><label class="label" for="pre-connect">Pre-connect seconds</label><input id="pre-connect" class="input" type="number" min="0" v-model.number="settings.pre_connect_seconds" /></div>
                  <div class="field"><label class="label" for="connect-retry">Retry seconds</label><input id="connect-retry" class="input" type="number" min="0" v-model.number="settings.connect_retry_seconds" /></div>
                </div>
              </section>

              <section class="surface-card">
                <div class="surface-heading"><span class="surface-heading-icon material-icons" aria-hidden="true">graphic_eq</span><div><h2>Playback</h2><p>Output level and post-play connection state.</p></div></div>
                <div class="field"><label class="label" for="sink-volume">Speaker volume · {{ settings.sink_volume_percent }}%</label><input id="sink-volume" class="volume-slider" type="range" min="0" max="150" step="1" v-model.number="settings.sink_volume_percent" /><div class="range-labels"><span>0%</span><span>100%</span><span>150%</span></div><p v-if="Number(settings.sink_volume_percent) > 100" class="field-warning"><span class="material-icons" aria-hidden="true">volume_up</span>Levels above 100% may sound louder but can distort.</p></div>
                <div class="field"><label class="label" for="disconnect-after">After playback</label><div class="select is-fullwidth"><select id="disconnect-after" v-model="settings.disconnect_after_play"><option :value="true">Disconnect from the speaker</option><option :value="false">Keep the speaker connected</option></select></div></div>
              </section>
            </div>

            <div class="pane-actions split-actions">
              <button type="button" class="button is-primary" @click="saveSettings"><span class="material-icons" aria-hidden="true">check</span>Save speaker settings</button>
              <div class="button-group" aria-label="Speaker actions">
                <button type="button" class="button is-accent" @click="connect"><span class="material-icons" aria-hidden="true">link</span>Connect</button>
                <button type="button" class="button" @click="disconnect"><span class="material-icons" aria-hidden="true">link_off</span>Disconnect</button>
                <button type="button" class="button" @click="testPlay"><span class="material-icons" aria-hidden="true">play_arrow</span>Test</button>
                <button type="button" class="button is-danger" @click="stopTest"><span class="material-icons" aria-hidden="true">stop</span>Stop</button>
              </div>
            </div>
          </template>

          <template v-else-if="activeSection === 'timetable'">
            <SectionHeader icon="calendar_today" title="Timetable" subtitle="Review today and tomorrow, import the annual schedule, or adjust a specific date." />

            <section class="schedule-comparison">
              <article class="surface-card schedule-day-card">
                <div class="schedule-day-heading"><div><p class="section-kicker">Today</p><h2>{{ todayLabel }}</h2></div><span class="material-icons" aria-hidden="true">today</span></div>
                <PrayerTable :data="todaySchedule" />
              </article>
              <article class="surface-card schedule-day-card">
                <div class="schedule-day-heading"><div><p class="section-kicker">Tomorrow</p><h2>{{ tomorrowLabel }}</h2></div><span class="material-icons" aria-hidden="true">event</span></div>
                <PrayerTable :data="tomorrowSchedule" />
              </article>
            </section>

            <div class="card-grid two-col timetable-tools">
              <section class="surface-card">
                <div class="surface-heading"><span class="surface-heading-icon material-icons" aria-hidden="true">upload_file</span><div><h2>Import timetable</h2><p>Preview a CSV before adding it to the scheduler.</p></div></div>
                <UploadBox label="Choose timetable CSV" accept="text/csv,.csv" @file="uploadCsv" />
                <div v-if="preview.length" class="preview-area">
                  <div class="table-wrapper"><table class="table is-fullwidth is-striped is-size-7"><thead><tr><th v-for="key in columns" :key="key" scope="col">{{ key }}</th></tr></thead><tbody><tr v-for="(row, index) in preview" :key="index"><td v-for="key in columns" :key="key">{{ row[key] || '—' }}</td></tr></tbody></table></div>
                  <div class="import-actions"><label class="checkbox"><input type="checkbox" v-model="replaceOverrides" />Replace overrides for imported dates</label><button type="button" class="button is-primary" @click="importCsv">Import timetable</button></div>
                </div>
              </section>

              <section class="surface-card">
                <div class="surface-heading"><span class="surface-heading-icon material-icons" aria-hidden="true">edit_calendar</span><div><h2>Manual adjustment</h2><p>Fine-tune one date without changing the source CSV.</p></div></div>
                <div class="field"><label class="label" for="manual-date">Date</label><input id="manual-date" class="input date-input" type="date" v-model="selectedDate" @change="loadManual" /></div>
                <div class="manual-grid"><TimeEditor v-for="prayer in manualPrayers" :key="prayer" :prayer="prayer" :value="manual[prayer]?.time" :enabled="manual[prayer]?.enabled" @update:time="value => manual[prayer].time = value" @update:enabled="value => manual[prayer].enabled = value" /></div>
                <p class="field-help">Adjusted prayers remain identified as manual overrides.</p>
                <button type="button" class="button is-primary mt-4" @click="saveManual">Save overrides</button>
              </section>
            </div>
          </template>

          <template v-else-if="activeSection === 'audio'">
            <SectionHeader icon="graphic_eq" title="Athan audio" subtitle="Manage recordings and decide which profile plays for each prayer." />
            <div class="audio-layout">
              <section class="surface-card upload-profile-card">
                <div class="surface-heading"><span class="surface-heading-icon material-icons" aria-hidden="true">library_add</span><div><h2>Add a profile</h2><p>Upload an MP3 and give the recording a clear name.</p></div></div>
                <div class="field"><label class="label" for="audio-name">Profile name</label><input id="audio-name" class="input" v-model="audioName" placeholder="Fajr Athan" /></div>
                <UploadBox label="Choose an MP3 recording" accept="audio/mpeg,.mp3" @file="uploadAudio" />
                <p class="field-help">Your currently selected recording is preserved until you change the prayer mapping.</p>
              </section>

              <section class="surface-card profiles-card">
                <div class="surface-heading"><span class="surface-heading-icon material-icons" aria-hidden="true">queue_music</span><div><h2>Audio profiles</h2><p>Enable, test or remove saved recordings.</p></div></div>
                <div class="table-wrapper"><table class="table is-fullwidth audio-table"><thead><tr><th scope="col">Profile</th><th scope="col">Status</th><th scope="col"><span class="sr-only">Actions</span></th></tr></thead><tbody><tr v-if="!profiles.length"><td colspan="3"><div class="empty-state"><span class="material-icons" aria-hidden="true">music_off</span><strong>No audio profiles</strong><p>Upload an MP3 to make it available for prayer mapping.</p></div></td></tr><tr v-for="profile in profiles" :key="profile.id"><td><div class="profile-name"><span class="material-icons" aria-hidden="true">audio_file</span><span><strong>{{ profile.name }}</strong><small>Profile {{ profile.id }}</small></span></div></td><td><label class="switch-control"><input type="checkbox" v-model="profile.enabled" @change="toggleProfile(profile)" /><span class="switch-track" aria-hidden="true"><span></span></span><span class="sr-only">Enable {{ profile.name }}</span></label></td><td><div class="action-buttons"><button type="button" class="button is-small icon-only" :aria-label="`Test ${profile.name}`" title="Test profile" @click="testProfile(profile.id)"><span class="material-icons" aria-hidden="true">play_arrow</span></button><button type="button" class="button is-small is-danger icon-only" :aria-label="`Delete ${profile.name}`" title="Delete profile" @click="deleteProfile(profile.id)"><span class="material-icons" aria-hidden="true">delete</span></button></div></td></tr></tbody></table></div>

                <div class="mapping-section"><div class="mapping-heading"><h3>Prayer mapping</h3><p>Select the recording used for each scheduled prayer.</p></div><div class="mapping-grid"><div v-for="prayer in prayers" :key="prayer" class="mapping-card"><label class="label" :for="`mapping-${prayer}`">{{ formatPrayer(prayer) }}</label><div class="select is-fullwidth"><select :id="`mapping-${prayer}`" v-model="mapping[prayer]"><option :value="null">Select profile</option><option v-for="profile in profiles" :key="profile.id" :value="profile.id">{{ profile.name }}</option></select></div></div></div><div class="pane-actions"><button type="button" class="button is-primary" @click="saveMapping">Save prayer mapping</button></div></div>
              </section>
            </div>
          </template>

          <template v-else-if="activeSection === 'activity'">
            <SectionHeader icon="history" title="Activity" subtitle="Recent playback, connection and scheduling events from this Athan Hub." />
            <section class="surface-card activity-card">
              <div v-if="!activity.length" class="empty-state"><span class="material-icons" aria-hidden="true">history_toggle_off</span><strong>No activity recorded yet</strong><p>Playback and speaker events will appear here as the system runs.</p></div>
              <ol v-else class="activity-list">
                <li v-for="entry in activity" :key="entry.id || `${entry.ts}-${entry.message}`" class="activity-row">
                  <span class="activity-icon material-icons" aria-hidden="true">{{ activityIcon(entry) }}</span>
                  <div class="activity-copy"><strong>{{ entry.message }}</strong><p><time :datetime="entry.ts">{{ formatTs(entry.ts) }}</time><span v-if="entry.level"> · {{ entry.level }}</span></p></div>
                  <span class="activity-line" aria-hidden="true"></span>
                </li>
              </ol>
            </section>
          </template>

          <template v-else>
            <SectionHeader icon="block" title="Exclusions" subtitle="Skip all or selected prayers by date, date range or weekday." />
            <div class="card-grid two-col exclusions-grid">
              <section class="surface-card">
                <div class="surface-heading"><span class="surface-heading-icon material-icons" aria-hidden="true">rule</span><div><h2>New exclusion</h2><p>Choose when and which prayer should be skipped.</p></div></div>
                <div class="field"><label class="label" for="rule-type">Rule type</label><div class="select is-fullwidth"><select id="rule-type" v-model="exclusionForm.kind"><option value="date">Specific date</option><option value="date_range">Date range</option><option value="weekday">Weekday</option></select></div></div>
                <div v-if="exclusionForm.kind === 'date'" class="field"><label class="label" for="exclude-date">Date</label><input id="exclude-date" class="input" type="date" v-model="exclusionForm.value" /></div>
                <div v-else-if="exclusionForm.kind === 'date_range'" class="range-grid"><div class="field"><label class="label" for="exclude-from">From</label><input id="exclude-from" class="input" type="date" v-model="exclusionForm.start" /></div><div class="field"><label class="label" for="exclude-to">To</label><input id="exclude-to" class="input" type="date" v-model="exclusionForm.end" /></div></div>
                <div v-else class="field"><label class="label" for="exclude-weekday">Weekday</label><div class="select is-fullwidth"><select id="exclude-weekday" v-model="exclusionForm.value"><option v-for="day in weekdays" :key="day" :value="day.toLowerCase()">{{ day }}</option></select></div></div>
                <div class="field"><label class="label" for="exclude-prayer">Prayer</label><div class="select is-fullwidth"><select id="exclude-prayer" v-model="exclusionForm.prayer_name"><option :value="null">All prayers</option><option v-for="prayer in prayers" :key="prayer" :value="prayer">{{ formatPrayer(prayer) }}</option></select></div></div>
                <button type="button" class="button is-primary" @click="addExclusion"><span class="material-icons" aria-hidden="true">add</span>Add exclusion</button>
              </section>

              <section class="surface-card">
                <div class="surface-heading"><span class="surface-heading-icon material-icons" aria-hidden="true">event_busy</span><div><h2>Active rules</h2><p>Rules currently applied by the scheduler.</p></div></div>
                <div v-if="!exclusions.length" class="empty-state"><span class="material-icons" aria-hidden="true">event_available</span><strong>No active exclusions</strong><p>Every enabled prayer will follow the timetable.</p></div>
                <div v-else class="rule-list"><div v-for="rule in exclusions" :key="rule.id" class="rule-row"><span class="rule-icon material-icons" aria-hidden="true">block</span><div><strong>{{ rule.prayer_name ? formatPrayer(rule.prayer_name) : 'All prayers' }}</strong><p>{{ formatKind(rule.kind) }} · {{ rule.value }}</p></div><button type="button" class="button is-small is-danger icon-only" :aria-label="`Delete exclusion for ${rule.prayer_name || 'all prayers'}`" title="Delete exclusion" @click="deleteExclusion(rule.id)"><span class="material-icons" aria-hidden="true">delete</span></button></div></div>
              </section>
            </div>
          </template>
        </div>
      </Transition>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, inject, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api from '../api'
import PrayerTable from '../components/PrayerTable.vue'
import SectionHeader from '../components/SectionHeader.vue'
import StatusPill from '../components/StatusPill.vue'
import TimeEditor from '../components/TimeEditor.vue'
import UploadBox from '../components/UploadBox.vue'
import { enterPane, leavePane } from '../motion'

const toast = inject<(message: string, type?: any) => void>('toast') || (() => {})
const route = useRoute()
const router = useRouter()
const sections = [
  { id: 'timetable', label: 'Timetable', icon: 'calendar_today' },
  { id: 'bluetooth', label: 'Bluetooth & speaker', icon: 'speaker' },
  { id: 'activity', label: 'Activity', icon: 'history' },
  { id: 'exclusions', label: 'Exclusions', icon: 'block' },
  { id: 'audio', label: 'Athan audio', icon: 'graphic_eq' },
  { id: 'general', label: 'General', icon: 'tune' }
]
const sectionFromQuery = () => {
  const query = String(route.query.tab || '').toLowerCase()
  return sections.some(item => item.id === query) ? query : 'general'
}
const activeSection = ref(sectionFromQuery())
const activeSectionMeta = computed(() => sections.find(section => section.id === activeSection.value) || sections[5])
watch(() => route.query.tab, () => { activeSection.value = sectionFromQuery() })
const selectSection = (id: string) => {
  activeSection.value = id
  router.replace({ query: { ...route.query, tab: id } })
}

const pageLoading = ref(true)
const settings = reactive<any>({ timezone: 'Europe/London', grace_seconds: 120, echo_mac: '', pre_connect_seconds: 10, connect_retry_seconds: 20, sink_volume_percent: 140, disconnect_after_play: true, dashboard_background: 'bg.png' })
const bt = reactive<any>({ connected: false })
const devices = ref<any[]>([])
const scanning = ref(false)
const pairingMac = ref('')
const backgrounds = ref<string[]>([])
const preview = ref<any[]>([])
const replaceOverrides = ref(false)
const columns = ['date', 'fajr', 'shurooq', 'dhuhr', 'asr', 'maghrib', 'isha']
const localDateString = (value: Date) => `${value.getFullYear()}-${String(value.getMonth() + 1).padStart(2, '0')}-${String(value.getDate()).padStart(2, '0')}`
const todayDate = new Date()
const tomorrowDate = new Date(todayDate.getFullYear(), todayDate.getMonth(), todayDate.getDate() + 1)
const selectedDate = ref(localDateString(todayDate))
const todaySchedule = ref<any>(null)
const tomorrowSchedule = ref<any>(null)
const activity = ref<any[]>([])
const todayLabel = computed(() => new Intl.DateTimeFormat(undefined, { weekday: 'long', day: 'numeric', month: 'short' }).format(todayDate))
const tomorrowLabel = computed(() => new Intl.DateTimeFormat(undefined, { weekday: 'long', day: 'numeric', month: 'short' }).format(tomorrowDate))
const manual = reactive<any>({})
const manualPrayers = ['fajr', 'shurooq', 'dhuhr', 'asr', 'maghrib', 'isha']
const profiles = ref<any[]>([])
const audioName = ref('Athan')
const prayers = ['fajr', 'dhuhr', 'asr', 'maghrib', 'isha']
const mapping = reactive<Record<string, number | null>>({ fajr: null, dhuhr: null, asr: null, maghrib: null, isha: null })
const exclusions = ref<any[]>([])
const weekdays = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
const exclusionForm = reactive<any>({ kind: 'date', value: localDateString(todayDate), start: '', end: '', prayer_name: null })
const err = (error: any, fallback: string) => toast(error.response?.data?.detail || fallback, 'danger')
const formatKind = (kind: string) => String(kind || '').replace('_', ' ').replace(/^./, value => value.toUpperCase())
const formatPrayer = (prayer: string) => prayer.charAt(0).toUpperCase() + prayer.slice(1)
const formatTs = (value: string) => value ? new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value)) : 'Unknown time'
const activityIcon = (entry: any) => entry.prayer ? 'notifications_active' : /connect|bluetooth|speaker/i.test(entry.message || '') ? 'speaker' : /error|fail/i.test(entry.message || '') ? 'error_outline' : 'history'

const loadManual = async () => {
  try {
    const data = (await api.get('/timetable/day', { params: { date: selectedDate.value } })).data
    for (const prayer of manualPrayers) manual[prayer] = { time: data.prayers?.[prayer]?.effective || '', enabled: data.prayers?.[prayer]?.enabled !== false }
  } catch (error) { err(error, 'Could not load this date') }
}

const load = async () => {
  const [s, b, bg, p, m, x, today, tomorrow, logs] = await Promise.all([
    api.get('/settings'),
    api.get('/bluetooth/status'),
    api.get('/backgrounds'),
    api.get('/audio/profiles'),
    api.get('/audio/mapping'),
    api.get('/exclusions'),
    api.get('/timetable/day', { params: { date: localDateString(todayDate) } }),
    api.get('/timetable/day', { params: { date: localDateString(tomorrowDate) } }),
    api.get('/logs', { params: { limit: 50 } })
  ])
  Object.assign(settings, s.data)
  settings.disconnect_after_play = ['1', 1, true, 'true', 'True'].includes(settings.disconnect_after_play)
  Object.assign(bt, b.data)
  backgrounds.value = bg.data.backgrounds || []
  if (!settings.dashboard_background && backgrounds.value.length) settings.dashboard_background = backgrounds.value[0]
  profiles.value = p.data
  Object.assign(mapping, m.data)
  exclusions.value = x.data
  todaySchedule.value = today.data
  tomorrowSchedule.value = tomorrow.data
  activity.value = logs.data || []
  await loadManual()
}

const saveSettings = async () => { try { settings.sink_volume_percent = Math.max(0, Math.min(150, Number(settings.sink_volume_percent))); await api.put('/settings', settings); toast('Settings saved', 'success') } catch (error) { err(error, 'Save failed') } }
const connect = async () => { try { await api.post('/bluetooth/connect'); Object.assign(bt, (await api.get('/bluetooth/status')).data); toast('Connected', 'success') } catch (error) { err(error, 'Connect failed') } }
const scanDevices = async () => { scanning.value = true; try { devices.value = (await api.post('/bluetooth/scan')).data.devices || []; if (!devices.value.length) toast('No Bluetooth devices found. Confirm pairing mode and try again.', 'warning') } catch (error) { err(error, 'Bluetooth scan failed') } finally { scanning.value = false } }
const pairDevice = async (device: any) => { pairingMac.value = device.mac; try { await api.post('/bluetooth/pair', { mac: device.mac }); settings.echo_mac = device.mac; Object.assign(bt, (await api.get('/bluetooth/status')).data); toast(`${device.name} paired and connected`, 'success') } catch (error) { err(error, 'Pairing failed') } finally { pairingMac.value = '' } }
const disconnect = async () => { try { await api.post('/bluetooth/disconnect'); Object.assign(bt, (await api.get('/bluetooth/status')).data); toast('Disconnected', 'info') } catch (error) { err(error, 'Disconnect failed') } }
const testPlay = async () => { try { await api.post('/bluetooth/test-play', { prayer_name: 'fajr' }); toast('Test started', 'success') } catch (error) { err(error, 'Upload an MP3 before testing') } }
const stopTest = async () => { try { await api.post('/bluetooth/stop-test'); toast('Stopped', 'info') } catch (error) { err(error, 'Stop failed') } }
const uploadBackground = async (file: File) => { const data = new FormData(); data.append('file', file); try { const result = (await api.post('/backgrounds/upload', data)).data; backgrounds.value = Array.from(new Set([...backgrounds.value, result.filename])); settings.dashboard_background = result.filename; toast('Background uploaded', 'success') } catch (error) { err(error, 'Upload failed') } }
const uploadCsv = async (file: File) => { const data = new FormData(); data.append('file', file); try { preview.value = (await api.post('/timetable/upload', data)).data.preview } catch (error) { err(error, 'CSV upload failed') } }
const importCsv = async () => { try { await api.post('/timetable/import', null, { params: { replace_overrides: replaceOverrides.value } }); toast('Timetable imported', 'success'); await loadManual() } catch (error) { err(error, 'Import failed') } }
const saveManual = async () => { try { await api.put('/timetable/day', { prayers: manual }, { params: { date: selectedDate.value } }); toast('Overrides saved', 'success') } catch (error) { err(error, 'Could not save overrides') } }
const uploadAudio = async (file: File) => { const data = new FormData(); data.append('name', audioName.value); data.append('file', file); try { await api.post('/audio/upload', data); profiles.value = (await api.get('/audio/profiles')).data; toast('Audio uploaded', 'success') } catch (error) { err(error, 'Audio upload failed') } }
const toggleProfile = async (profile: any) => { try { await api.put(`/audio/profiles/${profile.id}`, { enabled: profile.enabled }) } catch (error) { profile.enabled = !profile.enabled; err(error, 'Could not update profile') } }
const testProfile = async (id: number) => { try { await api.post(`/audio/profiles/${id}/test`); toast('Test started', 'success') } catch (error) { err(error, 'Test failed') } }
const deleteProfile = async (id: number) => { try { await api.delete(`/audio/profiles/${id}`); profiles.value = profiles.value.filter(profile => profile.id !== id); for (const prayer of prayers) if (mapping[prayer] === id) mapping[prayer] = null; toast('Profile deleted', 'info') } catch (error) { err(error, 'Delete failed') } }
const saveMapping = async () => { try { await api.put('/audio/mapping', mapping); toast('Mapping saved', 'success') } catch (error) { err(error, 'Mapping save failed') } }
const addExclusion = async () => { const value = exclusionForm.kind === 'date_range' ? `${exclusionForm.start}..${exclusionForm.end}` : exclusionForm.value; if (!value || value === '..') { toast('Complete the exclusion rule', 'warning'); return } try { await api.post('/exclusions', { kind: exclusionForm.kind, value, prayer_name: exclusionForm.prayer_name, enabled: true }); exclusions.value = (await api.get('/exclusions')).data; toast('Exclusion added', 'success') } catch (error) { err(error, 'Could not add exclusion') } }
const deleteExclusion = async (id: number) => { try { await api.delete(`/exclusions/${id}`); exclusions.value = exclusions.value.filter(rule => rule.id !== id); toast('Exclusion removed', 'info') } catch (error) { err(error, 'Could not remove exclusion') } }

load().catch(error => err(error, 'Could not load settings')).finally(() => { pageLoading.value = false })
</script>

<style scoped>
.settings-shell { display: grid; grid-template-columns: 260px minmax(0, 1fr); gap: clamp(28px, 4vw, 60px); min-height: calc(100dvh - 152px); }
.settings-sidebar { position: sticky; top: 88px; align-self: start; min-height: min(690px, calc(100dvh - 120px)); padding: 18px; border: 1px solid var(--color-border); border-radius: var(--radius-xl); background: linear-gradient(160deg, rgba(16,34,41,.95), rgba(8,21,28,.93)); box-shadow: var(--shadow-card); }
.settings-brand { display: flex; align-items: center; gap: 12px; padding: 4px 6px 18px; border-bottom: 1px solid var(--color-border); color: var(--color-text); text-decoration: none; }
.settings-brand-mark { display: grid; width: 42px; height: 42px; place-items: center; border: 1px solid rgba(209,179,111,.35); border-radius: 14px 14px 14px 5px; background: var(--color-accent-soft); color: var(--color-accent-strong); font-family: var(--font-display); font-size: 1.2rem; font-weight: 700; }
.settings-brand > span:last-child { display: grid; gap: 1px; }
.settings-brand strong { font-size: .92rem; }
.settings-brand small { color: var(--color-text-subtle); font-size: .68rem; }
.sidebar-nav { display: grid; gap: 5px; margin-top: 18px; }
.nav-item { position: relative; display: flex; min-height: 48px; align-items: center; gap: 11px; width: 100%; padding: 0 11px; border: 1px solid transparent; border-radius: var(--radius-md); background: transparent; color: var(--color-text-muted); cursor: pointer; font: inherit; font-size: .8rem; font-weight: 700; text-align: left; transition: border-color var(--motion-fast) var(--ease-standard), background var(--motion-fast) var(--ease-standard), color var(--motion-fast) var(--ease-standard); }
.nav-item:hover { border-color: var(--color-border); background: var(--color-surface-hover); color: var(--color-text); }
.nav-item.active { border-color: rgba(209,179,111,.24); background: var(--color-accent-soft); color: var(--color-accent-strong); }
.nav-item > .material-icons { color: var(--color-text-subtle); font-size: 20px; }
.nav-item.active > .material-icons { color: var(--color-accent); }
.nav-chevron { margin-left: auto; opacity: .5; }
.sidebar-status { position: absolute; right: 18px; bottom: 18px; left: 18px; display: grid; grid-template-columns: 36px minmax(0,1fr) 8px; align-items: center; gap: 10px; padding: 12px; border: 1px solid var(--color-border); border-radius: var(--radius-md); background: rgba(3,15,21,.26); }
.sidebar-status-icon { display: grid; width: 36px; height: 36px; place-items: center; border-radius: 12px; background: var(--color-secondary-soft); color: var(--color-secondary); }
.sidebar-status div { display: grid; gap: 1px; min-width: 0; }
.sidebar-status strong { font-size: .72rem; }
.sidebar-status small { color: var(--color-text-subtle); font-size: .64rem; }
.online-dot { width: 7px; height: 7px; border-radius: 50%; background: var(--color-success); box-shadow: 0 0 0 4px rgba(94,189,154,.1); }
.settings-content { min-width: 0; }
.settings-mobile-bar,
.settings-mobile-nav { display: none; }
.settings-pane { min-width: 0; }
.card-grid { display: grid; grid-template-columns: minmax(0,1fr); gap: 16px; }
.card-grid.two-col { grid-template-columns: repeat(2, minmax(0,1fr)); }
.form-grid,
.range-grid { display: grid; grid-template-columns: repeat(2, minmax(0,1fr)); gap: 12px; }
.pane-actions { display: flex; justify-content: flex-end; margin-top: 22px; }
.split-actions { align-items: center; justify-content: space-between; gap: 16px; }
.button-group { display: flex; flex-wrap: wrap; justify-content: flex-end; gap: 8px; }
.button .material-icons { margin-right: 7px; font-size: 18px; }
.speaker-overview { display: flex; align-items: center; justify-content: space-between; gap: 18px; margin-bottom: 16px; }
.speaker-overview .status-pill { justify-self: start; }
.speaker-identity { display: flex; min-width: 0; align-items: center; gap: 16px; }
.speaker-icon { display: grid; width: 58px; height: 58px; flex: 0 0 auto; place-items: center; border: 1px solid rgba(126,167,163,.25); border-radius: 20px 20px 20px 7px; background: var(--color-secondary-soft); color: #a9cbc7; font-size: 28px; }
.speaker-identity h2 { margin-top: 3px; font-family: var(--font-display); font-size: 1.25rem; font-weight: 700; }
.speaker-identity > div > p:last-child { margin-top: 3px; overflow-wrap: anywhere; color: var(--color-text-subtle); font-size: .72rem; }
.speaker-settings-grid { align-items: stretch; }
.discovery-tools { display: flex; align-items: center; flex-wrap: wrap; gap: 8px 12px; margin-top: 14px; }
.discovery-tools .field-help { margin: 0; }
.device-list { display: grid; gap: 8px; margin-top: 14px; }
.device-row { display: grid; grid-template-columns: 34px minmax(0,1fr) auto; align-items: center; gap: 10px; padding: 9px; border: 1px solid var(--color-border); border-radius: var(--radius-md); background: rgba(3,15,21,.28); }
.device-row > .material-icons { color: var(--color-secondary); }
.device-row > span:nth-child(2) { display: grid; min-width: 0; gap: 2px; }
.device-row strong { overflow: hidden; font-size: .75rem; text-overflow: ellipsis; white-space: nowrap; }
.device-row small { color: var(--color-text-subtle); font-size: .62rem; }
.volume-slider { width: 100%; accent-color: var(--color-accent); cursor: pointer; }
.range-labels { display: flex; justify-content: space-between; margin-top: 5px; color: var(--color-text-subtle); font-size: .62rem; }
.field-warning { display: flex; align-items: center; gap: 7px; margin-top: 12px; color: var(--color-warning-text); font-size: .72rem; }
.field-warning .material-icons { font-size: 18px; }
.schedule-comparison { display: grid; grid-template-columns: repeat(2, minmax(0,1fr)); gap: 16px; }
.schedule-day-card { padding-bottom: 20px; }
.schedule-day-heading { display: flex; align-items: center; justify-content: space-between; margin-bottom: 18px; }
.schedule-day-heading h2 { margin-top: 3px; font-family: var(--font-display); font-size: 1.18rem; font-weight: 700; }
.schedule-day-heading > .material-icons { color: var(--color-text-subtle); font-size: 25px; }
.timetable-tools { align-items: start; margin-top: 16px; }
.preview-area { margin-top: 18px; }
.preview-area .table-wrapper { max-height: 260px; }
.import-actions { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-top: 14px; }
.date-input { max-width: 280px; }
.manual-grid { display: grid; grid-template-columns: repeat(2, minmax(0,1fr)); gap: 10px; }
.audio-layout { display: grid; grid-template-columns: minmax(270px,.72fr) minmax(0,1.4fr); align-items: start; gap: 16px; }
.upload-profile-card { position: sticky; top: 88px; }
.profiles-card .table-wrapper { max-height: 340px; }
.profile-name { display: flex; align-items: center; gap: 10px; min-width: 0; }
.profile-name > .material-icons { color: var(--color-accent); }
.profile-name > span:last-child { display: grid; min-width: 0; gap: 2px; }
.profile-name strong { overflow-wrap: anywhere; }
.profile-name small { color: var(--color-text-subtle); font-size: .65rem; }
.action-buttons { display: flex; justify-content: flex-end; gap: 7px; }
.mapping-section { margin-top: 26px; padding-top: 24px; border-top: 1px solid var(--color-border); }
.mapping-heading h3 { font-family: var(--font-display); font-size: 1rem; font-weight: 700; }
.mapping-heading p { margin-top: 3px; color: var(--color-text-subtle); font-size: .73rem; }
.mapping-grid { display: grid; grid-template-columns: repeat(2, minmax(0,1fr)); gap: 10px; margin-top: 16px; }
.mapping-card { padding: 13px; border: 1px solid var(--color-border); border-radius: var(--radius-md); background: rgba(3,15,21,.28); }
.activity-card { padding-block: 10px; }
.activity-list { margin: 0; padding: 0; list-style: none; }
.activity-row { position: relative; display: grid; grid-template-columns: 42px minmax(0,1fr); gap: 13px; padding: 16px 10px; }
.activity-row:not(:last-child) { border-bottom: 1px solid var(--color-border); }
.activity-icon { display: grid; width: 42px; height: 42px; place-items: center; border: 1px solid var(--color-border); border-radius: 50%; background: var(--color-muted-surface); color: var(--color-accent); font-size: 20px; }
.activity-copy strong { overflow-wrap: anywhere; font-size: .82rem; }
.activity-copy p { margin-top: 4px; color: var(--color-text-subtle); font-size: .7rem; }
.rule-list { display: grid; gap: 9px; }
.rule-row { display: grid; grid-template-columns: 38px minmax(0,1fr) 44px; align-items: center; gap: 11px; padding: 11px; border: 1px solid var(--color-border); border-radius: var(--radius-md); background: rgba(3,15,21,.28); }
.rule-icon { display: grid; width: 38px; height: 38px; place-items: center; border-radius: 12px; background: rgba(217,111,106,.08); color: var(--color-danger); font-size: 19px; }
.rule-row strong { font-size: .78rem; }
.rule-row p { margin-top: 2px; color: var(--color-text-subtle); font-size: .68rem; }
.settings-skeleton { padding-top: 16px; }
.skeleton { overflow: hidden; border-radius: var(--radius-md); background: rgba(255,255,255,.055); }
.skeleton::after { display: block; width: 45%; height: 100%; background: linear-gradient(90deg,transparent,rgba(255,255,255,.07),transparent); content: ''; animation: settings-shimmer 1.5s ease-in-out infinite; }
.skeleton-heading { width: min(440px,72vw); height: 76px; }
.skeleton-card-grid { display: grid; grid-template-columns: repeat(2,minmax(0,1fr)); gap: 16px; margin-top: 40px; }
.skeleton-panel { height: 260px; }
.skeleton-panel.is-wide { grid-column: 1/-1; height: 180px; }
@keyframes settings-shimmer { from { transform: translateX(-140%); } to { transform: translateX(260%); } }

@media (max-width: 1120px) {
  .settings-shell { display: block; }
  .settings-sidebar { display: none; }
  .settings-mobile-bar { display: flex; align-items: center; justify-content: space-between; gap: 16px; margin-bottom: 14px; }
  .settings-mobile-bar > div > p:last-child { margin-top: 2px; font-family: var(--font-display); font-size: 1.2rem; font-weight: 700; }
  .settings-mobile-nav { position: sticky; z-index: var(--z-sticky); top: 10px; display: flex; gap: 6px; overflow-x: auto; margin-bottom: 30px; padding: 6px; border: 1px solid var(--color-border); border-radius: var(--radius-lg); background: rgba(8,21,28,.94); box-shadow: var(--shadow-sm); scrollbar-width: none; backdrop-filter: blur(12px); }
  .settings-mobile-nav::-webkit-scrollbar { display: none; }
  .settings-mobile-nav .nav-item { flex: 0 0 auto; width: auto; min-height: 44px; padding-inline: 12px; white-space: nowrap; }
  .settings-mobile-nav .nav-item .material-icons { font-size: 18px; }
  .upload-profile-card { position: static; }
}

@media (max-width: 760px) {
  .card-grid.two-col,
  .schedule-comparison,
  .audio-layout,
  .form-grid,
  .range-grid,
  .mapping-grid,
  .skeleton-card-grid { grid-template-columns: 1fr; }
  .manual-grid { grid-template-columns: repeat(2,minmax(0,1fr)); }
  .split-actions { align-items: stretch; flex-direction: column; }
  .split-actions > .button { width: 100%; }
  .button-group { display: grid; grid-template-columns: repeat(2,minmax(0,1fr)); }
  .button-group .button { padding-inline: 12px; }
  .speaker-overview { align-items: flex-start; }
  .speaker-identity { align-items: flex-start; }
  .speaker-icon { width: 50px; height: 50px; }
  .import-actions { align-items: stretch; flex-direction: column; }
  .import-actions .button { width: 100%; }
  .skeleton-panel.is-wide { grid-column: auto; }
}

@media (max-width: 440px) {
  .settings-mobile-bar .status-pill { display: none; }
  .settings-mobile-nav { margin-inline: -4px; }
  .manual-grid { grid-template-columns: 1fr; }
  .speaker-overview { display: grid; }
  .button-group { grid-template-columns: 1fr; }
  .pane-actions .button { width: 100%; }
}

@media (prefers-reduced-motion: reduce) {
  .skeleton::after { animation: none; }
}
</style>
