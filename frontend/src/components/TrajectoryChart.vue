<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, shallowRef, watch } from 'vue'
import * as echarts from 'echarts/core'
import { LineChart } from 'echarts/charts'
import { GridComponent, LegendComponent, MarkLineComponent, MarkPointComponent, TooltipComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import type { HistoryPoint, Projection, TimeToCoast } from '../api'
import { wan, ym } from '../format'

echarts.use([LineChart, GridComponent, LegendComponent, TooltipComponent, MarkLineComponent, MarkPointComponent, CanvasRenderer])

const props = defineProps<{ projection: Projection; history: HistoryPoint[]; timeToCoast: TimeToCoast }>()

const el = ref<HTMLDivElement>()
const chart = shallowRef<echarts.ECharts>()
const range = ref<'10y' | 'all'>('all')

const COLORS = {
  history: '#2dd4bf',
  withC: '#93c5fd',
  noC: '#8393b3',
  coast: '#fbbf24',
  grid: '#24324f',
  axis: '#8393b3',
}

const data = computed(() => {
  // Last snapshot of each month, in today's TWD.
  const hist = new Map<string, number>()
  for (const h of props.history) hist.set(h.date.slice(0, 7), h.total_value_real)
  let proj = props.projection.series
  if (range.value === '10y') proj = proj.slice(0, 121)
  const months = [...new Set([...hist.keys(), ...proj.map((p) => p.month)])].sort()
  const byMonth = new Map(proj.map((p) => [p.month, p]))
  return {
    months,
    history: months.map((m) => hist.get(m) ?? null),
    withC: months.map((m) => byMonth.get(m)?.with_contribution ?? null),
    noC: months.map((m) => byMonth.get(m)?.no_contribution ?? null),
    coast: months.map((m) => byMonth.get(m)?.coast_target ?? null),
  }
})

function option(): echarts.EChartsCoreOption {
  const d = data.value
  const hit = props.timeToCoast.status === 'reachable' ? props.timeToCoast.month : null
  const hitIdx = hit ? d.months.indexOf(hit) : -1
  const line = (name: string, values: (number | null)[], color: string, extra: object = {}) => ({
    name,
    type: 'line',
    data: values,
    showSymbol: false,
    connectNulls: false,
    lineStyle: { color, width: 2 },
    itemStyle: { color },
    emphasis: { focus: 'series' },
    ...extra,
  })
  return {
    backgroundColor: 'transparent',
    animationDuration: 600,
    grid: { left: 8, right: 16, top: 40, bottom: 8, containLabel: true },
    legend: {
      top: 0,
      left: 0,
      icon: 'roundRect',
      itemWidth: 14,
      itemHeight: 4,
      textStyle: { color: '#a9b6cf', fontSize: 12 },
    },
    tooltip: {
      trigger: 'axis',
      backgroundColor: '#111a2e',
      borderColor: '#34456a',
      textStyle: { color: '#e6ecf7', fontSize: 12 },
      valueFormatter: (v: unknown) => (typeof v === 'number' ? wan(v) : '—'),
      axisPointer: { lineStyle: { color: '#34456a' } },
    },
    xAxis: {
      type: 'category',
      data: d.months,
      boundaryGap: false,
      axisLine: { lineStyle: { color: COLORS.grid } },
      axisTick: { show: false },
      axisLabel: { color: COLORS.axis, formatter: (v: string) => (v.endsWith('-01') ? v.slice(0, 4) : '') , interval: 0, hideOverlap: true },
    },
    yAxis: {
      type: 'value',
      splitLine: { lineStyle: { color: COLORS.grid, type: 'dashed' } },
      axisLabel: { color: COLORS.axis, formatter: (v: number) => wan(v) },
    },
    series: [
      line('Coast 門檻', d.coast, COLORS.coast, { lineStyle: { color: COLORS.coast, width: 1.5, type: [6, 4] } }),
      line('零投入複利', d.noC, COLORS.noC, { lineStyle: { color: COLORS.noC, width: 1.5, type: [2, 4] } }),
      line('持續定期定額', d.withC, COLORS.withC, {
        markPoint:
          hitIdx >= 0
            ? {
                symbol: 'circle',
                symbolSize: 10,
                itemStyle: { color: COLORS.coast, borderColor: '#0b1220', borderWidth: 2 },
                label: { show: true, position: 'top', color: '#fbbf24', fontSize: 12, formatter: '達成 ' + ym(hit) },
                data: [{ coord: [hitIdx, d.withC[hitIdx]] }],
              }
            : undefined,
      }),
      line('歷史真實資產', d.history, COLORS.history, {
        lineStyle: { color: COLORS.history, width: 2.5 },
        areaStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: 'rgba(45,212,191,0.25)' },
          { offset: 1, color: 'rgba(45,212,191,0)' },
        ]) },
      }),
    ],
  }
}

function render() {
  chart.value?.setOption(option(), true)
}

let ro: ResizeObserver | undefined
onMounted(() => {
  chart.value = echarts.init(el.value!, undefined, { renderer: 'canvas' })
  render()
  ro = new ResizeObserver(() => chart.value?.resize())
  ro.observe(el.value!)
})
onBeforeUnmount(() => {
  ro?.disconnect()
  chart.value?.dispose()
})
watch(() => [props.projection, props.history, props.timeToCoast, range.value], render)
</script>

<template>
  <section class="card">
    <div class="mb-3 flex flex-wrap items-center justify-between gap-2">
      <div>
        <h2 class="text-sm font-semibold">Coast FIRE 雙軌預測</h2>
        <p class="text-xs text-ink-400">全部以今日台幣購買力計算；歷史資產已依通膨換算</p>
      </div>
      <div class="flex rounded-lg border border-ink-700 p-0.5 text-xs" role="group" aria-label="時間範圍">
        <button
          v-for="opt in [{ k: '10y', t: '未來 10 年' }, { k: 'all', t: '到退休' }] as const"
          :key="opt.k"
          class="rounded-md px-2.5 py-1"
          :class="range === opt.k ? 'bg-ink-700 text-ink-100' : 'text-ink-400 hover:text-ink-100'"
          @click="range = opt.k"
        >
          {{ opt.t }}
        </button>
      </div>
    </div>
    <div ref="el" class="h-80 w-full sm:h-96" role="img" aria-label="Coast FIRE 預測圖" />
  </section>
</template>
