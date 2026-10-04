<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { api } from '../api'
const data = ref<any>(null)
const candidates = ref<any[]>([])
const papers = ref<any[]>([])
const violKeys = ref<Set<string>>(new Set())
const error = ref('')
async function run() {
  error.value = ''
  try {
    data.value = await api('/seating/run?hall_id=1', { method: 'POST' })
  } catch (e: any) {
    data.value = null // 整场失败不出图, 不留旧图
    error.value = e.message // 主卷人数不足等整场失败
    return
  }
  try {
    const v = await api('/seating/violations?hall_id=1')
    const keys = new Set<string>()
    for (const x of v.violations || []) {
      if (x.a_id != null) keys.add(String(x.a_id))
      if (x.b_id != null) keys.add(String(x.b_id))
    }
    violKeys.value = keys
  } catch { violKeys.value = new Set() }
}
onMounted(async () => {
  candidates.value = await api('/candidates')
  papers.value = await api('/papers')
  await run()
})
const gridStyle = computed(() => data.value ? ({ gridTemplateColumns: `repeat(${data.value.cols}, 72px)` }) : {})
const cells = computed(() => {
  if (!data.value) return []
  const map = new Map<string, any>()
  for (const a of data.value.assignments || []) map.set(a.row + ',' + a.col, a)
  const out: any[] = []
  for (let r = 0; r < data.value.rows; r++) {
    for (let c = 0; c < data.value.cols; c++) {
      out.push(map.get(r + ',' + c) || { empty: true, row: r, col: c })
    }
  }
  return out
})
const paperDist = computed(() => {
  // 排座图套卷分布: 与统计页同源, 均取最新方案的 stats.per_paper
  const per = data.value?.stats?.per_paper || {}
  return papers.value
    .filter(p => per[String(p.id)])
    .map(p => ({ code: p.code, seated: per[String(p.id)].seated, unplaced: per[String(p.id)].unplaced }))
})
const unplacedList = computed(() => data.value?.unplaced || [])
function isViol(cell: any) {
  if (cell.empty) return false
  const id = cell.candidate_id ?? cell.id
  return id != null && violKeys.value.has(String(id))
}
function paperClass(pid: number) {
  return pid % 2 === 0 ? 'b' : 'a'
}
</script>
<template>
  <h1>考场课桌网格</h1>
  <p class="sub">课桌网格为主视图 · 左侧考生名册夹板 · 违规课桌高亮</p>
  <button class="btn" @click="run">重新排座</button>
  <span v-if="paperDist.length" class="muted" style="margin-left:0.75rem;font-size:0.85rem">
    套卷分布：<span v-for="d in paperDist" :key="d.code" style="margin-right:0.6rem">{{ d.code }} {{ d.seated }} 人<template v-if="d.unplaced">（未排 {{ d.unplaced }}）</template></span>
  </span>
  <p v-if="error" style="color:#a33">{{ error }}</p>
  <div class="hs-classroom" style="margin-top:0.85rem">
    <aside class="hs-clipboard">
      <h2>考生名册</h2>
      <div v-for="c in candidates" :key="c.id" class="hs-roster-row">
        <div>
          <div>{{ c.name }}</div>
          <div class="hs-ticket">{{ c.ticket_no }}</div>
        </div>
        <div>卷{{ c.paper_id }}</div>
      </div>
    </aside>
    <div class="hs-desk-stage" v-if="data">
      <div class="hs-grid-board" :style="gridStyle">
        <div
          v-for="(cell,i) in cells" :key="i"
          class="hs-desk"
          :class="{ empty: cell.empty, 'hs-viol': isViol(cell) }"
        >
          <template v-if="!cell.empty">
            <span class="hs-paper-tag" :class="paperClass(cell.paper_id)">卷{{ cell.paper_id }}</span>
            <div>{{ cell.name }}</div>
          </template>
          <template v-else>·</template>
        </div>
      </div>
    </div>
  </div>
  <div class="card" v-if="unplacedList.length" style="margin-top:0.85rem">
    <h3>未排上</h3>
    <div v-for="u in unplacedList" :key="u.id">{{ u.name }}（{{ u.ticket_no }}）· 卷{{ u.paper_id }} · {{ u.reason }}</div>
  </div>
</template>
