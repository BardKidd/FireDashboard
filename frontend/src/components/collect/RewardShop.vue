<script setup lang="ts">
import { ref } from 'vue'
import { api, type Game, type RewardRow } from '../../api'
import StarIcon from './StarIcon.vue'

const props = defineProps<{ game: Game }>()
const emit = defineEmits<{ changed: []; theme: [key: string] }>()

const form = ref({ name: '', cost: 100, repeatable: true })
const adding = ref(false)
const err = ref('')
const flash = ref('')

const SUGGEST = [
  { name: '一杯好咖啡', cost: 50, repeatable: true },
  { name: '吃一頓好的', cost: 300, repeatable: true },
  { name: '買一本想看的書', cost: 200, repeatable: true },
  { name: '週末小旅行', cost: 2000, repeatable: true },
]

async function run(fn: () => Promise<unknown>, ok = '') {
  err.value = ''
  try {
    await fn()
    flash.value = ok
    if (ok) window.setTimeout(() => (flash.value = ''), 4000)
    emit('changed')
  } catch (e) {
    err.value = (e as Error).message
  }
}

function add() {
  if (!form.value.name.trim() || !(form.value.cost > 0)) return
  run(async () => {
    await api.addReward({ ...form.value, name: form.value.name.trim(), cost: Math.round(form.value.cost), note: null })
    form.value = { name: '', cost: 100, repeatable: true }
    adding.value = false
  })
}

function redeem(r: RewardRow) {
  if (!window.confirm(`用 ${r.cost} 顆星星兌換「${r.name}」？`)) return
  run(() => api.redeem(r.id), `兌換成功：${r.name}，好好享受！`)
}

function remove(r: RewardRow) {
  if (!window.confirm(`刪除獎勵「${r.name}」？`)) return
  run(() => api.deleteReward(r.id))
}

function undo(id: number, name: string) {
  if (!window.confirm(`取消「${name}」這筆兌換並退回星星？`)) return
  run(() => api.undoRedemption(id))
}

function pickTheme(key: string) {
  run(() => api.gameSettings({ theme: key })).then(() => emit('theme', key))
}

const canAfford = (r: RewardRow) => props.game.stars.balance >= r.cost && (r.repeatable || !r.redeemed)
</script>

<template>
  <article class="card flex flex-col gap-5">
    <section>
      <div class="mb-1 flex items-center justify-between">
        <h2 class="text-sm font-semibold">獎勵兌換</h2>
        <span class="flex items-center gap-1 text-sm font-semibold text-warm"><StarIcon class="h-4 w-4" />{{ game.stars.balance.toLocaleString() }}</span>
      </div>
      <p class="mb-3 text-xs text-ink-400">替自己設定真實生活的獎勵。兌換只花星星，不會降低等級。</p>

      <ul v-if="game.rewards.length" class="grid gap-2">
        <li v-for="r in game.rewards" :key="r.id" class="flex items-center gap-3 rounded-xl border border-ink-700/70 bg-ink-950/50 px-3 py-2.5">
          <div class="min-w-0 flex-1">
            <p class="truncate text-sm font-medium">{{ r.name }}</p>
            <p class="flex items-center gap-1 text-xs text-ink-400">
              <StarIcon class="h-3 w-3 text-warm" />{{ r.cost.toLocaleString() }}
              <span v-if="!r.repeatable">・限一次{{ r.redeemed ? '（已兌換）' : '' }}</span>
            </p>
          </div>
          <button class="btn-primary py-1" :disabled="!canAfford(r)" @click="redeem(r)">兌換</button>
          <button class="btn p-1 text-ink-400 hover:text-ink-100" :aria-label="'刪除 ' + r.name" @click="remove(r)">
            <svg viewBox="0 0 20 20" class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M5 6h10M8 6V4h4v2M6.5 6l.7 10h5.6l.7-10" /></svg>
          </button>
        </li>
      </ul>
      <div v-else class="mb-1 flex flex-wrap gap-2">
        <button v-for="s in SUGGEST" :key="s.name" class="btn-ghost py-1 text-xs" @click="run(() => api.addReward({ ...s, note: null }))">
          ＋ {{ s.name }}・{{ s.cost }}
        </button>
      </div>

      <form v-if="adding" class="mt-3 grid gap-2 sm:grid-cols-[1fr_6rem_auto]" @submit.prevent="add">
        <label class="sr-only" for="rw-name">獎勵名稱</label>
        <input id="rw-name" v-model="form.name" class="input" placeholder="獎勵名稱，例如：買新耳機" maxlength="100" />
        <label class="sr-only" for="rw-cost">需要星星</label>
        <input id="rw-cost" v-model.number="form.cost" class="input" type="number" min="1" step="1" />
        <button class="btn-primary">新增</button>
        <label class="flex items-center gap-2 text-xs text-ink-400 sm:col-span-3">
          <input v-model="form.repeatable" type="checkbox" class="accent-[var(--color-accent)]" /> 可以重複兌換
        </label>
      </form>
      <button v-else class="btn-ghost mt-3 w-full" @click="adding = true">＋ 自訂獎勵</button>
      <p v-if="flash" class="mt-2 text-sm text-accent" role="status">{{ flash }}</p>
      <p v-if="err" class="mt-2 text-xs text-warm" role="alert">{{ err }}</p>

      <details v-if="game.redemptions.length" class="mt-3 text-xs text-ink-400">
        <summary class="cursor-pointer hover:text-ink-100">兌換紀錄（{{ game.redemptions.length }}）</summary>
        <ul class="mt-2 grid gap-1">
          <li v-for="x in game.redemptions" :key="x.id" class="flex justify-between gap-2">
            <span>{{ x.date }}・{{ x.name }}</span>
            <span class="flex gap-2"><span class="num">−{{ x.cost }}</span><button class="hover:text-ink-100" @click="undo(x.id, x.name)">取消</button></span>
          </li>
        </ul>
      </details>
    </section>

    <section>
      <h2 class="mb-1 text-sm font-semibold">主題色</h2>
      <p class="mb-3 text-xs text-ink-400">升級會解鎖新的主題色。</p>
      <div class="flex flex-wrap gap-2">
        <button
          v-for="t in game.themes"
          :key="t.key"
          class="flex items-center gap-2 rounded-lg border px-2.5 py-1.5 text-xs transition disabled:cursor-not-allowed"
          :class="game.settings.theme === t.key ? 'border-ink-300 text-ink-100' : 'border-ink-700 text-ink-400 hover:border-ink-600'"
          :disabled="!t.unlocked"
          :aria-pressed="game.settings.theme === t.key"
          @click="pickTheme(t.key)"
        >
          <span class="h-3.5 w-3.5 rounded-full" :style="{ background: t.unlocked ? t.accent : 'var(--color-ink-700)' }" />
          {{ t.name }}
          <span v-if="!t.unlocked" class="text-ink-600">Lv.{{ t.level }}</span>
        </button>
      </div>
    </section>
  </article>
</template>
