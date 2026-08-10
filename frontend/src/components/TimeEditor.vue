<template>
  <div class="time-editor" :class="{ 'is-disabled': !enabled }">
    <div class="time-editor-heading">
      <label class="time-editor-label" :for="timeId">{{ titleCase(prayer) }}</label>
      <label class="switch-control">
        <input type="checkbox" :checked="enabled" @change="$emit('update:enabled', ($event.target as HTMLInputElement).checked)" />
        <span class="switch-track" aria-hidden="true"><span></span></span>
        <span class="sr-only">Enable {{ prayer }}</span>
      </label>
    </div>
    <input :id="timeId" class="input" type="time" :value="value" :disabled="!enabled" @input="$emit('update:time', ($event.target as HTMLInputElement).value)" />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{ prayer: string; value?: string | null; enabled?: boolean }>()
defineEmits<{
  'update:time': [value: string]
  'update:enabled': [value: boolean]
}>()
const timeId = computed(() => `manual-time-${props.prayer}`)
const titleCase = (value: string) => value.charAt(0).toUpperCase() + value.slice(1)
</script>
