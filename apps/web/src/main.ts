import { createApp, onMounted } from 'vue'
import { createPinia } from 'pinia'
import { useNetworkStore } from './stores/network'
import { classifyObject } from './rendering/renderSpec'
import './style.css'

const App = {
  setup() {
    const network = useNetworkStore()
    onMounted(() => network.load())
    return { network, classifyObject }
  },
  template: `<main><aside class="panel"><p class="eyebrow">HydroPilot v0.1</p><h1>Sacramento Water Network</h1><p class="note">Map-first viewer for directed river topology and water-engineering objects.</p><button @click="network.highlightDownstream('reach-001')">Highlight downstream chain</button></aside><section class="map"><div class="globe"><div v-for="obj in network.objects.slice(0, 18)" :key="obj.id" class="node" :class="[classifyObject(obj, network.highlightedIds).kind, {highlighted: network.highlightedIds.has(obj.id)}]"></div></div></section></main>`
}

createApp(App).use(createPinia()).mount('#app')
