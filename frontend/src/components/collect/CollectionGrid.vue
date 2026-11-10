<script setup lang="ts">
import { ref } from 'vue'
import { api, type CollectRow } from '../../api'
import { pct, shares } from '../../format'

defineProps<{ rows: CollectRow[]; selected: string | null }>()
const emit = defineEmits<{ select: [symbol: string]; changed: [] }>()

const editing = ref<string | null>(null)
const draft = ref<number | null>(null)
const err = ref('')

function startEdit(r: CollectRow) {
  editing.value = r.symbol
  draft.value = r.target_shares ? Math.round(r.target_shares) : null
  err.value = ''
}

async function save(r: CollectRow, reset = false) {
  try {
    const v = reset || !draft.value ? null : draft.value
    await api.patchHolding(r.symbol, { target_shares: v })
    editing.value = null
    emit('changed')
  } catch (e) {
    err.value = (e as Error).message
  }
}

const fmtTarget = (r: CollectRow) => {
  const t = r.target_shares
  if (t == null) return '—'
  if (r.market === 'TW' && t >= 1000) return (t / 1000).toFixed(t >= 10000 ? 0 : 1) + ' 張'
  return t.toFixed(t >= 100 ? 0 : 1) + ' 股'
}
const bar = (v: number | null) => Math.min(100, Math.max(0, (v ?? 0) * 100)) + '%'
const onSale = (r: CollectRow) => (r.radar?.extra_vs_ma60 ?? 0) > 0.005
</script>

<template>
  <section aria-label="收集冊">
    <div class="mb-3 flex items-end justify-between">
      <div>
        <h2 class="text-sm font-semibold">收集冊</h2>
        <p class="text-xs text-ink-400">只看股數，不看市值。點卡片看收集曲線。</p>
      </div>
    </div>
    <div v-if="rows.length" class="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
      <article
        v-for="r in rows"
        :key="r.symbol"
        class="card flex cursor-pointer flex-col gap-3 transition hover:border-ink-600"
        :class="selected === r.symbol ? 'border-accent/70' : ''"
        tabindex="0"
        role="button"
        :aria-pressed="selected === r.symbol"
        @click="emit('select', r.symbol)"
        @keydown.enter.self="emit('select', r.symbol)"
      >
        <header class="flex items-start justify-between gap-2">
          <div class="min-w-0">
            <p class="flex items-center gap-2 font-semibold">
              {{ r.label }}
              <span class="rounded bg-ink-800 px-1.5 py-0.5 text-[11px] font-normal text-ink-400">{{ r.market === 'TW' ? '台股' : '美股' }}</span>
            </p>
            <p class="truncate text-xs text-ink-400">{{ r.name }}</p>
          </div>
          <span class="shrink-0 rounded-full bg-accent-soft px-2.5 py-1 text-xs font-semibold text-accent">Lv.{{ r.level }}</span>
        </header>

        <div>
          <p class="num text-2xl font-semibold tracking-tight">{{ shares(r.shares, r.market) }}</p>
          <p class="text-xs text-ink-400">收集第 {{ r.days_held.toLocaleString() }} 天</p>
        </div>

        <div>
          <div class="mb-1 flex justify-between text-xs text-ink-400">
            <span>{{ r.next_milestone ? '下一階 ' + r.next_label : '已達最高階' }}</span>
            <span class="num">{{ r.next_milestone ? pct(r.progress_to_next, 0) : '' }}</span>
          </div>
          <div class="h-1.5 overflow-hidden rounded-full bg-ink-800">
            <div class="h-full rounded-full bg-calm" :style="{ width: r.next_milestone ? bar(r.progress_to_next) : '100%' }" />
          </div>
        </div>

        <div @click.stop>
          <div class="mb-1 flex items-center justify-between text-xs text-ink-400">
            <span>
              籃子 {{ fmtTarget(r) }}
              <span v-if="r.target_is_manual" class="text-ink-300">（自訂）</span>
            </span>
            <span class="flex items-center gap-2">
              <span class="num">{{ pct(r.target_progress, 0) }}</span>
              <button class="text-ink-400 underline-offset-2 hover:text-ink-100 hover:underline" @click="startEdit(r)">調整</button>
            </span>
          </div>
          <div class="h-1.5 overflow-hidden rounded-full bg-ink-800">
            <div class="h-full rounded-full bg-accent" :style="{ width: bar(r.target_progress) }" />
          </div>
          <form v-if="editing === r.symbol" class="mt-2 flex items-center gap-2" @submit.prevent="save(r)">
            <label class="sr-only" :for="'t-' + r.symbol">目標股數</label>
            <input :id="'t-' + r.symbol" v-model.number="draft" type="number" min="0" step="any" class="input py-1"  placeholder="目標股數" />
            <span class="text-xs text-ink-400">股</span>
            <button class="btn-primary py-1">存</button>
            <button v-if="r.target_is_manual" type="button" class="btn-ghost py-1" @click="save(r, true)">自動</button>
            <button type="button" class="btn py-1 text-ink-400" @click="editing = null">取消</button>
          </form>
          <p v-if="editing === r.symbol && err" class="mt-1 text-xs text-warm">{{ err }}</p>
        </div>

        <p v-if="!r.radar" class="rounded-lg bg-ink-950/60 px-3 py-2 text-xs text-ink-400">等待報價</p>
        <p v-else-if="onSale(r)" class="rounded-lg bg-accent-soft/40 px-3 py-2 text-xs">
          <span class="font-semibold text-accent">特價中</span>
          比 60 日均低 {{ pct(r.radar.discount_vs_ma60) }}，同樣金額多收集
          <span class="num font-semibold text-accent">{{ pct(r.radar.extra_vs_ma60) }}</span> 股數
          <span v-if="(r.radar.discount_vs_high ?? 0) > 0.05" class="block text-ink-400">相對 52 週高點，同樣金額多收 {{ pct(r.radar.extra_vs_high) }}</span>
        </p>
        <p v-else class="rounded-lg bg-ink-950/60 px-3 py-2 text-xs text-ink-400">價格在 60 日均之上，照原本節奏收集就好</p>
      </article>
    </div>
    <p v-else class="card text-center text-sm text-ink-400">還沒有股票或 ETF。到「儀表板」新增標的後，這裡就會出現收集卡。</p>
  </section>
</template>
