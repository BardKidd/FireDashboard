<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, ref } from 'vue'
import { TIPS } from './content'

const props = defineProps<{ k: keyof typeof TIPS | string }>()
const tip = computed(() => TIPS[props.k])
const open = ref(false)
const btn = ref<HTMLButtonElement>()
const panel = ref<HTMLElement>()
const pos = ref({ left: '0px', top: '0px' })
const id = 'tip-' + Math.random().toString(36).slice(2, 8)

function place() {
  const b = btn.value?.getBoundingClientRect()
  const p = panel.value
  if (!b || !p) return
  const w = p.offsetWidth
  const h = p.offsetHeight
  const left = Math.min(Math.max(12, b.left + b.width / 2 - w / 2), window.innerWidth - w - 12)
  const top = b.bottom + 8 + h <= window.innerHeight - 8 ? b.bottom + 8 : Math.max(8, b.top - 8 - h)
  pos.value = { left: left + 'px', top: top + 'px' }
}

function onOutside(e: Event) {
  const t = e.target as Node
  if (panel.value?.contains(t) || btn.value?.contains(t)) return
  close()
}
function onKey(e: KeyboardEvent) {
  if (e.key === 'Escape') {
    close()
    btn.value?.focus()
  }
}
function close() {
  open.value = false
  window.removeEventListener('pointerdown', onOutside, true)
  window.removeEventListener('scroll', close, true)
  window.removeEventListener('resize', close)
  window.removeEventListener('keydown', onKey)
}
async function toggle() {
  if (open.value) return close()
  open.value = true
  await nextTick()
  place()
  window.addEventListener('pointerdown', onOutside, true)
  window.addEventListener('scroll', close, true)
  window.addEventListener('resize', close)
  window.addEventListener('keydown', onKey)
}
onBeforeUnmount(close)
</script>

<template>
  <button
    v-if="tip"
    ref="btn"
    type="button"
    class="ml-1 inline-grid h-4 w-4 place-items-center rounded-full border border-ink-600 align-[-2px] text-[10px] font-semibold leading-none text-ink-400 transition hover:border-accent hover:text-accent focus-visible:outline-2 focus-visible:outline-accent"
    :class="open ? 'border-accent text-accent' : ''"
    :aria-label="'說明：' + tip.title"
    :aria-expanded="open"
    :aria-controls="id"
    @click.stop="toggle"
  >?</button>
  <Teleport to="body">
    <div
      v-if="open && tip"
      :id="id"
      ref="panel"
      role="tooltip"
      class="fixed z-[70] w-[min(20rem,calc(100vw-1.5rem))] rounded-xl border border-ink-700 bg-ink-900 p-4 text-left font-sans shadow-2xl"
      :style="pos"
    >
      <p class="display mb-1.5 text-base text-warm">{{ tip.title }}</p>
      <div class="grid gap-1.5 text-xs leading-relaxed text-ink-300">
        <p v-for="(p, i) in tip.body" :key="i">{{ p }}</p>
      </div>
    </div>
  </Teleport>
</template>
