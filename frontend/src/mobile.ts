import { ref } from 'vue'

/** Phone layout (bottom tabs, sheets) below Tailwind's md breakpoint. */
const mq = window.matchMedia('(max-width: 767px)')
export const isMobile = ref(mq.matches)
mq.addEventListener('change', (e) => (isMobile.value = e.matches))

export type MobileTab = 'fire' | 'logs' | 'path' | 'book'
