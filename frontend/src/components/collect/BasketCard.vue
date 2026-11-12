<script setup lang="ts">
import { computed } from 'vue'
import type { BasketGoal, Collect } from '../../api'
import { pct, wan } from '../../format'
import InfoTip from '../../guide/InfoTip.vue'

const props = defineProps<{ collect: Collect }>()
const emit = defineEmits<{ goal: [g: BasketGoal] }>()

const p = computed(() => props.collect.basket_progress ?? 0)
const R = 44
const C = 2 * Math.PI * R
const dash = computed(() => C * Math.min(1, p.value))
</script>

<template>
  <article class="card flex flex-col gap-4">
    <div class="flex flex-wrap items-start justify-between gap-2">
      <div>
        <h2 class="text-sm font-semibold">目標股數籃子<InfoTip k="basket" /></h2>
        <p class="text-xs text-ink-400">把目標金額依目前配置，以 200 日均價折算成各標的要收集的股數</p>
      </div>
      <div class="flex rounded-lg border border-ink-700 p-0.5 text-xs" role="group" aria-label="籃子目標">
        <button
          v-for="g in (['coast', 'fire'] as const)"
          :key="g"
          class="rounded-md px-2.5 py-1 transition"
          :class="collect.basket_goal === g ? 'bg-accent text-ink-950' : 'text-ink-300 hover:text-ink-100'"
          :aria-pressed="collect.basket_goal === g"
          @click="emit('goal', g)"
        >
          {{ g === 'coast' ? 'Coast' : 'FIRE' }}
        </button>
      </div>
    </div>
    <div class="flex items-center gap-5">
      <svg viewBox="0 0 100 100" class="h-28 w-28 shrink-0 -rotate-90" aria-hidden="true">
        <circle cx="50" cy="50" :r="R" fill="none" stroke="var(--color-ink-800)" stroke-width="9" />
        <circle
          cx="50" cy="50" :r="R" fill="none" stroke="var(--color-accent)" stroke-width="9" stroke-linecap="round"
          :stroke-dasharray="dash + ' ' + C" class="transition-all duration-700"
        />
      </svg>
      <div>
        <p class="num text-3xl font-semibold tracking-tight">{{ collect.basket_progress == null ? '—' : pct(collect.basket_progress) }}</p>
        <p class="text-xs text-ink-400">{{ collect.basket_goal === 'coast' ? 'Coast 目標' : 'FIRE 目標' }} {{ wan(collect.goal_amount) }}<template v-if="collect.debt > 0">＋待還負債 {{ wan(collect.debt) }}</template></p>
        <p v-if="p >= 1 && collect.basket_goal === 'coast'" class="mt-2 text-xs text-accent">Coast 籃子集滿了，可以換成 FIRE 籃子繼續收集。</p>
        <p v-else-if="collect.basket_progress == null" class="mt-2 text-xs text-ink-400">等報價更新後就能算出目標股數。</p>
      </div>
    </div>
  </article>
</template>
