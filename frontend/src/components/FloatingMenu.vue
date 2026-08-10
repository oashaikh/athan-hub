<template>
  <div class="menu-wrap">
    <button
      ref="toggleButton"
      class="menu-toggle"
      :class="{ active: open }"
      type="button"
      aria-controls="athan-navigation"
      :aria-label="open ? 'Close navigation menu' : 'Open navigation menu'"
      :aria-expanded="open"
      @click="open = !open"
    >
      <span class="menu-toggle-lines" aria-hidden="true">
        <span></span><span></span><span></span>
      </span>
      <span class="menu-toggle-label">Menu</span>
    </button>

    <Transition :css="false" @enter="enterMenu" @leave="leaveMenu">
      <div v-if="open" class="menu-layer">
        <button class="menu-scrim" type="button" aria-label="Close navigation menu" @click="close"></button>
        <nav id="athan-navigation" class="menu-panel" aria-label="Athan Hub navigation">
          <div class="menu-brand">
            <span class="brand-mark" aria-hidden="true">A</span>
            <div>
              <p class="brand-name">Athan Hub</p>
              <p class="brand-subtitle">Prayer, quietly orchestrated</p>
            </div>
          </div>

          <router-link class="menu-link menu-link-primary" to="/" @click="close">
            <span class="material-icons" aria-hidden="true">space_dashboard</span>
            <span><strong>Dashboard</strong><small>Prayer times at a glance</small></span>
          </router-link>

          <p class="menu-heading">Settings</p>
          <div class="menu-list">
            <router-link
              v-for="item in settingsItems"
              :key="item.tab"
              class="menu-link"
              :to="`/settings?tab=${item.tab}`"
              @click="close"
            >
              <span class="material-icons" aria-hidden="true">{{ item.icon }}</span>
              <span>{{ item.label }}</span>
            </router-link>
          </div>

          <footer class="menu-footer">
            <span class="status-dot" aria-hidden="true"></span>
            <span>athan.local</span>
          </footer>
        </nav>
      </div>
    </Transition>
  </div>
</template>

<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { enterMenu, leaveMenu } from '../motion'

const route = useRoute()
const open = ref(false)
const toggleButton = ref<HTMLButtonElement | null>(null)

const settingsItems = [
  { tab: 'timetable', label: 'Timetable', icon: 'calendar_today' },
  { tab: 'bluetooth', label: 'Bluetooth & speaker', icon: 'speaker' },
  { tab: 'activity', label: 'Activity', icon: 'history' },
  { tab: 'exclusions', label: 'Exclusions', icon: 'block' },
  { tab: 'audio', label: 'Athan audio', icon: 'graphic_eq' },
  { tab: 'general', label: 'General', icon: 'tune' }
]

const close = () => {
  open.value = false
}

const onKeydown = (event: KeyboardEvent) => {
  if (event.key !== 'Escape' || !open.value) return
  close()
  nextTick(() => toggleButton.value?.focus())
}

watch(() => route.fullPath, close)
onMounted(() => window.addEventListener('keydown', onKeydown))
onBeforeUnmount(() => window.removeEventListener('keydown', onKeydown))
</script>

<style scoped>
.menu-wrap {
  position: fixed;
  z-index: var(--z-navigation);
  top: max(18px, env(safe-area-inset-top));
  right: max(clamp(16px, 3vw, 38px), env(safe-area-inset-right));
}

.menu-toggle {
  position: relative;
  z-index: 2;
  display: inline-flex;
  min-width: 104px;
  min-height: 48px;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 0 17px;
  border: 1px solid var(--color-border-strong);
  border-radius: var(--radius-pill);
  background: rgba(9, 20, 27, 0.84);
  box-shadow: var(--shadow-nav);
  color: var(--color-text);
  cursor: pointer;
  font: inherit;
  font-size: 0.78rem;
  font-weight: 750;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  backdrop-filter: blur(14px);
  transition: border-color var(--motion-fast) var(--ease-standard), background var(--motion-fast) var(--ease-standard), color var(--motion-fast) var(--ease-standard);
  touch-action: manipulation;
}

.menu-toggle:hover,
.menu-toggle.active {
  border-color: rgba(227, 198, 134, 0.64);
  background: rgba(22, 39, 45, 0.96);
  color: var(--color-accent-strong);
}

.menu-toggle-lines {
  display: grid;
  width: 18px;
  gap: 4px;
}

.menu-toggle-lines span {
  display: block;
  width: 100%;
  height: 1.5px;
  border-radius: 999px;
  background: currentColor;
  transition: transform var(--motion-fast) var(--ease-standard), opacity var(--motion-fast) var(--ease-standard);
}

.menu-toggle.active .menu-toggle-lines span:first-child { transform: translateY(5.5px) rotate(45deg); }
.menu-toggle.active .menu-toggle-lines span:nth-child(2) { opacity: 0; }
.menu-toggle.active .menu-toggle-lines span:last-child { transform: translateY(-5.5px) rotate(-45deg); }

.menu-layer {
  position: fixed;
  z-index: 1;
  inset: 0;
}

.menu-scrim {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  padding: 0;
  border: 0;
  background: rgba(2, 8, 12, 0.5);
  cursor: default;
  backdrop-filter: blur(3px);
}

.menu-panel {
  position: absolute;
  top: max(76px, calc(env(safe-area-inset-top) + 62px));
  right: max(clamp(16px, 3vw, 38px), env(safe-area-inset-right));
  width: min(356px, calc(100vw - 28px));
  max-height: calc(100dvh - 94px);
  overflow-y: auto;
  padding: 18px;
  border: 1px solid var(--color-border-strong);
  border-radius: var(--radius-xl);
  background: linear-gradient(155deg, rgba(16, 32, 39, 0.99), rgba(7, 18, 25, 0.99));
  box-shadow: var(--shadow-overlay);
}

.menu-brand {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 4px 4px 18px;
  border-bottom: 1px solid var(--color-border);
}

.brand-mark {
  display: grid;
  width: 42px;
  height: 42px;
  flex: 0 0 auto;
  place-items: center;
  border: 1px solid rgba(227, 198, 134, 0.48);
  border-radius: 14px 14px 14px 5px;
  background: linear-gradient(145deg, rgba(227, 198, 134, 0.2), rgba(227, 198, 134, 0.06));
  color: var(--color-accent-strong);
  font-family: var(--font-display);
  font-size: 1.2rem;
  font-weight: 700;
}

.brand-name { color: var(--color-text); font-weight: 800; }
.brand-subtitle { margin-top: 1px; color: var(--color-text-muted); font-size: 0.72rem; }

.menu-heading {
  margin: 18px 10px 8px;
  color: var(--color-text-subtle);
  font-size: 0.65rem;
  font-weight: 800;
  letter-spacing: 0.18em;
  text-transform: uppercase;
}

.menu-list { display: grid; gap: 4px; }

.menu-link {
  display: flex;
  min-height: 48px;
  align-items: center;
  gap: 12px;
  padding: 0 12px;
  border: 1px solid transparent;
  border-radius: var(--radius-md);
  color: var(--color-text-muted);
  font-size: 0.88rem;
  font-weight: 700;
  text-decoration: none;
  transition: border-color var(--motion-fast) var(--ease-standard), background var(--motion-fast) var(--ease-standard), color var(--motion-fast) var(--ease-standard);
}

.menu-link:hover {
  border-color: var(--color-border);
  background: var(--color-surface-hover);
  color: var(--color-text);
}

.menu-link.router-link-exact-active {
  border-color: rgba(227, 198, 134, 0.26);
  background: var(--color-accent-soft);
  color: var(--color-accent-strong);
}

.menu-link .material-icons { color: var(--color-accent); font-size: var(--icon-md); }

.menu-link-primary {
  min-height: 70px;
  margin-top: 14px;
  background: rgba(255, 255, 255, 0.025);
}

.menu-link-primary > span:last-child { display: grid; gap: 2px; }
.menu-link-primary strong { color: inherit !important; }
.menu-link-primary small { color: var(--color-text-subtle); font-size: 0.7rem; font-weight: 500; }

.menu-footer {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 16px;
  padding: 14px 8px 2px;
  border-top: 1px solid var(--color-border);
  color: var(--color-text-subtle);
  font-size: 0.72rem;
  font-weight: 650;
}

.status-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--color-success);
  box-shadow: 0 0 0 4px rgba(94, 189, 154, 0.1);
}

@media (max-width: 560px) {
  .menu-wrap { top: max(12px, env(safe-area-inset-top)); right: max(12px, env(safe-area-inset-right)); }
  .menu-toggle { min-width: 48px; width: 48px; padding: 0; }
  .menu-toggle-label { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); }
  .menu-panel { top: max(70px, calc(env(safe-area-inset-top) + 58px)); right: max(12px, env(safe-area-inset-right)); }
}
</style>
