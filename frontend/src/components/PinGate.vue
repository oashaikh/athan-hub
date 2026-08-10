<template>
  <div class="pin-gate">
    <div class="pin-ambient" aria-hidden="true"></div>
    <form class="pin-card" aria-labelledby="pin-title" @submit.prevent="verify">
      <div class="pin-brand" aria-hidden="true">A</div>
      <p class="section-kicker">Private dashboard</p>
      <h1 id="pin-title">Welcome to Athan Hub</h1>
      <p class="pin-intro">Enter your access PIN to manage prayer times and speaker settings.</p>
      <div class="field">
        <label class="label" for="access-pin">Access PIN</label>
        <input
          id="access-pin"
          v-model="pin"
          class="input"
          type="password"
          inputmode="numeric"
          autocomplete="current-password"
          :aria-invalid="!!error"
          aria-describedby="pin-error"
          autofocus
        />
        <p v-if="error" id="pin-error" class="field-error" role="alert">{{ error }}</p>
      </div>
      <button class="button is-primary is-fullwidth" :class="{ 'is-loading': verifying }" :disabled="verifying">
        Unlock dashboard
      </button>
      <p class="pin-host">athan.local</p>
    </form>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import api from '../api'

const emit = defineEmits<{ verified: [] }>()
const pin = ref('')
const error = ref('')
const verifying = ref(false)

const verify = async () => {
  verifying.value = true
  error.value = ''
  try {
    await api.post('/pin/verify', { pin: pin.value })
    emit('verified')
  } catch {
    error.value = 'That PIN was not recognised. Check it and try again.'
  } finally {
    verifying.value = false
  }
}
</script>

<style scoped>
.pin-gate { position: fixed; z-index: var(--z-modal); inset: 0; display: grid; min-height: 100dvh; place-items: center; overflow: auto; padding: 24px; background: #07131a; }
.pin-ambient { position: absolute; width: min(80vw, 760px); aspect-ratio: 1; border: 1px solid rgba(227,198,134,.08); border-radius: 50%; box-shadow: 0 0 0 80px rgba(255,255,255,.012), 0 0 0 160px rgba(255,255,255,.008); }
.pin-card { position: relative; width: min(100%, 430px); padding: clamp(28px, 6vw, 48px); border: 1px solid var(--color-border-strong); border-radius: var(--radius-xl); background: linear-gradient(155deg, rgba(18,37,44,.97), rgba(8,21,28,.98)); box-shadow: var(--shadow-overlay); text-align: center; }
.pin-brand { display: grid; width: 54px; height: 54px; margin: 0 auto 20px; place-items: center; border: 1px solid rgba(227,198,134,.45); border-radius: 18px 18px 18px 6px; color: var(--color-accent-strong); font-family: var(--font-display); font-size: 1.5rem; font-weight: 700; }
.pin-card h1 { margin: 8px 0 10px; font-family: var(--font-display); font-size: clamp(1.8rem, 5vw, 2.5rem); font-weight: 650; letter-spacing: -.035em; }
.pin-intro { margin: 0 auto 26px; color: var(--color-text-muted); font-size: .9rem; line-height: 1.65; }
.field { text-align: left; }
.field-error { margin-top: 8px; color: var(--color-danger-text); font-size: .78rem; }
.pin-host { margin-top: 18px; color: var(--color-text-subtle); font-size: .68rem; letter-spacing: .08em; }
</style>
