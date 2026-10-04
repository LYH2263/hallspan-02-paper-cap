<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api } from '../api'
const rows = ref<any[]>([])
const msg = ref('')
const err = ref('')
async function load() { rows.value = await api('/papers') }
async function save(r: any) {
  msg.value = ''; err.value = ''
  try {
    await api(`/papers/${r.id}`, {
      method: 'PUT',
      body: JSON.stringify({ is_main: !!r.is_main, max_seated: Number(r.max_seated), min_seated: Number(r.min_seated) }),
    })
    msg.value = `已保存 ${r.code}，重新排座后按新上下限出图`
    await load()
  } catch (e: any) {
    err.value = `保存失败：${e.message}`
    await load() // 拒绝保存后回退显示, 不落库的值不允许留在界面上
  }
}
onMounted(load)
</script>
<template>
  <h1>试卷套</h1>
  <p class="sub">顶部纸套标签对应的试卷版本 · 上限 0 不截断 · 下限 0 关闭保底 · 主卷低于下限整场失败</p>
  <div class="hs-tabs" style="margin-bottom:1rem;background:transparent">
    <span
      v-for="(r,i) in rows" :key="r.id ?? JSON.stringify(r)"
      class="hs-tabs"
      style="display:inline-block"
    >
      <span
        style="display:inline-block;padding:0.45rem 0.9rem;background:var(--hs-clip);border:1px solid #b0a890;border-radius:6px 6px 0 0;margin-right:0.25rem;font-family:Segoe UI,PingFang SC,sans-serif;font-size:0.85rem"
      >{{ r.code }} · {{ r.title }}<template v-if="r.is_main"> · 主卷</template></span>
    </span>
  </div>
  <p v-if="msg" class="muted">{{ msg }}</p>
  <p v-if="err" style="color:#a33">{{ err }}</p>
  <div class="card">
    <table>
      <thead><tr><th>编码</th><th>名称</th><th>主卷</th><th>人数上限</th><th>主卷下限</th><th></th></tr></thead>
      <tbody>
        <tr v-for="r in rows" :key="r.id ?? JSON.stringify(r)">
          <td>{{ r.code }}</td>
          <td>{{ r.title }}</td>
          <td><input type="radio" name="main-paper" :checked="r.is_main" @change="r.is_main = true; save(r)" /></td>
          <td><input v-model.number="r.max_seated" type="number" min="0" style="width:5rem" /></td>
          <td><input v-model.number="r.min_seated" type="number" min="0" style="width:5rem" :disabled="!r.is_main" /></td>
          <td><button class="btn" @click="save(r)">保存</button></td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
