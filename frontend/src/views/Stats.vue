<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { api } from '../api'
const s = ref<any>({})
const papers = ref<any[]>([])
const error = ref('')
onMounted(async () => {
  try {
    s.value = await api('/seating/stats?hall_id=1')
    papers.value = await api('/papers')
  } catch (e: any) { error.value = e.message }
})
const perPaper = computed(() => {
  // 与排座图同源: 同一份方案的各套已座/未排
  const per = s.value.per_paper || {}
  return papers.value
    .filter(p => per[String(p.id)])
    .map(p => ({ code: p.code, title: p.title, ...per[String(p.id)] }))
})
</script>
<template>
  <h1>统计</h1>
  <p class="sub">排座占用与违规汇总</p>
  <p v-if="error" style="color:#a33">{{ error }}</p>
  <div class="card" style="display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:1rem">
    <div><div class="muted">已排座</div><div class="stat">{{ s.seated }}</div></div>
    <div><div class="muted">未排上</div><div class="stat">{{ s.unplaced }}</div></div>
    <div><div class="muted">违规数</div><div class="stat">{{ s.violations }}</div></div>
    <div><div class="muted">座位容量</div><div class="stat">{{ s.capacity }}</div></div>
  </div>
  <div class="card" v-if="perPaper.length">
    <h3>各套人数</h3>
    <table>
      <thead><tr><th>试卷套</th><th>名称</th><th>已座</th><th>未排</th></tr></thead>
      <tbody>
        <tr v-for="p in perPaper" :key="p.code">
          <td>{{ p.code }}</td><td>{{ p.title }}</td><td>{{ p.seated }}</td><td>{{ p.unplaced }}</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
