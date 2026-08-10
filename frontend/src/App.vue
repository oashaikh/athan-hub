<template>
  <div class="app-root" :class="{ 'is-locked': showPinGate }">
    <a class="skip-link" href="#main-content">Skip to main content</a>
    <div class="app-ambient" aria-hidden="true"></div>
    <FloatingMenu />

    <main
      v-if="!showPinGate"
      id="main-content"
      ref="mainContent"
      class="app-shell"
      :class="{ 'is-dashboard': isDashboard }"
      tabindex="-1"
    >
      <router-view v-slot="{ Component, route: activeRoute }">
        <Transition mode="out-in" :css="false" @enter="enterRoute" @leave="leaveRoute" @after-enter="focusMain">
          <component
            :is="Component"
            :key="String(activeRoute.name)"
            @toast="pushToast"
          />
        </Transition>
      </router-view>
    </main>

    <PinGate v-if="showPinGate" @verified="onPinVerified" />
    <Toasts :items="toasts" @dismiss="removeToast" />
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, provide, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import api from './api'
import FloatingMenu from './components/FloatingMenu.vue'
import PinGate from './components/PinGate.vue'
import Toasts, { ToastItem } from './components/Toasts.vue'
import { enterRoute, leaveRoute } from './motion'

const route = useRoute()
const mainContent = ref<HTMLElement | null>(null)
const toasts = reactive<ToastItem[]>([])
let idCounter = 1
const isDashboard = computed(() => route.name === 'dashboard')
const pinRequired = ref(false)
const pinVerified = ref(true)
const showPinGate = computed(() => pinRequired.value && !pinVerified.value)

const pushToast = (message: string, type: ToastItem['type'] = 'success') => {
  const id = idCounter++
  toasts.push({ id, message, type })
  window.setTimeout(() => removeToast(id), 3500)
}

const removeToast = (id: number) => {
  const idx = toasts.findIndex(toast => toast.id === id)
  if (idx >= 0) toasts.splice(idx, 1)
}

provide('toast', pushToast)

const loadPinStatus = async () => {
  try {
    const res = await api.get('/pin/status')
    pinRequired.value = !!res.data.required
    pinVerified.value = !res.data.required || !!res.data.verified
  } catch {
    pinRequired.value = false
    pinVerified.value = true
  }
}

const onPinVerified = async () => {
  pinVerified.value = true
  await loadPinStatus()
}

const onPinRequired = () => {
  pinRequired.value = true
  pinVerified.value = false
}

const focusMain = () => {
  mainContent.value?.focus({ preventScroll: true })
}

onMounted(() => {
  loadPinStatus()
  window.addEventListener('athan-pin-required', onPinRequired as EventListener)
})

onBeforeUnmount(() => {
  window.removeEventListener('athan-pin-required', onPinRequired as EventListener)
})
</script>

<style scoped>
.app-root {
  position: relative;
  min-height: 100vh;
  min-height: 100dvh;
  isolation: isolate;
}

.app-root.is-locked {
  height: 100vh;
  overflow: hidden;
}

.app-ambient {
  position: fixed;
  z-index: var(--z-background);
  inset: 0;
  overflow: hidden;
  pointer-events: none;
}

.app-ambient::before,
.app-ambient::after {
  position: absolute;
  width: min(64vw, 860px);
  aspect-ratio: 1;
  border-radius: 50%;
  content: '';
  filter: blur(1px);
  opacity: 0.2;
}

.app-ambient::before {
  top: -42%;
  left: -20%;
  background: radial-gradient(circle, rgba(125, 158, 154, 0.24), transparent 68%);
}

.app-ambient::after {
  right: -28%;
  bottom: -48%;
  background: radial-gradient(circle, rgba(205, 167, 93, 0.2), transparent 68%);
}

.app-shell {
  position: relative;
  z-index: var(--z-content);
  width: min(100%, 1480px);
  min-height: 100vh;
  min-height: 100dvh;
  margin-inline: auto;
  padding: clamp(84px, 9vw, 112px) clamp(16px, 4vw, 64px) clamp(40px, 6vw, 72px);
  outline: none;
}

.app-shell.is-dashboard {
  width: 100%;
  max-width: none;
  padding: 0;
}

@media (max-width: 768px) {
  .app-shell {
    padding: 78px 14px 36px;
  }
}
</style>
