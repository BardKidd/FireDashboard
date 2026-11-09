<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { api, type LogKind, type Position, type ShareLog } from '../api'
import { money, shares as fmtShares, todayISO } from '../format'
import BaseModal from './BaseModal.vue'

const props = defineProps<{ position: Position }>()
const emit = defineEmits<{ close: []; changed: [] }>()

const isCash = computed(() => props.position.market === 'CASH')
const kinds = computed<{ k: LogKind; t: string }[]>(() =>
  isCash.value
    ? [
        { k: 'deposit', t: '存入' },
        { k: 'withdraw', t: '提出' },
        { k: 'adjust', t: '校正餘額' },
      ]
    : [
        { k: 'buy', t: '買入' },
        { k: 'sell', t: '賣出' },
        { k: 'adjust', t: '校正股數' },
      ],
)

const day = ref(todayISO())
const kind = ref<LogKind>(isCash.value ? 'deposit' : 'buy')
const amount = ref<number | null>(null)
const unitPrice = ref<number | null>(null)
const note = ref('')
const busy = ref(false)
const error = ref('')
const logs = ref<ShareLog[]>([])

const unit = computed(() => (isCash.value ? (props.position.currency === 'USD' ? '美元' : '元') : '股'))
const amountLabel = computed(() => {
  if (kind.value === 'adjust') return isCash.value ? '當日餘額（' + unit.value + '）' : '當日總股數'
  return (kinds.value.find((k) => k.k === kind.value)?.t ?? '') + '數量（' + unit.value + '）'
})

const KIND_LABEL: Record<string, string> = {
  buy: '買入', sell: '賣出', adjust: '校正', deposit: '存入', withdraw: '提出', split: '分割', dividend: '股息',
}

async function load() {
  logs.value = await api.logs(props.position.symbol)
}
onMounted(load)

async function submit() {
  error.value = ''
  if (amount.value == null || Number.isNaN(amount.value)) {
    error.value = '請輸入數量'
    return
  }
  busy.value = true
  try {
    await api.addLog({
      symbol: props.position.symbol,
      date: day.value,
      kind: kind.value,
      ...(kind.value === 'adjust' ? { set_total: amount.value } : { delta: amount.value }),
      ...(kind.value === 'buy' && unitPrice.value ? { price: unitPrice.value } : {}),
      note: note.value || undefined,
    })
    amount.value = null
    unitPrice.value = null
    note.value = ''
    await load()
    emit('changed')
  } catch (e) {
    error.value = (e as Error).message
  } finally {
    busy.value = false
  }
}

async function remove(l: ShareLog) {
  if (!confirm(l.date + ' 的這筆紀錄要刪除嗎？')) return
  try {
    await api.deleteLog(l.id)
    await load()
    emit('changed')
  } catch (e) {
    error.value = (e as Error).message
  }
}

function fmt(v: number) {
  return isCash.value ? money(v, props.position.currency) : fmtShares(v, props.position.market)
}
</script>

<template>
  <BaseModal :title="(isCash ? position.name : position.symbol) + '・紀錄'" wide @close="emit('close')">
    <form class="grid gap-3 sm:grid-cols-2" @submit.prevent="submit">
      <div class="sm:col-span-2 flex gap-1 rounded-lg border border-ink-700 p-0.5 text-sm" role="radiogroup" aria-label="類型">
        <button
          v-for="k in kinds"
          :key="k.k"
          type="button"
          role="radio"
          :aria-checked="kind === k.k"
          class="flex-1 rounded-md px-3 py-1.5"
          :class="kind === k.k ? 'bg-ink-700 text-ink-100' : 'text-ink-400 hover:text-ink-100'"
          @click="kind = k.k"
        >
          {{ k.t }}
        </button>
      </div>
      <label class="grid gap-1">
        <span class="label">日期（可補登過去）</span>
        <input v-model="day" type="date" required class="input" :max="todayISO()" />
      </label>
      <label class="grid gap-1">
        <span class="label">{{ amountLabel }}</span>
        <input v-model.number="amount" type="number" step="any" min="0" required class="input num" />
      </label>
      <label v-if="kind === 'buy'" class="grid gap-1">
        <span class="label">成交價（選填，用來更新均價）</span>
        <input v-model.number="unitPrice" type="number" step="any" min="0" class="input num" />
      </label>
      <label class="grid gap-1" :class="kind === 'buy' ? '' : 'sm:col-span-2'">
        <span class="label">備註（選填）</span>
        <input v-model="note" type="text" class="input" placeholder="定期定額、大跌加碼…" />
      </label>
      <p v-if="error" class="sm:col-span-2 rounded-lg bg-amber-950/50 px-3 py-2 text-sm text-warm" role="alert">{{ error }}</p>
      <div class="sm:col-span-2 flex justify-end">
        <button type="submit" class="btn-primary" :disabled="busy">{{ busy ? '儲存中…' : '新增紀錄' }}</button>
      </div>
    </form>

    <h3 class="mt-6 mb-2 text-xs font-medium text-ink-400">歷史紀錄</h3>
    <div class="max-h-72 overflow-y-auto rounded-lg border border-ink-700/70">
      <table class="w-full text-sm">
        <tbody>
          <tr v-for="l in logs" :key="l.id" class="border-b border-ink-800 last:border-0">
            <td class="num px-3 py-2 text-ink-300">{{ l.date }}</td>
            <td class="px-3 py-2">
              <span class="rounded bg-ink-800 px-1.5 py-0.5 text-xs" :class="l.kind === 'split' || l.kind === 'dividend' ? 'text-calm' : 'text-ink-300'">
                {{ KIND_LABEL[l.kind] }}
              </span>
            </td>
            <td class="num px-3 py-2 text-right">{{ (l.delta_shares >= 0 ? '+' : '−') + fmt(Math.abs(l.delta_shares)) }}</td>
            <td class="num px-3 py-2 text-right text-ink-400">→ {{ fmt(l.total_shares_after) }}</td>
            <td class="px-3 py-2 text-xs text-ink-400">{{ l.note }}</td>
            <td class="px-2 py-2 text-right">
              <button
                v-if="l.kind !== 'split' && l.kind !== 'dividend'"
                class="rounded p-1 text-ink-600 hover:bg-ink-800 hover:text-warm"
                aria-label="刪除"
                @click="remove(l)"
              >
                <svg viewBox="0 0 20 20" class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M5 6h10M8 6V4h4v2M6 6l1 10h6l1-10" /></svg>
              </button>
            </td>
          </tr>
          <tr v-if="!logs.length">
            <td class="px-3 py-6 text-center text-ink-400">尚無紀錄</td>
          </tr>
        </tbody>
      </table>
    </div>
  </BaseModal>
</template>
