<script setup lang="ts">
import { computed, ref } from 'vue'
import type { DividendRow } from '../api'
import { money } from '../format'

const props = defineProps<{ dividends: DividendRow[] }>()
const open = ref(false)

const thisYear = new Date().getFullYear().toString()
const ytd = computed(() => {
  const r = { TWD: 0, USD: 0 }
  for (const d of props.dividends) if (d.ex_date.startsWith(thisYear)) r[d.currency] += d.net
  return r
})
</script>

<template>
  <section class="card">
    <button class="flex w-full items-center justify-between text-left" :aria-expanded="open" @click="open = !open">
      <div>
        <h2 class="text-sm font-semibold">股息入帳</h2>
        <p class="num text-xs text-ink-400">
          {{ thisYear }} 年稅後：{{ money(ytd.TWD) }} ＋ {{ money(ytd.USD, 'USD') }}・已自動計入現金
        </p>
      </div>
      <svg viewBox="0 0 20 20" class="h-5 w-5 text-ink-400 transition" :class="open ? 'rotate-180' : ''" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M5 8l5 5 5-5" /></svg>
    </button>
    <div v-if="open" class="-mx-5 mt-4 overflow-x-auto">
      <table class="w-full min-w-[640px] text-sm">
        <thead>
          <tr class="border-b border-ink-700/70 text-left text-xs text-ink-400">
            <th class="px-5 py-2 font-medium">除息日</th>
            <th class="px-3 py-2 font-medium">標的</th>
            <th class="px-3 py-2 text-right font-medium">每股</th>
            <th class="px-3 py-2 text-right font-medium">持股</th>
            <th class="px-3 py-2 text-right font-medium">稅前</th>
            <th class="px-3 py-2 text-right font-medium">預扣稅／健保</th>
            <th class="px-5 py-2 text-right font-medium">實收</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="d in dividends" :key="d.symbol + d.ex_date" class="border-b border-ink-800 last:border-0">
            <td class="num px-5 py-2 text-ink-300">{{ d.ex_date }}</td>
            <td class="px-3 py-2">{{ d.symbol.replace(/\.TWO?$/, '') }}</td>
            <td class="num px-3 py-2 text-right">{{ d.per_share.toFixed(3) }}</td>
            <td class="num px-3 py-2 text-right">{{ d.shares_held.toLocaleString() }}</td>
            <td class="num px-3 py-2 text-right">{{ money(d.gross, d.currency) }}</td>
            <td class="num px-3 py-2 text-right text-ink-400">{{ money(d.tax_withheld + d.nhi_premium, d.currency) }}</td>
            <td class="num px-5 py-2 text-right">{{ money(d.net, d.currency) }}</td>
          </tr>
          <tr v-if="!dividends.length">
            <td colspan="7" class="px-5 py-6 text-center text-ink-400">尚無股息</td>
          </tr>
        </tbody>
      </table>
      <p class="px-5 pt-3 text-xs text-ink-400">入帳日以除息日計，會比實際發放早幾週。</p>
    </div>
  </section>
</template>
