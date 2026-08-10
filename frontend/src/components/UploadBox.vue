<template>
  <label class="upload-box" :class="{ 'is-dragging': dragging }" @dragenter.prevent="dragging = true" @dragover.prevent @dragleave.prevent="dragging = false" @drop.prevent="drop">
    <span class="upload-icon material-icons" aria-hidden="true">drive_folder_upload</span>
    <span class="upload-copy"><strong>{{ label }}</strong><small>Choose a file or drag it here</small></span>
    <span class="upload-action">Browse</span>
    <input class="upload-input" type="file" :accept="accept" @change="change" />
  </label>
</template>

<script setup lang="ts">
import { ref } from 'vue'

withDefaults(defineProps<{ label?: string; accept?: string }>(), { label: 'Choose a file', accept: '' })
const emit = defineEmits<{ file: [file: File] }>()
const dragging = ref(false)
const change = (event: Event) => {
  const file = (event.target as HTMLInputElement).files?.[0]
  if (file) emit('file', file)
}
const drop = (event: DragEvent) => {
  dragging.value = false
  const file = event.dataTransfer?.files?.[0]
  if (file) emit('file', file)
}
</script>
