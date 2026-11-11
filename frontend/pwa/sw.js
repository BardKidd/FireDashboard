/* FireDashboard service worker.
 * - App shell and hashed assets: cached so the app opens without a network.
 * - GET /api/*: network first; the last good answer is kept and served when offline,
 *   marked with x-offline + x-cached-at headers so the page can say how old it is.
 * - Anything else (POST/PUT/DELETE) goes straight to the network.
 */
// Filled in at build time by the pwa plugin in vite.config.ts.
const VERSION = '__BUILD_ID__'
const PRECACHE = __PRECACHE__
const SHELL = 'fire-shell-' + VERSION
const DATA = 'fire-data-v1'
const FONTS = 'fire-fonts-v1'

self.addEventListener('install', (e) => {
  e.waitUntil(caches.open(SHELL).then((c) => c.addAll(['/', ...PRECACHE])))
  self.skipWaiting()
})

self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches
      .keys()
      .then((keys) => Promise.all(keys.filter((k) => k.startsWith('fire-shell-') && k !== SHELL).map((k) => caches.delete(k))))
      .then(() => self.clients.claim()),
  )
})

async function networkFirstPage(req) {
  const cache = await caches.open(SHELL)
  try {
    const res = await fetch(req)
    if (res.ok) cache.put('/', res.clone())
    return res
  } catch {
    return (await cache.match('/')) || Response.error()
  }
}

async function cacheFirst(req, name) {
  const cache = await caches.open(name)
  const hit = await cache.match(req)
  if (hit) return hit
  const res = await fetch(req)
  if (res.ok || res.type === 'opaque') cache.put(req, res.clone())
  return res
}

async function api(req) {
  const cache = await caches.open(DATA)
  try {
    const res = await fetch(req)
    if (res.ok) {
      const headers = new Headers(res.headers)
      headers.set('x-cached-at', new Date().toISOString())
      const body = await res.clone().blob()
      cache.put(req, new Response(body, { status: res.status, statusText: res.statusText, headers }))
    }
    return res
  } catch (err) {
    const hit = await cache.match(req)
    if (!hit) throw err
    const headers = new Headers(hit.headers)
    headers.set('x-offline', '1')
    return new Response(await hit.blob(), { status: hit.status, statusText: hit.statusText, headers })
  }
}

self.addEventListener('fetch', (e) => {
  const req = e.request
  if (req.method !== 'GET') return
  const url = new URL(req.url)
  if (url.origin === location.origin) {
    if (url.pathname.startsWith('/api/')) return e.respondWith(api(req))
    if (req.mode === 'navigate') return e.respondWith(networkFirstPage(req))
    if (url.pathname.startsWith('/assets/') || url.pathname.startsWith('/icons/')) return e.respondWith(cacheFirst(req, SHELL))
    return
  }
  if (url.hostname === 'fonts.googleapis.com' || url.hostname === 'fonts.gstatic.com') e.respondWith(cacheFirst(req, FONTS))
})
