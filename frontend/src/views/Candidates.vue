<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api } from '../api'
const rows = ref<any[]>([])
const stats = ref<any>(null)
onMounted(async () => {
  // 名册各套人数与排座图套卷分布、统计未排取同一方案（stats 即 latest 方案）
  const [c, s] = await Promise.all([
    api('/candidates'),
    api('/seating/stats?hall_id=1').catch(() => null),
  ])
  rows.value = c
  stats.value = s
})
</script>
<template>
  <h1>考生名册</h1>
  <p class="sub">夹板名册样式 · 各套人数与排座图、统计同源</p>

  <div class="card" v-if="stats && stats.ok !== false">
    <h3 style="margin:0 0 0.5rem;font-size:0.95rem">名单各套人数</h3>
    <table>
      <thead><tr><th>试卷套</th><th>名册人数</th><th>已座</th><th>未排</th></tr></thead>
      <tbody>
        <tr v-for="b in stats.paper_breakdown || []" :key="b.paper_id">
          <td>
            {{ b.code || ('卷' + b.paper_id) }}
            <span v-if="b.is_primary" class="badge badge-ok" style="margin-left:0.25rem">主</span>
          </td>
          <td>{{ b.total }}</td>
          <td>{{ b.seated }}</td>
          <td :style="b.unplaced ? 'color:var(--hs-bad);font-weight:700' : ''">{{ b.unplaced }}</td>
        </tr>
      </tbody>
    </table>
    <p class="muted" style="font-size:0.78rem;margin-bottom:0">
      合计名册 {{ stats.seated + stats.unplaced }} 人 = 已座 {{ stats.seated }} + 未排 {{ stats.unplaced }}
    </p>
  </div>
  <div class="card" v-else-if="stats && stats.ok === false" style="border-color:var(--hs-bad)">
    <strong style="color:var(--hs-bad)">主卷人数不足</strong>
    <div class="muted" style="font-size:0.85rem;margin-top:0.3rem">整场排座失败，未生成方案。</div>
  </div>

  <div class="hs-clipboard" style="max-width:420px">
    <h2>考生名册 · Clipboard</h2>
    <div v-for="r in rows" :key="r.id ?? JSON.stringify(r)" class="hs-roster-row">
      <div>
        <div>{{ r.name }}</div>
        <div class="hs-ticket">{{ r.ticket_no }}</div>
      </div>
      <div>
        {{ r.paper_code || ('卷' + r.paper_id) }}<span v-if="r.is_primary" class="badge badge-ok" style="margin-left:0.2rem">主</span>
        <span class="muted"> · 室{{ r.hall_id }}</span>
      </div>
    </div>
  </div>
</template>
