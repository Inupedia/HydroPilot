import { createApp, onMounted, watch } from 'vue'
import { createPinia } from 'pinia'
import Timeline from './components/Timeline.vue'
import { useNetworkStore } from './stores/network'
import { useScenarioStore } from './stores/scenario'
import { classifyObject } from './rendering/renderSpec'
import './style.css'

const App = {
  components: { Timeline },
  setup() {
    const network = useNetworkStore(); const scenario = useScenarioStore()
    onMounted(() => network.load())
    watch(() => network.states, (states) => scenario.setStates(states))
    return { network, scenario, classifyObject }
  },
  template: `<main><aside class="panel"><p class="eyebrow">HydroPilot v0.1</p><h1>Sacramento Water Network</h1><p class="note">Map-first viewer for directed river topology and water-engineering objects.</p><button @click="network.highlightDownstream('reach-001')">Highlight downstream chain</button><button @click="network.runScenario(2200)">Run release scenario</button></aside><section class="map"><div class="globe"><div v-for="obj in network.objects.slice(0, 18)" :key="obj.id" class="node" :class="[classifyObject(obj, network.highlightedIds, network.states).kind, classifyObject(obj, network.highlightedIds, network.states).status, {highlighted: network.highlightedIds.has(obj.id)}]"></div></div><Timeline/></section></main>`
}

createApp(App).use(createPinia()).mount('#app')
