<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import {
  api,
  type Config,
  type ContractInfo,
  type DividendRow,
  type HistoryPoint,
  type Holdings,
  type Position,
  type Projection,
  type Status,
  type Summary,
} from './api'
import AddHoldingDialog from './components/AddHoldingDialog.vue'
import ConfigModal from './components/ConfigModal.vue'
import ContractDialog from './components/ContractDialog.vue'
import DividendsCard from './components/DividendsCard.vue'
import HoldingEditDialog from './components/HoldingEditDialog.vue'
import HoldingsTable from './components/HoldingsTable.vue'
import ShareLogDialog from './components/ShareLogDialog.vue'
import StressCard from './components/StressCard.vue'
import SummaryCards from './components/SummaryCards.vue'
import TrajectoryChart from './components/TrajectoryChart.vue'

const summary = ref<Summary>()
const holdings = ref<Holdings>()
const projection = ref<Projection>()
const history = ref<HistoryPoint[]>([])
const dividends = ref<DividendRow[]>([])
const config = ref<Config>()
const status = ref<Status>()
const loadError = ref('')

const showConfig = ref(false)
const showAdd = ref(false)
const recordFor = ref<Position | null>(null)
const editFor = ref<Position | null>(null)
const contractFor = ref<ContractInfo | 'new' | null>(null)

function onEdit(p: Position) {
  if (p.contract) contractFor.value = p.contract
  else editFor.value = p
}

async function loadAll() {
  try {
    const [s, h, p, hi, d, c, st] = await Promise.all([
      api.summary(),
      api.holdings(),
      api.projection(),
      api.history(),
      api.dividends(),
      api.config(),
      api.status(),
    ])
    summary.value = s
    holdings.value = h
    projection.value = p
    history.value = hi
    dividends.value = d
    config.value = c
    status.value = st
    loadError.value = ''
  } catch (e) {
    loadError.value = (e as Error).message
  }
}

// While the backend is fetching, poll its status and reload once it finishes.
let timer: number | undefined
async function poll() {
  try {
    const was = status.value?.refreshing
    status.value = await api.status()
    if (was && !status.value.refreshing) await loadAll()
  } catch {
    /* backend restarting */
  }
  timer = window.setTimeout(poll, status.value?.refreshing ? 3000 : 30000)
}

async function refreshNow() {
  await api.refresh()
  if (status.value) status.value.refreshing = true
  window.clearTimeout(timer)
  timer = window.setTimeout(poll, 2000)
}

function afterAdd() {
  showAdd.value = false
  loadAll()
  refreshNow()
}

onMounted(async () => {
  await loadAll()
  poll()
})
onBeforeUnmount(() => window.clearTimeout(timer))

const updatedLabel = computed(() => {
  const st = status.value
  if (!st) return ''
  if (st.refreshing) return '正在更新報價…'
  if (!st.last_success_date) return '尚未取得報價'
  return '報價更新至 ' + st.last_success_date
})
const hasErrors = computed(() => (status.value?.errors.length ?? 0) > 0)
const errorDetail = computed(() =>
  (status.value?.symbols ?? [])
    .filter((s) => s.last_error)
    .map((s) => s.symbol + '：' + s.last_error)
    .join('\n'),
)
</script>

<template>
  <div class="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:py-8">
    <header class="mb-6 flex flex-wrap items-center justify-between gap-4">
      <div class="flex items-center gap-3">
        <div class="grid h-9 w-9 place-items-center rounded-xl bg-accent-soft text-accent" aria-hidden="true">
          <svg viewBox="0 0 24 24" class="h-5 w-5" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 17l5-5 4 3 8-9" /><path d="M15 6h5v5" /></svg>
        </div>
        <div>
          <h1 class="text-lg font-semibold tracking-tight">FireDashboard</h1>
          <p class="text-xs text-ink-400">
            <span>{{ updatedLabel }}</span>
            <span v-if="hasErrors" class="ml-2 cursor-help text-warm" :title="errorDetail">・部分標的更新失敗</span>
          </p>
        </div>
      </div>
      <div class="flex gap-2">
        <button class="btn-ghost" :disabled="status?.refreshing" @click="refreshNow">
          <svg viewBox="0 0 20 20" class="h-4 w-4" :class="status?.refreshing ? 'animate-spin' : ''" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M16 10a6 6 0 1 1-1.8-4.3M16 3v4h-4" /></svg>
          更新報價
        </button>
        <button class="btn-ghost" :disabled="!config" @click="showConfig = true">
          <svg viewBox="0 0 20 20" class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M4 6h8M16 6h0M4 14h2M10 14h6" /><circle cx="14" cy="6" r="2" /><circle cx="8" cy="14" r="2" /></svg>
          參數設定
        </button>
      </div>
    </header>

    <p v-if="loadError" class="mb-4 rounded-xl border border-amber-800/60 bg-amber-950/40 px-4 py-3 text-sm text-warm" role="alert">
      無法連線到後端：{{ loadError }}
    </p>
    <p
      v-if="summary?.missing_prices.length"
      class="mb-4 rounded-xl border border-ink-700 bg-ink-900 px-4 py-3 text-sm text-ink-300"
    >
      {{ summary.missing_prices.join('、') }} 還沒有報價，總資產暫時不含這些標的。
    </p>

    <div v-if="summary && holdings && projection" class="grid gap-4">
      <SummaryCards :summary="summary" />
      <div class="grid gap-4 lg:grid-cols-[minmax(0,1fr)_18rem]">
        <TrajectoryChart :projection="projection" :history="history" :time-to-coast="summary.time_to_coast" />
        <StressCard :summary="summary" />
      </div>
      <HoldingsTable :holdings="holdings" @add="showAdd = true" @add-contract="contractFor = 'new'" @record="recordFor = $event" @edit="onEdit" />
      <DividendsCard :dividends="dividends" />
    </div>
    <div v-else-if="!loadError" class="grid gap-4" aria-busy="true">
      <div class="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <div v-for="i in 4" :key="i" class="card h-32 animate-pulse" />
      </div>
      <div class="card h-96 animate-pulse" />
    </div>

    <footer class="mt-8 text-center text-xs text-ink-600">
      資料來源 Yahoo Finance・僅供個人規劃參考，非投資建議
    </footer>

    <ConfigModal v-if="showConfig && config" :config="config" @close="showConfig = false" @saved="loadAll" />
    <AddHoldingDialog v-if="showAdd" @close="showAdd = false" @added="afterAdd" />
    <ShareLogDialog v-if="recordFor" :position="recordFor" @close="recordFor = null" @changed="loadAll" />
    <ContractDialog
      v-if="contractFor"
      :contract="contractFor === 'new' ? undefined : contractFor"
      @close="contractFor = null"
      @changed="loadAll"
    />
    <HoldingEditDialog v-if="editFor" :position="editFor" @close="editFor = null" @changed="loadAll" />
  </div>
</template>
