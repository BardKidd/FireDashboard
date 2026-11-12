<script setup lang="ts">
import { computed } from 'vue'
import type { LoanInfo } from '../api'
import { money, pct, wan } from '../format'
import InfoTip from '../guide/InfoTip.vue'

const props = defineProps<{ loans: LoanInfo[]; totalAssets: number }>()
const emit = defineEmits<{ add: []; edit: [l: LoanInfo] }>()

const open = computed(() => props.loans.filter((l) => !l.paid_off))
const done = computed(() => props.loans.filter((l) => l.paid_off))
const debt = computed(() => open.value.reduce((s, l) => s + l.balance, 0))
</script>

<template>
  <section class="card">
    <div class="mb-4 flex flex-wrap items-center justify-between gap-3">
      <div>
        <h2 class="text-sm font-semibold">負債<InfoTip k="debt" /></h2>
        <p class="text-xs text-ink-400">
          剩餘本金 {{ wan(debt) }}・淨資產 {{ wan(totalAssets - debt) }}
        </p>
      </div>
      <button class="btn-ghost" @click="emit('add')">＋ 負債</button>
    </div>
    <ul class="-mx-5">
      <li v-for="l in [...open, ...done]" :key="l.id" class="border-b border-ink-800 last:border-0" :class="l.paid_off ? 'opacity-50' : ''">
        <button class="grid w-full gap-2 px-5 py-3 text-left hover:bg-ink-800/40 active:bg-ink-800/60" @click="emit('edit', l)">
          <span class="flex items-baseline justify-between gap-3">
            <span class="min-w-0 truncate font-medium">{{ l.name }}</span>
            <span class="num flex-none text-sm">{{ l.paid_off ? '已還清' : '還欠 ' + wan(l.balance) }}</span>
          </span>
          <span class="h-1.5 overflow-hidden rounded-full bg-ink-800" aria-hidden="true">
            <span class="block h-full rounded-full bg-calm" :style="{ width: pct(l.repaid_principal / l.principal) }" />
          </span>
          <span class="flex flex-wrap justify-between gap-x-3 text-xs text-ink-400">
            <span>{{ l.paid_months }} / {{ l.payoff_months }} 期・每月 {{ money(l.monthly_payment) }}・年利率 {{ pct(l.annual_rate, 2) }}</span>
            <span v-if="!l.paid_off">{{ l.payoff_month }} 還清{{ l.redirect_after ? '，之後轉為投入' : '' }}</span>
          </span>
        </button>
      </li>
    </ul>
  </section>
</template>
