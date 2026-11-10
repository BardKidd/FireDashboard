<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { api, type AssetType, type Position, type SplitRow } from '../api'
import BaseModal from './BaseModal.vue'

const props = defineProps<{ position: Position }>()
const emit = defineEmits<{ close: []; changed: [] }>()

const isCash = computed(() => props.position.market === 'CASH')
const name = ref(props.position.name)
const assetType = ref<AssetType>(props.position.asset_type)
const beta = ref(props.position.stress_beta)
const avgCost = ref<number | null>(props.position.avg_cost)
const targetShares = ref<number | null>(props.position.target_shares)
const busy = ref(false)
const error = ref('')

const splits = ref<SplitRow[]>([])
const splitDate = ref('')
const splitRatio = ref<number | null>(null)

onMounted(async () => {
  if (!isCash.value) splits.value = (await api.splits()).filter((s) => s.symbol === props.position.symbol)
})

async function save() {
  busy.value = true
  error.value = ''
  try {
    await api.patchHolding(props.position.symbol, {
      name: name.value,
      stress_beta: beta.value,
      ...(isCash.value ? {} : { asset_type: assetType.value, avg_cost: avgCost.value, target_shares: targetShares.value }),
    })
    emit('changed')
    emit('close')
  } catch (e) {
    error.value = (e as Error).message
  } finally {
    busy.value = false
  }
}

async function archive() {
  const msg = props.position.archived ? '要恢復這檔標的嗎？' : '封存後不再顯示，也不再抓價，但歷史紀錄會保留。確定封存？'
  if (!confirm(msg)) return
  try {
    if (props.position.archived) await api.patchHolding(props.position.symbol, { archived: false })
    else await api.deleteHolding(props.position.symbol)
    emit('changed')
    emit('close')
  } catch (e) {
    error.value = (e as Error).message
  }
}

async function addSplit() {
  if (!splitDate.value || !splitRatio.value) return
  try {
    await api.addSplit({ symbol: props.position.symbol, date: splitDate.value, ratio: splitRatio.value })
    splits.value = (await api.splits()).filter((s) => s.symbol === props.position.symbol)
    splitDate.value = ''
    splitRatio.value = null
    emit('changed')
  } catch (e) {
    error.value = (e as Error).message
  }
}
</script>

<template>
  <BaseModal :title="(isCash ? position.name : position.symbol) + '・設定'" @close="emit('close')">
    <form id="edit-holding" class="grid gap-3" @submit.prevent="save">
      <label class="grid gap-1">
        <span class="label">顯示名稱</span>
        <input v-model="name" class="input" />
      </label>
      <div v-if="!isCash" class="grid grid-cols-2 gap-3">
        <label class="grid gap-1">
          <span class="label">類型</span>
          <select v-model="assetType" class="input">
            <option value="equity">股票</option>
            <option value="leveraged">槓桿 ETF</option>
            <option value="bond">債券</option>
          </select>
        </label>
        <label class="grid gap-1">
          <span class="label">壓力測試 beta</span>
          <input v-model.number="beta" type="number" step="any" class="input num" />
        </label>
        <label class="grid gap-1">
          <span class="label">平均成本（原幣）</span>
          <input v-model.number="avgCost" type="number" step="any" min="0" class="input num" />
        </label>
        <label class="grid gap-1">
          <span class="label">目標股數（Phase 2）</span>
          <input v-model.number="targetShares" type="number" step="any" min="0" class="input num" />
        </label>
      </div>
      <p class="text-xs text-ink-400">beta 代表大盤跌 1% 時這檔約跌幾 %：一般股票 1、2 倍槓桿 2、債券與現金 0。</p>

      <div v-if="!isCash" class="mt-2 rounded-lg border border-ink-700/70 p-3">
        <p class="label">股票分割</p>
        <p class="mt-1 text-xs text-ink-400">Yahoo 有列出的分割會自動套用。少數台股的分割 Yahoo 沒列出（0050 在 2025-06-18 的 1 拆 4 已內建），遇到時在這裡補上。</p>
        <ul class="num mt-2 text-sm">
          <li v-for="s in splits" :key="s.id" class="text-ink-300">{{ s.date }}・1 拆 {{ s.ratio }}</li>
          <li v-if="!splits.length" class="text-ink-600">無</li>
        </ul>
        <div class="mt-2 flex gap-2">
          <input v-model="splitDate" type="date" class="input" aria-label="分割生效日" />
          <input v-model.number="splitRatio" type="number" step="any" min="0" class="input num w-28" placeholder="1 拆幾" aria-label="分割比例" />
          <button type="button" class="btn-ghost shrink-0" @click="addSplit">加入</button>
        </div>
      </div>
      <p v-if="error" class="rounded-lg bg-amber-950/50 px-3 py-2 text-sm text-warm" role="alert">{{ error }}</p>
    </form>
    <template #footer>
      <button v-if="!isCash" class="btn mr-auto text-ink-400 hover:text-warm" @click="archive">
        {{ position.archived ? '恢復' : '封存' }}
      </button>
      <button class="btn-ghost" @click="emit('close')">取消</button>
      <button class="btn-primary" form="edit-holding" type="submit" :disabled="busy">儲存</button>
    </template>
  </BaseModal>
</template>
