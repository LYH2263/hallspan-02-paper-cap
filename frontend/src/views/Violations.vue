<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api } from '../api'
const viols = ref<any[]>([])
const unplaced = ref<any[]>([])
const failed = ref(false)
const message = ref('')
onMounted(async () => {
  const res = await api('/seating/violations?hall_id=1')
  viols.value = res.violations
  unplaced.value = res.unplaced
  failed.value = res.ok === false
  message.value = res.message || ''
})
</script>
<template>
  <h1>违规</h1>
  <p class="sub">间距不足或同试卷四邻相邻</p>

  <div v-if="failed" class="card" style="border-color:var(--hs-bad)">
    <strong style="color:var(--hs-bad)">主卷人数不足</strong>
    <div class="muted" style="font-size:0.85rem;margin-top:0.3rem">整场排座失败，未生成方案。</div>
  </div>

  <div class="card">
    <table>
      <thead><tr><th>类型</th><th>考生A</th><th>考生B</th><th>说明</th></tr></thead>
      <tbody>
        <tr v-for="(v,i) in viols" :key="i">
          <td>{{ v.kind }}</td><td>{{ v.a_id }}</td><td>{{ v.b_id }}</td><td>{{ v.detail }}</td>
        </tr>
      </tbody>
    </table>
    <p v-if="!viols.length" class="muted">无违规</p>
  </div>

  <div class="card" v-if="!failed && unplaced.length">
    <h3>未排上</h3>
    <table>
      <thead><tr><th>考生</th><th>准考证</th><th>原因</th></tr></thead>
      <tbody>
        <tr v-for="u in unplaced" :key="u.id">
          <td>{{ u.name }}</td><td>{{ u.ticket_no }}</td>
          <td :style="u.reason === '同卷人数已满' ? 'color:var(--hs-paper-b);font-weight:700' : ''">{{ u.reason }}</td>
        </tr>
      </tbody>
    </table>
    <p class="muted" style="font-size:0.78rem;margin-bottom:0">
      「同卷人数已满」为该套触顶（即使有空位也不再塞同套）；不与其他原因并写。
    </p>
  </div>
</template>
