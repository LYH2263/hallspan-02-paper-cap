<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { api } from '../api'
const rows = ref<any[]>([])
onMounted(async () => { rows.value = await api('/candidates') })
const perPaper = computed(() => {
  // 名单各套人数: 与排座图/统计同源对齐 —— 各套报名 = 已座 + 未排
  const counts = new Map<number, number>()
  for (const r of rows.value) counts.set(r.paper_id, (counts.get(r.paper_id) || 0) + 1)
  return [...counts.entries()].sort((a, b) => a[0] - b[0]).map(([pid, n]) => ({ pid, n }))
})
</script>
<template>
  <h1>考生名册</h1>
  <p class="sub">夹板名册样式 · 各套人数：{{ perPaper.map(p => `卷${p.pid} × ${p.n}`).join(' · ') }}</p>
  <div class="hs-clipboard" style="max-width:420px">
    <h2>考生名册 · Clipboard</h2>
    <div v-for="r in rows" :key="r.id ?? JSON.stringify(r)" class="hs-roster-row">
      <div>
        <div>{{ r.name }}</div>
        <div class="hs-ticket">{{ r.ticket_no }}</div>
      </div>
      <div>卷{{ r.paper_id }} · 室{{ r.hall_id }}</div>
    </div>
  </div>
</template>
