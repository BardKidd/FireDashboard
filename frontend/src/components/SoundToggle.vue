<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { playMusic, stopMusic } from '../music'

const KEY = 'fire.sound'
const on = ref(false)

function save(v: boolean) {
  try {
    localStorage.setItem(KEY, v ? 'on' : 'off')
  } catch {
    /* private mode */
  }
}

function toggle() {
  on.value = !on.value
  save(on.value)
  try {
    on.value ? playMusic() : stopMusic()
  } catch {
    on.value = false
  }
}

// Browsers only allow sound after a click or key press, so a saved "on"
// starts the music at the first interaction with the page.
function resumeOnInteraction() {
  window.removeEventListener('pointerdown', resumeOnInteraction)
  window.removeEventListener('keydown', resumeOnInteraction)
  if (on.value) {
    try {
      playMusic()
    } catch {
      on.value = false
    }
  }
}

onMounted(() => {
  let saved = false
  try {
    saved = localStorage.getItem(KEY) === 'on'
  } catch {
    /* private mode */
  }
  if (saved) {
    on.value = true
    window.addEventListener('pointerdown', resumeOnInteraction)
    window.addEventListener('keydown', resumeOnInteraction)
  }
})
onBeforeUnmount(() => {
  resumeOnInteraction()
  stopMusic()
})
</script>

<template>
  <button
    class="btn-ghost"
    :aria-pressed="on"
    :title="on ? '關掉背景音樂' : '播放背景音樂'"
    :aria-label="on ? '關掉背景音樂' : '播放背景音樂'"
    @click.stop="toggle"
  >
    <svg viewBox="0 0 24 24" class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
      <path d="M4 9h4l5-4v14l-5-4H4z" />
      <path v-if="on" d="M16.5 8.5a5 5 0 0 1 0 7M19 6a8.5 8.5 0 0 1 0 12" />
      <path v-else d="M17 9l4 6M21 9l-4 6" />
    </svg>
    <span class="hidden sm:inline">{{ on ? '音樂' : '靜音' }}</span>
  </button>
</template>
