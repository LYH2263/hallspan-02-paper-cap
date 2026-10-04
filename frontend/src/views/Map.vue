<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { api } from '../api'
const data = ref<any>(null)
const candidates = ref<any[]>([])
const papers = ref<any[]>([])
const violKeys = ref<Set<string>>(new Set())
const runError = ref('')
const loading = ref(false)

// A failed whole-run (primary floor) carries an empty grid; this distinguishes
// "run failed" from "hall genuinely empty".
const floorFailed = computed(() => data.value && data.value.ok === false)

async function run() {
  runError.value = ''
  loading.value = true
  try {
    data.value = await api('/seating/run?hall_id=1', { method: 'POST' })
    await loadViolations()
  } catch (e: any) {
    // 主卷保底失败：只写「主卷人数不足」一句，图不出（方案不增）
    runError.value = e?.message || '排座失败'
    // Reflect the failure envelope from latest so stats/map stay aligned.
    try { data.value = await api('/seating/latest?hall_id=1') } catch { data.value = null }
  } finally {
    loading.value = false
  }
}

async function loadViolations() {
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
  loading.value = true
  try {
    const [c, p, d] = await Promise.all([
      api('/candidates'), api('/papers'), api('/seating/latest?hall_id=1'),
    ])
    candidates.value = c; papers.value = p; data.value = d
    if (!floorFailed.value) await loadViolations()
  } catch (e: any) {
    runError.value = e?.message || '加载失败'
  } finally {
    loading.value = false
  }
})

const gridStyle = computed(() => data.value ? ({ gridTemplateColumns: `repeat(${data.value.cols}, 72px)` }) : {})
const cells = computed(() => {
  if (!data.value || floorFailed.value) return []
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

function isViol(cell: any) {
  if (cell.empty) return false
  const id = cell.candidate_id ?? cell.id
  return id != null && violKeys.value.has(String(id))
}

const paperMeta = computed(() => {
  const m = new Map<number, any>()
  for (const p of papers.value) m.set(p.id, p)
  return m
})
function paperLabel(pid: number) {
  return paperMeta.value.get(pid)?.code || ('卷' + pid)
}
const colorPalette = ['var(--hs-paper-a)', 'var(--hs-paper-b)', '#2f855a', '#6b46c1', '#b7791f']
function paperColor(pid: number) {
  const idx = papers.value.findIndex(p => p.id === pid)
  return colorPalette[(idx >= 0 ? idx : pid - 1) % colorPalette.length]
}

// 图上套卷分布：与「统计」「名册」共用同一方案的同一分解
const breakdown = computed<any[]>(() => data.value?.paper_breakdown || [])
const cappedUnplaced = computed(() =>
  (data.value?.unplaced || []).filter((u: any) => u.reason === '同卷人数已满'))
const otherUnplaced = computed(() =>
  (data.value?.unplaced || []).filter((u: any) => u.reason !== '同卷人数已满'))
function bLabel(b: any) { return b.code || paperLabel(b.paper_id) }
</script>
<template>
  <h1>考场课桌网格</h1>
  <p class="sub">课桌网格为主视图 · 左侧考生名册夹板 · 违规课桌高亮 · 套卷分布与统计同源</p>
  <button class="btn" :disabled="loading" @click="run">{{ loading ? '排座中…' : '重新排座' }}</button>

  <!-- 下限失败：仅这一句，不与「同卷人数已满」并写 -->
  <div v-if="floorFailed" class="card" style="margin-top:0.85rem;border-color:var(--hs-bad)">
    <strong style="color:var(--hs-bad)">主卷人数不足</strong>
    <div class="muted" style="margin-top:0.3rem;font-size:0.85rem">
      整场排座失败，未生成方案；辅卷不顶满充数。请调整主卷下限或名单后重新排座。
    </div>
    <table style="margin-top:0.5rem" v-if="data.floor_failures?.length">
      <thead><tr><th>主卷套</th><th>已座</th><th>下限</th></tr></thead>
      <tbody>
        <tr v-for="f in data.floor_failures" :key="f.paper_id">
          <td>{{ f.code || f.paper_id }}</td><td>{{ f.seated }}</td><td>{{ f.min_count }}</td>
        </tr>
      </tbody>
    </table>
  </div>
  <p v-else-if="runError" class="badge badge-bad" style="font-size:0.85rem;padding:0.35rem 0.6rem">{{ runError }}</p>

  <div class="hs-classroom" style="margin-top:0.85rem">
    <aside class="hs-clipboard">
      <h2>考生名册</h2>
      <div v-for="c in candidates" :key="c.id" class="hs-roster-row">
        <div>
          <div>{{ c.name }}</div>
          <div class="hs-ticket">{{ c.ticket_no }}</div>
        </div>
        <div>
          <span :style="{ color: paperColor(c.paper_id), fontWeight: 700 }">{{ c.paper_code || ('卷' + c.paper_id) }}</span>
          <span v-if="c.is_primary" class="badge badge-ok" style="margin-left:0.25rem">主</span>
        </div>
      </div>
    </aside>

    <div>
      <div class="hs-desk-stage" v-if="data && !floorFailed">
        <div class="hs-grid-board" :style="gridStyle">
          <div
            v-for="(cell,i) in cells" :key="i"
            class="hs-desk"
            :class="{ empty: cell.empty, 'hs-viol': isViol(cell) }"
          >
            <template v-if="!cell.empty">
              <span class="hs-paper-tag" :style="{ background: paperColor(cell.paper_id) }">{{ paperLabel(cell.paper_id) }}</span>
              <div>{{ cell.name }}</div>
            </template>
            <template v-else>·</template>
          </div>
        </div>
      </div>
      <div v-else-if="!floorFailed" class="muted">尚无排座方案</div>

      <!-- 套卷分布（图上）：数字取自本次方案，与统计页完全一致 -->
      <div class="card" v-if="data && !floorFailed" style="margin-top:0.85rem">
        <h2 style="font-size:0.95rem;margin:0 0 0.5rem">套卷分布</h2>
        <table>
          <thead>
            <tr><th>试卷套</th><th>名册人数</th><th>已座</th><th>未排</th><th>上限</th><th>下限</th></tr>
          </thead>
          <tbody>
            <tr v-for="b in breakdown" :key="b.paper_id">
              <td>
                <span :style="{ color: paperColor(b.paper_id), fontWeight: 700 }">{{ bLabel(b) }}</span>
                <span v-if="b.is_primary" class="badge badge-ok" style="margin-left:0.25rem">主</span>
              </td>
              <td>{{ b.total }}</td>
              <td>{{ b.seated }}</td>
              <td :style="b.unplaced ? 'color:var(--hs-bad);font-weight:700' : ''">{{ b.unplaced }}</td>
              <td>{{ b.max_count === 0 ? '不截断' : b.max_count }}</td>
              <td>{{ b.min_count === 0 ? '关闭' : b.min_count }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- 触顶未排：只写同卷人数已满，一句不并；下限失败时整页不显示该名单 -->
      <div class="card" v-if="!floorFailed && cappedUnplaced.length" style="border-color:var(--hs-paper-b)">
        <h3 style="margin:0 0 0.4rem;font-size:0.9rem">同卷人数已满（{{ cappedUnplaced.length }} 人）</h3>
        <div v-for="u in cappedUnplaced" :key="u.id" style="font-size:0.82rem">
          {{ u.name }}（{{ u.ticket_no }}）· {{ paperLabel(u.paper_id) }}
        </div>
      </div>
      <div class="card" v-if="!floorFailed && otherUnplaced.length">
        <h3 style="margin:0 0 0.4rem;font-size:0.9rem">其他未排（{{ otherUnplaced.length }} 人）</h3>
        <div v-for="u in otherUnplaced" :key="u.id" style="font-size:0.82rem">
          {{ u.name }}（{{ u.ticket_no }}）· {{ paperLabel(u.paper_id) }} · {{ u.reason }}
        </div>
      </div>
    </div>
  </div>
</template>
