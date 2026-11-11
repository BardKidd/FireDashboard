<script setup lang="ts">
import { computed, ref } from 'vue'
import { api, type CheckinReport, type Game } from '../../api'
import InfoTip from '../../guide/InfoTip.vue'

const props = defineProps<{ game: Game }>()
const emit = defineEmits<{ checked: [r: CheckinReport] }>()

const note = ref('')
const busy = ref(false)
const err = ref('')

const WEEKS = 20
const done = computed(() => new Set(props.game.checkin.days))

/** Columns of weeks (Mon..Sun), oldest first, ending with the current week. */
const grid = computed(() => {
  const today = new Date(props.game.today + 'T00:00:00')
  const dow = (today.getDay() + 6) % 7
  const start = new Date(today)
  start.setDate(today.getDate() - dow - (WEEKS - 1) * 7)
  const cols: { iso: string; future: boolean; on: boolean; today: boolean }[][] = []
  for (let w = 0; w < WEEKS; w++) {
    const col = []
    for (let d = 0; d < 7; d++) {
      const x = new Date(start)
      x.setDate(start.getDate() + w * 7 + d)
      const iso = x.getFullYear() + '-' + String(x.getMonth() + 1).padStart(2, '0') + '-' + String(x.getDate()).padStart(2, '0')
      col.push({ iso, future: x > today, on: done.value.has(iso), today: iso === props.game.today })
    }
    cols.push(col)
  }
  return cols
})

async function go() {
  busy.value = true
  err.value = ''
  try {
    const r = await api.checkin(note.value.trim() || null)
    note.value = ''
    emit('checked', r)
  } catch (e) {
    err.value = (e as Error).message
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <article class="card flex flex-col gap-4">
    <div class="flex flex-wrap items-start justify-between gap-3">
      <div>
        <h2 class="text-sm font-semibold">每日打卡</h2>
        <p class="text-xs text-ink-400">每天一次 +10 星星。連續是以「週」計算，漏掉一天不會中斷。</p>
      </div>
      <div class="flex gap-4 text-right">
        <div>
          <p class="label">累積</p>
          <p class="num text-lg font-semibold">{{ game.checkin.total_days }} <span class="text-xs font-normal text-ink-400">天</span></p>
        </div>
        <div>
          <p class="label">連續<InfoTip k="streak" /></p>
          <p class="num text-lg font-semibold">{{ game.checkin.week_streak }} <span class="text-xs font-normal text-ink-400">週</span></p>
        </div>
      </div>
    </div>

    <div class="overflow-x-auto">
      <div class="flex w-max gap-[3px]" role="img" :aria-label="'近 ' + WEEKS + ' 週打卡紀錄，共 ' + game.checkin.total_days + ' 天'">
        <div v-for="(col, i) in grid" :key="i" class="flex flex-col gap-[3px]">
          <span
            v-for="c in col"
            :key="c.iso"
            :title="c.iso + (c.on ? ' 已打卡' : '')"
            class="h-3 w-3 rounded-[3px]"
            :class="[
              c.future ? 'bg-transparent' : c.on ? 'bg-accent' : 'bg-ink-800',
              c.today ? 'ring-1 ring-ink-300' : '',
            ]"
          />
        </div>
      </div>
    </div>

    <div v-if="game.checkin.today" class="flex items-center gap-3 rounded-xl bg-accent-soft/40 px-4 py-3 text-sm">
      <svg viewBox="0 0 20 20" class="h-5 w-5 shrink-0 text-accent" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 10.5l4 4 8-9" /></svg>
      <div>
        <p class="font-medium">今天已打卡</p>
        <p class="text-xs text-ink-300">{{ game.checkin.today_note || game.checkin.quote }}</p>
      </div>
    </div>
    <form v-else class="flex flex-col gap-2 sm:flex-row" @submit.prevent="go">
      <label class="sr-only" for="checkin-note">今天的一句話</label>
      <input id="checkin-note" v-model="note" class="input" maxlength="200" placeholder="想對未來的自己說一句話（選填）" />
      <button class="btn-primary shrink-0 px-5" :disabled="busy">{{ busy ? '打卡中…' : '今日打卡' }}</button>
    </form>
    <p v-if="err" class="text-xs text-warm" role="alert">{{ err }}</p>
  </article>
</template>
