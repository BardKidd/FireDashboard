import { readFileSync } from 'node:fs'
import { defineConfig, type Plugin } from 'vite'
import vue from '@vitejs/plugin-vue'
import tailwindcss from '@tailwindcss/vite'

/** Emits sw.js with this build's id and file list, so each deploy precaches the
 *  new bundle and drops the old one. Production build only. */
function serviceWorker(): Plugin {
  return {
    name: 'fire-sw',
    apply: 'build',
    generateBundle(_, bundle) {
      const files = Object.keys(bundle).filter((f) => !f.endsWith('.html') && !f.endsWith('.map'))
      const statics = ['manifest.webmanifest', 'icons/icon.svg', 'icons/icon-192.png', 'icons/apple-touch-icon.png']
      const src = readFileSync(new URL('./pwa/sw.js', import.meta.url), 'utf8')
        .replace('__BUILD_ID__', Date.now().toString(36))
        .replace('__PRECACHE__', JSON.stringify([...files, ...statics].map((f) => '/' + f)))
      this.emitFile({ type: 'asset', fileName: 'sw.js', source: src })
    },
  }
}

export default defineConfig({
  plugins: [vue(), tailwindcss(), serviceWorker()],
  server: {
    host: true,
    port: 5173,
    proxy: {
      '/api': process.env.API_TARGET ?? 'http://localhost:8000',
    },
  },
})
