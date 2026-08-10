<template>
  <div class="legacy-bluetooth-page">
    <SectionHeader icon="speaker" title="Bluetooth & speaker" subtitle="Manage the Echo connection and playback settings." />

    <section class="speaker-overview surface-card">
      <div class="speaker-identity">
        <span class="speaker-icon material-icons" aria-hidden="true">speaker</span>
        <div><p class="section-kicker">Audio output</p><h2>{{ status.sink_label || 'Echo speaker' }}</h2><p>{{ status.sink || 'No active audio sink' }}</p></div>
      </div>
      <StatusPill :tone="status.connected ? 'success' : 'danger'">{{ status.connected ? 'Connected' : 'Disconnected' }}</StatusPill>
    </section>

    <div class="bluetooth-grid">
      <section class="surface-card">
        <div class="surface-heading"><span class="surface-heading-icon material-icons" aria-hidden="true">bluetooth</span><div><h2>Connection</h2><p>Speaker identity and connection timing.</p></div></div>
        <div class="field"><label class="label" for="legacy-mac">MAC address</label><input id="legacy-mac" class="input" v-model="mac" placeholder="AA:BB:CC:DD:EE:FF" /></div>
        <div class="field"><label class="label" for="legacy-preconnect">Pre-connect seconds</label><input id="legacy-preconnect" class="input" type="number" min="0" v-model.number="settings.pre_connect_seconds" /></div>
        <div class="field"><label class="label" for="legacy-retry">Connect retry seconds</label><input id="legacy-retry" class="input" type="number" min="0" v-model.number="settings.connect_retry_seconds" /></div>
      </section>

      <section class="surface-card">
        <div class="surface-heading"><span class="surface-heading-icon material-icons" aria-hidden="true">graphic_eq</span><div><h2>Playback</h2><p>Grace window, output level and post-play state.</p></div></div>
        <div class="field"><label class="label" for="legacy-grace">Grace seconds</label><input id="legacy-grace" class="input" type="number" min="0" v-model.number="settings.grace_seconds" /></div>
        <div class="field"><label class="label" for="legacy-volume">Sink volume % (0–150)</label><input id="legacy-volume" class="input" type="number" min="0" max="150" v-model.number="settings.sink_volume_percent" /></div>
        <label class="checkbox"><input type="checkbox" v-model="disconnectAfter" />Disconnect after play</label>
      </section>
    </div>

    <div class="page-actions">
      <button type="button" class="button is-primary" @click="save"><span class="material-icons" aria-hidden="true">check</span>Save speaker settings</button>
      <div class="button-group">
        <button type="button" class="button is-accent" @click="connect"><span class="material-icons" aria-hidden="true">link</span>Connect</button>
        <button type="button" class="button" @click="disconnect"><span class="material-icons" aria-hidden="true">link_off</span>Disconnect</button>
        <button type="button" class="button" @click="test"><span class="material-icons" aria-hidden="true">play_arrow</span>Test</button>
        <button type="button" class="button is-danger" @click="stopTest"><span class="material-icons" aria-hidden="true">stop</span>Stop</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { inject, reactive, ref } from 'vue'
import api from '../api'
import SectionHeader from '../components/SectionHeader.vue'
import StatusPill from '../components/StatusPill.vue'

const toast = inject<(message: string, type?: string) => void>('toast') || (() => {})
const mac = ref('')
const disconnectAfter = ref(true)
const status = reactive<any>({ connected: false })
const settings = reactive<any>({ pre_connect_seconds: 10, connect_retry_seconds: 20, grace_seconds: 120, sink_volume_percent: 140 })

const load = async () => {
  const st = await api.get('/bluetooth/status')
  Object.assign(status, st.data)
  const response = await api.get('/settings')
  mac.value = response.data.echo_mac || ''
  settings.pre_connect_seconds = Number(response.data.pre_connect_seconds || 10)
  settings.connect_retry_seconds = Number(response.data.connect_retry_seconds || 20)
  settings.grace_seconds = Number(response.data.grace_seconds || 120)
  settings.sink_volume_percent = Number(response.data.sink_volume_percent || 140)
  disconnectAfter.value = String(response.data.disconnect_after_play || '1') === '1'
}

const save = async () => {
  await api.put('/settings', { echo_mac: mac.value, pre_connect_seconds: settings.pre_connect_seconds, connect_retry_seconds: settings.connect_retry_seconds, grace_seconds: settings.grace_seconds, sink_volume_percent: settings.sink_volume_percent, disconnect_after_play: disconnectAfter.value })
  toast('Saved Bluetooth settings', 'success')
  load()
}
const connect = async () => { try { await api.post('/bluetooth/connect'); toast('Connected', 'success'); load() } catch (error: any) { toast(error.response?.data?.detail || 'Connect failed', 'error') } }
const disconnect = async () => { try { await api.post('/bluetooth/disconnect'); toast('Disconnected', 'info'); load() } catch (error: any) { toast(error.response?.data?.detail || 'Disconnect failed', 'error') } }
const test = async () => { try { await api.post('/bluetooth/test-play', { prayer_name: 'fajr' }); toast('Test play started', 'success') } catch (error: any) { toast(error.response?.data?.detail || 'Test failed', 'error') } }
const stopTest = async () => { try { await api.post('/bluetooth/stop-test'); toast('Stopped test playback', 'info') } catch (error: any) { toast(error.response?.data?.detail || 'Stop failed', 'error') } }

load()
</script>

<style scoped>
.legacy-bluetooth-page { width: min(100%, 1120px); margin-inline: auto; }
.speaker-overview { display: flex; align-items: center; justify-content: space-between; gap: 18px; margin-bottom: 16px; }
.speaker-identity { display: flex; min-width: 0; align-items: center; gap: 16px; }
.speaker-icon { display: grid; width: 58px; height: 58px; place-items: center; border: 1px solid rgba(126,167,163,.25); border-radius: 20px 20px 20px 7px; background: var(--color-secondary-soft); color: #a9cbc7; font-size: 28px; }
.speaker-identity h2 { margin-top: 3px; font-family: var(--font-display); font-size: 1.25rem; font-weight: 700; }
.speaker-identity > div > p:last-child { color: var(--color-text-subtle); font-size: .72rem; overflow-wrap: anywhere; }
.bluetooth-grid { display: grid; grid-template-columns: repeat(2,minmax(0,1fr)); gap: 16px; }
.page-actions { display: flex; align-items: center; justify-content: space-between; gap: 16px; margin-top: 22px; }
.button-group { display: flex; flex-wrap: wrap; justify-content: flex-end; gap: 8px; }
.button .material-icons { margin-right: 7px; font-size: 18px; }
@media(max-width:760px){.speaker-overview,.page-actions{align-items:stretch;flex-direction:column}.bluetooth-grid{grid-template-columns:1fr}.button-group{display:grid;grid-template-columns:repeat(2,minmax(0,1fr))}.page-actions>.button{width:100%}}
@media(max-width:420px){.button-group{grid-template-columns:1fr}}
</style>
