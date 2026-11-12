<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { api, type LoanInfo, type LoanInput } from '../api'
import { money, wan } from '../format'
import BaseModal from './BaseModal.vue'

const props = defineProps<{ loan?: LoanInfo }>()
const emit = defineEmits<{ close: []; changed: [] }>()

// Rate is edited in percent, stored as a fraction.
const form = reactive({
  name: props.loan?.name ?? '信貸',
  start_date: props.loan?.start_date ?? '',
  principal: props.loan?.principal ?? 1_000_000,
  rate_pct: props.loan ? +(props.loan.annual_rate * 100).toFixed(4) : 3,
  term_months: props.loan?.term_months ?? 84,
  payment: (props.loan?.payment ?? null) as number | null,
  redirect_after: props.loan?.redirect_after ?? true,
  closed: props.loan?.closed ?? false,
  note: props.loan?.note ?? null,
})
const busy = ref(false)
const error = ref('')

// Same schedule as the backend (backend/app/loans.py), so the preview updates while typing.
const preview = computed(() => {
  const P = form.principal, n = form.term_months, r = (form.rate_pct || 0) / 1200
  if (!(P > 0 && n > 0)) return null
  const auto = r > 0 ? (P * r) / (1 - (1 + r) ** -n) : P / n
  const pay = form.payment && form.payment > 0 ? form.payment : auto
  if (pay <= P * r) return { auto, pay, bad: true as const }
  let b = P, months = n
  for (let k = 1; k <= n; k++) {
    b = b * (1 + r) - pay
    if (b <= 0.5) { months = k; break }
  }
  let balance = P
  if (form.start_date) {
    const [y, m] = form.start_date.split('-').map(Number)
    const now = new Date()
    const made = Math.max(0, Math.min(n, now.getFullYear() * 12 + now.getMonth() - (y * 12 + m - 1)))
    if (made >= months) balance = 0
    else for (let k = 0; k < made; k++) balance = balance * (1 + r) - pay
  }
  let end = ''
  if (form.start_date) {
    const [y, m] = form.start_date.split('-').map(Number)
    const idx = y * 12 + m - 1 + months
    end = `${Math.floor(idx / 12)}-${String((idx % 12) + 1).padStart(2, '0')}`
  }
  return { auto, pay, bad: false as const, months, interest: Math.max(0, pay * months - P), balance: Math.max(0, balance), end }
})

async function save() {
  busy.value = true
  error.value = ''
  const body: LoanInput = {
    name: form.name,
    start_date: form.start_date,
    principal: form.principal,
    annual_rate: (form.rate_pct || 0) / 100,
    term_months: form.term_months,
    payment: form.payment && form.payment > 0 ? form.payment : null,
    redirect_after: form.redirect_after,
    closed: form.closed,
    note: form.note || null,
  }
  try {
    if (props.loan) await api.updateLoan(props.loan.id, body)
    else await api.addLoan(body)
    emit('changed')
    emit('close')
  } catch (e) {
    error.value = (e as Error).message
  } finally {
    busy.value = false
  }
}

async function remove() {
  if (!props.loan || !confirm('刪除後這筆負債不再從淨資產扣除，歷史淨值也會跟著重算，確定？')) return
  await api.deleteLoan(props.loan.id)
  emit('changed')
  emit('close')
}
</script>

<template>
  <BaseModal :title="loan ? loan.name + '・設定' : '新增負債'" @close="emit('close')">
    <form id="loan-form" class="grid gap-3" @submit.prevent="save">
      <p v-if="!loan" class="text-sm text-ink-400">
        借來投入的錢已經算在持股裡；這裡登記還沒還的部分，火勢就會改用「資產 − 剩餘本金」計算。
      </p>
      <label class="grid gap-1">
        <span class="label">名稱</span>
        <input v-model="form.name" required class="input" placeholder="例如：信貸" />
      </label>
      <div class="grid grid-cols-2 gap-3">
        <label class="grid gap-1">
          <span class="label">撥款日期</span>
          <input v-model="form.start_date" type="date" required class="input" />
        </label>
        <label class="grid gap-1">
          <span class="label">借款金額（台幣）</span>
          <input v-model.number="form.principal" type="number" min="1" step="any" required class="input num" />
        </label>
        <label class="grid gap-1">
          <span class="label">年利率（%）</span>
          <input v-model.number="form.rate_pct" type="number" min="0" max="99" step="any" required class="input num" />
        </label>
        <label class="grid gap-1">
          <span class="label">共幾期（月）</span>
          <input v-model.number="form.term_months" type="number" min="1" max="600" required class="input num" />
        </label>
      </div>
      <label class="grid gap-1">
        <span class="label">每月還款（台幣，可不填）</span>
        <input
          v-model.number="form.payment"
          type="number"
          min="1"
          step="any"
          class="input num"
          :placeholder="preview ? '不填就用本息平均攤還：約 ' + money(preview.auto) : ''"
        />
      </label>
      <p v-if="preview?.bad" class="rounded-lg bg-amber-950/50 px-3 py-2 text-sm text-warm">月付金比每月利息還少，這樣永遠還不完。</p>
      <p v-else-if="preview" class="text-xs leading-relaxed text-ink-400">
        撥款後下個月開始還，每月 {{ money(preview.pay) }}，共 {{ preview.months }} 期，總利息約 {{ wan(preview.interest) }}。
        <template v-if="form.start_date">
          <br />目前剩餘本金約 {{ wan(preview.balance) }}，{{ preview.end }} 還清。和銀行帳單差很多的話，可以直接填帳單上的月付金。
        </template>
      </p>
      <label class="flex items-start gap-2 text-sm text-ink-300">
        <input v-model="form.redirect_after" type="checkbox" class="mt-1 accent-[var(--color-accent)]" />
        <span>還清後，把這筆月付金繼續拿去投資<span class="block text-xs text-ink-400">預測軌跡會在還清的下個月起，把它加進每月投入</span></span>
      </label>
      <label class="grid gap-1">
        <span class="label">備註</span>
        <input v-model="form.note" class="input" />
      </label>
      <label v-if="loan" class="flex items-center gap-2 text-sm text-ink-300">
        <input v-model="form.closed" type="checkbox" class="accent-[var(--color-accent)]" />
        已提前結清（不再從淨資產扣除）
      </label>
      <p v-if="error" class="rounded-lg bg-amber-950/50 px-3 py-2 text-sm text-warm" role="alert">{{ error }}</p>
    </form>
    <template #footer>
      <button v-if="loan" class="btn mr-auto text-ink-400 hover:text-warm" @click="remove">刪除</button>
      <button class="btn-ghost" @click="emit('close')">取消</button>
      <button class="btn-primary" form="loan-form" type="submit" :disabled="busy || preview?.bad">儲存</button>
    </template>
  </BaseModal>
</template>
