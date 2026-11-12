<script setup lang="ts">
import { reactive, ref } from 'vue'
import { api, type Config } from '../api'
import BaseModal from './BaseModal.vue'

const props = defineProps<{ config: Config }>()
const emit = defineEmits<{ close: []; saved: [] }>()

// Rates are edited as percentages.
const PCT_KEYS = ['swr', 'expected_nominal_return', 'inflation_rate', 'stress_drop', 'us_dividend_tax', 'tw_nhi_rate'] as const
const form = reactive<Record<string, number | boolean | string | null>>({ ...props.config })
for (const k of PCT_KEYS) form[k] = +((props.config[k] as number) * 100).toFixed(4)

const busy = ref(false)
const error = ref('')
const months = Array.from({ length: 12 }, (_, i) => i + 1)

async function save() {
  busy.value = true
  error.value = ''
  try {
    const out = { ...form } as unknown as Config
    for (const k of PCT_KEYS) (out as unknown as Record<string, number>)[k] = Number(form[k]) / 100
    if (out.fx_mode !== 'custom' && !out.custom_fx_rate) out.custom_fx_rate = null
    await api.saveConfig(out)
    emit('saved')
    emit('close')
  } catch (e) {
    error.value = (e as Error).message
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <BaseModal title="Coast FIRE 參數" wide @close="emit('close')">
    <form id="config-form" class="grid gap-6" @submit.prevent="save">
      <fieldset class="grid gap-3 sm:grid-cols-3">
        <legend class="label mb-2">你自己</legend>
        <label class="grid gap-1">
          <span class="label">出生年</span>
          <input v-model.number="form.birth_year" type="number" min="1900" max="2100" required class="input num" />
        </label>
        <label class="grid gap-1">
          <span class="label">出生月</span>
          <select v-model.number="form.birth_month" class="input">
            <option v-for="m in months" :key="m" :value="m">{{ m }} 月</option>
          </select>
        </label>
        <label class="grid gap-1">
          <span class="label">預計退休年齡</span>
          <input v-model.number="form.target_retire_age" type="number" min="18" max="100" required class="input num" />
        </label>
      </fieldset>

      <fieldset class="grid gap-3 sm:grid-cols-3">
        <legend class="label mb-2">退休目標與假設</legend>
        <label class="grid gap-1">
          <span class="label">退休年開銷（今日台幣）</span>
          <input v-model.number="form.annual_expense_twd" type="number" min="1" step="any" required class="input num" />
        </label>
        <label class="grid gap-1">
          <span class="label">安全提領率 SWR（%）</span>
          <input v-model.number="form.swr" type="number" step="any" min="0.1" max="99" required class="input num" />
        </label>
        <label class="grid gap-1">
          <span class="label">預期名目報酬（%／年）</span>
          <input v-model.number="form.expected_nominal_return" type="number" step="any" required class="input num" />
        </label>
        <label class="grid gap-1">
          <span class="label">通膨率（%／年）</span>
          <input v-model.number="form.inflation_rate" type="number" step="any" required class="input num" />
        </label>
        <label class="grid gap-1">
          <span class="label">每月定期定額（台幣）</span>
          <input v-model.number="form.monthly_contribution_twd" type="number" min="0" step="any" required class="input num" />
          <span class="text-xs text-ink-400">只填新投入的錢。貸款月付金不要算進來，在「負債」裡設定還清後轉為投入即可</span>
        </label>
        <label class="flex items-center gap-2 self-end pb-2 text-sm text-ink-300">
          <input v-model="form.contribution_indexed" type="checkbox" class="accent-[var(--color-accent)]" />
          每年隨通膨調升投入
        </label>
      </fieldset>

      <fieldset class="grid gap-3 sm:grid-cols-3">
        <legend class="label mb-2">匯率與壓力測試</legend>
        <label class="grid gap-1">
          <span class="label">計算達成率用的匯率</span>
          <select v-model="form.fx_mode" class="input">
            <option value="ma200">200 日均線（建議）</option>
            <option value="live">即時匯率</option>
            <option value="custom">自訂保守匯率</option>
          </select>
        </label>
        <label class="grid gap-1">
          <span class="label">自訂匯率</span>
          <input
            v-model.number="form.custom_fx_rate"
            type="number"
            step="any"
            min="1"
            class="input num"
            :disabled="form.fx_mode !== 'custom'"
            :required="form.fx_mode === 'custom'"
            placeholder="例如 30.5"
          />
        </label>
        <label class="grid gap-1">
          <span class="label">壓力測試大盤跌幅（%）</span>
          <input v-model.number="form.stress_drop" type="number" step="any" min="1" max="100" required class="input num" />
        </label>
      </fieldset>

      <fieldset class="grid gap-3 sm:grid-cols-3">
        <legend class="label mb-2">股息稅費</legend>
        <label class="grid gap-1">
          <span class="label">美股股息預扣稅（%）</span>
          <input v-model.number="form.us_dividend_tax" type="number" step="any" min="0" max="99" required class="input num" />
        </label>
        <label class="grid gap-1">
          <span class="label">二代健保補充保費（%）</span>
          <input v-model.number="form.tw_nhi_rate" type="number" step="any" min="0" max="99" required class="input num" />
        </label>
        <label class="grid gap-1">
          <span class="label">單筆股息達多少才扣（台幣）</span>
          <input v-model.number="form.tw_nhi_threshold" type="number" step="any" min="0" required class="input num" />
        </label>
      </fieldset>
      <p v-if="error" class="rounded-lg bg-amber-950/50 px-3 py-2 text-sm text-warm" role="alert">{{ error }}</p>
    </form>
    <template #footer>
      <button class="btn-ghost" @click="emit('close')">取消</button>
      <button class="btn-primary" form="config-form" type="submit" :disabled="busy">{{ busy ? '儲存中…' : '儲存' }}</button>
    </template>
  </BaseModal>
</template>
