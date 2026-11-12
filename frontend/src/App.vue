<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import {
  api,
  type Config,
  type ContractInfo,
  type DividendRow,
  type HistoryPoint,
  type Holdings,
  type LoanInfo,
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
import LoanDialog from './components/LoanDialog.vue'
import LoansCard from './components/LoansCard.vue'
import ShareLogDialog from './components/ShareLogDialog.vue'
import StressCard from './components/StressCard.vue'
import CampfireHero from './components/CampfireHero.vue'
import SoundToggle from './components/SoundToggle.vue'
import TrajectoryChart from './components/TrajectoryChart.vue'
import CollectView from './components/collect/CollectView.vue'
import { applyTheme } from './theme'
import GuideTour from './guide/GuideTour.vue'
import { collectTour, dashboardTour, type TourName, type TourStep } from './guide/content'
import BottomTabs from './components/BottomTabs.vue'
import PullRefresh from './components/PullRefresh.vue'
import QuickAddSheet from './components/QuickAddSheet.vue'
import { isMobile, type MobileTab } from './mobile'
import { hideSplash, offlineSince } from './pwa'
import { onLogoTap } from './viewport-debug'

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

// ---- Phone layout: bottom tabs. 收集冊 is the collect view; the other three split the dashboard.
function savedTab(): MobileTab {
  if (view.value === 'collect') return 'book'
  try {
    const t = localStorage.getItem('fire.tab')
    return t === 'logs' || t === 'path' ? t : 'fire'
  } catch {
    return 'fire'
  }
}
const mobileTab = ref<MobileTab>(savedTab())
function setTab(t: MobileTab) {
  const changed = t !== mobileTab.value
  mobileTab.value = t
  setView(t === 'book' ? 'collect' : 'dashboard')
  try {
    if (t !== 'book') localStorage.setItem('fire.tab', t)
  } catch {
    /* private mode */
  }
  if (changed) window.scrollTo({ top: 0 })
}
// Desktop switch to 收集冊 and back keeps the phone tab in step (window resized across the breakpoint).
watch(view, (v) => {
  if (v === 'collect') mobileTab.value = 'book'
  else if (mobileTab.value === 'book') mobileTab.value = 'fire'
})
/** On a phone only the current tab's sections render; on larger screens everything does. */
const shows = (t: MobileTab) => !isMobile.value || mobileTab.value === t

const summary = ref<Summary>()
const holdings = ref<Holdings>()
const projection = ref<Projection>()
const history = ref<HistoryPoint[]>([])
const dividends = ref<DividendRow[]>([])
const loans = ref<LoanInfo[]>([])
const config = ref<Config>()
const status = ref<Status>()
const loadError = ref('')

const showConfig = ref(false)
const showAdd = ref(false)
const recordFor = ref<Position | null>(null)
const editFor = ref<Position | null>(null)
const contractFor = ref<ContractInfo | 'new' | null>(null)
const loanFor = ref<LoanInfo | 'new' | null>(null)
const showQuick = ref(false)

function onEdit(p: Position) {
  if (p.contract) contractFor.value = p.contract
  else editFor.value = p
}

// A log in the campfire was tapped: open that holding, or the list for a grouped log.
const holdingsEl = ref<InstanceType<typeof HoldingsTable>>()
function onPickLog(symbol: string | null) {
  const p = symbol ? holdings.value?.rows.find((r) => r.symbol === symbol) : undefined
  if (p?.contract) contractFor.value = p.contract
  else if (p) recordFor.value = p
  else if (isMobile.value) setTab('logs')
  else (holdingsEl.value?.$el as HTMLElement | undefined)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}
function quickPick(p: Position) {
  showQuick.value = false
  recordFor.value = p
}

async function loadAll() {
  try {
    const [s, h, p, hi, d, c, st, lo] = await Promise.all([
      api.summary(),
      api.holdings(),
      api.projection(),
      api.history(),
      api.dividends(),
      api.config(),
      api.status(),
      api.loans(),
    ])
    summary.value = s
    holdings.value = h
    projection.value = p
    history.value = hi
    dividends.value = d
    config.value = c
    status.value = st
    loans.value = lo
    loadError.value = ''
  } catch (e) {
    loadError.value = (e as Error).message
  } finally {
    hideSplash()
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
  tour.value === 'collect' ? collectTour() : dashboardTour(summary.value, config.value, isMobile.value),
)
function onTourStep(st: TourStep) {
  if (isMobile.value && st.tab && st.tab !== mobileTab.value) setTab(st.tab)
}
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

const offlineLabel = computed(() => {
  const at = offlineSince.value
  if (at == null) return ''
  const d = at ? new Date(at) : null
  const when = d && !Number.isNaN(d.getTime())
    ? `${d.getMonth() + 1}/${d.getDate()} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
    : '上次'
  return `目前離線，顯示 ${when} 的資料。連上網路後會自動更新。`
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
  <div
    class="app-shell mx-auto max-w-7xl px-4 pt-[max(1rem,calc(env(safe-area-inset-top)+0.5rem))] pb-28 sm:px-6 md:pb-6 lg:pt-8 lg:pb-8"
  >
    <header class="mb-4 flex items-center justify-between gap-x-3 gap-y-3 md:mb-6 md:flex-wrap md:gap-x-4">
      <div class="flex min-w-0 items-center gap-3">
        <svg viewBox="0 0 32 32" class="logo h-9 w-9 flex-none text-accent" aria-hidden="true" @click="onLogoTap">
          <path class="outer" d="M16 3C18 10 25 13 25 21a9 9 0 0 1-18 0c0-4 2-6 4-8 0 3 1 5 3 5-1-6 1-11 2-15z" fill="currentColor" />
          <path class="inner" d="M16 15c1 3 4 4 4 7a4 4 0 0 1-8 0c0-2 1-3 2-4 0 1 .5 2 1.5 2-.5-2 0-4 .5-5z" fill="#ffd36e" />
        </svg>
        <div class="min-w-0">
          <h1 class="display truncate text-lg tracking-tight md:text-xl">FireDashboard</h1>
          <p class="truncate text-xs text-ink-400">
            <span>{{ updatedLabel }}</span>
            <span v-if="hasErrors" class="ml-2 cursor-help text-warm" :title="errorDetail">・部分標的更新失敗</span>
          </p>
        </div>
      </div>
      <div class="hdr-btns flex flex-none gap-1 md:flex-wrap md:gap-2">
        <div class="hidden rounded-lg border border-ink-700 p-0.5 text-sm md:flex" role="tablist" aria-label="檢視模式" data-tour="view-switch">
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
        <button class="btn-ghost" data-tour="help" title="操作導覽" aria-label="操作導覽" @click="startTour">
          <svg viewBox="0 0 20 20" class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><circle cx="10" cy="10" r="7.5" /><path d="M7.8 7.8a2.3 2.3 0 0 1 4.4.9c0 1.5-2.2 1.9-2.2 3.3M10 14.4v.1" stroke-linecap="round" /></svg>
          <span class="hidden sm:inline">導覽</span>
        </button>
        <SoundToggle />
        <button class="btn-ghost" data-tour="refresh" :disabled="status?.refreshing" aria-label="更新報價" @click="refreshNow">
          <svg viewBox="0 0 20 20" class="h-4 w-4" :class="status?.refreshing ? 'animate-spin' : ''" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><path d="M16 10a6 6 0 1 1-1.8-4.3M16 3v4h-4" /></svg>
          <span class="hidden sm:inline">更新報價</span>
        </button>
        <button class="btn-ghost" data-tour="config" :disabled="!config" aria-label="參數設定" @click="showConfig = true">
          <svg viewBox="0 0 20 20" class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><path d="M4 6h8M16 6h0M4 14h2M10 14h6" /><circle cx="14" cy="6" r="2" /><circle cx="8" cy="14" r="2" /></svg>
          <span class="hidden sm:inline">參數設定</span>
        </button>
      </div>
    </header>

    <p v-if="offlineLabel" class="mb-4 flex items-center gap-2 rounded-xl border border-ink-700 bg-ink-900 px-4 py-3 text-sm text-ink-300" role="status">
      <svg viewBox="0 0 24 24" class="h-5 w-5 flex-none text-calm" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" aria-hidden="true"><path d="M6.5 18a4.5 4.5 0 0 1-.9-8.9A6 6 0 0 1 17 8.4 4.8 4.8 0 0 1 18 18z" /><path d="M4 4l16 16" /></svg>
      {{ offlineLabel }}
    </p>
    <p v-else-if="loadError" class="mb-4 rounded-xl border border-amber-800/60 bg-amber-950/40 px-4 py-3 text-sm text-warm" role="alert">
      無法連線到後端：{{ loadError }}
    </p>
    <p
      v-if="summary?.missing_prices.length && view === 'dashboard'"
      class="mb-4 rounded-xl border border-ink-700 bg-ink-900 px-4 py-3 text-sm text-ink-300"
    >
      {{ summary.missing_prices.join('、') }} 還沒有報價，總資產暫時不含這些標的。
    </p>

    <CollectView v-if="view === 'collect'" ref="collectView" />
    <div v-else-if="summary && holdings && projection" class="grid grid-cols-[minmax(0,1fr)] gap-4">
      <CampfireHero v-if="shows('fire')" :summary="summary" :holdings="holdings" @pick="onPickLog" />
      <div v-if="shows('path')" class="grid gap-4 lg:grid-cols-[minmax(0,1fr)_18rem]">
        <TrajectoryChart data-tour="trajectory" :projection="projection" :history="history" :time-to-coast="summary.time_to_coast" />
        <StressCard data-tour="stress" :summary="summary" />
      </div>
      <HoldingsTable
        v-if="shows('logs')"
        ref="holdingsEl"
        data-tour="holdings"
        :holdings="holdings"
        @add="showAdd = true"
        @add-contract="contractFor = 'new'"
        @add-loan="loanFor = 'new'"
        @record="recordFor = $event"
        @edit="onEdit"
      />
      <LoansCard
        v-if="shows('logs') && loans.length"
        data-tour="loans"
        :loans="loans"
        :total-assets="holdings.total_twd"
        @add="loanFor = 'new'"
        @edit="loanFor = $event"
      />
      <DividendsCard v-if="shows('logs')" data-tour="dividends" :dividends="dividends" />
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

    <BottomTabs :tab="mobileTab" @update:tab="setTab" @add="showQuick = true" />
    <PullRefresh :refreshing="!!status?.refreshing" @refresh="refreshNow" />

    <QuickAddSheet
      v-if="showQuick"
      :holdings="holdings"
      @close="showQuick = false"
      @pick="quickPick"
      @add="(showQuick = false), (showAdd = true)"
      @add-contract="(showQuick = false), (contractFor = 'new')"
    />
    <ConfigModal v-if="showConfig && config" :config="config" @close="showConfig = false" @saved="loadAll" />
    <AddHoldingDialog v-if="showAdd" @close="showAdd = false" @added="afterAdd" />
    <ShareLogDialog v-if="recordFor" :position="recordFor" @close="recordFor = null" @changed="loadAll" />
    <ContractDialog
      v-if="contractFor"
      :contract="contractFor === 'new' ? undefined : contractFor"
      @close="contractFor = null"
      @changed="loadAll"
    />
    <LoanDialog
      v-if="loanFor"
      :loan="loanFor === 'new' ? undefined : loanFor"
      @close="loanFor = null"
      @changed="loadAll"
    />
    <HoldingEditDialog v-if="editFor" :position="editFor" @close="editFor = null" @changed="loadAll" />
    <GuideTour v-if="tour" :key="tour" :steps="tourSteps" @close="closeTour" @step="onTourStep" />
  </div>
</template>

<style scoped>
/* Phones: icon-only header buttons on one row with the title. */
@media (max-width: 639px) {
  .hdr-btns :deep(.btn-ghost) { padding: 0.5rem; border-color: transparent; }
}
/*
 * iOS home-screen app: iOS blurs a band just below the status bar, deeper than
 * the safe-area inset, so start the header clear of it.
 */
@media (display-mode: standalone) and (max-width: 767px) {
  .app-shell { padding-top: calc(env(safe-area-inset-top) + 2rem); }
}
/* The header flame breathes, a quiet sign the app is alive. */
.logo .outer,
.logo .inner {
  transform-box: fill-box;
  transform-origin: 50% 100%;
  animation: breathe 2.6s ease-in-out infinite alternate;
}
.logo .inner { animation-duration: 1.7s; animation-delay: -0.5s; }
@keyframes breathe {
  0% { transform: scale(1, 1) skewX(0); }
  50% { transform: scale(0.96, 1.05) skewX(2deg); }
  100% { transform: scale(1.02, 0.97) skewX(-1.5deg); }
}
@media (prefers-reduced-motion: reduce) {
  .logo .outer, .logo .inner { animation: none; }
}
</style>
