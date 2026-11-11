/**
 * Hidden viewport readout for chasing iOS layout bugs on a real phone.
 * Tap the header flame 5 times quickly to toggle it; the choice is remembered.
 */
const KEY = 'fire.debug.vp'
let taps: number[] = []
let box: HTMLDivElement | null = null
let timer = 0

function read() {
  const vv = window.visualViewport
  const nav = document.querySelector('nav[aria-label="分頁"]')?.getBoundingClientRect()
  const nav2 = window.navigator as Navigator & { standalone?: boolean }
  const probe = document.createElement('div')
  probe.style.cssText = 'position:fixed;top:0;height:100vh;visibility:hidden'
  document.body.appendChild(probe)
  const vh = probe.getBoundingClientRect().height
  probe.style.paddingTop = 'env(safe-area-inset-top)'
  probe.style.height = '0'
  const sat = probe.getBoundingClientRect().height
  probe.remove()
  return [
    `standalone ${nav2.standalone ?? window.matchMedia('(display-mode: standalone)').matches}`,
    `screen ${screen.width}x${screen.height}`,
    `inner ${window.innerWidth}x${window.innerHeight}  100vh ${Math.round(vh)}`,
    `vv h ${vv ? Math.round(vv.height) : '-'} top ${vv ? Math.round(vv.offsetTop) : '-'}`,
    `doc h ${document.documentElement.clientHeight} scrollH ${document.documentElement.scrollHeight}`,
    `scrollY ${Math.round(window.scrollY)}  safeTop ${Math.round(sat)}`,
    `tabs top ${nav ? Math.round(nav.top) : '-'} bottom ${nav ? Math.round(nav.bottom) : '-'}`,
  ].join('\n')
}

function paint() {
  if (box) box.textContent = read()
}

function show(on: boolean) {
  try {
    if (on) localStorage.setItem(KEY, '1')
    else localStorage.removeItem(KEY)
  } catch {
    /* storage may be unavailable */
  }
  if (!on) {
    box?.remove()
    box = null
    window.clearInterval(timer)
    return
  }
  box = document.createElement('div')
  box.style.cssText =
    'position:fixed;left:8px;top:calc(env(safe-area-inset-top) + 56px);z-index:9999;pointer-events:none;' +
    'white-space:pre;font:11px/1.35 ui-monospace,monospace;color:#ffd36e;background:rgba(0,0,0,.8);padding:6px 8px;border-radius:8px'
  document.body.appendChild(box)
  paint()
  timer = window.setInterval(paint, 400)
}

export function onLogoTap() {
  const now = Date.now()
  taps = [...taps.filter((t) => now - t < 1500), now]
  if (taps.length >= 5) {
    taps = []
    show(!box)
  }
}

try {
  if (localStorage.getItem(KEY)) window.addEventListener('load', () => show(true))
} catch {
  /* ignore */
}
