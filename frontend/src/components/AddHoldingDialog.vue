<script setup lang="ts">
import { ref } from 'vue'
import { api, type AssetType } from '../api'
import { todayISO } from '../format'
import BaseModal from './BaseModal.vue'

const emit = defineEmits<{ close: []; added: [symbol: string] }>()

const symbol = ref('')
const name = ref('')
const shares = ref<number | null>(null)
const day = ref(todayISO())
const avgCost = ref<number | null>(null)
const assetType = ref<Exclude<AssetType, 'cash'> | ''>('')
const busy = ref(false)
const error = ref('')

async function submit() {
  error.value = ''
  busy.value = true
  try {
    const r = await api.addHolding({
      symbol: symbol.value,
      name: name.value || undefined,
      shares: shares.value ?? 0,
      date: day.value,
      avg_cost: avgCost.value,
      asset_type: assetType.value || null,
    })
    emit('added', r.symbol)
  } catch (e) {
    error.value = (e as Error).message
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <BaseModal title="新增標的" @close="emit('close')">
    <form id="add-holding" class="grid gap-3" @submit.prevent="submit">
      <label class="grid gap-1">
        <span class="label">代號</span>
        <input v-model="symbol" required class="input" placeholder="0050、00687B、VOO、SSO" autofocus />
        <span class="text-xs text-ink-400">台股只要打數字，系統會自動判斷上市（.TW）或上櫃（.TWO）</span>
      </label>
      <label class="grid gap-1">
        <span class="label">顯示名稱（選填，留空用 Yahoo 名稱）</span>
        <input v-model="name" class="input" placeholder="元大台灣50" />
      </label>
      <div class="grid grid-cols-2 gap-3">
        <label class="grid gap-1">
          <span class="label">目前股數</span>
          <input v-model.number="shares" type="number" step="any" min="0" class="input num" placeholder="台股 1 張 = 1000" />
        </label>
        <label class="grid gap-1">
          <span class="label">從哪天開始持有</span>
          <input v-model="day" type="date" class="input" :max="todayISO()" />
        </label>
        <label class="grid gap-1">
          <span class="label">平均成本（選填）</span>
          <input v-model.number="avgCost" type="number" step="any" min="0" class="input num" />
        </label>
        <label class="grid gap-1">
          <span class="label">類型</span>
          <select v-model="assetType" class="input">
            <option value="">自動判斷</option>
            <option value="equity">股票</option>
            <option value="leveraged">槓桿 ETF</option>
            <option value="bond">債券</option>
          </select>
        </label>
      </div>
      <p v-if="error" class="rounded-lg bg-amber-950/50 px-3 py-2 text-sm text-warm" role="alert">{{ error }}</p>
    </form>
    <template #footer>
      <button class="btn-ghost" @click="emit('close')">取消</button>
      <button class="btn-primary" form="add-holding" type="submit" :disabled="busy">{{ busy ? '查詢 Yahoo 中…' : '新增' }}</button>
    </template>
  </BaseModal>
</template>
