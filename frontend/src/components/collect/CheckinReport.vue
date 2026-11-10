<script setup lang="ts">
import type { CheckinReport } from '../../api'
import { shares } from '../../format'
import BaseModal from '../BaseModal.vue'
import StarIcon from './StarIcon.vue'

defineProps<{ report: CheckinReport }>()
const emit = defineEmits<{ close: [] }>()
const label = (s: string) => s.replace(/\.TWO?$/, '')
const md = (d: string) => Number(d.slice(5, 7)) + '/' + Number(d.slice(8, 10))
</script>

<template>
  <BaseModal title="今日收集報告" @close="emit('close')">
    <div class="grid gap-5">
      <div class="text-center">
        <p class="num flex items-center justify-center gap-2 text-4xl font-bold text-warm">
          <StarIcon class="h-8 w-8" />+{{ report.points + report.bonus }}
        </p>
        <p class="mt-1 text-xs text-ink-400">
          打卡 +{{ report.points }}<template v-if="report.bonus">・新成就 +{{ report.bonus }}</template>
          ・累積 {{ report.total_days }} 天・連續 {{ report.week_streak }} 週
        </p>
      </div>

      <section v-if="report.new_achievements.length">
        <h3 class="label mb-2">解鎖成就</h3>
        <ul class="grid gap-1.5">
          <li v-for="a in report.new_achievements.slice(0, 8)" :key="a.key" class="flex items-center justify-between rounded-lg bg-ink-800 px-3 py-2 text-sm">
            <span>{{ a.title }}<span v-if="a.detail" class="ml-2 text-xs text-ink-400">{{ a.detail }}</span></span>
            <span class="num text-xs text-warm">+{{ a.points }}</span>
          </li>
          <li v-if="report.new_achievements.length > 8" class="text-xs text-ink-400">還有 {{ report.new_achievements.length - 8 }} 個，到成就牆查看</li>
        </ul>
      </section>

      <section v-if="report.since">
        <h3 class="label mb-2">自 {{ md(report.since) }} 上次打卡以來</h3>
        <ul v-if="report.collected.length" class="grid gap-1 text-sm">
          <li v-for="c in report.collected" :key="c.symbol">
            {{ label(c.symbol) }}
            <span :class="c.delta > 0 ? 'text-accent' : 'text-ink-300'">{{ c.delta > 0 ? '收集了' : '減少了' }} {{ shares(Math.abs(c.delta), c.market) }}</span>
          </li>
        </ul>
        <p v-else class="text-sm text-ink-300">股數沒有變動。什麼都沒做，也是長期投資的一部分。</p>
      </section>

      <section v-if="report.bargains.length">
        <h3 class="label mb-2">特價雷達</h3>
        <ul class="grid gap-1 text-sm">
          <li v-for="b in report.bargains" :key="b.symbol">
            {{ b.label }} 低於 60 日均，同樣金額可多收集 <span class="num text-accent">{{ (b.extra * 100).toFixed(1) }}%</span> 股數
          </li>
        </ul>
      </section>

      <p class="rounded-xl bg-ink-950/60 px-4 py-3 text-center text-sm text-ink-300">「{{ report.quote }}」</p>
    </div>
    <template #footer>
      <button class="btn-primary" @click="emit('close')">好</button>
    </template>
  </BaseModal>
</template>
