<script setup lang="ts">
import { computed } from 'vue'
import type { Holdings, Position } from '../api'
import { pct, shares, wan } from '../format'
import BaseModal from './BaseModal.vue'

const props = defineProps<{ holdings?: Holdings }>()
const emit = defineEmits<{ close: []; pick: [p: Position]; add: []; addContract: [] }>()

const rows = computed(() => (props.holdings?.rows ?? []).filter((r) => !r.archived && !r.contract))
const label = (r: Position) => (r.market === 'CASH' ? r.name : r.symbol.replace(/\.TWO?$/, ''))
</script>

<template>
  <BaseModal title="添柴" @close="emit('close')">
    <p class="mb-3 text-sm text-ink-400">要記錄哪一檔的買賣？</p>
    <ul class="-mx-5 border-y border-ink-800">
      <li v-for="r in rows" :key="r.symbol" class="border-b border-ink-800 last:border-0">
        <button class="flex w-full items-center gap-3 px-5 py-3 text-left active:bg-ink-800/60 hover:bg-ink-800/40" @click="emit('pick', r)">
          <span class="h-8 w-2 flex-none rounded-full bg-[#7a5236]" :style="{ opacity: 0.35 + Math.min(1, r.weight * 2.2) }" aria-hidden="true" />
          <span class="min-w-0 flex-1">
            <span class="block font-medium">{{ label(r) }}</span>
            <span class="block truncate text-xs text-ink-400">{{ r.market === 'CASH' ? '存入或提出' : shares(r.shares, r.market) }}</span>
          </span>
          <span class="num text-right text-sm text-ink-300">{{ wan(r.value_twd) }}<span class="block text-xs text-ink-400">{{ pct(r.weight) }}</span></span>
        </button>
      </li>
    </ul>
    <div class="mt-4 grid grid-cols-2 gap-2">
      <button class="btn-primary py-2.5" @click="emit('add')">
        <svg viewBox="0 0 20 20" class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="2"><path d="M10 4v12M4 10h12" /></svg>
        新的標的
      </button>
      <button class="btn-ghost py-2.5" @click="emit('addContract')">＋ 約定存款</button>
    </div>
  </BaseModal>
</template>
