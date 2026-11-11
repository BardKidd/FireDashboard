<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
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
import CampfireHero from './components/CampfireHero.vue'
import SoundToggle from './components/SoundToggle.vue'
import TrajectoryChart from './components/TrajectoryChart.vue'
import CollectView from './components/collect/CollectView.vue'
import { applyTheme } from './theme'
import GuideTour from './guide/GuideTour.vue'
import { collectTour, dashboardTour, type TourName } from './guide/content'

type View = 'dashboard' | 'collect'
function savedView(): View {
  try {
    return localStorage.getItem('fire.view') === 'collect' ? 'collect' : 'dashboard'
  } catch {
    return 'dashboard'
  }
}
const view = ref<View>(savedView())
function setView(v: View) {
  view.value = v
  try {
    localStorage.setItem('fire.view', v)
  } catch {
    /* private mode */
  }
}
const collectView = ref<InstanceType<typeof CollectView>>()

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
    if (was && !status.value.refreshing) {
      await loadAll()
      collectView.value?.load()
    }
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
  api.game().then((g) => applyTheme(g.themes, g.settings.theme)).catch(() => {})
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
// ---- Guided tour: shown once per view on first visit, replayable from the header.
const tour = ref<TourName | null>(null)
const tourSteps = computed(() =>
  tour.value === 'collect' ? collectTour() : dashboardTour(summary.value, config.value),
)
const seenKey = (t: TourName) => 'fire.tour.' + t
function seen(t: TourName): boolean {
  try {
    return localStorage.getItem(seenKey(t)) === 'done'
  } catch {
    return true // no storage: never nag on every visit
  }
}
function startTour() {
  tour.value = view.value
}
function closeTour() {
  if (tour.value) {
    try {
      localStorage.setItem(seenKey(tour.value), 'done')
    } catch {
      /* private mode */
    }
  }
  tour.value = null
}
watch(
  () => [view.value, !!summary.value] as const,
  ([v, loaded]) => {
    if (tour.value || seen(v)) return
    if (v === 'dashboard' && !loaded) return
    tour.value = v
  },
  { immediate: true },
)

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
        <svg viewBox="0 0 32 32" class="h-9 w-9 text-accent" aria-hidden="true">
          <path d="M16 3C18 10 25 13 25 21a9 9 0 0 1-18 0c0-4 2-6 4-8 0 3 1 5 3 5-1-6 1-11 2-15z" fill="currentColor" />
          <path d="M16 15c1 3 4 4 4 7a4 4 0 0 1-8 0c0-2 1-3 2-4 0 1 .5 2 1.5 2-.5-2 0-4 .5-5z" fill="#ffd36e" />
        </svg>
        <div>
          <h1 class="display text-xl tracking-tight">FireDashboard</h1>
          <p class="text-xs text-ink-400">
            <span>{{ updatedLabel }}</span>
            <span v-if="hasErrors" class="ml-2 cursor-help text-warm" :title="errorDetail">・部分標的更新失敗</span>
          </p>
        </div>
      </div>
      <div class="flex flex-wrap gap-2">
        <div class="flex rounded-lg border border-ink-700 p-0.5 text-sm" role="tablist" aria-label="檢視模式" data-tour="view-switch">
          <button
            v-for="v in (['dashboard', 'collect'] as const)"
            :key="v"
            role="tab"
            :aria-selected="view === v"
            class="display rounded-md px-3 py-1 transition"
            :class="view === v ? 'bg-accent text-ink-950' : 'text-ink-300 hover:text-ink-100'"
            @click="setView(v)"
          >
            {{ v === 'dashboard' ? '儀表板' : '收集冊' }}
          </button>
        </div>
        <button class="btn-ghost" data-tour="help" title="操作導覽" @click="startTour">
          <svg viewBox="0 0 20 20" class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><circle cx="10" cy="10" r="7.5" /><path d="M7.8 7.8a2.3 2.3 0 0 1 4.4.9c0 1.5-2.2 1.9-2.2 3.3M10 14.4v.1" stroke-linecap="round" /></svg>
          導覽
        </button>
        <SoundToggle />
        <button class="btn-ghost" data-tour="refresh" :disabled="status?.refreshing" @click="refreshNow">
          <svg viewBox="0 0 20 20" class="h-4 w-4" :class="status?.refreshing ? 'animate-spin' : ''" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M16 10a6 6 0 1 1-1.8-4.3M16 3v4h-4" /></svg>
          更新報價
        </button>
        <button class="btn-ghost" data-tour="config" :disabled="!config" @click="showConfig = true">
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

    <CollectView v-if="view === 'collect'" ref="collectView" />
    <div v-else-if="summary && holdings && projection" class="grid grid-cols-[minmax(0,1fr)] gap-4">
      <CampfireHero :summary="summary" :holdings="holdings" />
      <div class="grid gap-4 lg:grid-cols-[minmax(0,1fr)_18rem]">
        <TrajectoryChart data-tour="trajectory" :projection="projection" :history="history" :time-to-coast="summary.time_to_coast" />
        <StressCard data-tour="stress" :summary="summary" />
      </div>
      <HoldingsTable data-tour="holdings" :holdings="holdings" @add="showAdd = true" @add-contract="contractFor = 'new'" @record="recordFor = $event" @edit="onEdit" />
      <DividendsCard data-tour="dividends" :dividends="dividends" />
    </div>
    <div v-else-if="!loadError && view === 'dashboard'" class="grid gap-4" aria-busy="true">
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
    <GuideTour v-if="tour" :key="tour" :steps="tourSteps" @close="closeTour" />
  </div>
</template>
