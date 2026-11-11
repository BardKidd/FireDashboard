<script setup lang="ts">
import { computed } from 'vue'
import type { Holdings, Position, Summary } from '../api'
import { money, pct, wan, ym } from '../format'
import InfoTip from '../guide/InfoTip.vue'

const props = defineProps<{ summary: Summary; holdings: Holdings }>()

// ---- Numbers (same as the old summary cards) ----
const progress = computed(() => props.summary.progress ?? 0)
const ttc = computed(() => props.summary.time_to_coast)
const retireAge = computed(() => Math.round(props.summary.age_years + props.summary.months_remaining / 12))
const yearsLeft = computed(() => {
  const m = ttc.value.months ?? 0
  const y = Math.floor(m / 12)
  const r = m % 12
  return (y ? y + ' 年 ' : '') + (r ? r + ' 個月' : y ? '' : '不到 1 個月')
})
const fxLabel = computed(() => {
  const fx = props.summary.fx
  const name = { live: '即時', ma200: '200 日均', custom: '自訂' }[fx.mode]
  return fx.used ? name + '匯率 ' + fx.used.toFixed(2) : '尚無匯率'
})
const windy = computed(() => (props.summary.day_change_twd ?? 0) < 0)

const headline = computed(() => {
  if (!props.summary.progress) return '還沒點火。加入第一筆持股，火就會亮起來。'
  if (ttc.value.status === 'achieved') return `火已經燒過 Coast 線。就算不再添柴，也能一直燒到 ${retireAge.value} 歲。`
  if (ttc.value.status === 'reachable')
    return `火勢 ${pct(props.summary.progress)}。照現在每月添柴，${ym(ttc.value.month)}起不用再添也會一直燒。`
  return `火勢 ${pct(props.summary.progress)}。照目前的添柴速度，退休前還燒不到 Coast 線，可以調整投入或目標。`
})

// ---- Logs: each log is a holding (or a group of small ones), thickness by weight ----
interface Log { label: string; weight: number }

function category(p: Position): string {
  if (p.market === 'CONTRACT') return '約定存款'
  if (p.market === 'CASH') return '現金'
  if (p.asset_type === 'bond') return '債券'
  if (p.asset_type === 'leveraged') return p.market === 'TW' ? '台股槓桿' : '美股槓桿'
  return p.market === 'TW' ? '台股' : '美股'
}

const logs = computed<Log[]>(() => {
  const live = props.holdings.rows.filter((r) => !r.archived && r.weight > 0.0005)
  const out: Log[] = live.filter((r) => r.weight >= 0.05).map((r) => ({
    label: r.market === 'CONTRACT' || r.market === 'CASH' ? category(r) : r.symbol,
    weight: r.weight,
  }))
  const groups = new Map<string, { w: number; n: number }>()
  for (const r of live.filter((r) => r.weight < 0.05)) {
    const g = groups.get(category(r)) ?? { w: 0, n: 0 }
    g.w += r.weight
    g.n += 1
    groups.set(category(r), g)
  }
  for (const [k, g] of groups) out.push({ label: g.n > 1 && k !== '約定存款' ? `${k} ${g.n} 檔` : k, weight: g.w })
  out.sort((a, b) => b.weight - a.weight)
  if (out.length > 8) {
    const rest = out.splice(7)
    out.push({ label: `其他 ${rest.length} 組`, weight: rest.reduce((s, l) => s + l.weight, 0) })
  }
  return out
})

// Seen from ~45° above: the ground is a squashed ellipse.
const CX = 400
const CY = 280
const K = 0.55
const ANGLES = [1.15, 4.1, 2.35, 5.85, 0.35, 3.2, 5.15, 3.75]
const P = (r: number, a: number, lift = 0) => [CX + r * Math.cos(a), CY + r * Math.sin(a) * K - lift] as const

const logShapes = computed(() =>
  logs.value.map((l, i) => {
    const a = ANGLES[i]
    const thick = 7 + Math.sqrt(l.weight * 100) * 3.2
    const [x0, y0] = P(18, a, 40)
    const [x1, y1] = P(128, a, 4)
    const dx = x1 - x0
    const dy = y1 - y0
    const len = Math.hypot(dx, dy)
    const nx = (-dy / len) * (thick / 2)
    const ny = (dx / len) * (thick / 2)
    const [lx, ly] = P(152 + thick, a, -6)
    return {
      key: l.label,
      back: Math.sin(a) < 0,
      body: `M${x0 + nx} ${y0 + ny} L${x1 + nx} ${y1 + ny} L${x1 - nx} ${y1 - ny} L${x0 - nx} ${y0 - ny} Z`,
      grain: `M${x0 + nx * 0.5} ${y0 + ny * 0.5} L${x1 + nx * 0.5} ${y1 + ny * 0.5}`,
      char: `M${x0} ${y0} L${(x0 + x1) / 2} ${(y0 + y1) / 2}`,
      thick,
      x1,
      y1,
      rot: (Math.atan2(dy, dx) * 180) / Math.PI,
      lx,
      ly: ly + 4,
      anchor: Math.cos(a) > 0.25 ? 'start' : Math.cos(a) < -0.25 ? 'end' : 'middle',
      text: `${l.label} ${(l.weight * 100).toFixed(1)}%`,
    }
  }),
)

const stones = Array.from({ length: 16 }, (_, i) => {
  const a = (i / 16) * Math.PI * 2 + 0.1
  const [x, y] = P(152, a)
  return { x, y, w: 17 + ((i * 7) % 8), back: Math.sin(a) < 0 }
})

const LEAF = 'M0 -10 L2 -4 L7 -6 L5 -1 L10 1 L5 3 L6 8 L1 5 L0 10 L-1 5 L-6 8 L-5 3 L-10 1 L-5 -1 L-7 -6 L-2 -4 Z'
const LEAF_COLORS = ['#c8642c', '#a8452a', '#d9a441', '#8a3a22', '#d9822b']
const leaves = [
  [120, 330, 20], [190, 360, 30], [630, 345, 60], [690, 310, 10], [560, 372, -50],
  [235, 300, 80], [712, 372, -15], [86, 362, 40], [528, 318, 110],
].map(([x, y, r], i) => {
  const s = 1 + (i % 3) * 0.25
  return { t: `translate(${x} ${y}) rotate(${r}) scale(${s} ${s * 0.7})`, fill: LEAF_COLORS[i % LEAF_COLORS.length] }
})

// Flame height follows Coast progress; the dashed outline is 100 %.
const BASE_Y = CY - 26
const flameScale = computed(() => Math.min(1.25, Math.max(0.12, progress.value)))
const TARGET_TOP = BASE_Y - 170
const sparks = computed(() =>
  Array.from({ length: Math.round(5 + 10 * flameScale.value) }, (_, i) => ({
    x: CX + ((i * 37) % 60) - 30,
    y: BASE_Y - 170 * flameScale.value * 0.6 + ((i * 13) % 40),
    r: 1.2 + (i % 3) * 0.6,
    fill: i % 2 ? '#ffd36e' : '#ff8a3d',
    style: { '--d': 3 + (i % 5) * 0.7 + 's', '--delay': -i * 0.45 + 's', '--dx': (i % 2 ? 1 : -1) * (8 + i * 3) + 'px' },
  })),
)
</script>

<template>
  <section class="hero grid grid-cols-[minmax(0,1fr)] items-center gap-x-8 gap-y-2 lg:grid-cols-[minmax(0,1.35fr)_minmax(0,1fr)]" aria-label="核心指標">
    <svg
      viewBox="0 0 800 400"
      class="w-full"
      data-tour="campfire"
      role="img"
      :aria-label="`營火：每根柴是一組持股，火勢是 Coast FIRE 達成率 ${pct(summary.progress)}`"
    >
      <defs>
        <radialGradient id="cf-glow" cx="50%" cy="50%" r="50%">
          <stop offset="0" stop-color="#ff8a3d" stop-opacity=".45" />
          <stop offset=".5" stop-color="#c85a1e" stop-opacity=".15" />
          <stop offset="1" stop-color="#c85a1e" stop-opacity="0" />
        </radialGradient>
        <linearGradient id="cf-outer" x1="0" y1="1" x2="0" y2="0">
          <stop offset="0" stop-color="#ff6a2b" /><stop offset="1" stop-color="#c8371a" stop-opacity=".85" />
        </linearGradient>
        <linearGradient id="cf-mid" x1="0" y1="1" x2="0" y2="0">
          <stop offset="0" stop-color="#ffb347" /><stop offset="1" stop-color="#ff7a2e" />
        </linearGradient>
        <linearGradient id="cf-in" x1="0" y1="1" x2="0" y2="0">
          <stop offset="0" stop-color="#fff3c4" /><stop offset="1" stop-color="#ffd36e" />
        </linearGradient>
      </defs>

      <ellipse class="glow" :cx="CX" :cy="CY" rx="340" ry="150" fill="url(#cf-glow)" :style="{ opacity: 0.5 + flameScale * 0.5 }" />
      <path v-for="(l, i) in leaves" :key="'lf' + i" :d="LEAF" :transform="l.t" :fill="l.fill" opacity=".8" />

      <g v-for="(s, i) in stones.filter((s) => s.back)" :key="'sb' + i">
        <ellipse :cx="s.x" :cy="s.y + 4" :rx="s.w" :ry="s.w * 0.55" fill="#3b302a" />
        <ellipse :cx="s.x" :cy="s.y" :rx="s.w * 0.9" :ry="s.w * 0.48" fill="#6d6058" />
        <ellipse :cx="s.x - 3" :cy="s.y - 2" :rx="s.w * 0.45" :ry="s.w * 0.2" fill="#8f8178" opacity=".7" />
      </g>
      <g v-for="l in logShapes.filter((l) => l.back)" :key="'lb' + l.key">
        <path :d="l.body" fill="#5a3b26" />
        <path :d="l.grain" stroke="#7a5236" :stroke-width="l.thick * 0.18" fill="none" />
        <path :d="l.char" stroke="#1b110c" :stroke-width="l.thick * 0.9" stroke-opacity=".55" stroke-linecap="round" fill="none" />
        <ellipse :cx="l.x1" :cy="l.y1" :rx="l.thick * 0.32" :ry="l.thick / 2" :transform="`rotate(${l.rot} ${l.x1} ${l.y1})`" fill="#d9b07a" />
        <ellipse :cx="l.x1" :cy="l.y1" :rx="l.thick * 0.18" :ry="l.thick * 0.28" :transform="`rotate(${l.rot} ${l.x1} ${l.y1})`" fill="none" stroke="#a8794a" stroke-width="1.2" />
      </g>

      <!-- Coast line: the flame size that means "no more logs needed" -->
      <path
        d="M-48 0 C-48 -70 -12 -110 0 -170 C12 -110 48 -70 48 0 Z"
        :transform="`translate(${CX} ${BASE_Y})`"
        fill="none"
        stroke="#ffd36e"
        stroke-opacity=".5"
        stroke-dasharray="4 6"
      />
      <text :x="CX + 40" :y="TARGET_TOP + 8" class="display" font-size="15" fill="#ffd36e">Coast 線 · {{ wan(summary.coast_target) }}</text>
      <text :x="CX - 40" :y="TARGET_TOP + 8" class="display" font-size="15" fill="#f2e8dc" text-anchor="end">現在 · {{ wan(summary.total_assets) }}</text>

      <g v-if="progress > 0" :transform="`translate(${CX} ${BASE_Y}) scale(${flameScale})`">
        <g :class="{ windy }">
          <path class="tongue t2" d="M-58 0 C-58 -40 -40 -60 -32 -100 C-22 -60 -10 -40 -10 0 Z" fill="url(#cf-outer)" opacity=".85" />
          <path class="tongue t3" d="M10 0 C10 -40 22 -64 34 -108 C42 -64 58 -40 58 0 Z" fill="url(#cf-outer)" opacity=".85" />
          <path class="tongue" d="M-48 0 C-48 -70 -12 -110 0 -170 C12 -110 48 -70 48 0 Z" fill="url(#cf-outer)" />
          <path class="tongue t4" d="M-34 0 C-34 -50 -8 -80 0 -122 C8 -80 34 -50 34 0 Z" fill="url(#cf-mid)" />
          <path class="tongue t5" d="M-18 0 C-18 -26 -4 -44 0 -70 C4 -44 18 -26 18 0 Z" fill="url(#cf-in)" />
        </g>
      </g>
      <circle v-for="(s, i) in progress > 0 ? sparks : []" :key="'sp' + i" class="spark" :cx="s.x" :cy="s.y" :r="s.r" :fill="s.fill" :style="s.style" />

      <g v-for="l in logShapes.filter((l) => !l.back)" :key="'lf' + l.key">
        <path :d="l.body" fill="#5a3b26" />
        <path :d="l.grain" stroke="#7a5236" :stroke-width="l.thick * 0.18" fill="none" />
        <path :d="l.char" stroke="#1b110c" :stroke-width="l.thick * 0.9" stroke-opacity=".55" stroke-linecap="round" fill="none" />
        <ellipse :cx="l.x1" :cy="l.y1" :rx="l.thick * 0.32" :ry="l.thick / 2" :transform="`rotate(${l.rot} ${l.x1} ${l.y1})`" fill="#d9b07a" />
        <ellipse :cx="l.x1" :cy="l.y1" :rx="l.thick * 0.18" :ry="l.thick * 0.28" :transform="`rotate(${l.rot} ${l.x1} ${l.y1})`" fill="none" stroke="#a8794a" stroke-width="1.2" />
      </g>
      <g v-for="(s, i) in stones.filter((s) => !s.back)" :key="'sf' + i">
        <ellipse :cx="s.x" :cy="s.y + 4" :rx="s.w" :ry="s.w * 0.55" fill="#3b302a" />
        <ellipse :cx="s.x" :cy="s.y" :rx="s.w * 0.9" :ry="s.w * 0.48" fill="#6d6058" />
        <ellipse :cx="s.x - 3" :cy="s.y - 2" :rx="s.w * 0.45" :ry="s.w * 0.2" fill="#8f8178" opacity=".7" />
      </g>
      <text
        v-for="l in logShapes"
        :key="'t' + l.key"
        :x="l.lx"
        :y="l.ly"
        :text-anchor="l.anchor"
        class="display"
        font-size="14"
        fill="#f2e8dc"
      >{{ l.text }}</text>
      <path class="leaf-fall" :d="LEAF" transform="translate(690 120)" fill="#d9822b" />
    </svg>

    <div class="grid min-w-0 gap-5">
      <p class="display text-lg sm:text-xl leading-relaxed text-ink-100 text-balance">{{ headline }}</p>
      <p v-if="windy" class="-mt-3 text-sm text-ink-400">今天有點風，火晃得比較大，柴都還在。</p>
      <dl class="grid grid-cols-2 gap-x-6 gap-y-4">
        <div data-tour="assets">
          <dt class="label">柴堆（總資產）<InfoTip k="assets" /></dt>
          <dd class="display num mt-1 text-2xl sm:text-3xl text-warm">{{ wan(summary.total_assets) }}</dd>
          <dd class="mt-1 text-xs text-ink-400">
            {{ fxLabel }}
            <span v-if="summary.fx.mode !== 'live' && summary.fx.live" class="block">
              以即時匯率 {{ summary.fx.live.toFixed(2) }} 計為 {{ wan(summary.total_assets_live_fx) }}
            </span>
          </dd>
        </div>
        <div data-tour="progress">
          <dt class="label">火勢（Coast 達成率）<InfoTip k="progress" /></dt>
          <dd class="display num mt-1 text-2xl sm:text-3xl" :class="progress >= 1 ? 'text-accent' : 'text-warm'">{{ pct(summary.progress) }}</dd>
          <dd class="mt-1 text-xs text-ink-400">Coast 線 {{ wan(summary.coast_target) }}・終點 {{ wan(summary.fire_target) }}</dd>
        </div>
        <div data-tour="coast-date">
          <dt class="label">不用再添柴<InfoTip k="coastDate" /></dt>
          <template v-if="ttc.status === 'achieved'">
            <dd class="display mt-1 text-2xl sm:text-3xl text-accent">已達成</dd>
            <dd class="mt-1 text-xs text-ink-400">不再投入，也能在 {{ retireAge }} 歲達標</dd>
          </template>
          <template v-else-if="ttc.status === 'reachable'">
            <dd class="display num mt-1 text-2xl sm:text-3xl text-warm">{{ ym(ttc.month) }}</dd>
            <dd class="mt-1 text-xs text-ink-400">照目前定期定額，還要 {{ yearsLeft }}</dd>
          </template>
          <template v-else>
            <dd class="display mt-1 text-2xl text-warm">退休前燒不到</dd>
            <dd class="mt-1 text-xs text-ink-400">退休時差額 {{ wan(ttc.gap_at_retirement) }}</dd>
          </template>
        </div>
        <div data-tour="income">
          <dt class="label">現在停手，退休後每月可領<InfoTip k="income" /></dt>
          <dd class="display num mt-1 text-2xl sm:text-3xl text-warm">{{ money(summary.monthly_income_if_stop) }}</dd>
          <dd class="mt-1 text-xs text-ink-400">以今日購買力計，從 {{ retireAge }} 歲開始</dd>
        </div>
      </dl>
    </div>
  </section>
</template>

<style scoped>
.tongue {
  transform-box: fill-box;
  transform-origin: 50% 100%;
  animation: flick 1.6s ease-in-out infinite alternate;
}
.t2 { animation-duration: 1.1s; animation-delay: -0.4s; }
.t3 { animation-duration: 1.9s; animation-delay: -0.8s; }
.t4 { animation-duration: 0.9s; }
.t5 { animation-duration: 1.3s; animation-delay: -0.2s; }
@keyframes flick {
  0% { transform: scale(1, 1) skewX(0deg); }
  35% { transform: scale(0.94, 1.06) skewX(3deg); }
  70% { transform: scale(1.04, 0.95) skewX(-3deg); }
  100% { transform: scale(0.97, 1.03) skewX(1deg); }
}
/* A down day is wind: the flame leans and dips a little, the logs stay. */
.windy {
  transform-origin: 0 0;
  animation: gust 5s ease-in-out infinite;
}
@keyframes gust {
  0%, 100% { transform: skewX(0deg) scaleY(1); }
  40% { transform: skewX(-9deg) scaleY(0.9); }
  60% { transform: skewX(-5deg) scaleY(0.94); }
}
.glow { animation: glow 2.4s ease-in-out infinite alternate; }
@keyframes glow { from { filter: brightness(0.85); } to { filter: brightness(1.1); } }
.spark { animation: spark var(--d, 4s) linear var(--delay, 0s) infinite; }
@keyframes spark {
  0% { transform: translate(0, 0); opacity: 0; }
  10% { opacity: 1; }
  100% { transform: translate(var(--dx, 10px), -150px); opacity: 0; }
}
.leaf-fall { animation: leaffall 12s ease-in-out infinite; }
@keyframes leaffall {
  0% { transform: translate(690px, 80px) rotate(0); opacity: 0; }
  10% { opacity: 1; }
  80% { transform: translate(630px, 270px) rotate(280deg); opacity: 1; }
  100% { transform: translate(626px, 270px) rotate(290deg); opacity: 0; }
}
@media (prefers-reduced-motion: reduce) {
  .tongue, .windy, .glow, .spark, .leaf-fall { animation: none; }
  .spark { opacity: 0; }
}
</style>
