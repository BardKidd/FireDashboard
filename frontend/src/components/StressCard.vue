<script setup lang="ts">
import { computed } from 'vue'
import type { Summary } from '../api'
import { pct, wan } from '../format'
import InfoTip from '../guide/InfoTip.vue'

const props = defineProps<{ summary: Summary }>()
const s = computed(() => props.summary.stress)
const hasDebt = computed(() => props.summary.debt > 0.5)
const fx = computed(() => props.summary.fx)
const fxGap = computed(() => (fx.value.live && fx.value.ma200 ? fx.value.live / fx.value.ma200 - 1 : null))
</script>

<template>
  <section class="card flex flex-col gap-5">
    <div>
      <h2 class="text-sm font-semibold">抗跌安全邊際</h2>
      <p class="mt-1 text-xs text-ink-400">組合 beta {{ s.beta.toFixed(2) }}<InfoTip k="beta" />（現金、債券與約定存款為 0，槓桿 ETF 依倍數）</p>
      <p v-if="hasDebt && s.net_beta != null" class="mt-1 text-xs text-warm">計入負債後，淨資產的 beta 是 {{ s.net_beta.toFixed(2) }}：負債不會跟著跌，所以跌幅會被放大</p>
    </div>

    <div>
      <p class="label">可承受大盤下跌<InfoTip k="cushion" /></p>
      <p v-if="s.max_market_drop != null" class="num mt-1 text-2xl font-semibold text-accent">{{ pct(s.max_market_drop, 0) }}</p>
      <p v-else class="mt-1 text-lg font-semibold text-ink-300">尚未進入安全區</p>
      <p class="mt-1 text-xs text-ink-400">
        {{ s.max_market_drop != null ? '跌幅在此之內，' + (hasDebt ? '淨資產' : '資產') + '仍高於今日 Coast 門檻' : (hasDebt ? '淨資產' : '資產') + '超過 Coast 門檻後才會顯示' }}
      </p>
    </div>

    <div>
      <p class="label">若大盤下跌 {{ pct(s.drop, 0) }}<InfoTip k="stress" /></p>
      <p class="num mt-1 text-lg font-semibold">達成率 {{ pct(s.stressed_progress) }}</p>
      <p class="mt-1 text-xs text-ink-400">{{ hasDebt ? '淨資產' : '資產' }}約 {{ wan(s.stressed_value) }}・定期定額不受影響</p>
    </div>

    <div class="border-t border-ink-700/70 pt-4" data-tour="fx">
      <p class="label">美元匯率<InfoTip k="fx" /></p>
      <dl class="num mt-2 grid grid-cols-2 gap-y-1 text-sm">
        <dt class="text-ink-400">即時</dt>
        <dd class="text-right">{{ fx.live?.toFixed(3) ?? '—' }}</dd>
        <dt class="text-ink-400">200 日均</dt>
        <dd class="text-right">{{ fx.ma200?.toFixed(3) ?? '—' }}</dd>
        <template v-if="fx.custom">
          <dt class="text-ink-400">自訂</dt>
          <dd class="text-right">{{ fx.custom.toFixed(3) }}</dd>
        </template>
      </dl>
      <p v-if="fxGap != null" class="mt-2 text-xs text-ink-400">
        即時匯率比均線{{ fxGap >= 0 ? '高' : '低' }} {{ pct(Math.abs(fxGap)) }}，達成率以
        {{ { live: '即時', ma200: '200 日均', custom: '自訂' }[fx.mode] }}匯率計算
      </p>
    </div>
  </section>
</template>
