<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api } from '../api'
const s = ref<any>({})

async function load() {
  s.value = await api('/seating/stats?hall_id=1')
}
onMounted(load)
</script>
<template>
  <h1>统计</h1>
  <p class="sub">排座占用、未排与各套分布 · 与名册、排座图同源于一份方案</p>

  <div v-if="s.ok === false" class="card" style="border-color:var(--hs-bad)">
    <strong style="color:var(--hs-bad);font-size:1.05rem">主卷人数不足</strong>
    <div class="muted" style="margin-top:0.3rem;font-size:0.85rem">
      整场排座失败，未生成方案；不以辅卷顶满格子充数。请调整主卷下限或名单后重新排座。
    </div>
    <table style="margin-top:0.5rem" v-if="s.floor_failures?.length">
      <thead><tr><th>主卷套</th><th>已座</th><th>下限</th></tr></thead>
      <tbody>
        <tr v-for="f in s.floor_failures" :key="f.paper_id">
          <td>{{ f.code || f.paper_id }}</td><td>{{ f.seated }}</td><td>{{ f.min_count }}</td>
        </tr>
      </tbody>
    </table>
  </div>

  <template v-else>
    <div class="card" style="display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:1rem">
      <div><div class="muted">已排座</div><div class="stat">{{ s.seated }}</div></div>
      <div><div class="muted">未排上</div><div class="stat" :style="s.unplaced ? 'color:var(--hs-bad)' : ''">{{ s.unplaced }}</div></div>
      <div><div class="muted">违规数</div><div class="stat">{{ s.violations }}</div></div>
      <div><div class="muted">座位容量</div><div class="stat">{{ s.capacity }}</div></div>
    </div>

    <div class="card">
      <h3 style="margin:0 0 0.5rem;font-size:0.95rem">各试卷套人数（与排座图套卷分布一致）</h3>
      <table>
        <thead>
          <tr><th>试卷套</th><th>名册人数</th><th>已座</th><th>未排</th><th>上限</th><th>下限</th></tr>
        </thead>
        <tbody>
          <tr v-for="b in s.paper_breakdown || []" :key="b.paper_id">
            <td>
              {{ b.code || ('卷' + b.paper_id) }}
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
      <p class="muted" style="font-size:0.78rem;margin-bottom:0">
        校验：每行 名册人数 = 已座 + 未排；未排上合计 {{ s.unplaced }} 与违规页未排名单一致。
      </p>
    </div>
  </template>
</template>
