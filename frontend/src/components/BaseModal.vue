<script setup lang="ts">
import { onBeforeUnmount, onMounted } from 'vue'

defineProps<{ title: string; wide?: boolean }>()
const emit = defineEmits<{ close: [] }>()

function onKey(e: KeyboardEvent) {
  if (e.key === 'Escape') emit('close')
}
onMounted(() => window.addEventListener('keydown', onKey))
onBeforeUnmount(() => window.removeEventListener('keydown', onKey))
</script>

<template>
  <div class="fixed inset-0 z-40 flex items-start justify-center overflow-y-auto bg-black/60 p-4 sm:items-center" @mousedown.self="emit('close')">
    <div
      role="dialog"
      aria-modal="true"
      :aria-label="title"
      class="w-full rounded-2xl border border-ink-700 bg-ink-900 shadow-2xl"
      :class="wide ? 'max-w-3xl' : 'max-w-lg'"
    >
      <header class="flex items-center justify-between border-b border-ink-700/70 px-5 py-4">
        <h2 class="text-base font-semibold">{{ title }}</h2>
        <button class="rounded-md p-1 text-ink-400 hover:bg-ink-800 hover:text-ink-100" aria-label="關閉" @click="emit('close')">
          <svg viewBox="0 0 20 20" class="h-5 w-5" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M5 5l10 10M15 5L5 15" /></svg>
        </button>
      </header>
      <div class="px-5 py-4">
        <slot />
      </div>
      <footer v-if="$slots.footer" class="flex justify-end gap-2 border-t border-ink-700/70 px-5 py-3">
        <slot name="footer" />
      </footer>
    </div>
  </div>
</template>
