<template>
  <section class="reward-summary" aria-label="Your rewards">
    <div><span class="material-icons">star</span><strong>{{ rewards?.stars || 0 }}</strong><small>stars</small></div>
    <div><span class="material-icons">local_fire_department</span><strong>{{ rewards?.streak || 0 }}</strong><small>day streak</small></div>
    <div><span class="material-icons">workspace_premium</span><strong>{{ rewards?.badges?.length || 0 }}</strong><small>badges</small></div>
    <details v-if="leaderboard?.enabled" class="leaderboard-popover"><summary>Weekly board</summary><ol><li v-for="entry in leaderboard.entries" :key="entry.profile_id"><span>{{ entry.name }}</span><strong>{{ entry.stars }} ★</strong></li></ol></details>
  </section>
</template>
<script setup lang="ts">
defineProps<{ rewards: any; leaderboard?: any }>()
</script>
