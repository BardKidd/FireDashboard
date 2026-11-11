<script setup lang="ts">
import { onBeforeUnmount, onMounted } from 'vue'

defineProps<{ title: string; wide?: boolean }>()
const emit = defineEmits<{ close: [] }>()

function onKey(e: KeyboardEvent) {
  if (e.key === 'Escape') emit('close')
}
onMounted(() => {
  window.addEventListener('keydown', onKey)
  document.documentElement.classList.add('modal-open')
})
onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKey)
  // Another dialog may still be open underneath.
  if (document.querySelectorAll('.base-modal').length <= 1) document.documentElement.classList.remove('modal-open')
})
</script>

<template>
  <!-- Phones: a sheet that slides up from the bottom, within thumb reach. Larger screens: a centered dialog. -->
  <div
    class="base-modal fixed inset-0 bottom-[calc(-1*var(--ios-gap,0px))] z-40 flex items-end justify-center overflow-y-auto bg-black/60 md:items-center md:p-4"
    @mousedown.self="emit('close')"
  >
    <div
      role="dialog"
      aria-modal="true"
      :aria-label="title"
      class="sheet flex max-h-[92dvh] w-full flex-col rounded-t-3xl border border-b-0 border-ink-700 bg-ink-900 shadow-2xl md:max-h-none md:rounded-2xl md:border-b"
      :class="wide ? 'md:max-w-3xl' : 'md:max-w-lg'"
    >
      <div class="mx-auto mt-2 h-1 w-9 flex-none rounded-full bg-ink-700 md:hidden" aria-hidden="true" />
      <header class="flex flex-none items-center justify-between border-b border-ink-700/70 px-5 py-3 md:py-4">
        <h2 class="display text-lg md:font-sans md:text-base md:font-semibold">{{ title }}</h2>
        <button class="rounded-md p-1 text-ink-400 hover:bg-ink-800 hover:text-ink-100" aria-label="關閉" @click="emit('close')">
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
.sheet { animation: rise 0.32s cubic-bezier(0.2, 0.8, 0.2, 1); }
@keyframes fade { from { background: transparent; } }
@keyframes rise { from { transform: translateY(100%); } }
@media (min-width: 768px) {
  .sheet { animation: pop 0.18s ease-out; }
  @keyframes pop { from { opacity: 0; transform: translateY(6px); } }
}
@media (prefers-reduced-motion: reduce) {
  .base-modal, .sheet { animation: none; }
}
</style>
