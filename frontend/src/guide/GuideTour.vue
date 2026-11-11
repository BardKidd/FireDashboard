<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import type { TourStep } from './content'

const props = defineProps<{ steps: TourStep[] }>()
const emit = defineEmits<{ close: [] }>()

const i = ref(0)
const rect = ref<DOMRect | null>(null)
const card = ref<HTMLElement>()
const cardSize = ref({ w: 360, h: 220 })
const vw = ref(window.innerWidth)
const vh = ref(window.innerHeight)
const PAD = 8
const GAP = 14

const step = computed(() => props.steps[i.value])
const last = computed(() => i.value === props.steps.length - 1)
const reduced = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false

let target: HTMLElement | null = null
let raf = 0
let token = 0

function find(name: string): HTMLElement | null {
  const el = document.querySelector<HTMLElement>(`[data-tour="${name}"]`)
  return el && el.getClientRects().length ? el : null
}

// Targets can appear late (data still loading), so wait a little before skipping one.
async function waitFor(name: string, ms = 2500): Promise<HTMLElement | null> {
  const end = performance.now() + ms
  for (;;) {
    const el = find(name)
    if (el || performance.now() > end) return el
    await new Promise((r) => setTimeout(r, 100))
  }
}

async function show(n: number, dir: 1 | -1 = 1) {
  const my = ++token
  i.value = n
  const s = props.steps[n]
  if (!s.target) {
    target = null
    rect.value = null
  } else {
    const el = await waitFor(s.target)
    if (my !== token) return
    if (!el) {
      const next = n + dir
      if (next >= 0 && next < props.steps.length) return show(next, dir)
      target = null
      rect.value = null
    } else {
      target = el
      el.scrollIntoView({ block: el.offsetHeight > window.innerHeight * 0.6 ? 'start' : 'center', behavior: reduced ? 'auto' : 'smooth' })
    }
  }
  await nextTick()
  card.value?.focus({ preventScroll: true })
}

// Follow the target while it scrolls into place, resizes or the window changes.
function track() {
  vw.value = window.innerWidth
  vh.value = window.innerHeight
  rect.value = target ? target.getBoundingClientRect() : null
  if (card.value) cardSize.value = { w: card.value.offsetWidth, h: card.value.offsetHeight }
  raf = requestAnimationFrame(track)
}

function next() {
  if (last.value) emit('close')
  else show(i.value + 1, 1)
}
function prev() {
  if (i.value > 0) show(i.value - 1, -1)
}
function onKey(e: KeyboardEvent) {
  if (e.key === 'Escape') emit('close')
  else if (e.key === 'ArrowRight') next()
  else if (e.key === 'ArrowLeft') prev()
}

onMounted(() => {
  window.addEventListener('keydown', onKey)
  raf = requestAnimationFrame(track)
  show(0)
})
onBeforeUnmount(() => {
  token++
  window.removeEventListener('keydown', onKey)
  cancelAnimationFrame(raf)
})

const hole = computed(() => {
  const r = rect.value
  if (!r) return null
  return {
    left: r.left - PAD + 'px',
    top: r.top - PAD + 'px',
    width: r.width + PAD * 2 + 'px',
    height: r.height + PAD * 2 + 'px',
  }
})

const cardStyle = computed(() => {
  const r = rect.value
  const { w, h } = cardSize.value
  const W = vw.value
  const H = vh.value
  if (!r) return { left: Math.max(16, (W - w) / 2) + 'px', top: Math.max(16, (H - h) / 2) + 'px' }
  const clampX = (x: number) => Math.min(Math.max(16, x), W - w - 16)
  const below = r.bottom + PAD + GAP
  const above = r.top - PAD - GAP - h
  // Below, then above, then beside, then pinned to the bottom edge over the target.
  if (below + h <= H - 12) return { left: clampX(r.left) + 'px', top: below + 'px' }
  if (above >= 12) return { left: clampX(r.left) + 'px', top: above + 'px' }
  const right = r.right + PAD + GAP
  if (right + w <= W - 16) return { left: right + 'px', top: Math.min(Math.max(12, r.top), H - h - 12) + 'px' }
  const left = r.left - PAD - GAP - w
  if (left >= 16) return { left: left + 'px', top: Math.min(Math.max(12, r.top), H - h - 12) + 'px' }
  return { left: clampX((W - w) / 2) + 'px', top: H - h - 16 + 'px' }
})
</script>

<template>
  <Teleport to="body">
    <div class="tour fixed inset-0 z-[60]">
      <!-- Click shield: the page underneath stays still while the tour runs. -->
      <div class="absolute inset-0" :class="hole ? '' : 'bg-[rgba(10,7,5,.72)]'" />
      <div v-if="hole" class="hole pointer-events-none fixed rounded-2xl" :style="hole" />

      <div
        ref="card"
        class="tour-card fixed w-[min(22.5rem,calc(100vw-2rem))] rounded-2xl border border-ink-700 bg-ink-900 p-5 shadow-2xl outline-none"
        :style="cardStyle"
        role="dialog"
        aria-modal="true"
        :aria-label="'操作導覽：' + step.title"
        tabindex="-1"
      >
        <p class="label num mb-1">{{ i + 1 }} / {{ steps.length }}</p>
        <h2 class="display mb-2 text-lg text-warm">{{ step.title }}</h2>
        <div class="grid gap-2 text-sm leading-relaxed text-ink-300">
          <p v-for="(p, k) in step.body" :key="k">{{ p }}</p>
        </div>
        <div class="mt-4 flex items-center gap-2">
          <button class="btn text-ink-400 hover:text-ink-100" @click="emit('close')">{{ last ? '關閉' : '略過' }}</button>
          <span class="flex-1" />
          <button v-if="i > 0" class="btn-ghost" @click="prev">上一步</button>
          <button class="btn-primary" @click="next">{{ last ? '開始使用' : '下一步' }}</button>
        </div>
        <div class="mt-3 flex justify-center gap-1" aria-hidden="true">
          <span
            v-for="(_, k) in steps"
            :key="k"
            class="h-1 rounded-full transition-all"
            :class="k === i ? 'w-4 bg-accent' : 'w-1.5 bg-ink-700'"
          />
        </div>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.hole {
  box-shadow:
    0 0 0 2px rgba(245, 158, 75, 0.85),
    0 0 24px 4px rgba(245, 158, 75, 0.35),
    0 0 0 200vmax rgba(10, 7, 5, 0.72);
  transition: left 0.25s ease, top 0.25s ease, width 0.25s ease, height 0.25s ease;
}
.tour-card {
  transition: left 0.25s ease, top 0.25s ease;
  animation: pop 0.2s ease-out;
}
@keyframes pop {
  from { opacity: 0; transform: translateY(4px); }
}
@media (prefers-reduced-motion: reduce) {
  .hole, .tour-card { transition: none; animation: none; }
}
</style>
