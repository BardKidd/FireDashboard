import { createApp } from 'vue'
import './style.css'
import App from './App.vue'
import { hideSplash, registerServiceWorker, trackStandaloneGap } from './pwa'

createApp(App).mount('#app')
registerServiceWorker()
trackStandaloneGap()
// Never leave the splash up if the first load hangs.
window.setTimeout(hideSplash, 12000)
