<script setup lang="ts">
import { computed, ref } from 'vue'
import type { Holdings, Position } from '../api'
import { money, pct, price, shares, wan } from '../format'
import InfoTip from '../guide/InfoTip.vue'

const props = defineProps<{ holdings: Holdings }>()
const emit = defineEmits<{ record: [p: Position]; edit: [p: Position]; add: []; addContract: [] }>()

const showPnl = ref(false)
const showArchived = ref(false)

const rows = computed(() => props.holdings.rows.filter((r) => showArchived.value || !r.archived))
const archivedCount = computed(() => props.holdings.rows.filter((r) => r.archived).length)

const TYPE_LABEL: Record<string, string> = { equity: '股票', leveraged: '槓桿', bond: '債券', cash: '現金' }
const MARKET_LABEL: Record<string, string> = { US: '美股', TW: '台股', CASH: '現金', CONTRACT: '約定存款' }
const named = (r: Position) => r.market === 'CASH' || r.market === 'CONTRACT'
</script>

<template>
  <section class="card">
    <div class="mb-4 flex flex-wrap items-center justify-between gap-3">
      <div>
        <h2 class="text-sm font-semibold">持倉</h2>
        <p class="text-xs text-ink-400">
          共 {{ wan(holdings.total_twd) }}・<span class="hidden md:inline">點「記錄」新增買賣或補登過去的股數</span><span class="md:hidden">點一列記錄買賣</span>
        </p>
      </div>
      <div class="flex flex-wrap items-center gap-3">
        <label class="flex cursor-pointer items-center gap-2 text-xs text-ink-400">
          <input v-model="showPnl" type="checkbox" class="accent-[var(--color-accent)]" /> 顯示成本與損益
        </label>
        <label v-if="archivedCount" class="flex cursor-pointer items-center gap-2 text-xs text-ink-400">
          <input v-model="showArchived" type="checkbox" class="accent-[var(--color-accent)]" /> 顯示已封存（{{ archivedCount }}）
        </label>
        <button class="btn-ghost" @click="emit('addContract')">＋ 約定存款</button>
        <button class="btn-primary" @click="emit('add')">
          <svg viewBox="0 0 20 20" class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="2"><path d="M10 4v12M4 10h12" /></svg>
          新增標的
        </button>
      </div>
    </div>

    <!-- Phones: one tappable row per holding; tap to record a trade, pencil to edit. -->
    <ul class="-mx-5 md:hidden">
      <li v-for="r in rows" :key="r.symbol" class="flex items-stretch border-b border-ink-800 last:border-0" :class="r.archived ? 'opacity-50' : ''">
        <button
          class="grid min-w-0 flex-1 grid-cols-[minmax(0,1fr)_auto] items-center gap-x-3 py-3 pl-5 text-left active:bg-ink-800/60"
          @click="r.contract ? emit('edit', r) : emit('record', r)"
        >
          <span class="min-w-0">
            <span class="flex items-center gap-1.5">
              <span class="truncate font-medium">{{ named(r) ? r.name : r.symbol.replace(/\.TWO?$/, '') }}</span>
              <span class="flex-none rounded bg-ink-800 px-1.5 py-0.5 text-[10px] text-ink-400">{{ MARKET_LABEL[r.market] }}</span>
            </span>
            <span class="mt-0.5 block truncate text-xs text-ink-400">
              <template v-if="r.contract">{{ r.contract.paid_months }} / {{ r.contract.term_months }} 期・每月 {{ money(r.contract.monthly_deposit) }}</template>
              <template v-else-if="r.market === 'CASH'">{{ money(r.shares, r.currency) }}</template>
              <template v-else>{{ shares(r.shares, r.market) }}・{{ price(r.price, r.currency) }}</template>
            </span>
          </span>
          <span class="num text-right">
            <span class="block text-sm">{{ r.value_twd != null ? wan(r.value_twd) : '—' }}</span>
            <span class="block text-xs text-ink-400">
              {{ pct(r.weight) }}
              <template v-if="showPnl && r.pnl_native != null && !named(r)">・{{ (r.pnl_native >= 0 ? '+' : '') + money(r.pnl_native, r.currency) }}</template>
            </span>
          </span>
        </button>
        <button class="flex-none px-4 text-ink-400 active:text-ink-100" :aria-label="'編輯 ' + r.symbol" @click="emit('edit', r)">
          <svg viewBox="0 0 20 20" class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M13.5 3.5l3 3L7 16H4v-3z" /></svg>
        </button>
      </li>
      <li v-if="!rows.length" class="px-5 py-10 text-center text-sm text-ink-400">還沒有持倉，按「新增標的」開始。</li>
    </ul>

    <div class="relative -mx-5 hidden overflow-x-auto md:block">
      <table class="w-full min-w-[720px] text-sm">
        <thead>
          <tr class="border-b border-ink-700/70 text-left text-xs text-ink-400">
            <th class="px-5 py-2 font-medium">標的</th>
            <th class="px-3 py-2 text-right font-medium">持有</th>
            <th class="px-3 py-2 text-right font-medium">價格</th>
            <th class="px-3 py-2 text-right font-medium">市值（台幣）</th>
            <th class="px-3 py-2 text-right font-medium">占比<InfoTip k="weight" /></th>
            <th v-if="showPnl" class="px-3 py-2 text-right font-medium">均價／未實現</th>
            <th class="px-5 py-2 text-right font-medium"><span class="sr-only">操作</span></th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="r in rows"
            :key="r.symbol"
            class="border-b border-ink-800 last:border-0 hover:bg-ink-800/40"
            :class="r.archived ? 'opacity-50' : ''"
          >
            <td class="px-5 py-3">
              <div class="flex items-center gap-2">
                <span class="font-medium">{{ named(r) ? r.name : r.symbol.replace(/\.TWO?$/, '') }}</span>
                <span class="rounded bg-ink-800 px-1.5 py-0.5 text-[11px] text-ink-400">{{ MARKET_LABEL[r.market] }}</span>
                <span v-if="r.asset_type === 'leveraged' || r.asset_type === 'bond'" class="rounded bg-ink-800 px-1.5 py-0.5 text-[11px] text-calm">
                  {{ TYPE_LABEL[r.asset_type] }}
                </span>
              </div>
              <p v-if="r.contract" class="mt-0.5 text-xs text-ink-400">每月 {{ money(r.contract.monthly_deposit) }}・隱含年報酬 {{ pct(r.contract.implied_annual_rate) }}</p>
              <p v-else-if="r.market !== 'CASH'" class="mt-0.5 max-w-[16rem] truncate text-xs text-ink-400">{{ r.name }}</p>
            </td>
            <td class="num px-3 py-3 text-right">
              <template v-if="r.contract">
                {{ r.contract.paid_months }} / {{ r.contract.term_months }} 期
                <p class="text-[11px] text-ink-400">已存 {{ wan(r.contract.deposited) }}</p>
              </template>
              <template v-else>{{ r.market === 'CASH' ? money(r.shares, r.currency) : shares(r.shares, r.market) }}</template>
            </td>
            <td class="num px-3 py-3 text-right">
              <template v-if="r.contract">
                到期 {{ wan(r.contract.payout) }}
                <p class="whitespace-nowrap text-[11px] text-ink-400">{{ r.contract.payout_month }} 領回</p>
              </template>
              <template v-else-if="r.market !== 'CASH'">
                {{ price(r.price, r.currency) }}
                <p class="whitespace-nowrap text-[11px] text-ink-400">{{ r.price_date ?? '等待抓價' }}</p>
              </template>
              <span v-else class="text-ink-600">—</span>
            </td>
            <td class="num px-3 py-3 text-right">{{ r.value_twd != null ? money(r.value_twd) : '—' }}</td>
            <td class="num px-3 py-3 text-right text-ink-300">{{ pct(r.weight) }}</td>
            <td v-if="showPnl" class="num px-3 py-3 text-right text-ink-300">
              <template v-if="r.avg_cost && !named(r)">
                {{ price(r.avg_cost, r.currency) }}
                <p class="text-[11px] text-ink-400">
                  {{ r.pnl_native != null ? (r.pnl_native >= 0 ? '+' : '') + money(r.pnl_native, r.currency) : '—' }}
                </p>
              </template>
              <span v-else class="text-ink-600">—</span>
            </td>
            <td class="px-5 py-3 text-right whitespace-nowrap">
              <button v-if="!r.contract" class="btn-ghost" @click="emit('record', r)">記錄</button>
              <button class="btn ml-1 text-ink-400 hover:text-ink-100" :aria-label="'編輯 ' + r.symbol" @click="emit('edit', r)">
                <svg viewBox="0 0 20 20" class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M13.5 3.5l3 3L7 16H4v-3z" /></svg>
              </button>
            </td>
          </tr>
          <tr v-if="!rows.length">
            <td colspan="7" class="px-5 py-10 text-center text-sm text-ink-400">還沒有持倉，按「新增標的」開始。</td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
</template>
