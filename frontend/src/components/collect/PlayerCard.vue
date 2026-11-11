<script setup lang="ts">
import { computed } from 'vue'
import type { Game } from '../../api'
import StarIcon from './StarIcon.vue'
import InfoTip from '../../guide/InfoTip.vue'

const props = defineProps<{ game: Game }>()
const lv = computed(() => props.game.level)
const span = computed(() => lv.value.next_at - lv.value.current_floor)
const into = computed(() => lv.value.xp - lv.value.current_floor)
const bar = computed(() => Math.min(100, (into.value / span.value) * 100) + '%')
</script>

<template>
  <article class="card flex flex-col gap-4">
    <div class="flex items-center gap-4">
      <div class="grid h-16 w-16 shrink-0 place-items-center rounded-2xl bg-accent-soft text-accent">
        <div class="text-center leading-none">
          <p class="text-[10px] font-semibold tracking-widest">LV</p>
          <p class="num text-2xl font-bold">{{ lv.level }}</p>
        </div>
      </div>
      <div class="min-w-0">
        <p class="label">目前稱號</p>
        <p class="text-xl font-semibold tracking-tight">{{ lv.title }}</p>
        <p v-if="lv.next_title" class="text-xs text-ink-400">Lv.{{ lv.next_title.level }} 解鎖「{{ lv.next_title.title }}」</p>
      </div>
    </div>
    <div>
      <div class="mb-1 flex justify-between text-xs text-ink-400">
        <span>經驗值</span>
        <span class="num">{{ into }} / {{ span }}</span>
      </div>
      <div class="h-2 overflow-hidden rounded-full bg-ink-800" role="progressbar" :aria-valuenow="into" :aria-valuemax="span" aria-label="升級進度">
        <div class="h-full rounded-full bg-accent transition-all duration-700" :style="{ width: bar }" />
      </div>
    </div>
    <div class="flex items-end justify-between rounded-xl bg-ink-950/60 px-4 py-3">
      <div>
        <p class="label">可用星星<InfoTip k="stars" /></p>
        <p class="num flex items-center gap-1.5 text-2xl font-semibold text-warm">
          <StarIcon class="h-5 w-5" />{{ game.stars.balance.toLocaleString() }}
        </p>
      </div>
      <p class="text-right text-xs text-ink-400">
        累積獲得 {{ game.stars.earned.toLocaleString() }}<br />已兌換 {{ game.stars.spent.toLocaleString() }}
      </p>
    </div>
  </article>
</template>
