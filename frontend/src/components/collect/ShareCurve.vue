<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref, shallowRef, watch } from 'vue'
import * as echarts from 'echarts/core'
import { LineChart, ScatterChart } from 'echarts/charts'
import { GridComponent, MarkLineComponent, TooltipComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import type { CollectRow } from '../../api'
import { shares } from '../../format'
import { accentColor } from '../../theme'

echarts.use([LineChart, ScatterChart, GridComponent, TooltipComponent, MarkLineComponent, CanvasRenderer])

const props = defineProps<{ row: CollectRow; today: string }>()
const el = ref<HTMLDivElement>()
const chart = shallowRef<echarts.ECharts>()
const singleDay = () => new Set([...props.row.curve.map((p) => p.date), props.today]).size < 2

const KIND: Record<string, string> = { buy: '買入', sell: '賣出', adjust: '調整', deposit: '存入', withdraw: '提出' }

function option(): echarts.EChartsCoreOption {
  const r = props.row
  const pts = r.curve.map((p) => [p.date, p.shares])
  if (pts.length) pts.push([props.today, r.shares])
  const sells = r.events.filter((e) => e.delta < 0).map((e) => ({ value: [e.date, e.total], ev: e }))
  const marks: object[] = []
  if (r.next_milestone) {
    marks.push({ yAxis: r.next_milestone, name: '下一階', label: { formatter: '下一階 ' + r.next_label } })
  }
  if (r.target_shares) marks.push({ yAxis: r.target_shares, name: '籃子', label: { formatter: '籃子目標' }, lineStyle: { color: '#fbbf24' } })
  const accent = accentColor()
  return {
    animationDuration: 600,
    grid: { left: 8, right: 16, top: 24, bottom: 8, containLabel: true },
    tooltip: {
      trigger: 'axis',
      backgroundColor: '#111a2e',
      borderColor: '#24324f',
      textStyle: { color: '#e6ecf7' },
      formatter: (ps: { seriesName: string; value: [string, number]; data: { ev?: { note: string | null; kind: string } } }[]) => {
        const p = ps[0]
        let s = p.value[0] + '<br/>' + shares(p.value[1], r.market)
        for (const x of ps) if (x.data?.ev) s += '<br/>' + KIND[x.data.ev.kind] + (x.data.ev.note ? '：' + x.data.ev.note : '')
        return s
      },
    },
    xAxis: { type: 'time', minInterval: 86400000, axisLine: { lineStyle: { color: '#34456a' } }, axisLabel: { color: '#8393b3' }, splitLine: { show: false } },
    yAxis: {
      type: 'value',
      min: 0,
      axisLabel: { color: '#8393b3', formatter: (v: number) => (r.market === 'TW' ? v / 1000 + ' 張' : String(v)) },
      splitLine: { lineStyle: { color: '#24324f' } },
    },
    series: [
      {
        name: '股數',
        type: 'line',
        step: 'end',
        data: pts,
        showSymbol: false,
        lineStyle: { color: accent, width: 2 },
        areaStyle: { color: accent, opacity: 0.12 },
        markLine: { symbol: 'none', silent: true, lineStyle: { type: 'dashed', color: '#8393b3' }, label: { color: '#a9b6cf', position: 'insideEndTop' }, data: marks },
      },
      { name: '賣出', type: 'scatter', data: sells, symbolSize: 9, itemStyle: { color: '#93c5fd' } },
    ],
  }
}

function draw() {
  if (singleDay()) {
    chart.value?.dispose()
    chart.value = undefined
    return
  }
  if (!chart.value) chart.value = echarts.init(el.value!)
  chart.value.setOption(option(), true)
}

onMounted(() => {
  draw()
  window.addEventListener('resize', resize)
})
function resize() {
  chart.value?.resize()
}
watch(() => props.row, () => nextTick(draw))
onBeforeUnmount(() => {
  window.removeEventListener('resize', resize)
  chart.value?.dispose()
})
</script>

<template>
  <article class="card">
    <div class="mb-2 flex flex-wrap items-end justify-between gap-2">
      <div>
        <h2 class="text-sm font-semibold">{{ row.label }} 收集曲線</h2>
        <p class="text-xs text-ink-400">分割前的股數已換算成現在的單位，所以分割當天不會跳升。賣出的點會如實下降，滑過可看當時的備註。</p>
      </div>
    </div>
    <div v-show="!singleDay()" ref="el" class="h-64 w-full" role="img" :aria-label="row.label + ' 股數變化圖'" />
    <p v-if="singleDay()" class="grid h-32 place-items-center rounded-xl bg-ink-950/50 text-sm text-ink-400">
      今天是收集的第一天，之後每次記錄買進，曲線就會一點一點長出來。
    </p>
  </article>
</template>
