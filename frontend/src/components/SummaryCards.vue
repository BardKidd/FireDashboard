<script setup lang="ts">
import { computed } from 'vue'
import type { Summary } from '../api'
import { money, pct, wan, ym } from '../format'

const props = defineProps<{ summary: Summary }>()

const progress = computed(() => props.summary.progress ?? 0)
const barWidth = computed(() => Math.min(100, progress.value * 100) + '%')
const fxLabel = computed(() => {
  const fx = props.summary.fx
  const name = { live: '即時', ma200: '200 日均', custom: '自訂' }[fx.mode]
  return fx.used ? name + '匯率 ' + fx.used.toFixed(2) : '尚無匯率'
})
const ttc = computed(() => props.summary.time_to_coast)
const yearsLeft = computed(() => {
  const m = ttc.value.months ?? 0
  const y = Math.floor(m / 12)
  const r = m % 12
  return (y ? y + ' 年 ' : '') + (r ? r + ' 個月' : y ? '' : '不到 1 個月')
})
</script>

<template>
  <section class="grid gap-4 sm:grid-cols-2 xl:grid-cols-4" aria-label="核心指標">
    <article class="card">
      <p class="label">總資產（今日）</p>
      <p class="num mt-2 text-3xl font-semibold tracking-tight">{{ wan(summary.total_assets) }}</p>
      <p class="mt-2 text-xs text-ink-400">
        {{ fxLabel }}
        <span v-if="summary.fx.mode !== 'live' && summary.fx.live" class="block">
          以即時匯率 {{ summary.fx.live.toFixed(2) }} 計為 {{ wan(summary.total_assets_live_fx) }}
        </span>
      </p>
    </article>

    <article class="card">
      <p class="label">Coast FIRE 達成率</p>
      <p class="num mt-2 text-3xl font-semibold tracking-tight" :class="progress >= 1 ? 'text-accent' : ''">
        {{ pct(summary.progress) }}
      </p>
      <div class="mt-3 h-2 overflow-hidden rounded-full bg-ink-800" role="progressbar" :aria-valuenow="Math.round(progress * 100)" aria-valuemin="0" aria-valuemax="100">
        <div class="h-full rounded-full bg-accent transition-all duration-700" :style="{ width: barWidth }" />
      </div>
      <p class="mt-2 text-xs text-ink-400">今日門檻 {{ wan(summary.coast_target) }}・終點目標 {{ wan(summary.fire_target) }}</p>
    </article>

    <article class="card">
      <p class="label">預計達成 Coast FIRE</p>
      <template v-if="ttc.status === 'achieved'">
        <p class="mt-2 text-3xl font-semibold tracking-tight text-accent">已達成</p>
        <p class="mt-2 text-xs text-ink-400">不再投入，複利也能在 {{ Math.round(summary.age_years + summary.months_remaining / 12) }} 歲達標</p>
      </template>
      <template v-else-if="ttc.status === 'reachable'">
        <p class="num mt-2 text-3xl font-semibold tracking-tight">{{ ym(ttc.month) }}</p>
        <p class="mt-2 text-xs text-ink-400">照目前定期定額，還要 {{ yearsLeft }}</p>
      </template>
      <template v-else>
        <p class="mt-2 text-2xl font-semibold tracking-tight text-warm">退休前無法達成</p>
        <p class="mt-2 text-xs text-ink-400">退休時差額 {{ wan(ttc.gap_at_retirement) }}，可調整投入或目標</p>
      </template>
    </article>

    <article class="card">
      <p class="label">現在停扣，退休後每月可領</p>
      <p class="num mt-2 text-3xl font-semibold tracking-tight">{{ money(summary.monthly_income_if_stop) }}</p>
      <p class="mt-2 text-xs text-ink-400">以今日購買力計，從 {{ Math.round(summary.age_years + summary.months_remaining / 12) }} 歲開始</p>
    </article>
  </section>
</template>
