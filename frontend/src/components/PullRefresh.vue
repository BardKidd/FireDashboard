<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { isMobile } from '../mobile'

/** Pull the page down from the top to fetch quotes. A small flame grows with the pull. */
const props = defineProps<{ refreshing: boolean }>()
const emit = defineEmits<{ refresh: [] }>()

const THRESHOLD = 70
const pull = ref(0)
const holding = ref(false)
let startY: number | null = null
const dragging = ref(false)

const blocked = () =>
  !isMobile.value || window.scrollY > 0 || !!document.querySelector('.base-modal, .tour')

function onStart(e: TouchEvent) {
  startY = blocked() || holding.value ? null : e.touches[0].clientY
  dragging.value = startY != null
}
function onMove(e: TouchEvent) {
  if (startY == null) return
  const dy = e.touches[0].clientY - startY
  if (dy <= 0 || window.scrollY > 0) {
    pull.value = 0
    return
  }
  pull.value = Math.min(120, dy * 0.5)
}
function onEnd() {
  if (startY == null) return
  startY = null
  dragging.value = false
  if (pull.value >= THRESHOLD) {
    holding.value = true
    pull.value = 56
    navigator.vibrate?.(10)
    emit('refresh')
    // If the server never reports a refresh, let go after a while.
    window.setTimeout(() => !props.refreshing && release(), 2500)
  } else pull.value = 0
}
function release() {
  holding.value = false
  pull.value = 0
}
watch(
  () => props.refreshing,
  (r, was) => {
    if (was && !r) release()
  },
)

onMounted(() => {
  window.addEventListener('touchstart', onStart, { passive: true })
  window.addEventListener('touchmove', onMove, { passive: true })
  window.addEventListener('touchend', onEnd)
  window.addEventListener('touchcancel', onEnd)
})
onBeforeUnmount(() => {
  window.removeEventListener('touchstart', onStart)
  window.removeEventListener('touchmove', onMove)
  window.removeEventListener('touchend', onEnd)
  window.removeEventListener('touchcancel', onEnd)
})

const ratio = computed(() => Math.min(1, pull.value / THRESHOLD))
const ready = computed(() => pull.value >= THRESHOLD)
const label = computed(() => (holding.value ? '正在更新報價' : ready.value ? '放開就更新報價' : '下拉更新報價'))
</script>

<template>
  <div
    v-if="pull > 0"
    class="ptr pointer-events-none fixed inset-x-0 z-50 flex justify-center md:hidden"
    :class="{ settle: !dragging }"
    :style="{ top: 'env(safe-area-inset-top)', transform: `translateY(${pull - 44}px)` }"
    role="status"
    :aria-label="label"
  >
    <div class="flex items-center gap-2 rounded-full border border-ink-700 bg-ink-900/95 py-1.5 pr-3.5 pl-2 shadow-lg">
      <svg viewBox="0 0 32 32" class="h-7 w-7" aria-hidden="true">
        <circle cx="16" cy="16" r="14" fill="none" stroke="var(--color-ink-700)" stroke-width="2" />
        <circle
          cx="16" cy="16" r="14" fill="none" stroke="var(--color-accent)" stroke-width="2" stroke-linecap="round"
          :stroke-dasharray="88" :stroke-dashoffset="88 * (1 - ratio)" transform="rotate(-90 16 16)"
          :class="{ spin: holding }"
        />
        <g :style="{ transform: `scale(${0.35 + ratio * 0.65})` }" class="flame" :class="{ lit: holding || ready }">
          <path d="M16 6c1.2 4 5 5.6 5 10a5 5 0 0 1-10 0c0-2.3 1.2-3.5 2.3-4.6 0 1.6.6 2.7 1.7 2.7-.8-3 0-5.8 1-8.1z" fill="var(--color-accent)" />
          <path d="M16.1 13.5c.5 1.4 2 2 2 3.6a2.1 2.1 0 0 1-4.2 0c0-.9.5-1.5 1-1.9 0 .6.3 1 .8 1-.2-1 0-2 .4-2.7z" fill="#ffd36e" />
        </g>
      </svg>
      <span class="text-xs text-ink-300">{{ label }}</span>
    </div>
  </div>
</template>

<style scoped>
.settle { transition: transform 0.25s ease; }
.flame { transform-box: fill-box; transform-origin: 50% 100%; transition: transform 0.1s; }
.flame.lit path:first-child { animation: flick 0.9s ease-in-out infinite alternate; transform-box: fill-box; transform-origin: 50% 100%; }
.spin { transform-origin: 16px 16px; animation: spin 1.2s linear infinite; }
@keyframes spin { from { transform: rotate(-90deg); } to { transform: rotate(270deg); } }
@keyframes flick {
  0% { transform: scale(1, 1) skewX(0); }
  100% { transform: scale(0.94, 1.08) skewX(3deg); }
}
@media (prefers-reduced-motion: reduce) {
  .spin, .flame.lit path:first-child { animation: none; }
}
</style>
