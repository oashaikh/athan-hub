<template>
  <div class="prayer-table-wrap">
    <table class="table is-fullwidth prayer-table">
      <thead><tr><th scope="col">Prayer</th><th scope="col">Time</th><th scope="col">Source</th></tr></thead>
      <tbody>
        <tr v-for="row in rows" :key="row.prayer" :class="{ 'is-adjusted': row.source === 'manual' || row.source === 'override' }">
          <th scope="row"><span class="prayer-name">{{ titleCase(row.prayer) }}</span></th>
          <td><time class="table-time" :datetime="row.effective || undefined">{{ row.effective || '—' }}</time></td>
          <td><span class="source-label">{{ sourceLabel(row.source) }}</span></td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{ data?: any }>()
const prayerNames = ['fajr', 'shurooq', 'dhuhr', 'asr', 'maghrib', 'isha']
const rows = computed(() => prayerNames.map(prayer => {
  const effective = props.data?.prayers?.[prayer]?.effective
  return { prayer, effective, source: effective ? (props.data?.prayers?.[prayer]?.source || 'n/a') : '—' }
}))
const titleCase = (value: string) => value.charAt(0).toUpperCase() + value.slice(1)
const sourceLabel = (value: string) => value === 'csv' ? 'Timetable' : titleCase(value)
</script>
