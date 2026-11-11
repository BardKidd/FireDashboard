<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'

defineProps<{ title: string; wide?: boolean }>()
const emit = defineEmits<{ close: [] }>()

// Close with the same slide the sheet opened with, then let the parent unmount it.
const closing = ref(false)
const reduced = () => window.matchMedia('(prefers-reduced-motion: reduce)').matches
function requestClose() {
  if (closing.value) return
  closing.value = true
  window.setTimeout(() => emit('close'), reduced() ? 0 : 220)
}

// Drag the handle/header down to dismiss, like a native sheet.
const drag = ref(0)
const dragging = ref(false)
let startY: number | null = null
let startT = 0
function onDragStart(e: TouchEvent) {
  if ((e.target as HTMLElement).closest('button')) return
  startY = e.touches[0].clientY
  startT = performance.now()
  dragging.value = true
}
function onDragMove(e: TouchEvent) {
  if (startY == null) return
  drag.value = Math.max(0, e.touches[0].clientY - startY)
  if (drag.value > 0) e.preventDefault()
}
function onDragEnd() {
  if (startY == null) return
  const fast = drag.value / Math.max(1, performance.now() - startT) > 0.6
  startY = null
  dragging.value = false
  if (drag.value > 110 || (fast && drag.value > 30)) requestClose()
  else drag.value = 0
}

function onKey(e: KeyboardEvent) {
  if (e.key === 'Escape') requestClose()
}

// Lock the page behind while any dialog is open (iOS ignores overflow:hidden on body).
let savedY = 0
function lockPage() {
  if (document.documentElement.classList.contains('modal-open')) return
  savedY = window.scrollY
  document.documentElement.classList.add('modal-open')
  Object.assign(document.body.style, { position: 'fixed', top: `-${savedY}px`, left: '0', right: '0', width: '100%' })
  document.body.dataset.lockY = String(savedY)
}
function unlockPage() {
  const y = Number(document.body.dataset.lockY ?? 0)
  document.documentElement.classList.remove('modal-open')
  Object.assign(document.body.style, { position: '', top: '', left: '', right: '', width: '' })
  delete document.body.dataset.lockY
  window.scrollTo(0, y)
}

onMounted(() => {
  window.addEventListener('keydown', onKey)
  lockPage()
})
onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKey)
  // Another dialog may still be open underneath.
  if (document.querySelectorAll('.base-modal').length <= 1) unlockPage()
})
</script>

<template>
  <!-- Phones: a sheet that slides up from the bottom, within thumb reach. Larger screens: a centered dialog. -->
  <div
    class="base-modal fixed inset-0 z-40 flex items-end justify-center overflow-y-auto overscroll-contain bg-black/60 md:items-center md:p-4"
    :class="{ closing }"
    @click.self="requestClose"
  >
    <div
      role="dialog"
      aria-modal="true"
      :aria-label="title"
      class="sheet flex max-h-[92dvh] w-full flex-col rounded-t-3xl border border-b-0 border-ink-700 bg-ink-900 shadow-2xl md:max-h-none md:rounded-2xl md:border-b"
      :class="[wide ? 'md:max-w-3xl' : 'md:max-w-lg', { dragging }]"
      :style="drag ? { transform: `translateY(${drag}px)` } : undefined"
    >
      <div class="grab flex-none md:hidden" @touchstart="onDragStart" @touchmove="onDragMove" @touchend="onDragEnd" @touchcancel="onDragEnd">
        <div class="mx-auto mt-2 h-1 w-9 rounded-full bg-ink-600" aria-hidden="true" />
      </div>
      <header
        class="grab flex flex-none items-center justify-between border-b border-ink-700/70 px-5 py-3 md:py-4"
        @touchstart="onDragStart"
        @touchmove="onDragMove"
        @touchend="onDragEnd"
        @touchcancel="onDragEnd"
      >
        <h2 class="display text-lg md:font-sans md:text-base md:font-semibold">{{ title }}</h2>
        <button class="rounded-md p-1 text-ink-400 hover:bg-ink-800 hover:text-ink-100" aria-label="關閉" @click="requestClose">
          <svg viewBox="0 0 20 20" class="h-5 w-5" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M5 5l10 10M15 5L5 15" /></svg>
        </button>
      </header>
      <div class="min-h-0 flex-1 overflow-y-auto overscroll-contain px-5 py-4 md:overflow-visible">
        <slot />
      </div>
      <footer
        v-if="$slots.footer"
        class="flex flex-none justify-end gap-2 border-t border-ink-700/70 px-5 py-3 pb-[max(0.75rem,env(safe-area-inset-bottom))] md:pb-3"
      >
        <slot name="footer" />
      </footer>
      <div v-else class="h-[env(safe-area-inset-bottom)] flex-none md:hidden" />
    </div>
  </div>
</template>

<style scoped>
.base-modal { animation: fade 0.2s ease-out; }
.sheet { animation: rise 0.32s cubic-bezier(0.2, 0.8, 0.2, 1); transition: transform 0.22s ease; }
.sheet.dragging { transition: none; }
.grab { touch-action: none; }
.base-modal.closing { animation: fade-out 0.22s ease-in forwards; pointer-events: none; }
.base-modal.closing .sheet { animation: sink 0.22s ease-in forwards; }
@keyframes fade { from { background: transparent; } }
@keyframes fade-out { to { background: transparent; } }
@keyframes rise { from { transform: translateY(100%); } }
@keyframes sink { to { transform: translateY(100%); } }
@media (min-width: 768px) {
  .sheet { animation: pop 0.18s ease-out; }
  .base-modal.closing .sheet { animation: pop-out 0.15s ease-in forwards; }
  @keyframes pop { from { opacity: 0; transform: translateY(6px); } }
  @keyframes pop-out { to { opacity: 0; transform: translateY(6px); } }
}
@media (prefers-reduced-motion: reduce) {
  .base-modal, .sheet, .base-modal.closing, .base-modal.closing .sheet { animation: none; }
}
</style>
