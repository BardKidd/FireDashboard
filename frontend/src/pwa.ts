import { ref } from 'vue'

/** ISO time of the cached data being shown while offline; null when the data is live. */
export const offlineSince = ref<string | null>(null)

/** Called for every API response; the service worker marks answers it served from cache. */
export function noteResponse(res: Response) {
  if (res.headers.get('x-offline')) offlineSince.value = res.headers.get('x-cached-at') ?? offlineSince.value ?? ''
  else if (res.ok) offlineSince.value = null
}

export function registerServiceWorker() {
  // Service workers only run on https or localhost; on a plain-http LAN address this is a no-op.
  if (!import.meta.env.PROD || !('serviceWorker' in navigator) || !window.isSecureContext) return
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js').catch(() => {
      /* the app still works, just without offline support */
    })
  })
}

/** Fade out the kindling splash that index.html paints before the app loads. */
export function hideSplash() {
  const el = document.getElementById('kindle')
  if (!el || el.classList.contains('out')) return
  el.classList.add('out')
  window.setTimeout(() => el.remove(), 500)
}
