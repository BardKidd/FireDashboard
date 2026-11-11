<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { api, type BasketGoal, type CheckinReport, type Collect, type Game } from '../../api'
import { applyTheme } from '../../theme'
import BadgeWall from './BadgeWall.vue'
import BasketCard from './BasketCard.vue'
import CheckinCard from './CheckinCard.vue'
import CheckinReportModal from './CheckinReport.vue'
import CollectionGrid from './CollectionGrid.vue'
import PlayerCard from './PlayerCard.vue'
import RewardShop from './RewardShop.vue'
import ShareCurve from './ShareCurve.vue'

const game = ref<Game>()
const collect = ref<Collect>()
const report = ref<CheckinReport | null>(null)
const selected = ref<string | null>(null)
const err = ref('')

async function load() {
  try {
    const [g, c] = await Promise.all([api.game(), api.collect()])
    game.value = g
    collect.value = c
    applyTheme(g.themes, g.settings.theme)
    if (!selected.value || !c.holdings.some((h) => h.symbol === selected.value)) selected.value = c.holdings[0]?.symbol ?? null
    err.value = ''
  } catch (e) {
    err.value = (e as Error).message
  }
}

async function setGoal(g: BasketGoal) {
  await api.gameSettings({ basket_goal: g })
  await load()
}

function onChecked(r: CheckinReport) {
  report.value = r
  load()
}

const selectedRow = computed(() => collect.value?.holdings.find((h) => h.symbol === selected.value))
defineExpose({ load })
onMounted(load)
</script>

<template>
  <div>
    <p v-if="err" class="mb-4 rounded-xl border border-amber-800/60 bg-amber-950/40 px-4 py-3 text-sm text-warm" role="alert">{{ err }}</p>
    <div v-if="game && collect" class="grid gap-4">
      <div class="grid gap-4 lg:grid-cols-3">
        <PlayerCard :game="game" data-tour="player" />
        <CheckinCard :game="game" data-tour="checkin" @checked="onChecked" />
        <BasketCard :collect="collect" data-tour="basket" @goal="setGoal" />
      </div>
      <CollectionGrid :rows="collect.holdings" :selected="selected" @select="selected = $event" @changed="load" />
      <ShareCurve v-if="selectedRow && selectedRow.curve.length" :row="selectedRow" :today="collect.today" />
      <div class="grid gap-4 lg:grid-cols-2">
        <BadgeWall :game="game" data-tour="badges" />
        <RewardShop :game="game" data-tour="rewards" @changed="load" />
      </div>
    </div>
    <div v-else-if="!err" class="grid gap-4 lg:grid-cols-3" aria-busy="true">
      <div v-for="i in 3" :key="i" class="card h-56 animate-pulse" />
    </div>
    <CheckinReportModal v-if="report" :report="report" @close="report = null" />
  </div>
</template>
