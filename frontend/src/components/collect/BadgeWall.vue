<script setup lang="ts">
import { computed, ref } from 'vue'
import type { AchievementRow, Game } from '../../api'
import StarIcon from './StarIcon.vue'

const props = defineProps<{ game: Game }>()

const CAT: Record<string, { name: string; cls: string }> = {
  milestone: { name: '股數', cls: 'bg-accent-soft text-accent' },
  first: { name: '新收藏', cls: 'bg-accent-soft text-accent' },
  coast: { name: 'Coast', cls: 'bg-amber-950/60 text-warm' },
  checkin: { name: '打卡', cls: 'bg-sky-950/60 text-calm' },
  streak: { name: '連續', cls: 'bg-sky-950/60 text-calm' },
  dividend: { name: '股息', cls: 'bg-ink-800 text-ink-300' },
}

const showAll = ref(false)
const badges = computed(() => props.game.achievements.filter((a) => a.category !== 'dividend'))
const shown = computed(() => (showAll.value ? badges.value : badges.value.slice(0, 12)))
const dividends = computed(() => props.game.achievements.filter((a) => a.category === 'dividend'))
const divStars = computed(() => dividends.value.reduce((s, a) => s + a.points, 0))
const recent = computed<AchievementRow[]>(() => props.game.achievements.slice(0, 6))
const bar = (v: number | null) => Math.min(100, (v ?? 0) * 100) + '%'
</script>

<template>
  <article class="card flex flex-col gap-5">
    <section>
      <h2 class="mb-3 text-sm font-semibold">下一個目標</h2>
      <ul class="grid gap-3">
        <li v-for="g in game.next_goals" :key="g.title">
          <div class="mb-1 flex items-center justify-between gap-2 text-sm">
            <span>{{ g.title }}</span>
            <span class="flex items-center gap-1 text-xs text-warm"><StarIcon class="h-3 w-3" />{{ g.points }}</span>
          </div>
          <div v-if="g.progress != null" class="h-1.5 overflow-hidden rounded-full bg-ink-800">
            <div class="h-full rounded-full bg-accent" :style="{ width: bar(g.progress) }" />
          </div>
          <p class="mt-0.5 text-xs text-ink-400">{{ g.hint }}</p>
        </li>
      </ul>
    </section>

    <section>
      <div class="mb-3 flex items-baseline justify-between">
        <h2 class="text-sm font-semibold">成就牆 <span class="text-xs font-normal text-ink-400">{{ badges.length }} 枚</span></h2>
        <span v-if="dividends.length" class="text-xs text-ink-400">另領過 {{ dividends.length }} 次股息（+{{ divStars }}）</span>
      </div>
      <ul v-if="badges.length" class="grid grid-cols-2 gap-2 sm:grid-cols-3">
        <li v-for="a in shown" :key="a.key" class="rounded-xl border border-ink-700/70 bg-ink-950/50 px-3 py-2.5" :title="a.detail ?? ''">
          <span class="rounded px-1.5 py-0.5 text-[10px] font-medium" :class="CAT[a.category].cls">{{ CAT[a.category].name }}</span>
          <p class="mt-1.5 text-sm font-medium leading-snug">{{ a.title }}</p>
          <p class="num text-[11px] text-ink-400">{{ a.earned_on }}</p>
        </li>
      </ul>
      <p v-else class="text-sm text-ink-400">打卡或收集到第一股，就會得到第一枚徽章。</p>
      <button v-if="badges.length > 12" class="mt-2 text-xs text-ink-400 hover:text-ink-100" @click="showAll = !showAll">
        {{ showAll ? '收合' : '顯示全部 ' + badges.length + ' 枚' }}
      </button>
      <p class="mt-3 text-xs text-ink-600">已獲得的成就不會因為賣出或修改紀錄而收回。</p>
    </section>

    <section v-if="recent.length">
      <h2 class="mb-2 text-sm font-semibold">最近獲得</h2>
      <ul class="grid gap-1 text-sm">
        <li v-for="a in recent" :key="a.key" class="flex justify-between gap-2">
          <span class="truncate">{{ a.title }}</span>
          <span class="num shrink-0 text-xs text-ink-400">{{ a.earned_on.slice(5) }}・<span class="text-warm">+{{ a.points }}</span></span>
        </li>
      </ul>
    </section>
  </article>
</template>
