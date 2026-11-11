import { createApp } from 'vue'
import './style.css'
import App from './App.vue'
import { hideSplash, registerServiceWorker } from './pwa'

createApp(App).mount('#app')
registerServiceWorker()
// Never leave the splash up if the first load hangs.
window.setTimeout(hideSplash, 12000)
