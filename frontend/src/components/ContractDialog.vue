<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { api, type ContractInfo, type ContractInput } from '../api'
import { pct } from '../format'
import BaseModal from './BaseModal.vue'

const props = defineProps<{ contract?: ContractInfo }>()
const emit = defineEmits<{ close: []; changed: [] }>()

const form = reactive<ContractInput>({
  name: props.contract?.name ?? '',
  start_month: props.contract?.start_month ?? '',
  monthly_deposit: props.contract?.monthly_deposit ?? 10000,
  term_months: props.contract?.term_months ?? 120,
  payout: props.contract?.payout ?? 0,
  valuation: props.contract?.valuation ?? 'accrued',
  closed: props.contract?.closed ?? false,
  note: props.contract?.note ?? null,
})
const busy = ref(false)
const error = ref('')

// Same formula as the backend, so the rate updates while typing.
const impliedRate = computed(() => {
  const d = form.monthly_deposit, n = form.term_months, p = form.payout
  if (!(d > 0 && n > 0 && p > d * n)) return 0
  let lo = 1e-9, hi = 1
  for (let i = 0; i < 200; i++) {
    const r = (lo + hi) / 2
    const fv = (d * ((1 + r) ** n - 1)) / r * (1 + r)
    if (fv < p) lo = r
    else hi = r
  }
  return (1 + (lo + hi) / 2) ** 12 - 1
})

async function save() {
  busy.value = true
  error.value = ''
  try {
    if (props.contract) await api.updateContract(props.contract.id, { ...form })
    else await api.addContract({ ...form })
    emit('changed')
    emit('close')
  } catch (e) {
    error.value = (e as Error).message
  } finally {
    busy.value = false
  }
}

async function remove() {
  if (!props.contract || !confirm('刪除後這筆約定存款會從資產與歷史中移除，確定？')) return
  await api.deleteContract(props.contract.id)
  emit('changed')
  emit('close')
}
</script>

<template>
  <BaseModal :title="contract ? contract.name + '・設定' : '新增約定存款'" @close="emit('close')">
    <form id="contract-form" class="grid gap-3" @submit.prevent="save">
      <label class="grid gap-1">
        <span class="label">名稱</span>
        <input v-model="form.name" required class="input" placeholder="家人約定存款" />
      </label>
      <div class="grid grid-cols-2 gap-3">
        <label class="grid gap-1">
          <span class="label">第一期存入月份</span>
          <input v-model="form.start_month" type="month" required class="input" />
        </label>
        <label class="grid gap-1">
          <span class="label">每月存入（台幣）</span>
          <input v-model.number="form.monthly_deposit" type="number" min="1" step="any" required class="input num" />
        </label>
        <label class="grid gap-1">
          <span class="label">共幾期（月）</span>
          <input v-model.number="form.term_months" type="number" min="1" required class="input num" />
        </label>
        <label class="grid gap-1">
          <span class="label">到期領回（台幣）</span>
          <input v-model.number="form.payout" type="number" min="1" step="any" required class="input num" />
        </label>
      </div>
      <p class="text-xs text-ink-400">隱含年報酬約 {{ pct(impliedRate) }}（每月月初存入，最後一期的下個月領回）</p>
      <label class="grid gap-1">
        <span class="label">計入總資產的方式</span>
        <select v-model="form.valuation" class="input">
          <option value="accrued">依隱含報酬累積的價值（建議）</option>
          <option value="deposited">只算已存入的本金（保守）</option>
        </select>
      </label>
      <label class="grid gap-1">
        <span class="label">備註</span>
        <input v-model="form.note" class="input" />
      </label>
      <label v-if="contract" class="flex items-center gap-2 text-sm text-ink-300">
        <input v-model="form.closed" type="checkbox" class="accent-[var(--color-accent)]" />
        已領回（領回的錢請另外記到台幣現金）
      </label>
      <p v-if="error" class="rounded-lg bg-amber-950/50 px-3 py-2 text-sm text-warm" role="alert">{{ error }}</p>
    </form>
    <template #footer>
      <button v-if="contract" class="btn mr-auto text-ink-400 hover:text-warm" @click="remove">刪除</button>
      <button class="btn-ghost" @click="emit('close')">取消</button>
      <button class="btn-primary" form="contract-form" type="submit" :disabled="busy">儲存</button>
    </template>
  </BaseModal>
</template>
