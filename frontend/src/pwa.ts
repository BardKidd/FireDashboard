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

/**
 * iOS home-screen apps (black-translucent status bar) sometimes report a layout
 * viewport shorter than the screen, so `bottom: 0` floats above the real bottom
 * edge with an empty strip underneath. Measure the shortfall and expose it as
 * --ios-gap so fixed bottom UI can sit on the true edge. 0 everywhere else.
 */
export function trackStandaloneGap() {
  const nav = navigator as Navigator & { standalone?: boolean }
  const standalone = nav.standalone === true || window.matchMedia('(display-mode: standalone)').matches
  if (!standalone) return
  const update = () => {
    const portrait = window.matchMedia('(orientation: portrait)').matches
    const full = portrait ? Math.max(screen.width, screen.height) : Math.min(screen.width, screen.height)
    const gap = full - window.innerHeight
    document.documentElement.style.setProperty('--ios-gap', gap > 0 && gap < 120 ? `${gap}px` : '0px')
  }
  update()
  window.addEventListener('resize', update)
  window.addEventListener('orientationchange', () => window.setTimeout(update, 300))
}
