<template>
  <div class="toast-container" aria-live="polite" aria-atomic="true">
    <TransitionGroup :css="false" @enter="enterToast" @leave="leaveToast">
      <div v-for="item in items" :key="item.id" class="toast" :class="`is-${item.type}`" role="status">
        <span class="toast-icon material-icons" aria-hidden="true">{{ iconFor(item.type) }}</span>
        <span class="toast-message">{{ item.message }}</span>
        <button type="button" class="toast-dismiss" aria-label="Dismiss notification" @click="$emit('dismiss', item.id)">
          <span class="material-icons" aria-hidden="true">close</span>
        </button>
      </div>
    </TransitionGroup>
  </div>
</template>

<script lang="ts">
export interface ToastItem {
  id: number
  message: string
  type: 'success' | 'info' | 'warning' | 'danger' | 'error'
}
</script>

<script setup lang="ts">
import { enterToast, leaveToast } from '../motion'

defineProps<{ items: ToastItem[] }>()
defineEmits<{ dismiss: [id: number] }>()
const iconFor = (type: ToastItem['type']) => type === 'success' ? 'check_circle' : type === 'warning' ? 'warning' : type === 'danger' || type === 'error' ? 'error' : 'info'
</script>
