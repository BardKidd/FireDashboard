<script setup lang="ts">
import type { MobileTab } from '../mobile'

defineProps<{ tab: MobileTab }>()
const emit = defineEmits<{ 'update:tab': [t: MobileTab]; add: [] }>()

const LEFT: { key: MobileTab; label: string }[] = [
  { key: 'fire', label: '營火' },
  { key: 'logs', label: '柴堆' },
]
const RIGHT: { key: MobileTab; label: string }[] = [
  { key: 'path', label: '軌跡' },
  { key: 'book', label: '收集冊' },
]
</script>

<template>
  <nav
    class="tabs fixed inset-x-0 bottom-[calc(-1*var(--ios-gap,0px))] z-30 grid grid-cols-5 items-end border-t border-ink-800 px-1 pt-1.5 pb-[max(0.5rem,env(safe-area-inset-bottom))] md:hidden"
    aria-label="分頁"
    data-tour="view-switch"
  >
    <template v-for="group in [LEFT, RIGHT]" :key="group[0].key">
      <button
        v-for="t in group"
        :key="t.key"
        class="tab grid justify-items-center gap-0.5 py-1 text-[10.5px] font-medium transition-colors"
        :class="[tab === t.key ? 'text-accent' : 'text-ink-400', t.key === 'path' ? 'col-start-4' : '']"
        :aria-current="tab === t.key ? 'page' : undefined"
        @click="emit('update:tab', t.key)"
      >
        <svg viewBox="0 0 24 24" class="h-6 w-6" aria-hidden="true">
          <g v-if="t.key === 'fire'" :class="{ flicker: tab === 'fire' }">
            <path d="M12 2.5c1.5 5 6.5 7 6.5 12.5a6.5 6.5 0 0 1-13 0c0-3 1.5-4.5 3-6 0 2 .8 3.5 2.2 3.5C10 8 11.2 5 12 2.5z" fill="currentColor" />
            <path v-if="tab === 'fire'" d="M12.2 11c.6 1.8 2.6 2.6 2.6 4.6a2.8 2.8 0 0 1-5.6 0c0-1.2.7-2 1.3-2.5 0 .8.4 1.4 1 1.4-.3-1.4 0-2.6.7-3.5z" fill="#ffd36e" />
          </g>
          <g v-else-if="t.key === 'logs'" fill="none" stroke="currentColor" stroke-width="1.8">
            <rect x="3" y="6" width="17" height="4.6" rx="2.3" /><circle cx="19.7" cy="8.3" r="1" />
            <rect x="5" y="13.4" width="16" height="4.6" rx="2.3" /><circle cx="5.3" cy="15.7" r="1" />
          </g>
          <g v-else-if="t.key === 'path'" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round">
            <path d="M3 18c4-1 6-5 9-8s5.5-4.5 9-5.5" />
            <path d="M3 9h18" stroke-dasharray="2 3" opacity=".6" />
          </g>
          <g v-else fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round">
            <path d="M5 4h11a3 3 0 0 1 3 3v13H8a3 3 0 0 1-3-3z" /><path d="M5 17a3 3 0 0 1 3-3h11" />
            <path d="M11.5 6.8l.8 1.6 1.7.2-1.3 1.2.4 1.7-1.6-.9-1.6.9.4-1.7-1.3-1.2 1.7-.2z" fill="currentColor" stroke="none" />
          </g>
        </svg>
        {{ t.label }}
      </button>
      <div v-if="group === LEFT" class="grid justify-items-center gap-0.5 text-[10.5px] font-medium text-ink-300">
        <button class="fab -mt-5 grid h-13 w-13 place-items-center rounded-full bg-accent text-ink-950" aria-label="添柴：記錄買賣" data-tour="add-fab" @click="emit('add')">
          <svg viewBox="0 0 24 24" class="h-6 w-6" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" aria-hidden="true"><path d="M12 5v14M5 12h14" /></svg>
        </button>
        添柴
      </div>
    </template>
  </nav>
</template>

<style scoped>
.tabs {
  background: color-mix(in srgb, var(--color-ink-950) 88%, transparent);
  backdrop-filter: blur(14px);
  -webkit-backdrop-filter: blur(14px);
}
.fab {
  box-shadow: 0 6px 18px -4px color-mix(in srgb, var(--color-accent) 70%, transparent), 0 0 0 4px var(--color-ink-950);
  transition: transform 0.15s;
}
.fab:active { transform: scale(0.92); }
.tab:active svg { transform: scale(0.9); }
.flicker {
  transform-box: fill-box;
  transform-origin: 50% 100%;
  animation: flick 1.4s ease-in-out infinite alternate;
}
@keyframes flick {
  0% { transform: scale(1, 1) skewX(0); }
  50% { transform: scale(0.95, 1.06) skewX(2deg); }
  100% { transform: scale(1.03, 0.96) skewX(-2deg); }
}
@media (prefers-reduced-motion: reduce) {
  .flicker { animation: none; }
}
</style>
