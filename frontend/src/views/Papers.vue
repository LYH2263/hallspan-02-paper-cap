<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api } from '../api'
const rows = ref<any[]>([])
const drafts = ref<Record<number, { max_count: string; min_count: string; is_primary: boolean }>>({})
const saving = ref<Set<number>>(new Set())
const error = ref('')
const okMsg = ref('')

async function load() {
  rows.value = await api('/papers')
  for (const r of rows.value) {
    drafts.value[r.id] = {
      max_count: String(r.max_count ?? 0),
      min_count: String(r.min_count ?? 0),
      is_primary: !!r.is_primary,
    }
  }
}
onMounted(load)

async function save(r: any) {
  error.value = ''; okMsg.value = ''
  const d = drafts.value[r.id]
  const max_count = Number(d.max_count)
  const min_count = Number(d.min_count)
  if (!Number.isInteger(max_count) || !Number.isInteger(min_count)) {
    error.value = '上下限必须为整数'
    return
  }
  saving.value.add(r.id)
  try {
    await api(`/papers/${r.id}`, {
      method: 'PUT',
      body: JSON.stringify({ max_count, min_count, is_primary: d.is_primary }),
    })
    okMsg.value = `已保存 ${r.code}，旧排座图已作废，请重新排座`
    await load()
  } catch (e: any) {
    // 负值等 400：后端拒绝保存，输入回退到现值（三处不动）
    error.value = e?.message || '保存失败'
    await load()
  } finally {
    saving.value.delete(r.id)
  }
}
</script>
<template>
  <h1>试卷套</h1>
  <p class="sub">各试卷套的人数上限与主卷保底 · 上限 0 表示不截断，下限 0 表示关闭保底；下限仅对主卷套生效</p>
  <p v-if="error" class="badge badge-bad" style="font-size:0.85rem;padding:0.35rem 0.6rem">{{ error }}</p>
  <p v-if="okMsg" class="badge badge-ok" style="font-size:0.85rem;padding:0.35rem 0.6rem">{{ okMsg }}</p>
  <div class="card">
    <table>
      <thead>
        <tr><th>编码</th><th>名称</th><th>主卷</th><th>人数上限</th><th>人数下限</th><th>名册人数</th><th></th></tr>
      </thead>
      <tbody>
        <tr v-for="r in rows" :key="r.id">
          <td>{{ r.code }}</td>
          <td>{{ r.title }}</td>
          <td><input type="checkbox" v-model="drafts[r.id].is_primary" /></td>
          <td><input style="width:5.5rem" v-model="drafts[r.id].max_count" /></td>
          <td><input style="width:5.5rem" v-model="drafts[r.id].min_count" /></td>
          <td>{{ r.candidate_count }}</td>
          <td>
            <button class="btn" :disabled="saving.has(r.id)" @click="save(r)">
              {{ saving.has(r.id) ? '保存中' : '保存' }}
            </button>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
  <p class="muted" style="font-size:0.8rem">
    某套已达上限后，即使考场仍有空位也不再排入该套（未排原因：同卷人数已满）；
    主卷套已座人数低于下限时整场排座失败，不以辅卷顶满格子充数。
  </p>
</template>
